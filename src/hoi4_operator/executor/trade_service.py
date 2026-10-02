"""Bounded import commitments, scoped observations and repeat contract readback."""

from copy import deepcopy

from ..actions.trade import RESOURCES, COUNTRIES, SUPPORTED_FACTORIES, target
from ..actions.snapshots import SessionSnapshots
from .guard import ActionError
from .pipeline import ActionPipeline


class TradeExecutor:
    def __init__(self, executor, ui):
        self.executor, self.ui = executor, ui
        self.pipeline = ActionPipeline(executor)
        self.snapshots = SessionSnapshots("trade", "imports", "trade_id",
            ("resource", "country", "civilian_factories", "requested_amount"))

    def get_trade_state(self):
        def operation(tx):
            self.ui.observation_retries = 0
            with tx.stage("navigation"):
                view = self.ui.observe()
            tx.result.evidence.update(self.snapshots.replace(view, tx.fresh()["latest_seq"]))
            tx.result.evidence["ui_observation_retry_count"] = self.ui.observation_retries
            tx.result.accepted, tx.result.status = True, "confirmed"
        return self.pipeline.run("get_trade_state", operation)

    def set_trade_import(self, resource, country, civilian_factories):
        def operation(tx):
            self.ui.observation_retries = 0
            if (type(resource) is not str or resource not in RESOURCES or type(country) is not str or
                    country not in COUNTRIES or country not in RESOURCES[resource]["supported_countries"] or
                    type(civilian_factories) is not int or civilian_factories not in SUPPORTED_FACTORIES):
                raise ActionError("unsupported_target", "rejected")
            with tx.stage("navigation"):
                before = self.ui.observe()
            tx.result.evidence["before"] = deepcopy(before)
            wanted = (resource, country, civilian_factories, civilian_factories*8)
            if target(before) == wanted:
                tx.result.accepted, tx.result.status = True, "already_satisfied"
                tx.result.evidence["after"] = deepcopy(before)
                return
            with tx.stage("target_lookup"):
                delta = civilian_factories-before["imports"][0]["civilian_factories"]
                if before["available_civilian_factories"] < delta:
                    raise ActionError("insufficient_factory", "rejected")
                tx.fresh()
            with tx.stage("submit"):
                self.ui.change(before, civilian_factories, tx.commit)
            with tx.stage("readback"):
                after = self.ui.observe()
                if target(after) != wanted:
                    raise ActionError("unexpected_state_change", "uncertain")
            with tx.stage("confirmation"):
                repeated, now = self.ui.observe(), tx.fresh()
                if target(repeated) != wanted:
                    raise ActionError("unexpected_state_change", "uncertain")
                tx.result.status = "confirmed"
                tx.result.evidence["ui_observation_retry_count"] = self.ui.observation_retries
                tx.result.evidence.update(after=self.snapshots.replace(repeated, now["latest_seq"]),
                    ui_confirmation={"contract_country_resource_factories": True, "requested_and_delivered_amount": True,
                                     "reopened_contract_and_repeated_readback": True},
                    telemetry_confirmation={"before_seq": tx.before["latest_seq"], "after_seq": now["latest_seq"],
                                            "trade_state": "UNKNOWN; scoped GUI contract confirmation"})
        return self.pipeline.run("set_trade_import", operation, invalidate=self.snapshots.invalidate, cleanup=self.ui.close)
