"""Summarize persisted real SDK action results, preserving failures separately."""

from collections import Counter, defaultdict
import json
from pathlib import Path
from statistics import mean


ROOT=Path(__file__).resolve().parents[1]
DIRECTORY=ROOT/"artifacts/phase4"


def main():
    rows=[]
    sessions=[]
    for path in sorted(DIRECTORY.glob("*-live-*.json")):
        document=json.loads(path.read_text(encoding="utf-8"))
        sessions.append({"file":path.name,"harness_stop":document.get("harness_stop"),
            "before_date":document.get("before_telemetry",{}).get("game_date"),
            "after_date":document.get("after_telemetry",{}).get("game_date")})
        for item in document.get("actions",[]):
            result=item["result"]
            rows.append({"file":path.name,"action":item["action"],"arguments":item["arguments"],
                "action_id":result.get("action_id"),"status":result.get("status"),
                "accepted":result.get("accepted"),"reason":result.get("reason"),
                "duration_ms":result.get("duration_ms"),"retry_count":result.get("retry_count"),
                "timings_ms":result.get("timings_ms")})
    groups=defaultdict(list)
    for row in rows:
        groups[row["action"]].append(row)
    actions={}
    for name,items in groups.items():
        confirmed=[item for item in items if item["status"]=="confirmed"]
        actions[name]={"status_counts":dict(Counter(item["status"] for item in items)),
            "confirmed_mean_duration_ms":round(mean(item["duration_ms"] for item in confirmed),2) if confirmed else None,
            "confirmed_targets":[item["arguments"] for item in confirmed]}
    result={"source":"Persisted official SDK stdio calls against real HOI4 normal GUI",
        "manual_calibration_counted_as_sdk_success":False,"sessions":sessions,
        "status_counts":dict(Counter(row["status"] for row in rows)),"by_action":actions,
        "failures":[row for row in rows if row["status"] not in {"confirmed","already_satisfied"}],
        "actions":rows,"limitations":{"offensive_line":"Documented backend has no right-button drag",
            "move_divisions":"Province identity and order readback uncalibrated",
            "naval_mutations":"Sea region mapping and mission readback uncalibrated"}}
    path=DIRECTORY/"live-summary-20261002.json"
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"file":str(path),"status_counts":result["status_counts"],"by_action":actions},ensure_ascii=False))


if __name__=="__main__":
    main()
