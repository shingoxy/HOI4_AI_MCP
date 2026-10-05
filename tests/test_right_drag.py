"""Real guard with a fake mouse: no native input is injected by these tests."""

from pathlib import Path
import ctypes
import sys
import threading
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hoi4_operator.executor.guard import ActionError, Guard
from hoi4_operator.executor.right_drag import Input, NativeRightDragBackend, WindowsRightMouse


class Probe:
    reason = None
    def check(self, *_): return self.reason


class Backend:
    def __init__(self, timeout=2):
        self.probe = Probe()
        self.guard = Guard(self.probe, 1, 2)
        self.guard.arm(timeout)
        self.last_capture = "current-screenshot"
        self.releases = 0
    def check(self):
        if not self.guard.active:
            raise ActionError("action_not_armed", "rejected")
        self.guard.check()
    def release(self):
        self.last_capture = None
        self.releases += 1
    def end(self): self.release(); self.guard.disarm()
    def close(self): self.end(); self.guard.close()


class Mouse:
    def __init__(self):
        self.events = []
        self.fail = None
        self.on_down = lambda: None
    def prepare(self, start, end, capture_size=(2560,1080)): return start, end
    def move(self, point):
        self.events.append(("move", point))
        if self.fail == "move" and any(event[0] == "down" for event in self.events):
            raise RuntimeError("native move failed")
    def down(self):
        self.events.append(("down",))
        self.on_down()
        if self.fail == "down": raise RuntimeError("down outcome unknown")
    def up(self):
        self.events.append(("up",))
        if self.fail == "up": raise RuntimeError("release failed")


@pytest.fixture
def adapter():
    backend, mouse = Backend(), Mouse()
    result = NativeRightDragBackend(backend, mouse=mouse)
    yield result
    mouse.fail = None
    result.close()


def test_success_one_down_release_after_endpoint_and_delegate_invalidation(adapter):
    adapter.right_drag((1200,500), (1500,600))
    events = adapter.mouse.events
    assert events[0] == ("move", (1200,500))
    assert events[-2:] == [("move", (1500,600)), ("up",)]
    assert sum(event[0] == "down" for event in events) == 1
    assert sum(event[0] == "up" for event in events) == 1
    assert adapter.backend.last_capture is None and not adapter._held


@pytest.mark.parametrize("failure", ["down", "move"])
def test_exception_after_possible_down_always_releases(adapter, failure):
    adapter.mouse.fail = failure
    with pytest.raises(RuntimeError): adapter.right_drag((1200,500), (1500,600))
    assert adapter.mouse.events[-1] == ("up",)
    assert not adapter._held and adapter.backend.last_capture is None


@pytest.mark.parametrize("reason", ["emergency_stop", "loss_of_focus", "game_exited", "wrong_process"])
def test_stop_before_input_sends_no_native_event(adapter, reason):
    adapter.backend.probe.reason = reason
    with pytest.raises(ActionError, match=reason): adapter.right_drag((1200,500), (1500,600))
    assert not adapter.mouse.events


@pytest.mark.parametrize("reason", ["emergency_stop", "loss_of_focus", "action_timeout", "watchdog_timeout"])
def test_guard_stops_drag_and_releases_without_further_move(adapter, reason):
    def interrupt():
        if reason == "action_timeout": adapter.guard.deadline = time.monotonic()-1
        elif reason == "watchdog_timeout": adapter.guard.heartbeat = time.monotonic()-20
        else: adapter.backend.probe.reason = reason
    adapter.mouse.on_down = interrupt
    with pytest.raises(ActionError, match=reason): adapter.right_drag((1200,500), (1500,600))
    assert adapter.mouse.events == [("move", (1200,500)), ("down",), ("up",)]
    assert not adapter._held


def test_independent_monitor_releases_while_native_call_stalls(adapter):
    released = threading.Event()
    up = adapter.mouse.up
    def signal_release(): up(); released.set()
    adapter.mouse.up = signal_release
    def stall():
        adapter.backend.probe.reason = "loss_of_focus"
        assert released.wait(.4), "release waited for stalled native down"
    adapter.mouse.on_down = stall
    with pytest.raises(ActionError, match="loss_of_focus"):
        adapter.right_drag((1200,500), (1500,600))
    assert sum(event[0] == "up" for event in adapter.mouse.events) >= 2
    assert not adapter._held


