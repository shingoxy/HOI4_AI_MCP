"""Behavioral runtime contracts without Windows input or provider network calls."""

from copy import deepcopy
import json
from types import SimpleNamespace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from hoi4_operator.agent import CodexAdapter, DecisionError, ScriptedAgent, validate_decision
from hoi4_operator.agent_runtime import AgentRuntime, RunAudit
from hoi4_operator.action_catalog import build_catalog, VALIDATED_ACTIONS
from hoi4_operator.game_time import GameTimeController
from hoi4_operator.observation import ObservationAggregator, game_datetime, section
from hoi4_operator.operator import OperatorAPI


class Model:
    def __init__(self):
        self.data = dict(status="fresh", game_date="24:00, 23 3月, 1936", latest_seq=1, session_id="test", revision=0,
            freshness_basis="frame_received_at", received_at="2026-10-06T00:00:00+00:00",
            state=dict(country="GER", politics=dict(political_power=160), industry=dict(military_factories=28),
                       research=dict(slot_count=4, tracked_technologies=[dict(tech_id="basic_machine_tools", researching=False, researched=False)]),
                       focus=dict(completed=False)))
        self.events = []
    def poll(self): return False
    def summary(self): return deepcopy(self.data)
    def changes(self, after): return dict(events=[e for e in self.events if e["revision"] > after])


def setup_observation():
    model = Model()
    clock = [0]
    capability = lambda: dict(backend="windows_native", native_subset_ready=True, action_readiness={
        "build":dict(map_state="MAP_READY",profile_calibrated=True,target_identity_valid=True),
        "create_frontline":dict(map_state="MAP_READY",profile_calibrated=True),
        "create_offensive_line":dict(map_state="MAP_READY",profile_calibrated=True)})
    agg = ObservationAggregator(model, capabilities=capability, clock=lambda: clock[0])
    agg.remember("research_gui", dict(slots=[dict(slot=0, tech_id="empty"), dict(slot=1, tech_id="unknown")]))
    agg.remember("focus_gui", dict(active=False))
    agg.remember("construction", dict(queue=[]), complete=True)
    agg.remember("production", dict(lines=[dict(line_id="p", equipment_id="infantry_equipment_1", factories=11,
        maximum_assignable_factories=18, identity_complete=True, action_supported=True)], available_factories=7))
    return model, agg, clock, capability


def test_aggregation_unknown_partial_and_no_fake_empty():
    model, agg, _, _ = setup_observation()
    view = agg.get()
    assert view["meta"]["date"] == "1936-03-24"
    assert view["navy"]["status"] == "unknown" and view["navy"]["data"] is None
    assert view["research"]["status"] == "partial" and not view["research"]["complete"]
    assert view["politics"]["status"] == "known"
    assert view["construction"]["navigation_required"]
    names = [a["type"] for a in view["alerts"]]
    assert set(names) == {"political_power_available", "research_slot_available", "focus_missing", "construction_queue_empty", "unused_military_factory"}
    assert len([a for a in view["alerts"] if a["type"] == "research_slot_available"]) == 1


@pytest.mark.parametrize("data,status", [(None,"unknown"), ([],"known_empty"), (0,"known_zero"), ([1],"known")])
def test_explicit_knowledge_states(data, status):
    assert section(data, complete=True)["status"] == status


def test_stale_gui_does_not_generate_empty_alerts():
    model, agg, clock, _ = setup_observation()
    clock[0] = 121
    view = agg.get("summary")
    assert view["construction"]["status"] == "stale"
    assert [a["type"] for a in view["alerts"]] == ["political_power_available"]
    model.data["status"] = "stale"
    assert agg.get()["alerts"] == [dict(type="telemetry_stale")]


