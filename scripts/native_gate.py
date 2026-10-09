"""Operator-only gate runner: native GUI time advancement stops after 25 seconds.

The independent timer pauses even while the semantic SDK subprocess is waiting.
No Computer Use pump, console, save write, or semantic action retry is used.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import threading
import time

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hoi4_operator.executor.guard import ActionError, WindowsProbe
from hoi4_operator.executor.windows_native import WindowsNativeBackend
from hoi4_operator.executor.templates import Templates


class BoundedClock:
    # The pause decoration blinks, so prove clock state using timestamp movement.
    DATE = (2294, 9, 2410, 30)
    HEADER = (2237, 4, 2262, 31)

    def __init__(self, backend, reference, output, seconds=25, fresh_signal=None):
        self.backend, self.output, self.seconds = backend, output, seconds
        self.fresh_signal = fresh_signal
        self.reference = np.asarray(Image.open(reference).convert("RGB"))
        if self.reference.shape != (1600, 2560, 3):
            raise ValueError("clock reference must be the calibrated physical profile")
        self.stop = threading.Event()
        self.thread = None
        self.menu_paused = False
        self.templates = Templates(ROOT/'artifacts/phase5/templates')
        self.evidence = {"pump": "OFF", "maximum_running_seconds": seconds,
                         "primitive": "SendInput.KEYBDINPUT_SCANCODE", "events": []}

    @staticmethod
    def crop(rgb, box):
        x0, y0, x1, y1 = box
        return rgb[y0:y1, x0:x1].astype(float)

    def clock_value(self, rgb):
        if rgb.shape != self.reference.shape:
            raise ActionError("clock_profile_mismatch", "rejected")
        if np.mean(abs(self.crop(rgb, self.HEADER)-self.crop(self.reference, self.HEADER))) > 8:
            if self.templates.find(rgb,'clock_menu',(1230,585,1330,620),.9):
                self.menu_paused=True
                self.evidence['pause_source']='known_GUI_game_menu'
                return np.zeros((21,116),dtype=bool)
            raise ActionError("clock_header_unrecognized", "rejected")
        self.menu_paused=False
        text = self.crop(rgb, self.DATE)
        return (text.min(axis=2) > 180) & (text.max(axis=2)-text.min(axis=2) < 40)

    def stable_clock(self, seconds=2):
        first = self.clock_value(self.backend.capture())
        if self.menu_paused:
            return True
        deadline = time.monotonic()+seconds
        while time.monotonic() < deadline:
            self.backend.check()
            time.sleep(.2)
            # Seven paused samples vary by at most four antialiasing pixels.
            current=self.clock_value(self.backend.capture())
            if self.menu_paused:
                return True
            if np.count_nonzero(first != current) > 8:
                return False
        return True

    def save(self):
        self.output.write_text(json.dumps(self.evidence, indent=2), encoding="utf-8")

    def confirm_pause(self):
        # A queued display update can change one hour after the pause tap.
        # Only repeat observation here, never the pause input.
        deadline=time.monotonic()+4
        while time.monotonic()<deadline:
            if self.stable_clock():
                return True
            time.sleep(.2)
        return False

    def start(self):
        self.backend.begin(self.seconds+8)
        self.backend.capture()
        if not self.stable_clock():
            raise ActionError("gate_requires_paused_start", "rejected")
        if self.menu_paused:
            raise ActionError('gate_requires_clear_game_ui','rejected')
        self.started = time.monotonic()
        # Install the independent pause path before the first time-control input.
        self.thread = threading.Thread(target=self.watch, daemon=False)
        self.thread.start()
        self.backend.key("space")
        rgb = self.backend.capture()
        Image.fromarray(rgb).save(self.output.with_name(self.output.stem+"-running.png"))
        moving = not self.stable_clock()
        self.evidence["events"].append({"event": "unpause", "confirmed": moving})
        self.save()
        if not moving:
            raise ActionError("unpause_not_confirmed", "rejected")

    def watch(self):
        try:
            while not self.stop.wait(.25) and time.monotonic()-self.started < self.seconds:
                self.backend.check()  # Heartbeat and focus/F12 stay active.
                if self.fresh_signal and self.fresh_signal.exists():
                    self.evidence["stopped_after_fresh_telemetry"] = True
                    break
            if not self.stable_clock():
                deadline = time.monotonic()+1
                while (any(self.backend.desktop.held("mouse", button) for button in ("left", "right")) and
                       time.monotonic() < deadline):
                    self.backend.check()
                    time.sleep(.02)
                self.backend.key("space")
            self.evidence["final_paused"] = self.confirm_pause()
            rgb = self.backend.capture()
            Image.fromarray(rgb).save(self.output.with_suffix(".png"))
        except Exception as exc:
            self.evidence["pause_error"] = str(exc)
            self.evidence["final_paused"] = False
        finally:
            self.evidence["duration_ms"] = round((time.monotonic()-self.started)*1000)
            self.backend.close()
            self.save()

    def finish(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=8)
            if self.thread.is_alive():
                raise RuntimeError("native_pause_thread_did_not_finish")
        else:
            self.backend.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window", type=int, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--paused-reference", type=Path, required=True)
    parser.add_argument("--capture-space", choices=("physical", "legacy"), default="physical")
    parser.add_argument("--production-readback-of", type=Path)
    parser.add_argument("--construction-readback-of", type=Path)
    parser.add_argument("--army-readback-of", type=Path)
    parser.add_argument("--frontline-readback-of", type=Path)
    parser.add_argument("--offensive-readback-of", type=Path)
    parser.add_argument("--pause-after-fresh", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("refuse to reuse gate evidence path")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    probe = WindowsProbe()
    clock = BoundedClock(WindowsNativeBackend(args.window, probe.pid(args.window), probe=probe),
                         args.paused_reference, args.output.with_name(args.output.stem+"-clock.json"),
                         fresh_signal=args.output.with_suffix('.fresh.json') if args.pause_after_fresh else None)
    try:
        clock.start()
        command = [sys.executable, str(ROOT/"scripts/native_client.py"), "--window", str(args.window),
                   "--plan", str(args.plan), "--output", str(args.output), "--capture-space", args.capture_space]
        if args.pause_after_fresh:
            command += ["--fresh-signal", str(args.output.with_suffix('.fresh.json'))]
        if args.production_readback_of:
            command += ["--production-readback-of", str(args.production_readback_of)]
        if args.construction_readback_of:
            command += ["--construction-readback-of", str(args.construction_readback_of)]
        if args.army_readback_of:
            command += ["--army-readback-of", str(args.army_readback_of)]
        if args.frontline_readback_of:
            command += ["--frontline-readback-of", str(args.frontline_readback_of)]
        if args.offensive_readback_of:
            command += ["--offensive-readback-of", str(args.offensive_readback_of)]
        subprocess.run(command, check=True, timeout=125)
    finally:
        clock.finish()
    if not clock.evidence.get("final_paused"):
        raise RuntimeError("final_pause_not_confirmed")


if __name__ == "__main__":
    main()
