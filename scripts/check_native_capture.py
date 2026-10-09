"""Read-only native capture/geometry comparison; does not send input or refocus."""

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hoi4_operator.executor.guard import WindowsProbe
from hoi4_operator.executor.windows_native import WindowsNativeBackend


def hashes():
    directory = Path("D:/Documents/Paradox Interactive/Hearts of Iron IV")
    files = [directory / "dlc_load.json", *sorted((directory / "save games").glob("*.hoi4"))]
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.exists()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window", type=int, required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/phase5/capture-check.json")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    probe = WindowsProbe()
    backend = WindowsNativeBackend(args.window, probe.pid(args.window), probe=probe, capture_space="legacy")
    result = {"source": "LIVE native Win32 read-only capture / Computer Use pump OFF", "input_count": 0}
    try:
        backend.begin(12)
        result["geometry"] = backend.get_window_geometry()
        captures = []
        for index in range(3):
            started = time.monotonic()
            rgb = backend.capture()
            captures.append(round((time.monotonic()-started)*1000, 2))
            path = args.output.parent / "captures" / f"native-{index}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(rgb).save(path)
        result["capture_ms"] = captures
        result["profile"] = asdict(backend.capture_profile)
        result["status"] = "captured"
        if args.baseline:
            other = np.asarray(Image.open(args.baseline).convert("RGB"))
            result["baseline_size"] = [other.shape[1], other.shape[0]]
            if other.shape == rgb.shape:
                # UI header is static while the map, mouse tooltip and water animate.
                delta = np.abs(other[:60].astype(float)-rgb[:60].astype(float))
                result["header_mean_absolute_error"] = round(float(delta.mean()), 3)
                result["header_p95_error"] = round(float(np.percentile(delta, 95)), 3)
            else:
                result["comparison"] = "size_mismatch"
        result["files"] = hashes()
    finally:
        backend.close()
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "files"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
