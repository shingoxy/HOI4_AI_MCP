"""Production identity, exact readback, safety and single-submit offline proof."""

from copy import deepcopy
from pathlib import Path
import time

import numpy as np
from PIL import Image
import pytest

from test_executor import FakeModel, FakeWorker, summary
from hoi4_operator.actions.production import ProductionSnapshots, signature
from hoi4_operator.executor.guard import ActionError
from hoi4_operator.executor.production_service import ProductionExecutor
from hoi4_operator.executor.production_ui import ProductionUI, HEADER_BOX, ROW_TOPS
from hoi4_operator.executor.service import Executor
from hoi4_operator.executor.templates import Templates

ROOT = Path(__file__).resolve().parents[1] / "artifacts/phase3b1"


def telemetry(seq=10, status="fresh", total=28):
    state = summary(seq, status=status)
    state["state"]["industry"] = {"military_factories": total}
    return state


class FakeProductionUI:
    def __init__(self):
        self.view = {"lines": [{"equipment": name, "position": i, "factories": n,
                               "maximum_assignable_factories": n+8, "visible": True,
                               "identity_source": "gui", "stable_game_identity": False}
                              for i, (name, n) in enumerate([("rifle", 10), ("support", 2)])],
                     "assigned_military_factories": 20, "military_factories": 28,
                     "available_military_factories": 8, "factory_count_evidence": "FAKE digits AND grid"}
        self.calls, self.failure, self.applies = 0, None, True
        self.observe_calls, self.alter_after = 0, None
    def open(self):
        if self.failure == "panel_not_found":
            raise ActionError(self.failure)
        return None
    def read(self, rgb):
        if self.failure and self.failure != "after_submit":
            raise ActionError(self.failure, "rejected")
        return deepcopy(self.view)
    def observe(self):
        self.observe_calls += 1
        if self.alter_after and self.observe_calls >= self.alter_after:
            self.view["lines"][0]["factories"] += 1
        return deepcopy(self.view)
    def adjust_one(self, position, increasing, on_commit, expected):
        assert signature(expected) == signature(self.view)
        self.calls += 1
        on_commit()
        if self.failure == "after_submit":
            raise ActionError("worker_timeout", "timed_out")
        if self.applies:
            self.view["lines"][position]["factories"] += 1 if increasing else -1
            self.view["assigned_military_factories"] += 1 if increasing else -1
    def close(self):
        pass


def setup(states=None):
    worker, ui = FakeWorker(), FakeProductionUI()
    base = Executor(FakeModel(states or [telemetry()]), worker, None, timeout=0.1)
    executor = ProductionExecutor(base, ui)
    snapshot = executor.get_production_lines()
    assert snapshot["status"] == "confirmed"
    return executor, worker, ui, snapshot["lines"][0]["line_id"]


def test_snapshot_ids_are_session_local_versioned_and_not_coordinates():
    executor, _, ui, ident = setup()
    snap = executor.get_production_lines()
    assert snap["lines"][0]["line_id"] != ident
    assert snap["snapshot_version"] == 2 and not snap["stable_game_identity"]
    assert executor.set_production_factory_count(ident, 11)["reason"] == "production_snapshot_stale"
    other = ProductionSnapshots().replace(ui.view, 10)
    assert other["lines"][0]["line_id"] != snap["lines"][0]["line_id"]


@pytest.mark.parametrize("count", [12, 8])
def test_increase_and_decrease_confirm_actual_readback(count):
    executor, worker, ui, ident = setup()
    result = executor.set_production_factory_count(ident, count)
    assert result["status"] == "confirmed" and result["before"]["factories"] == 10
    assert result["after"]["factories"] == count and result["ui_confirmation"]["repeated_readback"]
    assert ui.calls == 2 and result["retry_count"] == 0
    assert worker.events[-2:] == ["release", "end"]
    assert executor.set_production_factory_count(ident, count)["status"] == "already_satisfied"


def test_already_satisfied_never_adjusts():
    executor, _, ui, ident = setup()
    assert executor.set_production_factory_count(ident, 10)["status"] == "already_satisfied"
    assert ui.calls == 0


@pytest.mark.parametrize("count,reason", [(-1, "invalid_factory_count"), (True, "invalid_factory_count"),
                                        ("12", "invalid_factory_count"), (19, "insufficient_available_factories"),
                                        (16, "unsupported_factory_count"), (151, "insufficient_available_factories")])
def test_illegal_request_never_changes_factories(count, reason):
    executor, _, ui, ident = setup()
    result = executor.set_production_factory_count(ident, count)
    assert result["status"] == "rejected" and result["reason"] == reason and ui.calls == 0


def test_invalid_and_missing_line_ids():
    executor, _, ui, ident = setup()
    assert executor.set_production_factory_count("y-374", 11)["reason"] == "invalid_line_id"
    assert executor.set_production_factory_count(ident[:-4] + "9999", 11)["reason"] == "target_line_not_found"
    assert ui.calls == 0


@pytest.mark.parametrize("change", ["order", "equipment", "equipment_type", "factories", "expired"])
def test_snapshot_staleness_never_adjusts(change):
    executor, _, ui, ident = setup()
    if change == "order":
        ui.view["lines"].reverse()
    elif change == "expired":
        executor.snapshots.created = time.monotonic()-121
    else:
        ui.view["lines"][0][change] = "renamed" if change == "equipment" else 9
    assert executor.set_production_factory_count(ident, 11)["reason"] == "production_snapshot_stale"
    assert ui.calls == 0


