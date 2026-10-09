"""Bounded Phase 5 native runtime host. Agents receive semantic JSON only."""

import argparse
import json
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hoi4_operator.agent import ScriptedAgent
from hoi4_operator.agent_runtime import AgentRuntime, RunAudit
from hoi4_operator.executor.native_runtime import NativeRuntimeHost
from hoi4_operator.executor.native_audit import map_metrics
from hoi4_operator.telemetry.paths import default_log_path


def run_single_gate(runtime, refresh_post=None):
    """Acceptance only; the Runtime failure/circuit/quarantine policy is unchanged."""
    status = runtime.cycle()
    audit = runtime.audit
    if status != "ACTIVE":
        audit.emit("single_gate", dict(passed=False, reason=status))
        return status
    if audit.summary["confirmed_mutations"] < 1 or audit.summary["circuit_breaker"]:
        audit.emit("single_gate", dict(passed=False, reason="confirmed_mutation_required"))
        return "SINGLE_GATE_NOT_PASSED"
    # The native host can produce a fresh paused frame before rebuilding GUI
    # snapshots. This bootstrap is audited separately from benchmark game days.
    if refresh_post:
        result = refresh_post()
        audit.emit("post_action_fresh_bootstrap", result)
        if result["status"] != "confirmed":
            audit.emit("single_gate", dict(passed=False, reason="post_action_bootstrap_failed"))
            return "SINGLE_GATE_NOT_PASSED"
    post = runtime.observe()
    valid = (post["meta"]["fresh"] and post["meta"]["backend"] == "windows_native" and
             post["capabilities"].get("computer_use_pump") == "OFF" and
             all(e["status"] in {"confirmed", "unsupported"} for e in post["navigation"]) and
             all(post[d]["freshness"] == "fresh" and post[d]["data"] is not None
                 for d in ("research_gui", "focus_gui", "production", "construction")))
    audit.emit("single_gate", dict(passed=valid, reason="confirmed_mutation_and_valid_post_observation" if valid
                                 else "post_action_observation_invalid"))
    return "SINGLE_CYCLE_CONFIRMED" if valid else "SINGLE_GATE_NOT_PASSED"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--paused-reference", type=Path, required=True)
    parser.add_argument("--mode", choices=("observe", "single", "days"), default="observe")
    parser.add_argument("--days", type=int, choices=(7, 30))
    parser.add_argument("--log", type=Path, default=default_log_path())
    args = parser.parse_args()
    if args.mode == "days" and args.days is None:
        parser.error("days mode requires --days")
    audit = RunAudit(args.output, "scripted")
    host = runtime = None
    try:
        host = NativeRuntimeHost(args.window, args.log, ROOT, audit.path / "native-audit", args.paused_reference)
        Image.fromarray(host.preflight()).save(audit.path / "preflight.png")
        audit.emit("initial_telemetry", host.model.summary())
        # Semantic bounded GUI bootstrap produces a fresh frame when paused telemetry is old.
        if host.model.summary()["status"] != "fresh":
            bootstrap = host.time.advance_days(1)
            audit.emit("fresh_bootstrap", bootstrap)
            if bootstrap["status"] != "confirmed":
                audit.summary.update(status='BLOCKED',blocker=bootstrap.get('reason','bootstrap_failed'))
                return
        runtime = AgentRuntime(host.operator, ScriptedAgent(), host.time, audit)
        observation = runtime.observe()
        catalog = host.operator.get_action_catalog()
        audit.emit("catalog", catalog)
        if any(e["status"] not in {"confirmed", "unsupported"} for e in observation["navigation"]):
            audit.summary.update(status="BLOCKED", blocker="strategic_observation_unstable")
            return
        if not observation["meta"]["fresh"]:
            audit.summary.update(status="BLOCKED", blocker="telemetry_stale_after_observation")
            return
        if args.mode == "observe":
            audit.summary["status"] = "OBSERVATION_CATALOG_CONFIRMED"
        elif args.mode == "single":
            audit.summary["status"] = run_single_gate(runtime, lambda: host.time.advance_days(1))
        else:
            audit.summary["status"] = runtime.run_for_game_days(args.days)
        audit.emit("final_observation", host.operator.get_game_state("summary"))
    except Exception as exc:
        audit.summary.update(status="BLOCKED", blocker=getattr(exc, "reason", type(exc).__name__))
        audit.emit("host_error", dict(reason=audit.summary["blocker"]))
    finally:
        if host:
            try:
                if runtime: runtime.close()
                shutdown=host.close()
                audit.emit('shutdown',shutdown)
                audit.summary.update(shutdown=shutdown['shutdown'],game_pause=shutdown['game_pause'],
                    operator_intervention_required=shutdown['operator_intervention_required'],
                    time_metrics=shutdown['time_metrics'],time_ownership=shutdown['ownership_state'])
                if shutdown['owns_running']:
                    audit.summary.update(status='BLOCKED',blocker='owned_running_stop_unconfirmed')
            except Exception as exc:
                audit.summary.update(status="BLOCKED", blocker="host_cleanup_failed")
                if host.time.owns_running:
                    audit.summary.update(shutdown='unsafe_stop_failed',game_pause='UNKNOWN',
                        operator_intervention_required=True,time_ownership=str(host.time.state),
                        time_metrics=dict(host.time.metrics))
                audit.emit("host_cleanup_error", dict(reason=getattr(exc, "reason", type(exc).__name__)))
        audit.summary['native_map_metrics']=map_metrics(audit.path/'native-audit')
        audit.summary['human_strategic_interventions']=0
        audit.save()
        print(json.dumps(audit.summary, ensure_ascii=False))
        if audit.summary.get("status") not in {"ACTIVE", "OBSERVATION_CATALOG_CONFIRMED", "SINGLE_CYCLE_CONFIRMED"}:
            raise SystemExit(2)


if __name__ == "__main__":
    main()
