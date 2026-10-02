"""Aggregate recorded SDK results; no game input, telemetry or save writes."""

from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT/"artifacts/phase3"


def main():
    confirmed, statuses, failures, harness, files = defaultdict(list), defaultdict(lambda: defaultdict(int)), [], [], []
    retries, observation_retries = 0, 0
    for path in sorted(DIRECTORY.glob("*live*.json")):
        evidence = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(evidence, dict) or evidence.get("source") != "LIVE HOI4 / official SDK stdio / semantic API / normal GUI": continue
        files.append(path.name)
        if evidence.get("harness_stop"):
            harness.append({"file": path.name, "reason": evidence["harness_stop"]})
        for step in evidence.get("actions", []):
            action, result = step["action"], step["result"]
            status = result["status"]
            statuses[action][status] += 1
            retries += result.get("retry_count", 0)
            observation_retries += result.get("ui_observation_retry_count", 0)
            if status == "confirmed": confirmed[action].append(result)
            elif status != "already_satisfied":
                failures.append({"file": path.name, "action": action, "status": status,
                                 "reason": result.get("reason"), "accepted": result.get("accepted"),
                                 "duration_ms": result.get("duration_ms"), "retry_count": result.get("retry_count", 0)})
    metrics = {}
    for action, results in confirmed.items():
        metrics[action] = {"confirmed_count": len(results), "average_duration_ms": round(mean(
            result["duration_ms"] for result in results), 2), "average_stages_ms": {
            stage: round(mean(result["timings_ms"].get(stage, 0) for result in results), 2)
            for stage in ("precheck", "navigation", "target_lookup", "submit", "readback", "confirmation", "total")}}
    summary = {"generated_at": datetime.now(timezone.utc).isoformat(), "status": "LIVE VERIFIED; limited Phase 3 PoC",
        "profile": "HOI4 1.19.3 / GER 1936 start / base Chinese / Telemetry Mod only / 2560x1080 / scale 1.0",
        "live_date_extension": "Naturally advanced into 1937 for PP and GUI calibration; final April 27 1937 before restoration",
        "evidence_files": files, "action_status_counts": statuses, "confirmed_metrics": metrics,
        "submission_retry_count": retries, "successful_trade_observation_retry_count": observation_retries,
        "failures": failures, "harness_stops": harness,
        "historical_actions": "Research, Focus and factory assignment proof retained from historical reports; not rerun",
        "restoration": json.loads((DIRECTORY/"restoration.json").read_text(encoding="utf-8-sig")),
        "proof_limit": "UI confirmation for unsupported telemetry fields; no claimed full trade, queue progress or internal production identities"}
    (DIRECTORY/"live-summary-20261002.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    for action, metric in metrics.items():
        print(f"{action}: {metric['confirmed_count']} confirmed; avg {metric['average_duration_ms']} ms")
    print(f"submission retries: {retries}; trade observation retries on successful results: {observation_retries}")
    print(f"retained action failures: {len(failures)}; harness stops: {len(harness)}")


if __name__ == "__main__":
    main()
