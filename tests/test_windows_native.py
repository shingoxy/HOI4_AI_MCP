"""Independent native backend with fake Win32 boundary; never inject OS input."""

import ctypes
import threading
import time
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hoi4_operator.executor.guard import ActionError
from hoi4_operator.executor.native_win32 import NativeInput, WindowGeometry
from hoi4_operator.executor.windows_native import CAPTURE_PROFILES, WindowsNativeBackend


class Probe:
    reason = None
    def check(self, *_): return self.reason


class Desktop:
    geom = WindowGeometry(2048, 1280, 0, 0, 96, (0, 0, 2048, 1280))
    fail = None
    on_down = lambda self: None
    modifier = False
    external_held = False
    def __init__(self): self.events = []
    def geometry(self): return self.geom
    def target_at(self, *_): return True
    def capture(self, geometry):
        rgb = np.zeros((geometry.height, geometry.width, 3), dtype=np.uint8)
        rgb[0, 0] = (255, 64, 32)
        return rgb
    def modifiers_held(self): return self.modifier
    def held(self, *_): return self.external_held
    def move(self, point, geometry):
        self.events.append(("move", point))
        if self.fail == "move": raise RuntimeError("move failed")
    def button(self, code, down):
        self.events.append(("mouse", code, down))
        if down: self.on_down()
        if self.fail == ("down" if down else "up"): raise RuntimeError("input failed")
    def keyboard(self, code, down):
        self.events.append(("key", code, down))
        if down: self.on_down()
        if self.fail == ("down" if down else "up"): raise RuntimeError("input failed")
    def wheel(self, delta): self.events.append(("wheel", delta))


@pytest.fixture
def backend():
    probe, desktop = Probe(), Desktop()
    value = WindowsNativeBackend(1, 2, probe=probe, desktop=desktop)
    value.begin(5)
    value.capture()
    yield value
    desktop.fail = None
    value.close()


def test_capture_rgb_and_exact_profile_metadata(backend):
    rgb = backend.capture()
    assert tuple(rgb[0, 0]) == (255, 64, 32)
    assert backend.last_capture_size == (2048, 1280)
    assert backend.get_window_geometry()["capture_profile"]["backend"] == "windows_native_gdi"


def test_dpi_mapping_keeps_aspect_and_bounds():
    profile = CAPTURE_PROFILES[-1]
    assert profile.physical_point((100, 100)) == (125, 125)
    assert profile.physical_point((2047, 1279)) == (2559, 1599)
    raw = np.zeros((1600, 2560, 3), dtype=np.uint8)
    raw[:, :, 0] = 255
    rgb = profile.normalize(raw)
    assert rgb.shape == (1280, 2048, 3) and np.all(rgb[:, :, 0] == 255)


@pytest.mark.parametrize("operation", ["click", "key", "left_drag", "right_drag", "scroll"])
def test_primitives_and_no_held_input(backend, operation):
    calls = {"click": lambda: backend.click((100, 100)), "key": lambda: backend.key("w"),
             "left_drag": lambda: backend.left_drag((100, 100), (120, 130)),
             "right_drag": lambda: backend.right_drag((100, 100), (120, 130)),
             "scroll": lambda: backend.scroll((100, 100), 120)}
    calls[operation]()
    events = backend.desktop.events
    downs = [e for e in events if e[0] in {"mouse", "key"} and e[2]]
    ups = [e for e in events if e[0] in {"mouse", "key"} and not e[2]]
    assert len(downs) == len(ups) == (0 if operation == "scroll" else 1)
    assert not backend._owners and backend.last_capture is None
    if "drag" in operation:
        assert events[-2] == ("move", (120, 130))


@pytest.mark.parametrize("reason", ["loss_of_focus", "emergency_stop", "wrong_process", "game_exited"])
def test_pre_input_guard_refuses_without_events(backend, reason):
    backend.guard.probe.reason = reason
    with pytest.raises(ActionError, match=reason): backend.click((100, 100))
    assert not backend.desktop.events


@pytest.mark.parametrize("operation", ["click", "key", "right_drag", "left_drag"])
@pytest.mark.parametrize("reason", ["loss_of_focus", "emergency_stop", "action_timeout", "watchdog_timeout"])
def test_interruption_after_down_releases_and_stops(backend, operation, reason):
    def interrupt():
        if reason == "action_timeout": backend.guard.deadline = time.monotonic()-1
        elif reason == "watchdog_timeout": backend.guard.heartbeat = time.monotonic()-20
        else: backend.guard.probe.reason = reason
    backend.desktop.on_down = interrupt
    with pytest.raises(ActionError):
        if operation == "key": backend.key("q")
        elif operation == "click": backend.click((100, 100))
        else: getattr(backend, operation)((100, 100), (120, 130))
    assert not backend._owners
    assert backend.desktop.events[-1][2] is False
    assert len([e for e in backend.desktop.events if e[0] == "move"]) <= 1


