"""Win32 marshalling, capture cleanup and coordinate tests with fake DLLs."""
from contextlib import nullcontext
import ctypes
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hoi4_operator.executor.guard import ActionError
from hoi4_operator.executor.native_win32 import WindowsDesktop, WindowGeometry


class User:
    def __init__(self, events): self.events = events
    def GetDC(self, hwnd): self.events.append(("getdc", hwnd)); return 1
    def ReleaseDC(self, hwnd, dc): self.events.append(("releasedc", hwnd, dc)); return 1


class GDI:
    failure = None
    def __init__(self, events): self.events = events
    def CreateCompatibleDC(self, dc): return 0 if self.failure == "memory" else 2
    def CreateCompatibleBitmap(self, dc, w, h): return 0 if self.failure == "bitmap" else 3
    def SelectObject(self, dc, value):
        self.events.append(("select", value))
        return 0 if self.failure == "select" else 4
    def BitBlt(self, *args):
        self.events.append(("blit", args))
        return 0 if self.failure == "blit" else 1
    def GetDIBits(self, dc, bitmap, start, height, address, info, flags):
        self.events.append(("dib",))
        # The bitmap is deselected before reading, top-down BGRA allocation.
        raw = (ctypes.c_ubyte * 8).from_address(address)
        raw[:] = [30, 20, 10, 255, 60, 50, 40, 255]
        return 0 if self.failure == "dib" else height
    def DeleteObject(self, value): self.events.append(("deletebitmap", value))
    def DeleteDC(self, value): self.events.append(("deletedc", value))


def desktop():
    result = WindowsDesktop.__new__(WindowsDesktop)
    events = []
    result.user, result.gdi = User(events), GDI(events)
    result.physical_pixels = nullcontext
    return result, events


def test_capture_channel_conversion_bitmap_deselection_and_cleanup():
    api, events = desktop()
    rgb = api.capture(WindowGeometry(2, 1, 7, 8, 96, (0, 0, 20, 20)))
    assert rgb.tolist() == [[[10, 20, 30], [40, 50, 60]]]
    assert events[events.index(("dib",))-1] == ("select", 4)
    blit = next(e[1] for e in events if e[0] == "blit")
    assert blit[6:8] == (7, 8)
    assert events[-3:] == [("deletebitmap", 3), ("deletedc", 2), ("releasedc", None, 1)]


@pytest.mark.parametrize("failure", ["memory", "bitmap", "select", "blit", "dib"])
def test_all_capture_failures_release_allocated_gdi_resources(failure):
    api, events = desktop()
    api.gdi.failure = failure
    with pytest.raises(ActionError, match="native_capture_failed"):
        api.capture(WindowGeometry(2, 1, 0, 0, 96, (0, 0, 20, 20)))
    assert ("releasedc", None, 1) in events
    if failure != "memory": assert ("deletedc", 2) in events
    if failure != "bitmap": assert ("deletebitmap", 3) in events


def test_send_input_short_write_is_never_success():
    api = WindowsDesktop.__new__(WindowsDesktop)
    class API:
        def SendInput(self, count, pointer, size): return 0
    api.user = API()
    with pytest.raises(ActionError, match="native_input_failed"): api.button("right", True)


def test_virtual_desktop_mapping_handles_negative_monitor_origin():
    api = WindowsDesktop.__new__(WindowsDesktop)
    events = []
    api._send = lambda event: events.append((event.mi.dx, event.mi.dy, event.mi.dwFlags))
    geometry = WindowGeometry(100, 100, -100, 20, 96, (-200, -100, 401, 201))
    api.move((0, 0), geometry)
    assert events == [(16384, 39321, 0xC001)]


def test_wheel_matches_computer_use_down_positive_convention():
    api = WindowsDesktop.__new__(WindowsDesktop)
    events = []
    api._send = lambda event: events.append((event.mi.mouseData, event.mi.dwFlags))
    api.wheel(120)
    assert events == [(0xFFFFFF88, 0x0800)]


def test_dpi_context_restored_after_exception():
    api = WindowsDesktop.__new__(WindowsDesktop)
    events = []
    class API:
        def SetThreadDpiAwarenessContext(self, value):
            events.append(value.value if isinstance(value, ctypes.c_void_p) else value)
            return 123
    api.user = API()
    with pytest.raises(ValueError):
        with api.physical_pixels(): raise ValueError("capture failure")
    assert events == [ctypes.c_void_p(-4).value, 123]
