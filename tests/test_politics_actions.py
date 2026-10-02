"""Normal-law/advisor semantics, costs, disabled choices, no blind submission."""

from copy import deepcopy
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from test_executor import FakeModel, FakeWorker
from test_production import telemetry
from hoi4_operator.actions.politics import LAWS, advisor_order
from hoi4_operator.executor.guard import ActionError
from hoi4_operator.executor.politics_service import PoliticsExecutor
from hoi4_operator.executor.politics_ui import PoliticsUI
from hoi4_operator.executor.service import Executor
from hoi4_operator.executor.templates import Templates


class UI:
    def __init__(self):
        self.current = {"economy": "partial_economic_mobilisation", "conscription": "limited_conscription"}
        self.slots = [None, None, None]
        self.disabled, self.missed, self.wrong, self.calls = False, False, False, 0
    def open_laws(self, group):
        return {"current_law": self.current[group], "choices": {law: {"enabled": not self.disabled}
                for law, data in LAWS.items() if data["group"] == group}}
    def change_law(self, group, target, before, commit):
        commit(); self.calls += 1
        if not self.missed: self.current[group] = "other" if self.wrong else target
    def advisors(self): return {"slots": [{"position": i, "advisor_id": a} for i, a in enumerate(self.slots)]}
    def hire(self, target, before, commit):
        if self.disabled: raise ActionError("requirements_not_met", "rejected")
        commit(); self.calls += 1
        if not self.missed: self.slots[self.slots.index(None)] = "other" if self.wrong else target
    def close(self): pass


def setup(pp=300, support=.35, status="fresh"):
    state = telemetry(status=status)
    state["state"]["politics"] = {"political_power": pp, "war_support": support}
    ui, worker = UI(), FakeWorker()
    return PoliticsExecutor(Executor(FakeModel([state]), worker, None), ui), ui, worker


@pytest.mark.parametrize("group,target", [("economy","low_economic_mobilisation"),("conscription","volunteer_only")])
def test_confirmed_and_law_idempotence(group, target):
    service, ui, _ = setup()
    action = getattr(service, "change_"+group+"_law")
    assert action(target)["status"] == "confirmed"
    assert action(target)["status"] == "already_satisfied" and ui.calls == 1


@pytest.mark.parametrize("pp,support,disabled,reason", [(149,.35,False,"insufficient_political_power"),
    (300,.1,False,"requirements_not_met"),(300,.35,True,"requirements_not_met")])
def test_law_preconditions(pp, support, disabled, reason):
    service, ui, _ = setup(pp, support)
    ui.disabled = disabled
    assert service.change_economy_law("low_economic_mobilisation")["reason"] == reason
    assert ui.calls == 0


def test_invalid_law_stale_and_no_double_submit():
    service, ui, _ = setup()
    assert service.change_economy_law("volunteer_only")["status"] == "rejected"
    ui.missed = True
    assert service.change_economy_law("low_economic_mobilisation")["status"] == "uncertain"
    assert ui.calls == 1
    service, ui, worker = setup(status="stale")
    assert service.change_economy_law("low_economic_mobilisation")["reason"] == "telemetry_stale"
    assert not worker.events


def test_advisor_hire_getter_and_already_satisfied():
    service, ui, _ = setup()
    view = service.get_advisors()
    assert view["slots"][0]["slot_id"].startswith("advisor-")
    result = service.hire_advisor("advisor_schacht")
    assert result["status"] == "confirmed" and advisor_order(result["after"]) == ["advisor_schacht", None, None]
    assert service.hire_advisor("advisor_schacht")["status"] == "already_satisfied" and ui.calls == 1


@pytest.mark.parametrize("failure,reason", [("invalid","unsupported_target"),("occupied","requirements_not_met"),
    ("poor","insufficient_political_power"),("disabled","requirements_not_met"),("wrong","unexpected_state_change")])
def test_advisor_rejections_and_identity_mismatch(failure, reason):
    service, ui, _ = setup(pp=74 if failure == "poor" else 300)
    if failure == "occupied": ui.slots = ["x","y","z"]
    if failure == "disabled": ui.disabled = True
    if failure == "wrong": ui.wrong = True
    result = service.hire_advisor("unknown" if failure == "invalid" else "advisor_schacht")
    assert result["reason"] == reason and ui.calls == (1 if failure == "wrong" else 0)
    if failure == "wrong": assert result["status"] == "uncertain" and service.snapshots.view is None


def test_real_law_and_advisor_captures():
    root = Path(__file__).resolve().parents[1]/"artifacts/phase3"
    class Base: worker = None
    ui = PoliticsUI(Base(), Templates(root/"templates"))
    def rgb(name): return np.asarray(Image.open(root/"captures"/name).convert("RGB"))
    for group, old, target in [("economy","partial_economic_mobilisation","low_economic_mobilisation"),
                               ("conscription","limited_conscription","volunteer_only")]:
        view = ui.read_laws(rgb(group+"-list-before.jpg"), group)
        assert view["current_law"] == old and view["choices"][target]["enabled"]
        assert ui.law_confirmation(rgb(group+"-confirm.jpg"), old, target)
        with pytest.raises(ActionError, match="identity_mismatch"):
            ui.law_confirmation(rgb(group+"-confirm.jpg"), target, old)
    assert advisor_order(ui.read_advisors(rgb("politics-before.jpg"))) == [None]*3
    assert advisor_order(ui.read_advisors(rgb("advisor-hired-calibration.jpg"))) == ["advisor_schacht",None,None]
    assert ui.advisor_option(rgb("advisor-list-before.jpg"))
    disabled = rgb("advisor-list-before.jpg").copy()
    disabled[320:325,974:979] = [220,20,20]
    assert not ui.advisor_option(disabled)
