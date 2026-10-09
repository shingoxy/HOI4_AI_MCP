"""Local Computer Use transport. Only atomic taps/clicks and capture are exposed.

The Node REPL pump uses the documented @oai/sky APIs. No native input injection,
launch, text entry, held input, or console/effect operation exists here.
"""

import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
from pathlib import Path
import queue
import secrets
import threading
import time
from uuid import uuid4

import numpy as np
from PIL import Image

from .guard import ActionError, Guard, WindowsProbe


class ComputerUseWorker:
    capabilities = {"capture": True, "click": True, "key_tap": True, "scroll": True,
                    "left_drag": False, "right_drag": False, "held_input": False}

    def __init__(self, hwnd: int, pid: int, *, endpoint_file: Path, probe=None):
        self.guard = Guard(probe or WindowsProbe(), hwnd, pid)
        self.commands = queue.Queue()
        self.pending = {}
        self.lock = threading.Lock()
        self.token = secrets.token_urlsafe(32)
        self.hwnd = hwnd
        self.last_capture = None
        self.last_capture_size = None
        self.last_poll = 0.0
        worker = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                if self.headers.get("Authorization") != f"Bearer {worker.token}":
                    self.send_error(403)
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 <= length <= 24_000_000:
                        raise ValueError("request_too_large")
                    data = json.loads(self.rfile.read(length) or b"{}")
                    if not isinstance(data, dict):
                        raise ValueError("invalid_request")
                    if self.path == "/next":
                        worker.last_poll = time.monotonic()
                        try:
                            reply = worker.commands.get(timeout=0.5)
                        except queue.Empty:
                            reply = None
                    elif self.path == "/permit":
                        with worker.lock:
                            active = data.get("id") in worker.pending
                        if not active or not worker.guard.active:
                            raise ActionError("expired_command")
                        worker.guard.check()
                        reply = {"allowed": True, "hwnd": worker.hwnd}
                    elif self.path == "/result":
                        with worker.lock:
                            waiter = worker.pending.get(data.get("id"))
                        if waiter:
                            try:
                                waiter.put_nowait(data)
                            except queue.Full:
                                raise ValueError("duplicate_result")
                        reply = {"accepted": bool(waiter)}
                    else:
                        self.send_error(404)
                        return
                    self.send_response(200)
                except (ValueError, ActionError) as exc:
                    reply = {"error": str(exc)}
                    self.send_response(409)
                body = json.dumps(reply).encode()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint_file = endpoint_file
        endpoint_file.parent.mkdir(parents=True, exist_ok=True)
        endpoint_file.write_text(json.dumps({
            "url": f"http://127.0.0.1:{self.server.server_port}",
            "token": self.token, "hwnd": hwnd,
        }), encoding="utf-8")

    def begin(self, timeout):
        self.last_capture = None
        self.guard.arm(timeout)

    def ready(self):
        return time.monotonic() - self.last_poll < 2.0

    def check(self):
        if not self.guard.active:
            raise ActionError("action_not_armed", "rejected")
        self.guard.check()

    def request(self, op, **args):
        self.check()
        ident, waiter = str(uuid4()), queue.Queue(maxsize=1)
        with self.lock:
            self.pending[ident] = waiter
        self.commands.put({"id": ident, "op": op, "args": args})
        try:
            end = time.monotonic() + 10
            while time.monotonic() < end:
                self.guard.check(heartbeat=False)
                try:
                    result = waiter.get(timeout=0.05)
                    self.check()
                    if result.get("error"):
                        raise ActionError("computer_use_error:" + result["error"])
                    return result.get("result")
                except queue.Empty:
                    pass
            raise ActionError("worker_timeout", "timed_out")
        finally:
            with self.lock:
                self.pending.pop(ident, None)

    def capture(self):
        result = self.request("capture")
        raw = base64.b64decode(result["image_base64"], validate=True)
        rgb = np.asarray(Image.open(BytesIO(raw)).convert("RGB"))
        self.last_capture = result["screenshot_id"]
        self.last_capture_size = (rgb.shape[1], rgb.shape[0])
        return rgb

    def click(self, point, *, button="left"):
        if self.last_capture is None:
            raise ActionError("observation_required")
        if button not in {"left", "right"}:
            raise ActionError("button_not_allowed", "rejected")
        self.request("click", point=list(point), screenshot_id=self.last_capture, button=button)
        self.last_capture = None

    def key(self, key):
        if key not in {"Escape", "w", "q", "y", "t", "r", "Return"}:
            raise ActionError("key_not_allowed", "rejected")
        self.request("key", key=key)
        self.last_capture = None

    def scroll(self, point, delta):
        if self.last_capture is None:
            raise ActionError("observation_required")
        if (isinstance(delta, bool) or not isinstance(delta, int) or
                delta == 0 or abs(delta) > 2400):
            raise ActionError("invalid_scroll", "rejected")
        self.request("scroll", point=list(point), delta=delta, screenshot_id=self.last_capture)
        self.last_capture = None

    def release(self):
        # sky.click/press_key are atomic down/up operations. There is deliberately
        # no API for holding an input; thus no executor-held input can survive.
        self.last_capture = None

    def end(self):
        self.release()
        self.guard.disarm()

    def close(self):
        self.end()
        self.guard.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=1)
        self.endpoint_file.unlink(missing_ok=True)