@pytest.mark.parametrize("operation", ["click", "key", "right_drag"])
def test_unknown_down_outcome_still_releases(backend, operation):
    backend.desktop.fail = "down"
    with pytest.raises(RuntimeError):
        if operation == "key": backend.key("q")
        elif operation == "click": backend.click((100, 100))
        else: backend.right_drag((100, 100), (120, 130))
    assert not backend._owners and backend.desktop.events[-1][2] is False


def test_release_failure_keeps_owner_and_rejects_next_transaction(backend):
    backend.desktop.fail = "up"
    with pytest.raises(ActionError, match="native_release_failed"): backend.click((100, 100))
    assert backend._owners
    with pytest.raises(ActionError): backend.end()
    with pytest.raises(ActionError, match="backend_unavailable"): backend.begin(1)
    backend.desktop.fail = None
    backend.release()
    assert not backend._owners


def test_monitor_releases_while_down_call_is_stalled(backend):
    entered, leave = threading.Event(), threading.Event()
    def stall():
        entered.set()
        leave.wait(2)
    backend.desktop.on_down = stall
    failures = []
    def click():
        try: backend.click((100, 100))
        except ActionError as exc: failures.append(exc)
    thread = threading.Thread(target=click)
    thread.start()
    assert entered.wait(1)
    backend.guard.probe.reason = "emergency_stop"
    end = time.monotonic()+1
    while not any(e == ("mouse", "left", False) for e in backend.desktop.events) and time.monotonic() < end:
        time.sleep(.01)
    assert ("mouse", "left", False) in backend.desktop.events
    leave.set()
    thread.join(1)
    assert failures and not backend._owners


def test_changed_geometry_rejects_before_input(backend):
    backend.desktop.geom = WindowGeometry(2048, 1280, 1, 0, 96, (0, 0, 4096, 1280))
    with pytest.raises(ActionError, match="window_geometry_changed"): backend.click((100, 100))
    assert not backend.desktop.events


def test_unknown_size_or_dpi_cannot_be_normalized(backend):
    backend.desktop.geom = WindowGeometry(2560, 1600, 0, 0, 96, (0, 0, 2560, 1600))
    with pytest.raises(ActionError, match="unsupported_capture_profile"): backend.capture()
    assert backend.last_capture is None


def test_physical_native_panel_is_explicit_not_general_resolution_support(backend):
    from hoi4_operator.executor.ui_state import UIState
    from hoi4_operator.executor.windows_native import PHYSICAL_PROFILE
    backend.desktop.geom = WindowGeometry(2560, 1600, 0, 0, 120, (0, 0, 2560, 1600))
    backend._geometry = None
    ui = UIState(backend, None)
    rgb = ui.capture()
    assert rgb.shape == (1600, 2560, 3)
    assert backend.capture_profile == PHYSICAL_PROFILE
    assert ui.centered_box(rgb, "replace_title") == (1050, 615, 1500, 685)
    backend.capture_profile = None
    backend.capture = lambda: rgb
    with pytest.raises(ActionError, match="unsupported_resolution"): ui.capture()


@pytest.mark.parametrize("point", [(True, 1), (-1, 0), (2048, 1), (1, 1280), [1, 2], (1.0, 2)])
def test_bad_coordinates_rejected_without_input(backend, point):
    with pytest.raises(ActionError): backend.click(point)
    assert not backend.desktop.events


@pytest.mark.parametrize("key", ["Control_L+w", "F12", "F11", "~", "Windows"])
def test_keys_are_finite_executor_whitelist(backend, key):
    with pytest.raises(ActionError, match="key_not_allowed"): backend.key(key)
    assert not backend.desktop.events


def test_no_observation_modifiers_and_external_down_reject(backend):
    backend.last_capture = None
    with pytest.raises(ActionError, match="observation_required"): backend.click((1, 1))
    backend.capture()
    backend.desktop.modifier = True
    with pytest.raises(ActionError, match="input_already_held"): backend.click((1, 1))
    backend.desktop.modifier = False
    backend.desktop.external_held = True
    with pytest.raises(ActionError, match="input_already_held"): backend.click((1, 1))
    assert not backend._owners


def test_foreign_window_at_point_never_receives_input(backend):
    backend.desktop.target_at = lambda *_: False
    with pytest.raises(ActionError, match="target_not_visible"): backend.click((1, 1))
    assert not backend.desktop.events


def test_foreign_window_during_drag_releases_without_moving_into_it(backend):
    def change(): backend.desktop.target_at = lambda *_: False
    backend.desktop.on_down = change
    with pytest.raises(ActionError, match="target_not_visible"): backend.right_drag((1, 1), (10, 10))
    assert backend.desktop.events == [("move", (1, 1)), ("mouse", "right", True), ("mouse", "right", False)]