def test_release_failure_not_hidden_and_end_retries_owned_release(adapter):
    adapter.mouse.fail = "up"
    with pytest.raises(RuntimeError, match="release failed"):
        adapter.right_drag((1200,500), (1500,600))
    assert adapter._held and adapter.backend.last_capture is None
    adapter.mouse.fail = None
    adapter.end()
    assert not adapter._held and not adapter.guard.active


@pytest.mark.parametrize("point", [(-1,5), (2560,10), (10,1080), (True,2), (1.1,2), [1,2], (1,)])
def test_invalid_segment_rejects_before_mouse_down(adapter, point):
    with pytest.raises(ActionError, match="map_target_unresolved"):
        adapter.right_drag(point, (1400,600))
    assert not adapter.mouse.events


def test_no_snapshot_or_disarmed_guard_rejects(adapter):
    adapter.backend.last_capture = None
    with pytest.raises(ActionError, match="observation_required"):
        adapter.right_drag((1200,500), (1500,600))
    adapter.guard.disarm()
    with pytest.raises(ActionError, match="action_not_armed"):
        adapter.right_drag((1200,500), (1500,600))
    assert not adapter.mouse.events


def test_native_mouse_input_layout_matches_windows_abi():
    assert ctypes.sizeof(Input) == (40 if ctypes.sizeof(ctypes.c_void_p)==8 else 28)


class WindowsCalls:
    size = (2560, 1080)
    held = False
    send_result = 1
    def __init__(self): self.bound = []
    def GetClientRect(self, hwnd, rect):
        self.bound.append(hwnd)
        rect._obj.right, rect._obj.bottom = self.size
        return 1
    def ClientToScreen(self, hwnd, point):
        self.bound.append(hwnd)
        # A negative-origin monitor, with the game on the second monitor.
        point._obj.x += 300
        return 1
    def GetAsyncKeyState(self, _): return 0x8000 if self.held else 0
    def GetSystemMetrics(self, index): return {76:-2560,77:0,78:5420,79:1440}[index]
    def SendInput(self, count, event, size):
        assert count==1 and size==ctypes.sizeof(Input) and event._obj.type==0
        return self.send_result


def windows_mouse():
    mouse=WindowsRightMouse.__new__(WindowsRightMouse)
    mouse.hwnd, mouse.user = 101, WindowsCalls()
    return mouse


def test_public_windows_mapping_uses_bound_client_and_virtual_desktop():
    mouse=windows_mouse()
    first,last=mouse.prepare((1200,500),(1500,600))
    assert mouse.user.bound == [101,101,101]
    assert first==(round(4060*65535/5419),round(500*65535/1439))
    assert last==(round(4360*65535/5419),round(600*65535/1439))


def test_wrong_client_size_and_existing_physical_hold_reject_before_down():
    mouse=windows_mouse()
    mouse.user.size=(2048,1280)
    with pytest.raises(ActionError,match="unsupported_resolution"):
        mouse.prepare((1200,500),(1500,600))
    mouse.user.size=(2560,1080)
    mouse.user.held=True
    with pytest.raises(ActionError,match="mouse_already_held"):
        mouse.prepare((1200,500),(1500,600))


def test_sendinput_failure_is_not_reported_as_success():
    mouse=windows_mouse()
    mouse.user.send_result=0
    with pytest.raises(ActionError,match="native_input_failed"): mouse.down()


def test_vendor_neutral_boundary_does_not_import_sky_or_expose_primitive_to_agent():
    source=(Path(__file__).resolve().parents[1]/"src/hoi4_operator/executor/right_drag.py").read_text()
    assert "@oai/sky" not in source and "SetForegroundWindow" not in source
    from hoi4_operator.operator import OperatorAPI
    assert OperatorAPI(None).execute("right_drag", {"start":[1,2],"end":[3,4]})["reason"]=="unsupported_target"
