"""Scoped trade contracts, independent readback and no duplicate submission."""

from copy import deepcopy
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from test_executor import FakeModel, FakeWorker
from test_production import telemetry
from hoi4_operator.actions.trade import target
from hoi4_operator.executor.guard import ActionError
from hoi4_operator.executor.service import Executor
from hoi4_operator.executor.templates import Templates
from hoi4_operator.executor.trade_service import TradeExecutor
from hoi4_operator.executor.trade_ui import TradeUI


class UI:
    def __init__(self):
        self.view = {"imports": [{"resource": "steel", "country": "SWE", "civilian_factories": 0,
                     "requested_amount": 0, "delivered_amount": 0}], "available_civilian_factories": 18}
        self.calls, self.reads, self.missed, self.error, self.changed_repeat = 0, 0, False, None, False
    def observe(self):
        self.reads += 1
        view = deepcopy(self.view)
        if self.changed_repeat and self.reads >= 3:
            view["imports"][0]["country"] = "other"
        return view
    def change(self, before, factories, commit):
        commit(); self.calls += 1
        if self.error: raise ActionError(*self.error)
        if not self.missed:
            self.view["imports"][0].update(civilian_factories=factories,
                                          requested_amount=factories*8, delivered_amount=factories*8)
    def close(self): pass


def setup(status="fresh", failure=None):
    ui, worker = UI(), FakeWorker(failure)
    return TradeExecutor(Executor(FakeModel([telemetry(status=status)]), worker, None), ui), ui, worker


def test_getter_scoped_identity_and_confirmed_import():
    service, ui, _ = setup()
    observed = service.get_trade_state()
    assert observed["imports"][0]["trade_id"].startswith("trade-")
    result = service.set_trade_import("steel", "SWE", 1)
    assert result["status"] == "confirmed" and target(result["after"]) == ("steel", "SWE", 1, 8)
    assert result["ui_confirmation"]["reopened_contract_and_repeated_readback"]
    assert result["telemetry_confirmation"]["trade_state"].startswith("UNKNOWN")
    assert service.set_trade_import("steel", "SWE", 1)["status"] == "already_satisfied"
    assert ui.calls == 1


@pytest.mark.parametrize("resource,country,count", [("oil","SWE",1),("steel","GER",1),
    ("steel","SWE",3),("steel","SWE",-1),("steel","SWE",True),("steel","SWE","1")])
def test_invalid_target_never_navigates_or_submits(resource, country, count):
    service, ui, _ = setup()
    assert service.set_trade_import(resource, country, count)["reason"] == "unsupported_target"
    assert ui.reads == ui.calls == 0


def test_insufficient_factory_and_cancellation_release():
    service, ui, _ = setup()
    ui.view["available_civilian_factories"] = 0
    assert service.set_trade_import("steel", "SWE", 1)["reason"] == "insufficient_factory"
    ui.view["imports"][0].update(civilian_factories=2, requested_amount=16, delivered_amount=16)
    assert service.set_trade_import("steel", "SWE", 0)["status"] == "confirmed"
    assert ui.calls == 1


@pytest.mark.parametrize("failure", ["missed", "repeat", "timeout", "focus"])
def test_uncertain_commit_never_retries(failure):
    service, ui, _ = setup()
    ui.missed = failure == "missed"
    ui.changed_repeat = failure == "repeat"
    if failure == "timeout": ui.error = ("worker_timeout", "timed_out")
    if failure == "focus": ui.error = ("loss_of_focus", "failed")
    result = service.set_trade_import("steel", "SWE", 1)
    assert result["status"] in {"uncertain", "timed_out"} and result["accepted"]
    assert result["retry_count"] == 0 and ui.calls == 1 and service.snapshots.view is None


def test_stale_telemetry_and_focus_guard_stop_before_input():
    service, ui, worker = setup(status="stale")
    assert service.set_trade_import("steel", "SWE", 1)["reason"] == "telemetry_stale"
    assert not worker.events and ui.calls == 0
    service, ui, _ = setup(failure="loss_of_focus")
    assert service.set_trade_import("steel", "SWE", 1)["reason"] == "loss_of_focus"
    assert ui.reads == ui.calls == 0


def test_real_contract_identity_amount_factories_and_main_readback():
    root = Path(__file__).resolve().parents[1]/"artifacts/phase3"
    class Base: worker = None
    ui = TradeUI(Base(), Templates(root/"templates"))
    def rgb(name): return np.asarray(Image.open(root/"captures"/name).convert("RGB")).copy()
    for count, name in enumerate(("zero", "one", "two")):
        capture = rgb("trade-swe-dialog-"+name+".jpg")
        assert target({"imports": [ui.read_dialog(capture)]}) == ("steel","SWE",count,count*8)
        capture[334:393,1440:1534] = 0
        with pytest.raises(ActionError, match="identity_mismatch"): ui.read_dialog(capture)
    main = ui.read_main(rgb("trade-steel-before.jpg"))
    assert main["available_civilian_factories"] == 18 and main["delivered_amount"] == 0
    main = ui.read_main(rgb("trade-steel-after-one.jpg"))
    assert main["available_civilian_factories"] == 17
    assert main["delivered_amount"] == main["requested_amount"] == 8
    capture = rgb("trade-swe-dialog-one.jpg")
    capture[583:605,1207:1238] = 0
    with pytest.raises(ActionError, match="readback_ambiguous"): ui.read_dialog(capture)


def test_dialog_factory_and_amount_must_agree_and_digits_must_be_unique():
    root = Path(__file__).resolve().parents[1]/"artifacts/phase3"
    class Base: worker = None
    ui = TradeUI(Base(), Templates(root/"templates"))
    one = np.asarray(Image.open(root/"captures/trade-swe-dialog-one.jpg").convert("RGB")).copy()
    two = np.asarray(Image.open(root/"captures/trade-swe-dialog-two.jpg").convert("RGB"))
    one[604:626,1223:1246] = two[604:626,1223:1246]
    with pytest.raises(ActionError, match="readback_ambiguous"): ui.read_dialog(one)
    ui.number(two, (1223,604,1246,626))  # Load calibrated glyphs.
    ui.digits[1] = list(ui.digits[2])
    with pytest.raises(ActionError, match="readback_ambiguous"): ui.number(two, (1223,604,1246,626))


def test_transient_dialog_repaint_is_bounded_observation_only(monkeypatch):
    class Base:
        worker = FakeWorker()
        def capture(self): return None
    ui = TradeUI(Base(), None)
    monkeypatch.setattr("hoi4_operator.executor.trade_ui.time.sleep", lambda _: None)
    calls = []
    def read(_):
        calls.append(1)
        if len(calls) == 1: raise ActionError("identity_mismatch", "rejected")
        return {"civilian_factories": 0}
    ui.read_dialog = read
    assert ui.settled_dialog()["civilian_factories"] == 0 and ui.observation_retries == 1
    ui.read_dialog = lambda _: (_ for _ in ()).throw(ActionError("identity_mismatch", "rejected"))
    with pytest.raises(ActionError, match="identity_mismatch"): ui.settled_dialog()
    assert ui.observation_retries == 2 and not ui.worker.events
