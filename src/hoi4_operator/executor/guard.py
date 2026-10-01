"""Read-only Windows safety queries. This module never injects input."""

import ctypes
from ctypes import wintypes
from pathlib import Path
import threading
import time


class ActionError(RuntimeError):
    def __init__(self, reason: str, status: str = "failed"):
        super().__init__(reason)
        self.reason, self.status = reason, status


class WindowsProbe:
    def __init__(self):
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.user.GetForegroundWindow.restype = wintypes.HWND
        self.user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.user.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self.user.GetAsyncKeyState.restype = ctypes.c_short
        self.user.IsWindow.argtypes = [wintypes.HWND]
        self.user.IsHungAppWindow.argtypes = [wintypes.HWND]
        self.kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel.OpenProcess.restype = wintypes.HANDLE
        self.kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                         wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]

    def pid(self, hwnd):
        pid = wintypes.DWORD()
        self.user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value

    def check(self, hwnd: int, pid: int) -> str | None:
        if self.user.GetAsyncKeyState(0x7B) & 0x8001:
            return "emergency_stop"
        actual = wintypes.DWORD()
        self.user.GetWindowThreadProcessId(hwnd, ctypes.byref(actual))
        if not self.user.IsWindow(hwnd) or actual.value != pid:
            return "game_exited"
        handle = self.kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return "process_identity_unavailable"
        try:
            path, size = ctypes.create_unicode_buffer(32768), wintypes.DWORD(32768)
            if not self.kernel.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size)):
                return "process_identity_unavailable"
            if Path(path.value).name.lower() != "hoi4.exe":
                return "wrong_process"
        finally:
            self.kernel.CloseHandle(handle)
        if self.user.IsHungAppWindow(hwnd):
            return "game_hung"
        if self.user.GetForegroundWindow() != hwnd:
            return "loss_of_focus"
        return None


class Guard:
    """Latch F12/focus loss/deadline; independently poll every 20 ms while armed."""
    def __init__(self, probe, hwnd: int, pid: int, *, watchdog_seconds=12.0):
        self.probe, self.hwnd, self.pid = probe, hwnd, pid
        self.watchdog_seconds = watchdog_seconds
        self.active = False
        self.reason = None
        self.deadline = self.heartbeat = 0.0
        self.closed = threading.Event()
        self.thread = threading.Thread(target=self._watch, daemon=True)
        self.thread.start()

    def arm(self, timeout):
        if self.reason == "emergency_stop":
            raise ActionError(self.reason, "rejected")
        self.reason = self.probe.check(self.hwnd, self.pid)
        if self.reason:
            raise ActionError(self.reason, "rejected")
        self.deadline = time.monotonic() + timeout
        self.heartbeat = time.monotonic()
        self.active = True

    def check(self, *, heartbeat=True):
        now = time.monotonic()
        if self.active and not self.reason:
            self.reason = self.probe.check(self.hwnd, self.pid)
            if now >= self.deadline:
                self.reason = self.reason or "action_timeout"
            if now - self.heartbeat > self.watchdog_seconds:
                self.reason = self.reason or "watchdog_timeout"
        if self.reason:
            status = "timed_out" if "timeout" in self.reason else "failed"
            raise ActionError(self.reason, status)
        if heartbeat:
            self.heartbeat = now

    def _watch(self):
        while not self.closed.wait(0.02):
            if self.active:
                try:
                    self.check(heartbeat=False)
                except ActionError:
                    pass

    def disarm(self):
        self.active = False

    def close(self):
        self.disarm()
        self.closed.set()
        self.thread.join(timeout=1)
