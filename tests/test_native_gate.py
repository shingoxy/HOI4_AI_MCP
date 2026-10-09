"""Clock safety tests use synthetic RGB and no Windows input."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from PIL import Image
import pytest

spec = importlib.util.spec_from_file_location("native_gate", Path(__file__).parents[1]/"scripts/native_gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class Backend:
    def __init__(self, image):
        self.image, self.events, self.closed = image.copy(), [], False
        self.running = False
        self.desktop = SimpleNamespace(held=lambda *_: False)
    def begin(self, timeout): pass
    def check(self): pass
    def capture(self):
        if self.running:
            x0, y0, _, _ = gate.BoundedClock.DATE
            self.image[y0:y0+4, x0:x0+6] = 255-self.image[y0:y0+4, x0:x0+6]
        return self.image.copy()
    def key(self, key):
        self.events.append(key)
        if key == "space":
            self.running = not self.running
    def close(self): self.closed = True


def make_clock(tmp_path, seconds=.5):
    rgb = np.zeros((1600, 2560, 3), np.uint8)
    rgb[0, 0] = 255
    path = tmp_path/"paused.png"
    Image.fromarray(rgb).save(path)
    backend = Backend(rgb)
    return gate.BoundedClock(backend, path, tmp_path/"clock.json", seconds), backend


def test_independent_timer_pauses_while_caller_is_blocked(tmp_path):
    clock, backend = make_clock(tmp_path)
    clock.start()
    clock.thread.join(5)
    assert backend.events == ["space", "space"]
    assert clock.evidence["final_paused"] and backend.closed
    clock.finish()
    assert backend.events.count("space") == 2


def test_finally_pause_and_already_paused_do_not_toggle_again(tmp_path):
    clock, backend = make_clock(tmp_path, 10)
    clock.start()
    backend.key("space")  # A normal GUI auto/manual pause during the action.
    clock.finish()
    assert backend.events == ["space", "space"]
    assert clock.evidence["final_paused"]


def test_unrecognized_header_blocks_before_time_input(tmp_path):
    clock, backend = make_clock(tmp_path)
    x0, y0, x1, y1 = gate.BoundedClock.HEADER
    backend.image[y0:y1, x0:x1] = 255
    try:
        with pytest.raises(gate.ActionError, match="clock_header_unrecognized"):
            clock.start()
    finally:
        clock.finish()
    assert not backend.events and backend.closed
