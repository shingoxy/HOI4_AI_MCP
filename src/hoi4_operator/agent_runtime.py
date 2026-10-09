"""Independent observe/decide/validate/execute/verify/advance orchestration."""

from collections import deque
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from uuid import uuid4

from .agent import DecisionError, validate_decision
from .action_catalog import VALIDATED_ACTIONS
from .observation import game_datetime


class RunAudit:
    def __init__(self, directory, agent):
        self.path = Path(directory)
        self.path.mkdir(parents=True, exist_ok=False)
        self.started = time.monotonic()
        self.summary = dict(run_id=str(uuid4()), agent=agent, backend="windows_native", pump="OFF",
                            started_at=datetime.now(timezone.utc).isoformat(), start_date=None, end_date=None,
                            observations=0, alerts=0, decisions=0, actions=0, results=0,
                            confirmed=0, already_satisfied=0, mutations_submitted=0, confirmed_mutations=0,
                            rejected=0, uncertain=0, timeouts=0,
                            timed_out=0, backend_errors=0, timeline_reset=0, circuit_breaker=None, game_days=0)
        self._idle_dates = {name: dict(known=set(), idle=set()) for name in
                            ("research", "focus", "construction_queue")}
        self.summary["unused_MIL_observations"] = dict(known=0, unused=0, unknown=0)
        self.save()

    def emit(self, event, data):
        with (self.path / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(dict(event=event, at=datetime.now(timezone.utc).isoformat(), data=data), ensure_ascii=False)+"\n")
        counters = dict(observation="observations", decision="decisions", action="actions", result="results")
        if event in counters:
            self.summary[counters[event]] += 1
        if event == "observation":
            self.summary["alerts"] += len(data["alerts"])
            date = data["meta"]["date"]
            self.summary["start_date"] = self.summary["start_date"] or date
            self.summary["end_date"] = date
            for name, domain, predicate in (
                ("research", "research_gui", lambda d: any(s["tech_id"] == "empty" for s in d.get("slots", []))),
                ("focus", "focus_gui", lambda d: d.get("active") is False),
                ("construction_queue", "construction", lambda d: d.get("queue") == [])):
                value = data.get(domain, {})
                known = value.get("freshness") == "fresh" and value.get("data") is not None
                sample = value.get("data") or {}
                if known and name == "research":
                    slots = sample.get("slots", [])
                    known = bool(slots) and (any(s["tech_id"] == "empty" for s in slots) or
                                             all(s["tech_id"] != "unknown" for s in slots))
                elif known and name == "focus":
                    known = type(sample.get("active")) is bool
                elif known and name == "construction_queue":
                    known = value.get("complete") is True and isinstance(sample.get("queue"), list)
                if known and date:
                    self._idle_dates[name]["known"].add(date)
                    if predicate(value["data"]):
                        self._idle_dates[name]["idle"].add(date)
            production = data.get("production", {})
            mil = self.summary["unused_MIL_observations"]
            available = (production.get("data") or {}).get("available_factories")
            if production.get("freshness") == "fresh" and type(available) is int and available >= 0:
                mil["known"] += 1
                mil["unused"] += available > 0
            else:
                mil["unknown"] += 1
        if event == "result":
            status = data.get("status")
            key = {"confirmed": "confirmed", "already_satisfied": "already_satisfied",
                   "rejected": "rejected", "uncertain": "uncertain", "timed_out": "timeouts"}.get(status)
            if key:
                self.summary[key] += 1
            if data.get("mutation_submitted") is True:
                self.summary["mutations_submitted"] += 1
                self.summary["confirmed_mutations"] += status == "confirmed"
        time_events = {"game_time", "fresh_bootstrap", "post_action_fresh_bootstrap"}
        if event in {"result"} | time_events and data.get("status") == "timed_out":
            self.summary["timed_out"] += 1
        if event in time_events and data.get("status") == "timed_out":
            self.summary["timeouts"] += 1
        if event == "timeline_reset":
            self.summary["timeline_reset"] += 1
        if event in {"result", "host_error"} | time_events and str(data.get("reason", "")).startswith(("backend_", "executor_error", "native_")):
            self.summary["backend_errors"] += 1
        self.save()  # Every action result is durable before any subsequent action.

    def save(self):
        for name, dates in self._idle_dates.items():
            self.summary[name+"_idle_days"] = dict(status="partial", known_game_dates=len(dates["known"]),
                observed_idle_dates=len(dates["idle"]),
                meaning="Dates with a reliable idle observation; not continuous 24-hour idle duration.")
        self.summary["wall_time_seconds"] = round(time.monotonic()-self.started, 3)
        temp = self.path / "summary.tmp"
        temp.write_text(json.dumps(self.summary, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path / "summary.json")


class AgentRuntime:
    def __init__(self, operator, adapter, time_controller, audit, *, max_mutations_per_cycle=3):
        if type(max_mutations_per_cycle) is not int or not 1 <= max_mutations_per_cycle <= 3:
            raise ValueError("mutation budget must be 1..3")
        self.operator, self.adapter, self.time_controller, self.audit = operator, adapter, time_controller, audit
        self.budget = max_mutations_per_cycle
        self.decisions, self.results, self.events = deque(maxlen=20), deque(maxlen=50), deque(maxlen=20)
        self.goals, self.plan, self.timeline = [], [], None
        self.status, self.phase = "ACTIVE", "OBSERVE"
        self.consecutive = dict(uncertain=0, rejected=0, backend=0)
        self.quarantine = set()
        self.unavailable = {}
        self.last_decision_date = None
        self.pending_triggers = set()

    def history(self):
        return deepcopy(dict(decisions=list(self.decisions), action_results=list(self.results),
                             goals=self.goals, events=list(self.events)))

    def pause(self, reason):
        self.stop_owned_time(reason)
        self.status, self.plan = "AGENT_PAUSED", []
        self.audit.summary["circuit_breaker"] = reason
        self.audit.emit("agent_paused", dict(reason=reason))

    def stop_owned_time(self, reason):
        if getattr(self.time_controller,'owns_running',False):
            ensure=getattr(self.time_controller,'ensure_game_stopped',None)
            try:
                stopped=ensure() if ensure else dict(paused=self.time_controller.pause_owned())
            except Exception as exc:
                stopped=dict(status='failed',paused=False,reason=getattr(exc,'reason','stop_failed'),
                             operator_intervention_required=True)
            self.audit.emit('time_safety_stop',dict(trigger=reason,**stopped))
            if not stopped['paused']:
                self.status='AGENT_PAUSED'
                self.audit.summary['circuit_breaker']='time_stop_failed'
                self.audit.summary.update(shutdown='unsafe_stop_failed',game_pause='UNKNOWN',
                                          operator_intervention_required=True)
                self.audit.save()

    def close(self):
        self.stop_owned_time('agent_runtime_exit')

    def observe(self, detail="strategic"):
        self.phase = "OBSERVE"
        observation = self.operator.get_game_state(detail)
        timeline = observation["meta"]["timeline_id"]
        if self.timeline is not None and timeline != self.timeline:
            self.plan, self.goals = [], []
            self.decisions.clear()
            self.results.clear()
            self.pending_triggers.clear()
            self.quarantine.clear()
            self.unavailable.clear()
            self.last_decision_date = None
            self.operator.invalidate_snapshots()
            self.events.clear()
            self.events.append(dict(type="timeline_reset"))
            self.audit.emit("timeline_reset", dict(before=self.timeline, after=timeline))
        self.timeline = timeline
        self.audit.emit("observation", observation)
        return observation

    @staticmethod
    def proposal_key(item):
        # Session-local ID versions must not permit the same semantic mutation to be retried.
        arguments = {k: v for k, v in item["arguments"].items() if k not in {"army_id", "division_ids", "line_id"}}
        return json.dumps([item["action"], arguments], sort_keys=True)

    def catalog(self):
        catalog = self.operator.get_action_catalog()
        for name, entry in catalog.items():
            if name in self.unavailable:
                entry.update(status="unsupported", reason=self.unavailable[name], options=[])
            elif entry["status"] == "available":
                options = [o for o in entry["options"] if self.proposal_key(dict(action=name, arguments=o)) not in self.quarantine]
                entry["options"] = options
                if not options:
                    entry.update(status="temporarily_blocked", reason="proposal_quarantined_requires_human")
                if "recommended" in entry and entry["recommended"] not in options:
                    entry["recommended"] = None
        return catalog

    def cycle(self):
        if self.status == "AGENT_PAUSED":
            return self.status
        self.status = "ACTIVE"
        observation = self.observe()
        if any(e["status"] not in {"confirmed", "unsupported"} for e in observation["navigation"]):
            self.stop_owned_time('strategic_observation_unstable')
            self.operator.invalidate_snapshots()
            self.plan=[]
            if self.status!='AGENT_PAUSED': self.status='PLAN_STOPPED'
            self.audit.emit("plan_stopped", dict(reason="strategic_observation_unstable"))
            safety = next((e.get("reason") for e in observation["navigation"] if e.get("reason") in
                           {"loss_of_focus", "emergency_stop", "watchdog_timeout", "watchdog_stalled"}), None)
            if safety:
                self.pause(safety)
            return self.status
        if not observation["meta"]["fresh"]:
            self.pause("telemetry_stale")
            return self.status
        catalog = self.catalog()
        self.phase = "DECIDE"
        try:
            decision = self.adapter.decide(deepcopy(observation), deepcopy(catalog), self.history())
            self.phase = "VALIDATE"
            decision = validate_decision(decision, catalog, self.budget)
            if any(self.proposal_key(a) in self.quarantine for a in decision["actions"]):
                raise DecisionError("proposal_quarantined_requires_human")
            if any(a["action"] not in VALIDATED_ACTIONS for a in decision["actions"]):
                raise DecisionError("runtime_policy_subset")
        except (DecisionError, TimeoutError) as exc:
            self.audit.emit("decision_rejected", dict(reason=str(exc)))
            self.plan = []
            self.status = "PLAN_STOPPED"
            self.consecutive["rejected"] += 1
            if self.consecutive["rejected"] >= 5:
                self.pause("consecutive_rejected_decisions")
            return self.status
        self.decisions.append(decision)
        self.goals = decision["goals"]
        self.plan = sorted(decision["actions"], key=lambda a: -catalog[a["action"]]["priority"])
        self.last_decision_date = game_datetime(observation["meta"]["game_date"])
        self.audit.emit("decision", decision)
        while self.plan:
            item = self.plan.pop(0)
            # Recheck freshness, current catalog and snapshot versions before each input.
            current_catalog = self.catalog()
            try:
                validate_decision(dict(assessment="Pre-submit check", goals=[], actions=[item]), current_catalog, 1)
            except DecisionError as exc:
                self.audit.emit("plan_stopped", dict(reason=str(exc)))
                self.plan = []
                self.status = "PLAN_STOPPED"
                if current_catalog.get(item["action"], {}).get("reason") == "telemetry_stale":
                    self.pause("telemetry_stale")
                return self.status
            self.phase = "EXECUTE"
            self.audit.emit("action", item)
            try:
                result = self.operator.execute(item["action"], item["arguments"])
            except Exception:
                # An exception escaping the Operator cannot prove whether input was submitted.
                result = dict(status="uncertain", reason="backend_unavailable", mutation_submitted=None)
            self.phase = "VERIFY"
            public_result = {k: deepcopy(result[k]) for k in ("action", "action_id", "status", "reason", "duration_ms", "mutation_submitted", "retry_count") if k in result}
            public_result["proposal"] = deepcopy(item)
            self.results.append(public_result)
            self.audit.emit("result", public_result)
            # Full operator proof is private audit evidence, never provider history.
            self.audit.emit("operator_proof", result)
            status, reason = result.get("status"), result.get("reason", "")
            if status == "rejected" and reason in {"already_satisfied", "already_researched", "already_completed"}:
                # Preserve the original rejected audit result; the goal needs no further mutation.
                status = "already_satisfied"
            self.consecutive["uncertain"] = self.consecutive["uncertain"]+1 if status == "uncertain" else 0
            self.consecutive["rejected"] = self.consecutive["rejected"]+1 if status == "rejected" else 0
            self.consecutive["backend"] = self.consecutive["backend"]+1 if reason.startswith(("backend_", "executor_error")) else 0
            safety = reason in {"loss_of_focus", "emergency_stop", "watchdog_timeout", "watchdog_stalled"}
            if safety or self.consecutive["uncertain"] >= 3 or self.consecutive["rejected"] >= 5 or self.consecutive["backend"] >= 3:
                self.pause(reason or "consecutive_failure")
            if status not in {"confirmed", "already_satisfied"}:
                self.stop_owned_time(reason or 'action_failed')
                if status == "rejected" and reason.startswith("unsupported"):
                    self.unavailable[item["action"]] = reason
                self.quarantine.add(self.proposal_key(item))
                self.plan = []
                self.operator.invalidate_snapshots()
                self.audit.emit("rejection_class", dict(reason=reason, category=("identity" if "identity" in reason else
                    "stale" if "stale" in reason else "unsupported" if "unsupported" in reason else "temporary")))
                self.observe("summary")
                if self.status != "AGENT_PAUSED":
                    self.status = "PLAN_STOPPED"
                return self.status
            # Reobserve after a mutation; remaining stale proposals cannot use old IDs.
            if self.plan:
                self.observe()
        return self.status

    def run_for_game_days(self, days):
        if type(days) is not int or not 1 <= days <= 30:
            raise ValueError("days must be 1..30")
        start = self.observe("summary")
        initial = game_datetime(start["meta"]["game_date"])
        if initial is None:
            self.pause("game_date_unknown")
            return self.status
        if self.cycle() != "ACTIVE":
            return self.status
        previous_alerts = set()
        for _ in range(days):
            self.phase = "ADVANCE"
            result = self.time_controller.advance_days(1)
            self.audit.emit("game_time", result)
            if result["status"] != "confirmed":
                self.operator.invalidate_snapshots()
                self.observe("summary")
                self.pause(result.get("reason", "game_time_failed"))
                break
            self.operator.invalidate_snapshots()  # Cached GUI state must not survive a game-day advance.
            observation = self.observe("summary")
            current = game_datetime(observation["meta"]["game_date"])
            if current is None or current < initial or observation["meta"]["timeline_reset"]:
                self.pause("timeline_reset_during_advance")
                break
            self.audit.summary["game_days"] = (current.date()-initial.date()).days
            self.audit.save()
            alerts = {a["type"] for a in observation["alerts"] if a["type"] not in {"political_power_available"}}
            weekly = self.last_decision_date is None or (current.date()-self.last_decision_date.date()).days >= 7
            if weekly or alerts-previous_alerts:
                if self.cycle() != "ACTIVE":
                    break
            previous_alerts = alerts
            if self.audit.summary["game_days"] >= days:
                break
        return self.status
