"""Read-only live guard check; operator/Computer Use supplies the stop event."""

import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hoi4_operator.executor.guard import ActionError, Guard, WindowsProbe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--watchdog", action="store_true", help="Test a one-second stalled-controller watchdog")
    args = parser.parse_args()
    probe = WindowsProbe()
    guard = Guard(probe, args.window, probe.pid(args.window),
                  watchdog_seconds=1 if args.watchdog else 12)
    started = time.monotonic()
    try:
        guard.arm(20 if args.watchdog else 8)
        print("armed", flush=True)
        # Intentionally no controller heartbeat: independent thread must latch.
        while not guard.reason:
            time.sleep(0.01)
        guard.check(heartbeat=False)
    except ActionError as exc:
        args.output.write_text(json.dumps({
            "source": "LIVE WindowsProbe / independent Guard thread",
            "reason": exc.reason, "status": exc.status,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
            "no_executor_input": True,
        }, indent=2), encoding="utf-8")
    finally:
        guard.close()


if __name__ == "__main__":
    main()
