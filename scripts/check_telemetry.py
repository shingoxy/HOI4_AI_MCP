"""One-shot, read-only diagnosis of Codex frames in HOI4 game.log."""

import argparse
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hoi4_operator.telemetry import FrameParser, StateCache
from hoi4_operator.telemetry.paths import default_log_path


def check(path: Path, stale_seconds: float) -> dict:
    result = {
        "log_path": str(path),
        "log_exists": path.is_file(),
        "log_last_write_at": None,
        "log_age_seconds": None,
        "begin_count": 0,
        "end_count": 0,
        "latest_seq": None,
        "latest_game_date": None,
        "latest_state": None,
        "cache_freshness": "unavailable",
        "freshness_basis": "game.log last-write time (upper bound on frame recency)",
        "parser_errors": [],
    }
    if not result["log_exists"]:
        return result

    parser = FrameParser()
    cache = StateCache()
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                result["begin_count"] += "CODEX_STATE_BEGIN|" in line
                result["end_count"] += "CODEX_STATE_END|" in line
                state = parser.feed(line)
                if state is not None:
                    cache.update(state)
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    except OSError as exc:
        result["read_error"] = str(exc)
        return result

    result["parser_errors"] = list(parser.errors)
    result["log_last_write_at"] = modified.isoformat()
    result["log_age_seconds"] = round((datetime.now(timezone.utc) - modified).total_seconds(), 2)
    result["latest_seq"] = cache.latest_seq
    result["latest_game_date"] = cache.game_date
    if cache.latest_state is not None:
        result["latest_state"] = asdict(cache.latest_state)
        # A one-shot replay cannot know when the frame was emitted. The file mtime
        # is an upper bound: unrelated later log writes can make it look fresher.
        cache.received_at = modified
        result["cache_freshness"] = cache.freshness(max_age=timedelta(seconds=stale_seconds))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, default=default_log_path())
    parser.add_argument("--stale-seconds", type=float, default=30)
    args = parser.parse_args()
    if args.stale_seconds <= 0:
        parser.error("--stale-seconds must be positive")
    print(json.dumps(check(args.log, args.stale_seconds), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
