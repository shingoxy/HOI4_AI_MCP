"""Bounded Windows right drag; all other input stays with the existing backend.

Reuses the reference worker's public SendInput mouse-event mapping. This is not
a desktop service: no capture, launch, focus, key or arbitrary-button API.
"""

import ctypes
from ctypes import wintypes
import threading
import time

from .guard import ActionError
from .map_profile import profile_for_size


class MouseInput(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class InputUnion(ctypes.Union):
    _fields_ = [("mi", MouseInput)]


class Input(ctypes.Structure):
    _anonymous_ = ("data",)
    _fields_ = [("type", wintypes.DWORD), ("data", InputUnion)]


class WindowsRightMouse:
    def __init__(self, hwnd):
        self.hwnd = hwnd
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.user.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int]
        self.user.SendInput.restype = wintypes.UINT
        self.user.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self.user.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
        self.user.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self.user.GetAsyncKeyState.restype = ctypes.c_short

    def prepare(self, start, end, capture_size=(2560, 1080)):
        rect = wintypes.RECT()
        if not self.user.GetClientRect(self.hwnd, ctypes.byref(rect)):
            raise ActionError("game_exited", "rejected")
        # Exact independently calibrated capture profile, never a projection.
        profile_for_size(capture_size)
        if (rect.right, rect.bottom) != capture_size:
            raise ActionError("unsupported_resolution", "rejected")
        if self.user.GetAsyncKeyState(0x02) & 0x8000:
            raise ActionError("mouse_already_held", "rejected")
        left, top, width, height = (self.user.GetSystemMetrics(n) for n in (76, 77, 78, 79))
        if width <= 1 or height <= 1:
            raise ActionError("map_target_unresolved", "rejected")
        points = []
        for x, y in (start, end):
            point = wintypes.POINT(x, y)
            if not self.user.ClientToScreen(self.hwnd, ctypes.byref(point)):
                raise ActionError("game_exited", "rejected")
            if not (left <= point.x < left + width and top <= point.y < top + height):
                raise ActionError("map_target_unresolved", "rejected")
            points.append((round((point.x-left)*65535/(width-1)),
                           round((point.y-top)*65535/(height-1))))
        return points

    def send(self, flags, point=(0, 0)):
        event = Input(type=0, mi=MouseInput(dx=point[0], dy=point[1], dwFlags=flags))
        if self.user.SendInput(1, ctypes.byref(event), ctypes.sizeof(Input)) != 1:
            raise ActionError("native_input_failed")

    def move(self, point): self.send(0x0001 | 0x8000 | 0x4000, point)
    def down(self): self.send(0x0008)
    def up(self): self.send(0x0010)


class NativeRightDragBackend:
    """Private adapter sharing the delegate's action guard and transaction lock."""
    def __init__(self, backend, *, mouse=None):
        self.backend = backend
        self.guard = backend.guard
        self.mouse = mouse or WindowsRightMouse(self.guard.hwnd)
        self._held = False
        self._lock = threading.Lock()

    @property
    def capabilities(self):
        return {**getattr(self.backend, "capabilities", {}), "right_drag": True}

    def __getattr__(self, name):
        return getattr(self.backend, name)

    def _release_mouse(self):
        # Release must work even when focus is lost or the guard has latched F12.
        # Do not move or press while releasing; never auto-activate another app.
        acquired = self._lock.acquire(timeout=.02)
        try:
            if self._held:
                self.mouse.up()
                # If native down/move stalled while holding the input lock, keep
                # ownership set so finally releases again after that call returns.
                if acquired:
                    self._held = False
        finally:
            if acquired:
                self._lock.release()

    def release(self):
        try:
            self._release_mouse()
        finally:
            self.backend.release()

    def right_drag(self, start, end):
        self.backend.check()
        if self.backend.last_capture is None:
            raise ActionError("observation_required", "rejected")
        size = getattr(self.backend, "last_capture_size", (2560, 1080))
        profile_for_size(size)
        for point in (start, end):
            if (not isinstance(point, tuple) or len(point) != 2 or
                    any(isinstance(v, bool) or not isinstance(v, int) for v in point) or
                    not (0 <= point[0] < size[0] and 0 <= point[1] < size[1])):
                raise ActionError("map_target_unresolved", "rejected")
        first, last = self.mouse.prepare(start, end, size)
        stop = threading.Event()
        interrupted = []

        def watch():
            while not stop.wait(.02):
                try:
                    self.guard.check(heartbeat=False)
                except ActionError as exc:
                    interrupted.append(exc)
                    try:
                        self._release_mouse()
                    except Exception:
                        pass  # finally/end attempts release again; no false success.
                    return

        monitor = threading.Thread(target=watch, daemon=True)
        monitor.start()
        try:
            with self._lock:
                self.backend.check()
                self.mouse.move(first)
                self.backend.check()
                self._held = True  # A failed down may already have reached Windows.
                self.mouse.down()
            for step in range(1, 13):
                time.sleep(.04)
                with self._lock:
                    self.backend.check()
                    if interrupted or not self._held:
                        raise interrupted[0] if interrupted else ActionError("input_interrupted")
                    point = tuple(round(a + (b-a)*step/12) for a, b in zip(first, last))
                    self.mouse.move(point)
            self.backend.check()
        finally:
            try:
                self.release()
            finally:
                stop.set()
                monitor.join(timeout=.1)

    def end(self):
        try:
            self.release()
        finally:
            self.backend.end()

    def close(self):
        try:
            self.release()
        finally:
            self.backend.close()
