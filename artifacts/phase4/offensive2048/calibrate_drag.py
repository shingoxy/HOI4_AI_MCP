"""Manual calibration only: one guarded drag, never counted as SDK confirmed."""

import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from hoi4_operator.executor.guard import WindowsProbe
from hoi4_operator.executor.right_drag import NativeRightDragBackend
from hoi4_operator.executor.worker import ComputerUseWorker
from hoi4_operator.executor.templates import Templates


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=["mainland", "east_prussia", "mainland_north_east"])
    args = parser.parse_args()
    directory = Path(__file__).resolve().parent
    crops = json.loads((directory / "templates/manifest.json").read_text())["crops"]
    templates = Templates(directory / "templates")
    probe = WindowsProbe()
    hwnd = 659082
    backend = NativeRightDragBackend(ComputerUseWorker(hwnd, probe.pid(hwnd), probe=probe,
        endpoint_file=ROOT / "artifacts/phase3a/runtime/endpoint.json"))
    result = {"source": "manual guarded calibration; not SDK confirmed", "target": args.target,
              "submit_count": 0, "retry_count": 0}
    started = time.monotonic()
    try:
        # Transport startup only; the armed action still has its original limits.
        ready_deadline = time.monotonic() + 120
        while not backend.last_poll and time.monotonic() < ready_deadline:
            time.sleep(.05)
        if not backend.last_poll:
            raise ValueError("Computer Use pump unavailable")
        backend.begin(30)
        rgb = backend.capture()
        if rgb.shape[:2] != (1280, 2048):
            raise ValueError("Wrong capture profile")
        names = ["anchor_amsterdam", "anchor_copenhagen", "anchor_konigsberg",
                 "army_name", "army_count_one", "army_no_general", "army_panzer_one",
                 "army_extra_plus", "offensive_active", "land_mode", "operation_white",
                 *(f"front_{'mainland' if args.target == 'mainland_north_east' else args.target}_{i}" for i in range(3))]
        if not all(templates.find(rgb, name, crops[name], .85 if name == 'army_extra_plus' else .9) for name in names):
            raise ValueError("Calibration precondition changed")
        from PIL import Image
        Image.fromarray(rgb).save(directory / f"captures/{args.target}-drag-before.png")
        start, end = ((1360, 600), (1360, 685)) if args.target == "mainland" else ((1540, 600), (1660, 600))
        result.update(segment=[start, end], anchors_verified=names[:3])
        result["submit_count"] = 1
        backend.right_drag(start, end)
        time.sleep(.4)
        after = backend.capture()
        Image.fromarray(after).save(directory / f"captures/{args.target}-drag-after.png")
        result["result"] = "drag returned and released; order awaits manual inspection"
    except Exception as exc:
        result["error"] = str(exc)
    finally:
        try:
            backend.close()
        finally:
            result["duration_ms"] = round((time.monotonic() - started) * 1000)
            (directory / f"{args.target}-calibration.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
