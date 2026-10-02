"""Bounded line operations: exact transitions and real captured UI recognition."""

from copy import deepcopy
from pathlib import Path
import time

import numpy as np
from PIL import Image
import pytest

from test_executor import FakeModel, FakeWorker
from test_production import telemetry
from hoi4_operator.actions.production import signature
from hoi4_operator.actions.production_lines import validate_transition, unique_target
from hoi4_operator.executor.guard import ActionError
from hoi4_operator.executor.production_lines_service import ProductionLineExecutor
from hoi4_operator.executor.production_lines_ui import ProductionLinesUI
from hoi4_operator.executor.service import Executor
from hoi4_operator.executor.templates import Templates


def view():
    return {"lines": [{"equipment": name, "equipment_type": "calibrated", "position": i,
                       "factories": count, "identity_complete": True, "visible": True}
                      for i, (name, count) in enumerate([("Kar 98k式步枪", 10), ("支援装备", 2)])],
            "assigned_military_factories": 12, "military_factories": 28,
            "available_military_factories": 16, "scope": "fake military list"}


class UI:
    def __init__(self):
        self.view = view()
        self.submits = 0
        self.applies = True
        self.error = None
        self.extra_change = False

    def open(self):
        return None

    def read(self, rgb):
        return deepcopy(self.view)

    def observe(self):
        return self.read(None)

    def change(self, action, before, commit, *, equipment_id=None, target=None, direction=None):
        assert signature(before) == signature(self.view)
        commit()
        self.submits += 1
        if self.error:
            raise ActionError(*self.error)
        if not self.applies:
            return
        if action == "create_production_line":
            name = "Kar 98k式步枪" if equipment_id == "infantry_equipment_1" else "支援装备"
            self.view["lines"].append({"equipment": name, "equipment_type": "calibrated",
                "position": len(self.view["lines"]), "factories": 1, "identity_complete": True})
        elif action == "delete_production_line":
            self.view["lines"].pop(target["position"])
        else:
            i = target["position"]
            j = i + (-1 if direction == "up" else 1)
            self.view["lines"][i], self.view["lines"][j] = self.view["lines"][j], self.view["lines"][i]
        for i, line in enumerate(self.view["lines"]):
            line["position"] = i
        if self.extra_change:
            self.view["lines"][0]["factories"] += 1
        assigned = sum(line["factories"] for line in self.view["lines"])
        self.view.update(assigned_military_factories=assigned, available_military_factories=28-assigned)

    def close(self):
        pass


def setup(states=None):
    worker, ui = FakeWorker(), UI()
    base = Executor(FakeModel(states or [telemetry()]), worker, None, timeout=1)
    service = ProductionLineExecutor(base, ui)
    snapshot = service.get_production_lines()
    return service, ui, worker, snapshot


@pytest.mark.parametrize("equipment", ["infantry_equipment_1", "support_equipment_1"])
def test_create_exactly_one_new_line_with_new_identity(equipment):
    service, ui, _, snapshot = setup()
    result = service.create_production_line(equipment)
    assert result["status"] == "confirmed" and result["accepted"]
    assert len(result["diff"]["added"]) == 1 and ui.submits == 1
    assert result["after"]["snapshot_version"] > snapshot["snapshot_version"]
    assert result["after"]["ttl_seconds"] == 120
    assert all(line["identity_signature"] for line in result["after"]["lines"])


def test_delete_only_target_and_reject_old_snapshot():
    service, ui, _, snapshot = setup()
    target = snapshot["lines"][1]["line_id"]
    result = service.delete_production_line(target)
    assert result["status"] == "confirmed" and len(result["after"]["lines"]) == 1
    assert result["diff"]["removed"][0]["line_id"] == target
    assert service.delete_production_line(target)["reason"] == "snapshot_stale"
    assert ui.submits == 1


@pytest.mark.parametrize("index,direction", [(0, "down"), (1, "up")])
def test_reorder_reconciles_identity(index, direction):
    service, ui, _, snapshot = setup()
    result = service.reorder_production_line(snapshot["lines"][index]["line_id"], direction)
    assert result["status"] == "confirmed"
    assert [line["equipment"] for line in result["after"]["lines"]] == ["支援装备", "Kar 98k式步枪"]
    assert ui.submits == 1


