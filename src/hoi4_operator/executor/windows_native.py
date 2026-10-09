"""Independent guarded backend; semantic services cannot access its primitives."""

from dataclasses import asdict, dataclass
import math
import json
from pathlib import Path
import threading
import time
from uuid import uuid4

import numpy as np
from PIL import Image

from .guard import ActionError, Guard, WindowsProbe
from .native_win32 import WindowsDesktop


@dataclass(frozen=True)
class CaptureProfile:
    name: str
    client_width: int
    client_height: int
    dpi: int
    capture_width: int
    capture_height: int
    template_set: str
    backend: str = "windows_native_gdi"
    offset: tuple[int, int] = (0, 0)

    def matches(self, geometry):
        return (geometry.width, geometry.height, geometry.dpi) == (
            self.client_width, self.client_height, self.dpi)

    def normalize(self, rgb):
        if rgb.dtype != np.uint8 or rgb.shape != (self.client_height, self.client_width, 3):
            raise ActionError("native_capture_failed")
        size = self.capture_width, self.capture_height
        if size == (self.client_width, self.client_height):
            return rgb
        return np.asarray(Image.fromarray(rgb).resize(size, Image.Resampling.BILINEAR)).copy()

    def physical_point(self, point):
        if (not isinstance(point, tuple) or len(point) != 2 or
                any(isinstance(v, bool) or not isinstance(v, int) for v in point) or
                not (0 <= point[0] < self.capture_width and 0 <= point[1] < self.capture_height)):
            raise ActionError("invalid_input_point", "rejected")
        return (min(self.client_width-1, round(point[0]*self.client_width/self.capture_width)),
                min(self.client_height-1, round(point[1]*self.client_height/self.capture_height)))


# Exact calibrated spaces only, never infer an arbitrary aspect-ratio conversion.
CAPTURE_PROFILES = (
    CaptureProfile("GER_2560x1080_DPI96", 2560, 1080, 96, 2560, 1080, "phase3a/phase3/phase4"),
    CaptureProfile("GER_2048x1280_DPI96", 2048, 1280, 96, 2048, 1280, "phase4/offensive2048"),
    CaptureProfile("GER_2560x1600_DPI120", 2560, 1600, 120, 2048, 1280, "phase4/offensive2048"),
)
PHYSICAL_PROFILE = CaptureProfile("GER_2560x1600_DPI120_PHYSICAL", 2560, 1600, 120,
                                 2560, 1600, "phase3a/phase3 + phase5 physical seven-action gate; limited targets")

KEYS = {"Escape": 0x1B, "Return": 0x0D, "w": 0x57, "q": 0x51,
        "y": 0x59, "t": 0x54, "r": 0x52, "space": 0x20}


