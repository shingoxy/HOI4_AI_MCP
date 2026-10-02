"""Semantic law/advisor transactions; repeated identity readback, no retries."""

from copy import deepcopy
import math

from ..actions.politics import LAWS, ADVISORS, advisor_order
from ..actions.snapshots import SessionSnapshots
from .guard import ActionError
from .pipeline import ActionPipeline


class PoliticsExecutor:
    def __init__(self, executor, ui):
        self.executor, self.ui = executor, ui
        self.pipeline = ActionPipeline(executor)
        self.snapshots = SessionSnapshots("advisor", "slots", "slot_id", ("advisor_id",))

    @staticmethod
    def pp(telemetry):
        value = telemetry["state"].get("politics", {}).get("political_power")
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ActionError("readback_ambiguous", "rejected")
        return value

    def change_economy_law(self, law_id):
        return self._law("economy", law_id)

    def change_conscription_law(self, law_id):
        return self._law("conscription", law_id)

    def _law(self, group, target):
        def operation(tx):
            if type(target) is not str or target not in LAWS or LAWS[target]["group"] != group:
                raise ActionError("unsupported_target", "rejected")
            with tx.stage("navigation"):
                before = self.ui.open_laws(group)
            tx.result.evidence["before"] = deepcopy(before)
            if before["current_law"] == target:
                tx.result.accepted, tx.result.status = True, "already_satisfied"
                tx.result.evidence["after"] = deepcopy(before)
                return
            with tx.stage("target_lookup"):
                now = tx.fresh()
                if self.pp(now) < LAWS[target]["cost"]:
                    raise ActionError("insufficient_political_power", "rejected")
                support = now["state"].get("politics", {}).get("war_support")
                if type(support) not in (int, float) or not math.isfinite(support):
                    raise ActionError("readback_ambiguous", "rejected")
                threshold = LAWS[target]["minimum_war_support"]
                if ((threshold > 0 and support <= threshold) or not before["choices"][target]["enabled"]):
                    raise ActionError("requirements_not_met", "rejected")
            with tx.stage("submit"):
                self.ui.change_law(group, target, before, tx.commit)
            with tx.stage("readback"):
                after = self.ui.open_laws(group)
                if after["current_law"] != target:
                    raise ActionError("readback_failed", "uncertain")
            with tx.stage("confirmation"):
                repeated, now = self.ui.open_laws(group), tx.fresh()
                if repeated["current_law"] != target:
                    raise ActionError("unexpected_state_change", "uncertain")
                tx.result.status = "confirmed"
                tx.result.evidence.update(after=repeated, ui_confirmation={"current_law_identity": target, "repeated_readback": True},
                    telemetry_confirmation={"before_seq": tx.before["latest_seq"], "after_seq": now["latest_seq"],
                        "political_power_before": self.pp(tx.before), "political_power_after": self.pp(now),
                        "active_law": "UNKNOWN; GUI confirms law ID"})
        return self.pipeline.run("change_"+group+"_law", operation, cleanup=self.ui.close)

    def get_advisors(self):
        def operation(tx):
            with tx.stage("navigation"):
                view = self.ui.advisors()
            tx.result.evidence.update(self.snapshots.replace(view, tx.fresh()["latest_seq"]), catalog=deepcopy(ADVISORS))
            tx.result.accepted, tx.result.status = True, "confirmed"
        return self.pipeline.run("get_advisors", operation)

    def hire_advisor(self, advisor_id):
        def operation(tx):
            if type(advisor_id) is not str or advisor_id not in ADVISORS:
                raise ActionError("unsupported_target", "rejected")
            with tx.stage("navigation"):
                before = self.ui.advisors()
            tx.result.evidence["before"] = deepcopy(before)
            identities = advisor_order(before)
            if advisor_id in identities:
                tx.result.accepted, tx.result.status = True, "already_satisfied"
                tx.result.evidence["after"] = deepcopy(before)
                return
            if None not in identities:
                raise ActionError("requirements_not_met", "rejected")
            with tx.stage("target_lookup"):
                if self.pp(tx.fresh()) < ADVISORS[advisor_id]["cost"]:
                    raise ActionError("insufficient_political_power", "rejected")
            with tx.stage("submit"):
                self.ui.hire(advisor_id, before, tx.commit)
            with tx.stage("readback"):
                after = self.ui.advisors()
                expected = list(identities)
                expected[expected.index(None)] = advisor_id
                if advisor_order(after) != expected:
                    raise ActionError("unexpected_state_change", "uncertain")
            with tx.stage("confirmation"):
                repeated, now = self.ui.advisors(), tx.fresh()
                if advisor_order(repeated) != expected:
                    raise ActionError("unexpected_state_change", "uncertain")
                tx.result.status = "confirmed"
                tx.result.evidence.update(after=self.snapshots.replace(repeated, now["latest_seq"]),
                    ui_confirmation={"exact_three_slot_transition": True, "repeated_readback": True},
                    telemetry_confirmation={"before_seq": tx.before["latest_seq"], "after_seq": now["latest_seq"],
                        "political_power_before": self.pp(tx.before), "political_power_after": self.pp(now),
                        "advisor_state": "UNKNOWN; GUI confirms portrait identity"})
        return self.pipeline.run("hire_advisor", operation, invalidate=self.snapshots.invalidate, cleanup=self.ui.close)
