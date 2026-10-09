"""Bounded semantic queue operations, verified complete queue transitions."""

from copy import deepcopy

from ..actions.construction import STATES, BUILDINGS, order, validate
from ..actions.snapshots import SessionSnapshots
from .guard import ActionError
from .pipeline import ActionPipeline


class ConstructionExecutor:
    def __init__(self, executor, ui):
        self.executor, self.ui = executor, ui
        self.pipeline = ActionPipeline(executor)
        self.snapshots = SessionSnapshots("construction", "queue", "queue_item_id", ("state_id", "building_type", "count"))

    def get_construction(self):
        def operation(tx):
            with tx.stage("navigation"):
                rgb = self.ui.open()
            with tx.stage("readback"):
                view = self.ui.read(rgb)
                tx.result.evidence.update(self.snapshots.replace(view, tx.fresh()["latest_seq"]))
            tx.result.accepted, tx.result.status = True, "confirmed"
        return self.pipeline.run("get_construction", operation)

    def build(self, state_id, building_type, count=1):
        return self._change("build", state_id=state_id, building_type=building_type, count=count)

    def cancel_construction(self, queue_item_id):
        return self._change("cancel_construction", queue_item_id=queue_item_id)

    def change_construction_priority(self, queue_item_id, direction):
        return self._change("change_construction_priority", queue_item_id=queue_item_id, direction=direction)

    def _change(self, action, *, state_id=None, building_type=None, count=1, queue_item_id=None, direction=None):
        def operation(tx):
            target = None
            if action == "build":
                if (type(state_id) is not int or state_id not in STATES or type(building_type) is not str or building_type not in BUILDINGS or
                        type(count) is not int or count != 1):
                    raise ActionError("unsupported_target", "rejected")
            else:
                if action == "change_construction_priority" and direction not in {"up", "down"}:
                    raise ActionError("unsupported_target", "rejected")
                target = self.snapshots.lookup(queue_item_id)
            with tx.stage("navigation"):
                rgb = self.ui.open()
            with tx.stage("target_lookup"):
                before = self.ui.read(rgb)
                tx.result.evidence["before"] = deepcopy(before)
                if target:
                    self.snapshots.validate(before, tx.before["latest_seq"])
                    if order(before).count((target["state_id"], target["building_type"], target["count"])) != 1:
                        raise ActionError("readback_ambiguous", "rejected")
                    if action == "change_construction_priority" and (
                            target["position"] == 0 and direction == "up" or
                            target["position"] == len(before["queue"])-1 and direction == "down"):
                        tx.result.accepted, tx.result.status = True, "already_satisfied"
                        tx.result.evidence["after"] = deepcopy(before)
                        return
                elif any(item["state_id"] == state_id and item["building_type"] == building_type for item in before["queue"]):
                    raise ActionError("unsupported_target", "rejected")
                tx.fresh()
            with tx.stage("submit"):
                try:
                    def commit():
                        tx.fresh()
                        tx.commit()
                    self.ui.change(action, before, commit, state_id=state_id, building_type=building_type,
                                   target=target, direction=direction)
                finally:
                    reader=getattr(self.ui,'tool_reader',None)
                    if action=='build' and reader and reader.evidence:
                        tx.result.evidence['construction_tool']=deepcopy(reader.evidence)
            with tx.stage("readback"):
                after = self.ui.observe()
                diff = validate(before, after, action, state_id=state_id, building_type=building_type,
                                target=target, direction=direction)
            with tx.stage("confirmation"):
                repeated, telemetry = self.ui.observe(), tx.fresh()
                if order(after) != order(repeated):
                    raise ActionError("unexpected_state_change", "uncertain")
                tx.result.status = "confirmed"
                tx.result.evidence.update(after=self.snapshots.replace(repeated, telemetry["latest_seq"]), diff=diff,
                    ui_confirmation={"exact_queue_transition": True, "repeated_readback": True},
                    telemetry_confirmation={"before_seq": tx.before["latest_seq"], "after_seq": telemetry["latest_seq"],
                                            "queue_state": "UNKNOWN; GUI confirmation"})
        return self.pipeline.run(action, operation, invalidate=self.snapshots.invalidate, cleanup=self.ui.close)
