"""Queue transitions, identity lifetime and real construction capture regression."""

from copy import deepcopy
from pathlib import Path
import time

import numpy as np
from PIL import Image
import pytest

from test_executor import FakeModel, FakeWorker
from test_production import telemetry
from hoi4_operator.actions.construction import order
from hoi4_operator.executor.construction_service import ConstructionExecutor
from hoi4_operator.executor.construction_ui import ConstructionUI
from hoi4_operator.executor.guard import ActionError
from hoi4_operator.executor.service import Executor
from hoi4_operator.executor.templates import Templates


class UI:
    def __init__(self):
        self.view = {"queue": []}
        self.submits, self.missed, self.wrong, self.error = 0, False, False, None
    def open(self): return None
    def read(self, rgb): return deepcopy(self.view)
    def observe(self): return self.read(None)
    def close(self): pass
    def change(self, action, before, commit, *, state_id=None, building_type=None, target=None, direction=None):
        if self.error:
            raise ActionError(self.error, "rejected")
        commit()
        self.submits += 1
        if self.missed: return
        if action == "build":
            self.view["queue"].append({"state_id": 99 if self.wrong else state_id,
                                       "building_type": building_type, "count": 1})
        elif action == "cancel_construction":
            self.view["queue"].pop(target["position"])
        else:
            i = target["position"]
            j = i+(-1 if direction == "up" else 1)
            self.view["queue"][i], self.view["queue"][j] = self.view["queue"][j], self.view["queue"][i]


def setup(status="fresh"):
    ui, worker = UI(), FakeWorker()
    base = Executor(FakeModel([telemetry(status=status)]), worker, None, timeout=1)
    return ConstructionExecutor(base, ui), ui, worker


@pytest.mark.parametrize("state,building", [(64,"military_factory"),(65,"civilian_factory"),(66,"infrastructure")])
def test_supported_build_confirmed(state, building):
    service, ui, _ = setup()
    result = service.build(state, building)
    assert result["status"] == "confirmed" and ui.submits == 1
    assert result["after"]["queue"][0]["identity_signature"]
    assert result["after"]["stable_game_identity"] is False


@pytest.mark.parametrize("state,building,count", [(99,"military_factory",1),(64,"naval_base",1),
                                                  (True,"military_factory",1),(64,"military_factory",2)])
def test_unsupported_rejected_without_submit(state, building, count):
    service, ui, _ = setup()
    assert service.build(state, building, count)["status"] == "rejected"
    assert ui.submits == 0


def test_cancel_priority_and_boundary_already_satisfied():
    service, ui, _ = setup()
    service.build(64, "military_factory")
    second = service.build(66, "infrastructure")["after"]["queue"][1]["queue_item_id"]
    result = service.change_construction_priority(second, "up")
    assert result["status"] == "confirmed" and order(result["after"])[0][0] == 66
    first = result["after"]["queue"][0]["queue_item_id"]
    assert service.change_construction_priority(first, "up")["status"] == "already_satisfied"
    result = service.cancel_construction(first)
    assert result["status"] == "confirmed" and len(result["after"]["queue"]) == 1
    assert ui.submits == 4


def test_stale_queue_version_ttl_and_external_identity_change():
    service, ui, _ = setup()
    identity = service.build(64,"military_factory")["after"]["queue"][0]["queue_item_id"]
    service.get_construction()
    assert service.cancel_construction(identity)["reason"] == "snapshot_stale"
    identity = service.snapshots.view["queue"][0]["queue_item_id"]
    ui.view["queue"][0]["state_id"] = 66
    assert service.cancel_construction(identity)["reason"] == "snapshot_stale"
    service.snapshots.created = time.monotonic()-121
    assert service.cancel_construction(identity)["reason"] == "snapshot_stale"
    assert ui.submits == 1


@pytest.mark.parametrize("failure", ["missed", "wrong", "identity_mismatch"])
def test_failure_does_not_double_submit(failure):
    service, ui, _ = setup()
    if failure == "identity_mismatch": ui.error = failure
    else: setattr(ui, failure, True)
    result = service.build(64,"military_factory")
    assert result["status"] == ("rejected" if ui.error else "uncertain")
    assert ui.submits == (0 if ui.error else 1)
    assert service.snapshots.view is None


def test_stale_telemetry_and_duplicate_build_rejected():
    service, ui, worker = setup("stale")
    assert service.build(64,"military_factory")["reason"] == "telemetry_stale"
    assert not worker.events
    service, ui, _ = setup()
    service.build(64,"military_factory")
    assert service.build(64,"military_factory")["status"] == "rejected" and ui.submits == 1


def test_real_three_state_queue_and_unknown_identity_fail_closed():
    root = Path(__file__).resolve().parents[1] / "artifacts/phase3"
    class Base: worker = None
    ui = ConstructionUI(Base(), Templates(root/"templates"))
    rgb = np.asarray(Image.open(root/"captures/construction-three.jpg").convert("RGB")).copy()
    view = ui.read(rgb)
    assert order(view) == [(65,"civilian_factory",1),(66,"infrastructure",1),(64,"military_factory",1)]
    assert [q["assigned_civilian_factories"] for q in view["queue"]] == [15,3,0]
    rgb[293:310, 20:170] = 0
    with pytest.raises(ActionError, match="identity_mismatch"): ui.read(rgb)


def test_unrecognized_tail_cannot_be_reported_as_empty():
    root = Path(__file__).resolve().parents[1] / "artifacts/phase3"
    class Base: worker = None
    ui = ConstructionUI(Base(), Templates(root/"templates"))
    rgb = np.asarray(Image.open(root/"captures/construction-three.jpg").convert("RGB")).copy()
    # A grey, unknown queue row can have no matching cancel template or color.
    rgb[450:455,60:90] = 200
    with pytest.raises(ActionError, match="readback_ambiguous"): ui.read(rgb)


@pytest.mark.parametrize("state,building", [(64,"military_factory"),(65,"civilian_factory"),(66,"infrastructure")])
def test_real_cancel_modal_checks_target_before_ok(state, building):
    root = Path(__file__).resolve().parents[1] / "artifacts/phase3"
    class Base: worker = None
    ui = ConstructionUI(Base(), Templates(root/"templates"))
    rgb = np.asarray(Image.open(root/f"captures/construction-cancel-{state}.jpg").convert("RGB"))
    assert ui.cancel_confirmation(rgb, {"state_id": state, "building_type": building})
    with pytest.raises(ActionError, match="identity_mismatch"):
        ui.cancel_confirmation(rgb, {"state_id": 65 if state != 65 else 64, "building_type": building})
    with pytest.raises(ActionError, match="modal_blocked"):
        ui.read(rgb)
