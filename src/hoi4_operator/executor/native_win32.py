"""Private public-Win32 capture/input. No launch, refocus or model integration."""

from contextlib import contextmanager
import ctypes
from ctypes import wintypes
from dataclasses import dataclass

import numpy as np

from .guard import ActionError
from .right_drag import MouseInput


class KeyboardInput(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_size_t)]


class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class InputData(ctypes.Union):
    _fields_ = [("mi", MouseInput), ("ki", KeyboardInput), ("hi", HardwareInput)]


class NativeInput(ctypes.Structure):
    _anonymous_ = ("data",)
    _fields_ = [("type", wintypes.DWORD), ("data", InputData)]


class BitmapHeader(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


class BitmapInfo(ctypes.Structure):
    _fields_ = [("bmiHeader", BitmapHeader), ("bmiColors", wintypes.DWORD * 1)]


@dataclass(frozen=True)
class WindowGeometry:
    width: int
    height: int
    x: int
    y: int
    dpi: int
    desktop: tuple[int, int, int, int]


class WindowsDesktop:
    def __init__(self, hwnd):
        self.hwnd = hwnd
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.gdi = ctypes.WinDLL("gdi32", use_last_error=True)
        signatures = {
            "GetClientRect": ([wintypes.HWND, ctypes.POINTER(wintypes.RECT)], wintypes.BOOL),
            "ClientToScreen": ([wintypes.HWND, ctypes.POINTER(wintypes.POINT)], wintypes.BOOL),
            "GetDpiForWindow": ([wintypes.HWND], wintypes.UINT),
            "IsIconic": ([wintypes.HWND], wintypes.BOOL),
            "GetDC": ([wintypes.HWND], wintypes.HDC),
            "ReleaseDC": ([wintypes.HWND, wintypes.HDC], ctypes.c_int),
            "SetThreadDpiAwarenessContext": ([ctypes.c_void_p], ctypes.c_void_p),
            "GetAsyncKeyState": ([ctypes.c_int], ctypes.c_short),
            "MapVirtualKeyW": ([wintypes.UINT, wintypes.UINT], wintypes.UINT),
            "WindowFromPoint": ([wintypes.POINT], wintypes.HWND),
            "GetAncestor": ([wintypes.HWND, wintypes.UINT], wintypes.HWND),
            "SendInput": ([wintypes.UINT, ctypes.POINTER(NativeInput), ctypes.c_int], wintypes.UINT),
        }
        for name, (args, result) in signatures.items():
            func = getattr(self.user, name)
            func.argtypes, func.restype = args, result
        signatures = {
            "CreateCompatibleDC": ([wintypes.HDC], wintypes.HDC),
            "CreateCompatibleBitmap": ([wintypes.HDC, ctypes.c_int, ctypes.c_int], wintypes.HBITMAP),
            "SelectObject": ([wintypes.HDC, wintypes.HANDLE], wintypes.HANDLE),
            "DeleteObject": ([wintypes.HANDLE], wintypes.BOOL),
            "DeleteDC": ([wintypes.HDC], wintypes.BOOL),
            "BitBlt": ([wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                        wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD], wintypes.BOOL),
            "GetDIBits": ([wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
                           ctypes.c_void_p, ctypes.POINTER(BitmapInfo), wintypes.UINT], ctypes.c_int),
        }
        for name, (args, result) in signatures.items():
            func = getattr(self.gdi, name)
            func.argtypes, func.restype = args, result

    @contextmanager
    def physical_pixels(self):
        old = self.user.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
        if not old:
            raise ActionError("dpi_context_unavailable", "rejected")
        try:
            yield
        finally:
            if not self.user.SetThreadDpiAwarenessContext(old):
                raise ActionError("dpi_context_restore_failed")

    def geometry(self):
        with self.physical_pixels():
            rect, origin = wintypes.RECT(), wintypes.POINT()
            if (self.user.IsIconic(self.hwnd) or
                    not self.user.GetClientRect(self.hwnd, ctypes.byref(rect)) or
                    not self.user.ClientToScreen(self.hwnd, ctypes.byref(origin))):
                raise ActionError("game_window_unavailable", "rejected")
            desktop = tuple(self.user.GetSystemMetrics(i) for i in (76, 77, 78, 79))
            width, height, dpi = rect.right, rect.bottom, self.user.GetDpiForWindow(self.hwnd)
            left, top, dw, dh = desktop
            if (not 0 < width <= 8192 or not 0 < height <= 8192 or not dpi or
                    dw <= 1 or dh <= 1 or origin.x < left or origin.y < top or
                    origin.x + width > left + dw or origin.y + height > top + dh):
                raise ActionError("invalid_client_geometry", "rejected")
            return WindowGeometry(width, height, origin.x, origin.y, dpi, desktop)

    def capture(self, geometry):
        # Desktop DC avoids legacy game's DPI-virtualized own DC. Foreground
        # is checked by the backend before/after this call; occlusion is visible.
        with self.physical_pixels():
            dc = memory = bitmap = old = None
            try:
                dc = self.user.GetDC(None)
                if not dc:
                    raise ActionError("native_capture_failed")
                memory = self.gdi.CreateCompatibleDC(dc)
                bitmap = self.gdi.CreateCompatibleBitmap(dc, geometry.width, geometry.height)
                if not memory or not bitmap:
                    raise ActionError("native_capture_failed")
                old = self.gdi.SelectObject(memory, bitmap)
                if not old or old == ctypes.c_void_p(-1).value:
                    old = None
                    raise ActionError("native_capture_failed")
                if not self.gdi.BitBlt(memory, 0, 0, geometry.width, geometry.height,
                                       dc, geometry.x, geometry.y, 0x00CC0020 | 0x40000000):
                    raise ActionError("native_capture_failed")
                self.gdi.SelectObject(memory, old)
                old = None
                info = BitmapInfo(bmiHeader=BitmapHeader(
                    biSize=ctypes.sizeof(BitmapHeader), biWidth=geometry.width,
                    biHeight=-geometry.height, biPlanes=1, biBitCount=32))
                raw = np.empty((geometry.height, geometry.width, 4), dtype=np.uint8)
                if self.gdi.GetDIBits(dc, bitmap, 0, geometry.height, raw.ctypes.data,
                                      ctypes.byref(info), 0) != geometry.height:
                    raise ActionError("native_capture_failed")
                return raw[:, :, 2::-1].copy()  # top-down BGRA -> RGB, ignore alpha
            finally:
                if old:
                    self.gdi.SelectObject(memory, old)
                if bitmap:
                    self.gdi.DeleteObject(bitmap)
                if memory:
                    self.gdi.DeleteDC(memory)
                if dc:
                    self.user.ReleaseDC(None, dc)

    def held(self, kind, code):
        vk = {"left": 1, "right": 2}[code] if kind == "mouse" else code
        return bool(self.user.GetAsyncKeyState(vk) & 0x8000)

    def modifiers_held(self):
        return any(self.user.GetAsyncKeyState(vk) & 0x8000 for vk in (0x10, 0x11, 0x12, 0x5B, 0x5C))

    def target_at(self, point, geometry):
        with self.physical_pixels():
            hwnd = self.user.WindowFromPoint(wintypes.POINT(geometry.x+point[0], geometry.y+point[1]))
            return bool(hwnd and self.user.GetAncestor(hwnd, 2) == self.hwnd)

    def _send(self, event):
        if self.user.SendInput(1, ctypes.byref(event), ctypes.sizeof(NativeInput)) != 1:
            raise ActionError("native_input_failed")

    def move(self, point, geometry):
        left, top, width, height = geometry.desktop
        x, y = point
        absolute = (round((geometry.x+x-left)*65535/(width-1)),
                    round((geometry.y+y-top)*65535/(height-1)))
        self._send(NativeInput(type=0, mi=MouseInput(
            dx=absolute[0], dy=absolute[1], dwFlags=0x0001 | 0x8000 | 0x4000)))

    def button(self, button, down):
        flags = {("left", True): 2, ("left", False): 4,
                 ("right", True): 8, ("right", False): 16}
        self._send(NativeInput(type=0, mi=MouseInput(dwFlags=flags[button, down])))

    def keyboard(self, vk, down):
        scan = self.user.MapVirtualKeyW(vk, 0)
        if not scan:
            raise ActionError("native_key_unmapped")
        self._send(NativeInput(type=1, ki=KeyboardInput(wScan=scan, dwFlags=8 | (0 if down else 2))))

    def wheel(self, delta):
        # Same public sign convention as Computer Use: positive means down.
        self._send(NativeInput(type=0, mi=MouseInput(mouseData=(-delta) & 0xFFFFFFFF, dwFlags=0x0800)))