def test_blank_and_failed_capture_never_keep_observation(backend):
    backend.desktop.capture = lambda g: np.zeros((g.height, g.width, 3), dtype=np.uint8)
    with pytest.raises(ActionError, match="native_capture_blank"): backend.capture()
    assert backend.last_capture is None


def test_full_input_abi():
    assert ctypes.sizeof(NativeInput) == (40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)
    event = NativeInput(type=1)
    event.ki.wVk = 0x57
    assert event.type == 1 and event.ki.wVk == 0x57


def test_keyboard_uses_scan_codes_and_checked_mapping():
    from hoi4_operator.executor.native_win32 import WindowsDesktop
    desktop = WindowsDesktop.__new__(WindowsDesktop)
    class User:
        def MapVirtualKeyW(self, vk, mode): return 0x11 if vk == 0x57 and mode == 0 else 0
    desktop.user = User()
    events = []
    desktop._send = lambda event: events.append((event.type, event.ki.wVk, event.ki.wScan, event.ki.dwFlags))
    desktop.keyboard(0x57, True)
    desktop.keyboard(0x57, False)
    assert events == [(1, 0, 0x11, 8), (1, 0, 0x11, 10)]
    with pytest.raises(ActionError, match="native_key_unmapped"): desktop.keyboard(0, True)


def test_native_backend_imports_without_computer_use_worker():
    from pathlib import Path
    source = Path(__file__).parents[1]/"src/hoi4_operator/executor/windows_native.py"
    assert "ComputerUseWorker" not in source.read_text(encoding="utf-8")
    assert "@oai/sky" not in source.read_text(encoding="utf-8")


def test_invalid_backend_configuration(tmp_path):
    from hoi4_operator.mcp_server import create_server
    with pytest.raises(ValueError, match="input_backend"):
        create_server(tmp_path/"missing.log", input_backend="arbitrary")


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan"), True, "2"])
def test_action_deadline_cannot_be_disabled(backend, timeout):
    backend.end()
    with pytest.raises(ActionError, match="invalid_action_timeout"): backend.begin(timeout)
    assert not backend.guard.active


def test_real_native_physical_research_fixture_reuses_existing_reader(backend):
    from PIL import Image
    from hoi4_operator.executor.templates import Templates
    from hoi4_operator.executor.ui_state import UIState
    root = Path(__file__).resolve().parents[1]
    rgb = np.asarray(Image.open(root/"artifacts/phase5/captures/native-research-physical.png").convert("RGB"))
    backend.desktop.geom = WindowGeometry(2560, 1600, 0, 0, 120, (0, 0, 2560, 1600))
    backend._geometry = None
    backend.desktop.capture = lambda *_: rgb
    ui = UIState(backend, Templates(root/"artifacts/phase3a/templates"))
    observed = ui.open_panel("research")
    assert [ui.slot(observed, i) for i in range(4)] == ["empty"]*4
    assert not backend.desktop.events


def test_native_default_infantry_tree_has_separate_calibrated_template(backend):
    from PIL import Image
    from hoi4_operator.executor.templates import Templates
    from hoi4_operator.executor.ui_state import UIState
    from hoi4_operator.executor.windows_native import PHYSICAL_PROFILE
    from hoi4_operator.executor.catalog import BOXES
    root = Path(__file__).resolve().parents[1]
    rgb = np.asarray(Image.open(root/"artifacts/phase5/gate-20261006/captures/research-tree-nav.png").convert("RGB"))
    ordinary = Templates(root/"artifacts/phase3a/templates")
    ui = UIState(backend, ordinary, Templates(root/"artifacts/phase5/templates"))
    assert ordinary.find(rgb, "tech_bar", BOXES["category_bar"]) is None
    backend.capture_profile = PHYSICAL_PROFILE
    assert ui.found(rgb, "tech_bar", BOXES["category_bar"]) is not None
    assert ui.found(np.zeros_like(rgb), "tech_bar", BOXES["category_bar"]) is None
    backend.capture_profile = None
    assert ui.found(rgb, "tech_bar", BOXES["category_bar"]) is None


@pytest.mark.parametrize('filename', ['return-menu-cancelled.png','game-menu-closed.png','construction-stop-current.png'])
def test_native_known_modals_block_before_input(backend, filename):
    from PIL import Image
    from hoi4_operator.executor.templates import Templates
    from hoi4_operator.executor.ui_state import UIState
    root=Path(__file__).parents[1]
    rgb=np.asarray(Image.open(root/'artifacts/phase5/gate-20261006/captures'/filename).convert('RGB'))
    backend.desktop.geom=WindowGeometry(2560,1600,0,0,120,(0,0,2560,1600))
    backend._geometry=None
    backend.desktop.capture=lambda *_: rgb
    ui=UIState(backend,Templates(root/'artifacts/phase3a/templates'),Templates(root/'artifacts/phase5/templates'))
    with pytest.raises(ActionError,match='modal_blocked'):
        ui.capture()
    assert not backend.desktop.events
