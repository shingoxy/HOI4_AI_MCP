"""Offline semantic, safety and confirmation tests; no real input is used."""

from copy import deepcopy
from pathlib import Path
import sys
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hoi4_operator.actions import focus, research
from hoi4_operator.executor.catalog import FOCUS, RESEARCH
from hoi4_operator.executor.guard import ActionError, Guard
from hoi4_operator.executor.service import Executor


def summary(seq=10, *, researching=False, completed=False, status="fresh"):
    return {"status": status, "latest_seq": seq, "parser_errors": [],
            "log_read_error": None, "state": {
                "country": "GER", "protocol_version": 2,
                "research": {"slot_count": 4, "tracked_technologies": [
                    {"tech_id": k, "researching": researching, "researched": False}
                    for k in RESEARCH]},
                "focus": {"tracked_id": FOCUS, "completed": completed,
                          "progress_lower_bound": 0.0, "progress_upper_bound": 0.1}}}


class FakeModel:
    def __init__(self, states):
        self.states, self.index = states, -1
    def poll(self):
        self.index = min(self.index + 1, len(self.states) - 1)
    def summary(self):
        return deepcopy(self.states[max(self.index, 0)])


class FakeWorker:
    def __init__(self, failure=None):
        self.failure, self.events = failure, []
    def begin(self, timeout):
        self.events.append("begin")
        if self.failure:
            raise ActionError(self.failure, "rejected")
    def check(self):
        pass
    def key(self, key):
        self.events.append(key)
    def release(self):
        self.events.append("release")
    def end(self):
        self.release()
        self.events.append("end")


class FakeUI:
    def __init__(self, *, slot="empty", active=False, matches=True, failures=0, after_commit=False):
        self.slot_id, self.active, self.matches = slot, active, matches
        self.failures, self.after_commit, self.calls = failures, after_commit, 0
    def open_panel(self, name):
        return object()
    def slot(self, rgb, slot):
        return self.slot_id
    def focus_active(self, rgb):
        return self.active
    def choose_research(self, slot, target, on_commit):
        self.calls += 1
        if self.after_commit:
            on_commit()
            raise ActionError("panel_not_found")
        if self.calls <= self.failures:
            raise ActionError("target_not_found")
        on_commit()
        if self.matches:
            self.slot_id = target
        return self.matches
    def choose_focus(self, on_commit):
        self.calls += 1
        on_commit()
        self.active = self.matches
        return self.matches
    def close_panel(self):
        pass


def setup(states=None, **ui_args):
    worker, ui = FakeWorker(), FakeUI(**ui_args)
    executor = Executor(FakeModel(states or [summary(), summary(11, researching=True)]),
                        worker, ui, timeout=0.035, poll_interval=0.001)
    return executor, worker, ui


@pytest.mark.parametrize("slot,tech,reason", [
    (0, "not_a_technology", "invalid_tech_id"),
    (-1, "construction1", "invalid_slot"), (4, "construction1", "invalid_slot"),
    (True, "construction1", "invalid_slot"), ("0", "construction1", "invalid_slot"),
])
def test_invalid_research_never_inputs(slot, tech, reason):
    executor, worker, ui = setup()
    result = executor.select_research(slot, tech)
    assert result["status"] == "rejected" and result["reason"] == reason
    assert not worker.events and not ui.calls


def test_invalid_focus_never_inputs():
    executor, worker, _ = setup()
    assert executor.select_focus("GER_rhineland")["reason"] == "invalid_focus_id"
    assert not worker.events


@pytest.mark.parametrize("status", ["stale", "unavailable"])
def test_stale_telemetry_rejected_before_input(status):
    executor, worker, _ = setup([summary(status=status)])
    result = executor.select_focus(FOCUS)
    assert result["status"] == "rejected" and not worker.events


@pytest.mark.parametrize("tech", list(RESEARCH))
def test_research_telemetry_and_correct_slot_confirm(tech):
    executor, worker, _ = setup()
    result = executor.select_research(0, tech)
    assert result["status"] == "confirmed" and result["accepted"]
    assert result["telemetry_confirmation"]["new_frame"]
    assert worker.events[-2:] == ["release", "end"]


def test_focus_ui_and_new_frame_confirm_zero_interval_is_not_sufficient_alone():
    executor, _, _ = setup([summary(), summary(11)])
    assert executor.select_focus(FOCUS)["status"] == "confirmed"
    executor, _, _ = setup([summary(), summary(11)], matches=False)
    result = executor.select_focus(FOCUS)
    assert result["status"] == "timed_out" and not result["ui_confirmation"]


