"""Local JSON query for the read-only telemetry cache."""

import argparse
import json
import time

from .service import TelemetryService


def main() -> None:
    parser = argparse.ArgumentParser(description="Tail HOI4 game.log for Codex state frames")
    parser.add_argument("--log", required=True, help="full path to game.log")
    parser.add_argument("--from-start", action="store_true", help="replay the existing log")
    parser.add_argument("--watch", action="store_true", help="keep polling and print changed states")
    parser.add_argument("--interval", type=float, default=0.25, help="poll interval in seconds")
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval must be positive")
    service = TelemetryService(args.log, start_at_end=not args.from_start)
    try:
        while True:
            changed = service.poll()
            if changed or not args.watch:
                print(json.dumps(service.get_summary(), ensure_ascii=False), flush=True)
            if not args.watch:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
