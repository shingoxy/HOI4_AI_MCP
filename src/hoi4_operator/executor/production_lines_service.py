"""Whole military-list creation/deletion/order with existing snapshot identity."""

from copy import deepcopy

from ..actions.equipment import EQUIPMENT
from ..actions.production import signature, telemetry_agrees
from ..actions.production_lines import unique_target, validate_transition
from .guard import ActionError
from .pipeline import ActionPipeline
from .production_service import ProductionExecutor


class ProductionLineExecutor(ProductionExecutor):
    def __init__(self, executor, ui):
        super().__init__(executor, ui)
        self.pipeline = ActionPipeline(executor)

    def get_production_lines(self):
        def operation(tx):
            with tx.stage("navigation"):
                rgb = self.ui.open()
            with tx.stage("readback"):
                view = self.ui.read(rgb)
                if not telemetry_agrees(tx.fresh(), view):
                    raise ActionError("readback_failed", "uncertain")
                snapshot = self.snapshots.replace(view, tx.before["latest_seq"])
            tx.result.accepted, tx.result.status = True, "confirmed"
            tx.result.evidence.update(snapshot)
        return self.pipeline.run("get_production_lines", operation)

    def create_production_line(self, equipment_id):
        return self._change("create_production_line", equipment_id=equipment_id)

    def delete_production_line(self, line_id):
        return self._change("delete_production_line", line_id=line_id)

    def reorder_production_line(self, line_id, direction):
        return self._change("reorder_production_line", line_id=line_id, direction=direction)

    def _change(self, action, *, equipment_id=None, line_id=None, direction=None):
        def operation(tx):
            target = None
            if action == "create_production_line":
                entry = EQUIPMENT.get(equipment_id)
                if not entry or not entry["supported"]:
                    raise ActionError("unsupported_target", "rejected")
                equipment = entry["display_identity"]
            else:
                if action == "reorder_production_line" and direction not in {"up", "down"}:
                    raise ActionError("unsupported_target", "rejected")
                target = self.snapshots.lookup(line_id)
                equipment = target["equipment"]
                if tx.before["latest_seq"] < self.snapshots.view["telemetry_seq"]:
                    raise ActionError("snapshot_stale", "rejected")
            with tx.stage("navigation"):
                rgb = self.ui.open()
            with tx.stage("target_lookup"):
                before = self.ui.read(rgb)
                if not telemetry_agrees(tx.fresh(), before):
                    raise ActionError("readback_failed", "uncertain")
                if target:
                    self.snapshots.validate(before)
                    index = unique_target(before, target)
                    if not target.get("identity_complete", True):
                        raise ActionError("readback_ambiguous", "rejected")
                    if action == "reorder_production_line" and (
                            index == 0 and direction == "up" or
                            index == len(before["lines"])-1 and direction == "down"):
                        tx.result.accepted, tx.result.status = True, "already_satisfied"
                        tx.result.evidence.update(before=deepcopy(before), after=deepcopy(before))
                        return
                tx.result.evidence["before"] = deepcopy(before)
            with tx.stage("submit"):
                # UI revalidates identity immediately before its single submit.
                self.ui.change(action, before, tx.commit, equipment_id=equipment_id,
                               target=target, direction=direction)
            with tx.stage("readback"):
                after = self.ui.observe()
                diff = validate_transition(before, after, action, target=target,
                                           equipment=equipment, direction=direction)
            with tx.stage("confirmation"):
                repeated = self.ui.observe()
                telemetry = tx.fresh()
                if signature(after) != signature(repeated) or not telemetry_agrees(telemetry, repeated):
                    raise ActionError("unexpected_state_change", "uncertain")
                snapshot = self.snapshots.replace(repeated, telemetry["latest_seq"])
                tx.result.status = "confirmed"
                tx.result.evidence.update(after=snapshot, diff=diff,
                    ui_confirmation={"exact_list_transition": True, "repeated_readback": True,
                                     "scope": repeated["scope"]},
                    telemetry_confirmation={"before_seq": tx.before["latest_seq"],
                        "after_seq": telemetry["latest_seq"], "totals_agree": True,
                        "per_line_state": "UNKNOWN; GUI confirmation"})
        return self.pipeline.run(action, operation, invalidate=self.snapshots.invalidate, cleanup=self.ui.close)