@pytest.mark.parametrize("kind", ["timeline_reset", "log_reset", "date_backwards"])
def test_observation_timeline_reset_discards_cache(kind):
    model, agg, _, _ = setup_observation()
    before = agg.get("summary")["meta"]["timeline_id"]
    model.data["revision"] = 1
    if kind == "date_backwards": model.data["game_date"] = "1936-01-01"
    else: model.events.append(dict(kind=kind, revision=1))
    view = agg.get("summary")
    assert view["meta"]["timeline_reset"] and view["meta"]["timeline_id"] != before
    assert view["construction"]["status"] == "unknown"


def test_navigation_serial_refresh_on_demand_and_cache():
    model = Model()
    calls = []
    agg = None
    def refresh(domains):
        for name in domains:
            calls.append(name)
            agg.remember(name, dict(queue=[]), complete=False)
        return [dict(domain=name, navigation_required=True, restored_safe_page=True) for name in domains]
    agg = ObservationAggregator(model, refresh=refresh)
    assert agg.get("summary")["navigation"] == [] and calls == []
    assert len(agg.get()["navigation"]) == 4
    agg.get()
    assert len(calls) == 4
    agg.get("detailed")
    assert calls[-1] == "military"


def test_semantic_allowlist_removes_private_evidence():
    _, agg, _, _ = setup_observation()
    agg.remember("military", dict(armies=[dict(army_id="a", name="Army", x=40, screenshot="private")], hwnd=123, roi=[1,2]))
    data = agg.get()["military"]["data"]
    assert data == dict(armies=[dict(army_id="a", name="Army")])


@pytest.mark.parametrize("cap,status,reason", [
    ({"native_subset_ready": True},"available","current_calibrated_target"),
    ({"native_subset_ready": False},"unsupported","backend_capability_mismatch"),
    ({"native_subset_ready": False,"reason":"profile_mismatch"},"unsupported","profile_mismatch")])
def test_catalog_requires_backend_profile_and_current_target(cap,status,reason):
    _, agg, _, _ = setup_observation()
    catalog = build_catalog(agg.get(), VALIDATED_ACTIONS, cap)
    assert catalog["select_research"]["status"] == status
    assert catalog["select_research"]["reason"] == reason
    assert catalog["move_divisions"]["status"] == "unsupported"


def test_catalog_stale_unknown_already_satisfied_and_no_third_division():
    model, agg, _, cap = setup_observation()
    military = dict(armies=[dict(army_id="a", division_names=["inf", "panzer"])],
        divisions=[dict(division_id="d", name="1. Panzer-Division", army_id="a")],
        fronts=[dict(army_id="a", target_id="GER_POL_mainland")], offensive_orders=[dict(target_id="poz")])
    agg.remember("military", military)
    cat = build_catalog(agg.get(), VALIDATED_ACTIONS, cap())
    assert all(cat[n]["status"] == "already_satisfied" for n in ["assign_divisions", "create_frontline", "create_offensive_line"])
    military["divisions"][0]["army_id"] = None
    agg.remember("military", military)
    assert build_catalog(agg.get(), VALIDATED_ACTIONS, cap())["assign_divisions"]["status"] == "temporarily_blocked"
    model.data["status"] = "stale"
    assert build_catalog(agg.get(), VALIDATED_ACTIONS, cap())["build"]["status"] == "temporarily_blocked"


def test_scripted_priorities_and_no_already_satisfied_or_unsupported():
    model, agg, _, cap = setup_observation()
    observation = agg.get()
    cat = build_catalog(observation, VALIDATED_ACTIONS, cap())
    agent = ScriptedAgent()
    decision = agent.decide(observation, cat, {})
    assert decision == agent.decide(observation, cat, {})
    assert decision["actions"][0]["action"] == "select_research"
    for entry in cat.values(): entry["status"] = "already_satisfied"
    cat["move_divisions"]["status"] = "unsupported"
    assert agent.decide(observation, cat, {})["actions"] == []