@pytest.mark.parametrize("ui_matches,new_seq,researching", [(False, 11, True), (True, 10, True), (True, 11, False)])
def test_click_or_old_frame_never_confirms(ui_matches, new_seq, researching):
    valid, _ = research.confirmation(summary(), summary(new_seq, researching=researching),
                                    "construction1", 0, ui_matches)
    assert not valid


def test_confirmation_timeout_releases_and_recovers_without_reselection():
    executor, worker, ui = setup([summary()])
    result = executor.select_research(0, "construction1")
    assert result["status"] == "timed_out" and result["accepted"]
    assert ui.calls == 1 and "Escape" in worker.events and "release" in worker.events


def test_target_lookup_retry_limit():
    executor, worker, ui = setup(failures=5)
    result = executor.select_research(0, "construction1")
    assert result["status"] == "failed" and result["reason"] == "target_not_found"
    assert ui.calls == 2 and result["retry_count"] == 1


def test_retry_then_confirm():
    executor, _, ui = setup(failures=1)
    result = executor.select_research(0, "construction1")
    assert result["status"] == "confirmed" and ui.calls == 2 and result["retry_count"] == 1


def test_never_retry_after_possibly_committed_click():
    executor, _, ui = setup(after_commit=True)
    result = executor.select_research(0, "construction1")
    assert result["status"] == "uncertain" and ui.calls == 1 and result["retry_count"] == 0


@pytest.mark.parametrize("kind", ["research", "focus"])
def test_already_satisfied_no_selection(kind):
    executor, _, ui = setup([summary(researching=True)], slot="construction1", active=True)
    result = (executor.select_research(0, "construction1") if kind == "research"
              else executor.select_focus(FOCUS))
    assert result["status"] == "confirmed" and result["reason"] == "already_satisfied"
    assert ui.calls == 0


def test_same_tech_elsewhere_does_not_confirm_requested_slot():
    executor, _, ui = setup([summary(researching=True)])
    assert executor.select_research(0, "construction1")["reason"] == "target_in_other_slot"
    assert ui.calls == 0


def test_timeline_rollback_after_action_is_uncertain():
    executor, _, _ = setup([summary(), summary(9, researching=True)])
    assert executor.select_research(0, "construction1")["status"] == "uncertain"


@pytest.mark.parametrize("reason", ["loss_of_focus", "emergency_stop", "wrong_process"])
def test_safety_rejects_before_any_ui_operation(reason):
    executor, worker, ui = setup()
    worker.failure = reason
    result = executor.select_research(0, "construction1")
    assert result["status"] == "rejected" and result["reason"] == reason and ui.calls == 0


class Probe:
    reason = None
    def check(self, hwnd, pid):
        return self.reason


@pytest.mark.parametrize("reason", ["loss_of_focus", "emergency_stop"])
def test_independent_guard_latches_even_if_controller_stalls(reason):
    probe = Probe()
    guard = Guard(probe, 1, 1)
    try:
        guard.arm(2)
        probe.reason = reason
        time.sleep(0.05)
        probe.reason = None
        with pytest.raises(ActionError, match=reason):
            guard.check()
    finally:
        guard.close()


def test_independent_watchdog_and_deadline():
    guard = Guard(Probe(), 1, 1, watchdog_seconds=0.025)
    try:
        guard.arm(2)
        time.sleep(0.06)
        with pytest.raises(ActionError, match="watchdog_timeout"):
            guard.check()
        guard.disarm()
        guard.arm(0.025)
        time.sleep(0.06)
        with pytest.raises(ActionError, match="action_timeout"):
            guard.check()
    finally:
        guard.close()


def test_emergency_stop_requires_worker_restart():
    probe = Probe()
    guard = Guard(probe, 1, 1)
    try:
        probe.reason = "emergency_stop"
        with pytest.raises(ActionError):
            guard.arm(2)
        probe.reason = None
        with pytest.raises(ActionError, match="emergency_stop"):
            guard.arm(2)
    finally:
        guard.close()


def test_action_lock_rejects_concurrent_controller():
    executor, worker, _ = setup()
    with executor.lock:
        assert executor.select_focus(FOCUS)["reason"] == "executor_busy"
    assert not worker.events


def test_focus_completed_never_confirms_active_or_mutates():
    executor, worker, _ = setup([summary(completed=True)])
    assert executor.select_focus(FOCUS)["reason"] == "already_completed"
    assert not worker.events
    assert not focus.confirmation(summary(), summary(11, completed=True), FOCUS, True)[0]