@pytest.mark.parametrize("reason", ["gui_identity_mismatch", "target_not_visible", "production_snapshot_stale"])
def test_ui_preflight_errors_never_adjust(reason):
    executor, _, ui, ident = setup()
    ui.failure = reason
    assert executor.set_production_factory_count(ident, 11)["reason"] == reason and ui.calls == 0


def test_stale_telemetry_never_opens_worker():
    executor, worker, ui, ident = setup()
    executor.executor.model = FakeModel([telemetry(status="stale")])
    worker.events.clear()
    assert executor.set_production_factory_count(ident, 11)["reason"] == "stale_telemetry"
    assert not worker.events and not ui.calls


@pytest.mark.parametrize("reason", ["loss_of_focus", "emergency_stop", "watchdog_timeout"])
def test_existing_guard_stops_production(reason):
    executor, worker, ui, ident = setup()
    worker.failure = reason
    result = executor.set_production_factory_count(ident, 11)
    assert result["status"] == "rejected" and result["reason"] == reason and not ui.calls


def test_timeout_and_no_double_submission():
    executor, _, ui, ident = setup()
    ui.failure = "after_submit"
    result = executor.set_production_factory_count(ident, 12)
    assert result["status"] == "timed_out" and ui.calls == 1 and result["retry_count"] == 0
    assert executor.set_production_factory_count(ident, 12)["reason"] == "production_snapshot_stale"


def test_ui_clamp_or_missed_click_is_uncertain_without_retry():
    executor, _, ui, ident = setup()
    ui.applies = False
    result = executor.set_production_factory_count(ident, 12)
    assert result["status"] == "uncertain" and result["reason"] == "factory_count_not_applied"
    assert ui.calls == 1


def test_telemetry_ui_disagreement_after_submit_is_uncertain():
    executor, _, ui, ident = setup()
    executor.executor.model = FakeModel([telemetry(), telemetry(), telemetry(total=27)])
    result = executor.set_production_factory_count(ident, 11)
    assert result["status"] == "uncertain" and result["reason"] == "telemetry_ui_disagreement"
    assert ui.calls == 1


def test_second_post_action_readback_cannot_use_old_proof():
    executor, _, ui, ident = setup()
    ui.alter_after = 2
    assert executor.set_production_factory_count(ident, 11)["status"] == "uncertain"


def test_shared_lock_prevents_research_or_production_overlap():
    executor, _, ui, ident = setup()
    with executor.executor.lock:
        assert executor.set_production_factory_count(ident, 11)["reason"] == "executor_busy"
    assert ui.calls == 0


class ImageUI:
    worker = None


def reader():
    return ProductionUI(ImageUI(), Templates(ROOT / "templates"))


def test_real_production_fixture_parses_six_rows_and_available_factories():
    view = reader().read(np.array(Image.open(ROOT / "captures/production-before.jpg")))
    assert [x["factories"] for x in view["lines"]] == [10, 2, 1, 2, 2, 1]
    assert view["available_military_factories"] == 8
    assert all(x["equipment_game_id"] is None for x in view["lines"])
    assert view["lines"][0]["equipment_type"] == "步兵装备 I型"
    assert [x["action_supported"] for x in view["lines"]] == [True, True, False, True, True, False]


def test_truncated_equipment_identity_cannot_authorize_assignment():
    executor, _, ui, _ = setup()
    ui.view["lines"][0]["action_supported"] = False
    snapshot = executor.get_production_lines()
    result = executor.set_production_factory_count(snapshot["lines"][0]["line_id"], 11)
    assert result["status"] == "rejected" and result["reason"] == "ambiguous_production_identity"
    assert ui.calls == 0


def test_live_jpeg_edge_does_not_stretch_header_two_into_another_digit():
    rgb = np.array(Image.open(ROOT / "captures/readback-11-failure.jpg"))
    view = reader().read(rgb)
    assert view["assigned_military_factories"] == 21
    assert view["lines"][0]["factories"] == 11


def test_null_line_id_is_rejected_by_setter_without_opening_ui():
    executor, _, ui, _ = setup()
    result = executor.set_production_factory_count(None, 11)
    assert result["status"] == "rejected" and result["reason"] == "invalid_line_id"
    assert ui.calls == 0


@pytest.mark.parametrize("used", [*range(11, 20), 23])
def test_colored_header_and_factory_digits_from_real_calibration(used):
    rgb = np.array(Image.open(ROOT / "captures" / f"calibration-{used}.jpg"))
    ui = reader()
    assert ui.number(rgb, HEADER_BOX, header=True) == f"{used}/28"
    assert int(ui.number(rgb, (412, ROW_TOPS[0]+3, 460, ROW_TOPS[0]+25))) == used-10


def test_actual_snapshot_rejects_corrupt_number_and_wrong_identity():
    rgb = np.array(Image.open(ROOT / "captures/production-before.jpg"))
    rgb[377:399, 412:460] = 0
    with pytest.raises(ActionError, match="production_number_unreadable"):
        reader().read(rgb)
    rgb = np.array(Image.open(ROOT / "captures/production-before.jpg"))
    rgb[374:400, 42:225] = 0
    with pytest.raises(ActionError, match="gui_identity_mismatch"):
        reader().read(rgb)


def test_numeric_counter_cannot_confirm_when_grid_disagrees():
    rgb = np.array(Image.open(ROOT / "captures/production-before.jpg"))
    rgb[407:427, 325:351] = 0
    with pytest.raises(ActionError, match="production_count_disagreement"):
        reader().read(rgb)