def decision(action="build", arguments=None):
    return dict(assessment="Develop industry", goals=["Industry"], actions=[dict(action=action,
        arguments=arguments or dict(state_id=64, building_type="civilian_factory", count=1), rationale="Known empty queue")])


class FakeOperator:
    def __init__(self, result="confirmed", reason=""):
        _, self.agg, _, self.cap = setup_observation()
        self.result, self.reason, self.calls, self.invalidations = result, reason, [], 0
    def get_game_state(self, detail="strategic"): return self.agg.get(detail)
    def get_action_catalog(self): return build_catalog(self.agg.get("summary"), VALIDATED_ACTIONS, self.cap())
    def invalidate_snapshots(self): self.invalidations += 1
    def execute(self, action, arguments):
        self.calls.append((action, arguments))
        return dict(action=action, status=self.result, reason=self.reason, mutation_submitted=True, private_pixels=[1,2])


class FixedAgent:
    name = "test"
    def __init__(self, value): self.value = value
    def decide(self, observation, catalog, history): return deepcopy(self.value)


def runtime(tmp_path, result="confirmed", reason="", value=None):
    op = FakeOperator(result, reason)
    audit = RunAudit(tmp_path/"run", "test")
    rt = AgentRuntime(op, FixedAgent(value or decision()), SimpleNamespace(owns_running=False), audit)
    return rt, op, audit