def test_boundary_order_already_satisfied_has_no_submit():
    service, ui, _, snapshot = setup()
    result = service.reorder_production_line(snapshot["lines"][0]["line_id"], "up")
    assert result["status"] == "already_satisfied" and result["accepted"] and ui.submits == 0


@pytest.mark.parametrize("equipment", ["invalid", "artillery_equipment_1", ""])
def test_unsupported_equipment_rejected(equipment):
    service, ui, _, _ = setup()
    assert service.create_production_line(equipment)["reason"] == "unsupported_target"
    assert ui.submits == 0


def test_duplicate_equipment_disambiguated_by_counts_but_identical_rows_rejected():
    service, ui, _, snapshot = setup()
    result = service.create_production_line("infantry_equipment_1")
    assert result["status"] == "confirmed"
    duplicate = deepcopy(ui.view["lines"][-1])
    duplicate["position"] += 1
    ui.view["lines"].append(duplicate)
    ui.view["assigned_military_factories"] += 1
    snapshot = service.get_production_lines()
    result = service.delete_production_line(snapshot["lines"][-1]["line_id"])
    assert result["status"] == "rejected" and result["reason"] == "readback_ambiguous"
    assert ui.submits == 1


@pytest.mark.parametrize("failure", ["missed", "extra", "timeout", "backend"])
def test_unknown_submit_outcome_invalidates_snapshot_and_never_replays(failure):
    service, ui, _, _ = setup()
    ui.applies = failure != "missed"
    ui.extra_change = failure == "extra"
    if failure == "timeout":
        ui.error = ("worker_timeout", "timed_out")
    elif failure == "backend":
        ui.error = ("computer_use_error:vendor details 1234", "failed")
    result = service.create_production_line("infantry_equipment_1")
    assert result["status"] in {"uncertain", "timed_out"} and ui.submits == 1
    assert service.snapshots.view is None
    assert "vendor details" not in str(result)


def test_external_change_and_expired_id_stop_before_submission():
    service, ui, _, snapshot = setup()
    ui.view["lines"].reverse()
    for i, line in enumerate(ui.view["lines"]):
        line["position"] = i
    target = snapshot["lines"][0]["line_id"]
    assert service.delete_production_line(target)["reason"] == "snapshot_stale"
    service.snapshots.created = time.monotonic()-121
    assert service.delete_production_line(target)["reason"] == "snapshot_stale"
    assert ui.submits == 0


def test_stale_telemetry_no_navigation_or_submission():
    service, ui, worker, _ = setup([telemetry(status="stale")])
    assert service.create_production_line("infantry_equipment_1")["reason"] == "telemetry_stale"
    assert ui.submits == 0 and not worker.events


def test_real_calibration_full_military_counts_and_identity():
    root = Path(__file__).resolve().parents[1] / "artifacts/phase3"
    class Base:
        worker = None
    ui = ProductionLinesUI(Base(), Templates(root / "templates"))
    rgb = np.asarray(Image.open(root / "captures/military-compact.jpg").convert("RGB"))
    observed = ui.read(rgb)
    assert [line["factories"] for line in observed["lines"]] == [10, 2, 1, 2, 2, 1, 1, 1]
    assert observed["assigned_military_factories"] == 20
    assert observed["lines"][3]["equipment"] == "Panzer II A型"
    changed = rgb.copy()
    changed[375:398, 43:225] = 0
    with pytest.raises(ActionError, match="identity_mismatch"):
        ui.read(changed)


def test_current_expanded_numeric_and_factory_grid_proof():
    root = Path(__file__).resolve().parents[1] / "artifacts/phase3"
    class Base:
        worker = None
    ui = ProductionLinesUI(Base(), Templates(root / "templates"))
    rgb = np.asarray(Image.open(root / "captures/production-top.jpg").convert("RGB")).copy()
    assert ui.grid_count(rgb, 374) == 10
    rgb[409:424, 330:347] = 0
    with pytest.raises(ActionError, match="readback_failed"):
        ui.grid_count(rgb, 374)