class WindowsNativeBackend:
    capabilities = {"capture": True, "click": True, "key_tap": True, "scroll": True,
                    "left_drag": True, "right_drag": True, "held_input": False}

    def __init__(self, hwnd, pid, *, probe=None, desktop=None, capture_space="physical", audit_directory=None):
        if capture_space not in {"physical", "legacy"}:
            raise ValueError("capture_space must be physical or legacy")
        self.capture_space = capture_space
        self.audit_directory = Path(audit_directory) if audit_directory else None
        self._trace = None
        self.desktop = desktop or WindowsDesktop(hwnd)
        self.guard = Guard(probe or WindowsProbe(), hwnd, pid)
        self.last_capture = None
        self.last_capture_size = None
        self.capture_profile = None
        self._geometry = None
        self._owners = set()
        self._input_lock = threading.Lock()
        self._stop = threading.Event()
        self._monitor = None
        self._closed = False

    def ready(self):
        return not self._closed and not self._owners

    def begin(self, timeout):
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ActionError("invalid_action_timeout", "rejected")
        if self._closed or self._owners or self.guard.active:
            raise ActionError("backend_unavailable", "rejected")
        self.last_capture = None
        self._geometry = None
        self.guard.arm(timeout)
        self._trace = {"trace_id": str(uuid4()), "backend": "WindowsNativeBackend",
                       "capture_method": "GDI_BitBlt_RGB", "pump": "OFF", "events": []}
        self._stop.clear()
        self._monitor = threading.Thread(target=self._watch, daemon=True)
        self._monitor.start()

    def _watch(self):
        while not self._stop.wait(.02):
            try:
                self.guard.check(heartbeat=False)
            except ActionError:
                try:
                    self.release()
                except Exception:
                    pass  # Retain ownership; finally/end must attempt release again.
                return

    def check(self):
        if not self.guard.active:
            raise ActionError("action_not_armed", "rejected")
        self.guard.check()

    def _current(self):
        self.check()
        geometry = self.desktop.geometry()
        profile = next((p for p in CAPTURE_PROFILES if p.matches(geometry)), None)
        if self.capture_space == "physical" and PHYSICAL_PROFILE.matches(geometry):
            profile = PHYSICAL_PROFILE
        if profile is None:
            raise ActionError("unsupported_capture_profile", "rejected")
        return geometry, profile

    def _validate_input(self):
        geometry, profile = self._current()
        if self._geometry is not None and geometry != self._geometry:
            self.last_capture = None
            raise ActionError("window_geometry_changed", "rejected")
        if self.desktop.modifiers_held():
            raise ActionError("input_already_held", "rejected")
        return geometry, profile

    def get_window_geometry(self):
        geometry, profile = self._current()
        return {**asdict(geometry), "capture_profile": asdict(profile)}

    def capture(self):
        started = time.monotonic()
        self.last_capture = None
        geometry, profile = self._current()
        rgb = profile.normalize(self.desktop.capture(geometry))
        self.check()
        if self.desktop.geometry() != geometry:
            raise ActionError("window_geometry_changed", "rejected")
        if rgb.max() == rgb.min():
            raise ActionError("native_capture_blank")
        self._geometry, self.capture_profile = geometry, profile
        self.last_capture_size = (profile.capture_width, profile.capture_height)
        self.last_capture = object()
        self._record("capture", size=list(self.last_capture_size), profile=asdict(profile),
                     duration_ms=round((time.monotonic()-started)*1000))
        return rgb

    def _record(self, op, **fields):
        if self._trace is not None:
            self._trace["events"].append({"op": op, **fields})

    def _point(self, point):
        if self.last_capture is None:
            raise ActionError("observation_required", "rejected")
        geometry, profile = self._validate_input()
        physical = profile.physical_point(point)
        if not self.desktop.target_at(physical, geometry):
            raise ActionError("target_not_visible", "rejected")
        return physical, geometry

    def _down(self, owner):
        kind, code = owner
        if (self.desktop.held(kind, code) or
                any(self.desktop.held("mouse", button) for button in ("left", "right"))):
            raise ActionError("input_already_held", "rejected")
        self._owners.add(owner)  # Failed SendInput may have already reached Windows.
        self._record("down_attempt", kind=kind, code=code, primitive="SendInput")
        if kind == "mouse":
            self.desktop.button(code, True)
        else:
            self.desktop.keyboard(code, True)

    def release(self):
        # Releases bypass focus/deadline checks, but never move or press.
        acquired = self._input_lock.acquire(timeout=.02)
        failures = []
        try:
            for kind, code in tuple(self._owners):
                try:
                    if kind == "mouse":
                        self.desktop.button(code, False)
                    else:
                        self.desktop.keyboard(code, False)
                    if acquired:
                        self._owners.discard((kind, code))
                    self._record("release", kind=kind, code=code, success=True)
                except Exception as exc:
                    self._record("release", kind=kind, code=code, success=False)
                    failures.append(exc)
            self.last_capture = None
            if failures:
                raise ActionError("native_release_failed") from failures[0]
        finally:
            if acquired:
                self._input_lock.release()

    def _settle(self, seconds=.5):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.check()
            time.sleep(.02)

    def _move(self, point, geometry):
        self._validate_input()
        if not self.desktop.target_at(point, geometry):
            raise ActionError("target_not_visible")
        self.desktop.move(point, geometry)

    def click(self, point, *, button="left"):
        if button not in {"left", "right"}:
            raise ActionError("button_not_allowed", "rejected")
        physical, geometry = self._point(point)
        self._record("click", point=list(point), physical_point=list(physical), button=button, primitive="SendInput.MOUSEINPUT")
        try:
            with self._input_lock:
                self._validate_input()
                self._move(physical, geometry)
                self._validate_input()
                self.last_capture = None
                self._down(("mouse", button))
            self._settle(.06)
        finally:
            self.release()
        self._settle()

    def key(self, key):
        if key not in KEYS:
            raise ActionError("key_not_allowed", "rejected")
        self._record("key", key=key, primitive="SendInput.KEYBDINPUT_SCANCODE")
        try:
            with self._input_lock:
                self._validate_input()
                self.last_capture = None
                self._down(("key", KEYS[key]))
            self._settle(.06)
        finally:
            self.release()
        self._settle()

    key_tap = key

    def scroll(self, point, delta):
        if isinstance(delta, bool) or not isinstance(delta, int) or delta == 0 or abs(delta) > 2400:
            raise ActionError("invalid_scroll", "rejected")
        physical, geometry = self._point(point)
        self._record("scroll", delta=delta, primitive="SendInput.MOUSEINPUT_WHEEL")
        with self._input_lock:
            self._validate_input()
            self._move(physical, geometry)
            self._validate_input()
            self.last_capture = None
            self.desktop.wheel(delta)
        self._settle()

    def _drag(self, start, end, button):
        first, geometry = self._point(start)
        last, _ = self._point(end)
        self._record(button+"_drag", start=list(start), end=list(end), primitive="SendInput.MOUSEINPUT")
        try:
            with self._input_lock:
                self._validate_input()
                self._move(first, geometry)
                self._validate_input()
                self.last_capture = None
                self._down(("mouse", button))
            for step in range(1, 13):
                self._settle(.04)
                with self._input_lock:
                    self._validate_input()
                    if ("mouse", button) not in self._owners:
                        raise ActionError("input_interrupted")
                    point = tuple(round(a + (b-a)*step/12) for a, b in zip(first, last))
                    self._move(point, geometry)
        finally:
            self.release()
        self._settle()

    def left_drag(self, start, end):
        self._drag(start, end, "left")

    def right_drag(self, start, end):
        self._drag(start, end, "right")

    def end(self):
        try:
            self.release()
        finally:
            self._stop.set()
            self.guard.disarm()
            if self._monitor:
                self._monitor.join(timeout=.2)
            if self._trace is not None and self.audit_directory:
                self.audit_directory.mkdir(parents=True, exist_ok=True)
                self._trace.update(guard_reason=self.guard.reason, held_input_remaining=bool(self._owners))
                path = self.audit_directory / (self._trace["trace_id"]+".json")
                path.write_text(json.dumps(self._trace, indent=2), encoding="utf-8")
            self._trace = None

    def close(self):
        try:
            self.end()
        finally:
            self._closed = True
            self.guard.close()