def test_valid_runtime_durable_results_and_semantic_history(tmp_path):
    rt, op, audit = runtime(tmp_path)
    assert rt.cycle() == "ACTIVE" and len(op.calls) == 1
    assert audit.summary["results"] == 1
    saved = [json.loads(l) for l in (audit.path/"events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert any(e["event"] == "operator_proof" for e in saved)
    assert "private_pixels" not in json.dumps(rt.history())


@pytest.mark.parametrize("status", ["uncertain", "timed_out", "failed", "rejected"])
def test_failure_stops_plan_invalidates_reobserves_no_resend(tmp_path, status):
    value = decision()
    value["actions"].append(dict(action="select_focus", arguments=dict(focus_id="GER_remilitarize_the_rhineland"), rationale="No active focus"))
    rt, op, audit = runtime(tmp_path, status, value=value)
    assert rt.cycle() == "PLAN_STOPPED"
    assert len(op.calls) == 1 and op.invalidations == 1
    assert audit.summary["observations"] == 2
    rt.cycle()
    assert len(op.calls) == 1  # Same proposal is quarantined after observation.


@pytest.mark.parametrize("reason", ["loss_of_focus", "emergency_stop", "watchdog_timeout"])
def test_safety_circuit_pauses_immediately(tmp_path, reason):
    rt, op, _ = runtime(tmp_path, "failed", reason)
    assert rt.cycle() == "AGENT_PAUSED"
    rt.cycle()
    assert len(op.calls) == 1


@pytest.mark.parametrize("kind,limit", [("uncertain",3),("rejected",5),("backend",3)])
def test_consecutive_circuit_threshold(tmp_path, kind, limit):
    status = "failed" if kind == "backend" else kind
    reason = "backend_unavailable" if kind == "backend" else "readback_failed"
    rt, _, _ = runtime(tmp_path, status, reason)
    rt.consecutive[kind] = limit-1
    assert rt.cycle() == "AGENT_PAUSED"


def test_timeline_reset_clears_bounded_history_and_old_plan(tmp_path):
    rt, op, _ = runtime(tmp_path)
    rt.cycle()
    rt.pending_triggers.add("x")
    op.agg.model.data.update(game_date="1936-01-01", revision=1)
    rt.observe("summary")
    assert not rt.decisions and not rt.results and not rt.goals and not rt.pending_triggers
    assert op.invalidations == 1


@pytest.mark.parametrize("mutate,error", [
    (lambda d: d.update(secret_reasoning="x"),"invalid_decision_schema"),
    (lambda d: d["actions"][0].update(action="move_divisions"),"action_unavailable"),
    (lambda d: d["actions"][0]["arguments"].update(state_id=65),"unsupported_target"),
    (lambda d: d["actions"][0]["arguments"].update(count=True),"unsupported_target"),
    (lambda d: d["actions"].extend(deepcopy(d["actions"])*3),"action_budget_exceeded")])
def test_codex_untrusted_decisions(mutate, error):
    _, agg, _, cap = setup_observation()
    cat = build_catalog(agg.get(), VALIDATED_ACTIONS, cap())
    data = decision()
    mutate(data)
    with pytest.raises(DecisionError, match=error):
        CodexAdapter(lambda request: json.dumps(data)).decide(agg.get(), cat, {})


def test_codex_valid_schema_bad_json_and_provider_timeout():
    _, agg, _, cap = setup_observation()
    cat = build_catalog(agg.get(), VALIDATED_ACTIONS, cap())
    assert CodexAdapter(lambda request: json.dumps(decision())).decide(agg.get(), cat, {}) == decision()
    with pytest.raises(DecisionError): CodexAdapter(lambda request: "not JSON").decide(agg.get(), cat, {})
    def timeout(request): raise TimeoutError("provider_timeout")
    with pytest.raises(TimeoutError): CodexAdapter(timeout).decide(agg.get(), cat, {})


class TimeGUI:
    def __init__(self, model, mode="advance"):
        self.model, self.mode, self.running = model, mode, False
        self.resumes, self.pauses = 0, 0
    def begin(self, timeout): pass
    def end(self): pass
    def is_paused(self): return not self.running
    def resume(self): self.running = True; self.resumes += 1
    def pause(self): self.running = False; self.pauses += 1; return True
    def check(self):
        if self.mode == "advance": self.model.data["game_date"] = "1936-03-25"
        if self.mode == "reset": self.model.data["game_date"] = "1936-01-01"


@pytest.mark.parametrize("mode,status,reason", [("advance","confirmed","fresh_date_advanced"),
    ("stall","timed_out","game_time_timeout"),("reset","failed","timeline_reset")])
def test_game_time_date_pause_timeout_reset(mode,status,reason):
    model = Model()
    gui = TimeGUI(model, mode)
    result = GameTimeController(model, gui, timeout=.08, poll_interval=.001).advance_days()
    assert result["status"] == status and result["reason"] == reason and result["paused"]
    assert gui.resumes == 1 and gui.pauses == 1 and not gui.running


def test_game_time_refuses_running_start():
    gui = TimeGUI(Model())
    gui.running = True
    result = GameTimeController(gui.model, gui).advance_days()
    assert result["reason"] == "requires_paused_start" and gui.resumes == 0 and gui.pauses == 0


@pytest.mark.parametrize("date,expected", [("24:00, 23 3月, 1936","1936-03-24"),
    ("23:00, 1 January, 1936","1936-01-01"),("25:00, 23 3月, 1936",None),("nonsense",None)])
def test_date_parsing(date,expected):
    actual = game_datetime(date)
    assert (actual.date().isoformat() if actual else None) == expected


def test_runtime_invalid_decision_and_budget_never_call_operator(tmp_path):
    rt, op, _ = runtime(tmp_path)
    rt.adapter.value = {"assessment": "bad", "goals": [], "actions": [], "raw_input": {"x": 4}}
    assert rt.cycle() == "PLAN_STOPPED" and not op.calls
    rt.adapter.value = decision()
    rt.adapter.value["actions"] *= 4
    assert rt.cycle() == "PLAN_STOPPED" and not op.calls


def test_duplicate_mutation_and_empty_rationale_rejected():
    _, agg, _, cap = setup_observation()
    cat = build_catalog(agg.get(), VALIDATED_ACTIONS, cap())
    data = decision()
    data["actions"] *= 2
    with pytest.raises(DecisionError, match="duplicate_action"): validate_decision(data, cat)
    data["actions"] = data["actions"][:1]
    data["actions"][0]["rationale"] = ""
    with pytest.raises(DecisionError): validate_decision(data, cat)


def test_unstable_observation_stops_before_agent_and_input(tmp_path):
    rt, op, _ = runtime(tmp_path)
    original = op.get_game_state
    def bad(detail="strategic"):
        view = original(detail)
        view["navigation"] = [dict(status="rejected", reason="modal_blocked")]
        return view
    op.get_game_state = bad
    assert rt.cycle() == "PLAN_STOPPED" and not op.calls


def test_stale_runtime_pauses_without_input(tmp_path):
    rt, op, _ = runtime(tmp_path)
    op.agg.model.data["status"] = "stale"
    assert rt.cycle() == "AGENT_PAUSED" and not op.calls


def test_repeated_bad_proposals_reach_circuit_without_input(tmp_path):
    rt, op, _ = runtime(tmp_path)
    rt.adapter.value = dict(assessment="Invalid target", goals=[], actions=[dict(action="click", arguments={}, rationale="invalid")])
    for _ in range(4): assert rt.cycle() == "PLAN_STOPPED"
    assert rt.cycle() == "AGENT_PAUSED" and not op.calls


def test_daily_time_weekly_decisions_seven_days_and_bounded_history(tmp_path):
    from datetime import timedelta
    rt, op, audit = runtime(tmp_path)
    rt.adapter.value = dict(assessment="All supported goals satisfied", goals=[], actions=[])
    class Time:
        owns_running = False
        calls = 0
        def advance_days(self, days):
            self.calls += 1
            model = op.agg.model
            current = game_datetime(model.data["game_date"])+timedelta(days=days)
            model.data["game_date"] = current.date().isoformat()
            return dict(status="confirmed", paused=True)
    rt.time_controller = Time()
    assert rt.run_for_game_days(7) == "ACTIVE"
    assert rt.time_controller.calls == 7 and audit.summary["game_days"] == 7
    assert audit.summary["decisions"] == 2  # Initial and day 7, never daily provider polling.
    for _ in range(60):
        rt.decisions.append({"assessment": "bounded"})
        rt.results.append({"status": "confirmed"})
    assert len(rt.history()["decisions"]) == 20 and len(rt.history()["action_results"]) == 50


def test_time_failure_stops_benchmark_and_does_not_advance_again(tmp_path):
    rt, op, audit = runtime(tmp_path)
    rt.adapter.value = dict(assessment="Wait", goals=[], actions=[])
    class Time:
        owns_running = False
        calls = 0
        def advance_days(self, days):
            self.calls += 1
            return dict(status="timed_out", reason="game_time_timeout")
    rt.time_controller = Time()
    assert rt.run_for_game_days(7) == "AGENT_PAUSED"
    assert rt.time_controller.calls == 1 and audit.summary["game_days"] == 0


def test_result_persisted_before_next_action_and_catalog_rechecked(tmp_path):
    rt, op, audit = runtime(tmp_path)
    data = decision("select_research", dict(slot=0, tech_id="basic_machine_tools"))
    data["actions"].append(decision()["actions"][0])
    rt.adapter.value = data
    execute = op.execute
    def submit(name, arguments):
        if op.calls:
            assert json.loads((audit.path/"summary.json").read_text())["results"] == 1
        return execute(name, arguments)
    op.execute = submit
    assert rt.cycle() == "ACTIVE" and len(op.calls) == 2
    assert audit.summary["results"] == 2


def test_codex_input_has_no_backend_or_ui_object():
    _, agg, _, cap = setup_observation()
    agg.remember("production", dict(lines=[], screenshot="hidden", hwnd=4, templates="private"))
    observation = agg.get()
    cat = build_catalog(observation, VALIDATED_ACTIONS, cap())
    requests = []
    def provider(request):
        requests.append(json.loads(request))
        return json.dumps(dict(assessment="Wait for reliable targets", goals=[], actions=[]))
    CodexAdapter(provider).decide(observation, cat, {})
    assert set(requests[0]) == {"observation", "action_catalog", "history"}
    assert all(k not in json.dumps(requests[0]) for k in ["screenshot", "hwnd", "templates"])


def test_mcp_new_facade_tools_are_semantic_and_unknown_when_unattached(tmp_path):
    import asyncio
    from mcp import Client
    from hoi4_operator.mcp_server import create_server
    async def check():
        async with Client(create_server(tmp_path/"missing.log")) as client:
            tools = {t.name: t for t in (await client.list_tools()).tools}
            assert set(tools["get_game_state"].input_schema["properties"]) == {"detail"}
            assert not tools["get_game_state"].annotations.read_only_hint
            assert tools["get_action_catalog"].annotations.read_only_hint
            state = (await client.call_tool("get_game_state", dict(detail="strategic"))).structured_content
            assert state["navy"]["status"] == "unknown" and not state["navy"]["complete"]
            cat = (await client.call_tool("get_action_catalog")).structured_content
            assert cat["select_research"]["status"] == "unsupported"
    asyncio.run(check())


def test_cache_date_change_marks_gui_stale_even_before_ttl():
    model, agg, _, _ = setup_observation()
    model.data["game_date"] = "1936-03-25"
    assert agg.get("summary")["construction"]["status"] == "stale"


@pytest.mark.parametrize("right_drag,profile,reason", [(False,True,"backend_capability_mismatch"),(True,False,"profile_mismatch")])
def test_native_capability_primitive_and_profile_mismatch(right_drag,profile,reason):
    from hoi4_operator.executor.native_runtime import NativeObservationHost
    from hoi4_operator.executor.windows_native import PHYSICAL_PROFILE
    backend = SimpleNamespace(capture_profile=PHYSICAL_PROFILE if profile else None,
        capabilities=dict(capture=True, click=True, key_tap=True, right_drag=right_drag), ready=lambda: True)
    host = NativeObservationHost(Model(), SimpleNamespace(worker=backend), None, None, None)
    assert not host.capability()["native_subset_ready"] and host.capability()["reason"] == reason


def test_facade_three_semantic_methods_no_backend_is_available_by_default():
    api = OperatorAPI(Model())
    assert api.get_game_state("strategic")["military"]["status"] == "unknown"
    assert api.get_action_catalog()["build"]["status"] == "unsupported"
    assert api.execute("click", dict(x=10, y=20))["status"] == "rejected"


def test_native_catalog_rejects_missing_calibration():
    from hoi4_operator.executor.native_runtime import NativeObservationHost
    from hoi4_operator.executor.windows_native import PHYSICAL_PROFILE
    backend = SimpleNamespace(capture_profile=PHYSICAL_PROFILE,
        capabilities=dict(capture=True, click=True, key_tap=True, right_drag=True), ready=lambda: True)
    host = NativeObservationHost(Model(), SimpleNamespace(worker=backend), None, None, None)
    assert not host.capability()["native_subset_ready"] and host.capability()["reason"] == "calibration_missing"


def test_escaping_operator_exception_is_uncertain_and_not_retried(tmp_path):
    rt, op, _ = runtime(tmp_path)
    def broken(action, arguments):
        op.calls.append((action, arguments))
        raise OSError("after unknown input state")
    op.execute = broken
    assert rt.cycle() == "PLAN_STOPPED"
    assert rt.results[-1]["status"] == "uncertain" and rt.results[-1]["mutation_submitted"] is None
    rt.cycle()
    assert len(op.calls) == 1


def test_unsupported_rejection_marks_runtime_catalog_unavailable(tmp_path):
    rt, op, _ = runtime(tmp_path, "rejected", "unsupported_target")
    assert rt.cycle() == "PLAN_STOPPED"
    assert rt.catalog()["build"]["status"] == "unsupported"
    rt.cycle()
    assert len(op.calls) == 1


def test_rejected_already_satisfied_continues_without_retry_or_forged_confirmation(tmp_path):
    rt, op, audit = runtime(tmp_path, "rejected", "already_satisfied")
    assert rt.cycle() == "ACTIVE" and len(op.calls) == 1
    assert rt.results[-1]["status"] == "rejected" and audit.summary["rejected"] == 1


def test_scripted_runs_through_same_runtime_and_operator_without_direct_gui_access(tmp_path):
    rt, op, _ = runtime(tmp_path)
    rt.adapter = ScriptedAgent()
    assert rt.cycle() == "ACTIVE"
    assert op.calls == [("select_research", dict(slot=0, tech_id="basic_machine_tools"))]


def test_focus_loss_during_observation_pauses_before_decision(tmp_path):
    rt, op, _ = runtime(tmp_path)
    original = op.get_game_state
    def blocked(detail="strategic"):
        view = original(detail)
        view["navigation"] = [dict(status="failed", reason="loss_of_focus")]
        return view
    op.get_game_state = blocked
    assert rt.cycle() == "AGENT_PAUSED" and not op.calls


def test_telemetry_expires_during_decision_pauses_before_submission(tmp_path):
    rt, op, _ = runtime(tmp_path)
    agent = rt.adapter
    def decide(observation, catalog, history):
        value = deepcopy(agent.value)
        op.agg.model.data["status"] = "stale"
        return value
    agent.decide = decide
    assert rt.cycle() == "AGENT_PAUSED" and not op.calls


def single_gate(rt, refresh=None):
    import importlib.util
    spec = importlib.util.spec_from_file_location('native_runtime_cli', Path(__file__).resolve().parents[1]/'scripts/run_agent_runtime.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run_single_gate(rt, refresh)


def submitted_runtime(tmp_path):
    rt, op, audit = runtime(tmp_path)
    execute = op.execute
    def submit(name, arguments):
        return {**execute(name, arguments), 'mutation_submitted': True}
    op.execute = submit
    original = op.get_game_state
    def with_pump(detail='strategic'):
        view = original(detail)
        view['capabilities']['computer_use_pump'] = 'OFF'
        return view
    op.get_game_state = with_pump
    return rt, op, audit


def test_single_gate_requires_confirmed_mutation_and_valid_post_observation(tmp_path):
    rt, op, audit = submitted_runtime(tmp_path)
    reads = audit.summary['observations']
    assert single_gate(rt, lambda: dict(status='confirmed')) == 'SINGLE_CYCLE_CONFIRMED'
    assert len(op.calls) == audit.summary['confirmed_mutations'] == 1
    assert audit.summary['observations'] == reads+2 and not audit.summary['circuit_breaker']
    events = [json.loads(line) for line in (audit.path/'events.jsonl').read_text(encoding='utf-8').splitlines()]
    assert events[-1]['data']['passed'] and events[-1]['event'] == 'single_gate'


def test_single_gate_noop_never_passes_or_advances_time(tmp_path):
    rt, op, audit = runtime(tmp_path, value=dict(assessment='Wait', goals=[], actions=[]))
    assert single_gate(rt, lambda: pytest.fail('No-op must not advance time')) == 'SINGLE_GATE_NOT_PASSED'
    assert audit.summary['confirmed_mutations'] == 0 and not op.calls


def test_single_gate_uncertain_never_passes_by_later_readback_or_retries(tmp_path):
    rt, op, audit = runtime(tmp_path, 'uncertain', 'production_number_unreadable')
    assert single_gate(rt, lambda: pytest.fail('Uncertain must stop')) == 'PLAN_STOPPED'
    assert audit.summary['uncertain'] == 1 and len(op.calls) == 1
    assert audit.summary['confirmed_mutations'] == 0


@pytest.mark.parametrize('error', ['stale', 'pump_on', 'navigation', 'missing_domain'])
def test_single_gate_invalid_post_observation_never_passes(tmp_path, error):
    rt, op, audit = submitted_runtime(tmp_path)
    def after():
        original = op.get_game_state
        def invalid(detail='strategic'):
            value = original(detail)
            if error == 'stale': value['meta']['fresh'] = False
            if error == 'pump_on': value['capabilities']['computer_use_pump'] = 'ON'
            if error == 'navigation': value['navigation'] = [dict(status='rejected', reason='identity_mismatch')]
            if error == 'missing_domain': value['production']['data'] = None
            return value
        op.get_game_state = invalid
        return dict(status='confirmed')
    assert single_gate(rt, after) == 'SINGLE_GATE_NOT_PASSED'
    assert audit.summary['confirmed_mutations'] == 1 and len(op.calls) == 1


def test_single_post_bootstrap_failure_stops_without_new_mutation(tmp_path):
    rt, op, _ = submitted_runtime(tmp_path)
    assert single_gate(rt, lambda: dict(status='timed_out')) == 'SINGLE_GATE_NOT_PASSED'
    assert len(op.calls) == 1


def test_fake_codex_semantic_gate_same_operator_and_no_cu(tmp_path):
    rt, op, audit = submitted_runtime(tmp_path)
    requests = []
    def provider(request):
        requests.append(json.loads(request))
        return json.dumps(decision())
    rt.adapter = CodexAdapter(provider)
    assert single_gate(rt) == 'SINGLE_CYCLE_CONFIRMED'
    assert set(requests[0]) == {'observation','action_catalog','history'}
    assert all(key not in json.dumps(requests[0]) for key in ['screenshot','coordinates','templates','hwnd','pid'])
    assert audit.summary['pump'] == 'OFF' and len(op.calls) == 1


def test_audit_counts_and_idle_metrics_use_only_reliable_sample_dates(tmp_path):
    audit = RunAudit(tmp_path/'audit', 'scripted')
    _, agg, _, _ = setup_observation()
    view = agg.get()
    audit.emit('observation', view)
    audit.emit('observation', view)
    assert audit.summary['research_idle_days']['known_game_dates'] == 1
    assert audit.summary['research_idle_days']['observed_idle_dates'] == 1
    assert audit.summary['focus_idle_days']['observed_idle_dates'] == 1
    assert audit.summary['construction_queue_idle_days']['observed_idle_dates'] == 1
    assert audit.summary['unused_MIL_observations'] == dict(known=2,unused=2,unknown=0)
    view['meta']['date'] = '1936-03-25'
    view['research_gui']['data'] = dict(slots=[dict(tech_id='unknown')])
    view['focus_gui']['data'] = dict(active=None)
    view['construction']['complete'] = False
    view['production']['freshness'] = 'stale'
    audit.emit('observation', view)
    assert audit.summary['research_idle_days']['known_game_dates'] == 1
    assert audit.summary['focus_idle_days']['known_game_dates'] == 1
    assert audit.summary['construction_queue_idle_days']['known_game_dates'] == 1
    assert audit.summary['unused_MIL_observations']['unknown'] == 1
    for status in ('confirmed','already_satisfied','uncertain','rejected','timed_out'):
        audit.emit('result', dict(status=status,mutation_submitted=status=='confirmed'))
        assert json.loads((audit.path/'summary.json').read_text(encoding='utf-8'))[status] == 1
    audit.emit('game_time', dict(status='timed_out',reason='backend_unavailable'))
    audit.emit('timeline_reset', {})
    assert audit.summary['timed_out'] == audit.summary['timeouts'] == 2
    assert audit.summary['backend_errors'] == audit.summary['timeline_reset'] == 1
    assert audit.summary['confirmed_mutations'] == audit.summary['mutations_submitted'] == 1
