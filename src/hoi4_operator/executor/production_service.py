"""Serialized factory-count actions with exact, repeated GUI readback."""

from copy import deepcopy
import time
from uuid import uuid4

from ..actions.production import ProductionSnapshots, signature, telemetry_agrees
from .guard import ActionError
from .production_ui import SUPPORTED_MAX
from .recovery import recover


class ProductionExecutor:
    def __init__(self, executor, ui):
        self.executor, self.ui, self.worker = executor, ui, executor.worker
        self.snapshots = ProductionSnapshots()

    def get_production_lines(self):
        return self._run(None, None, setter=False)

    def set_production_factory_count(self, line_id, factories):
        return self._run(line_id, factories, setter=True)

    def _run(self, line_id, factories, *, setter):
        start = time.monotonic()
        result = {"accepted": False, "action_id": str(uuid4()), "status": "rejected",
                  "retry_count": 0, "telemetry_confirmation": {}, "ui_confirmation": {},
                  "timings_ms": {"snapshot": 0, "navigation": 0, "adjustment": 0, "confirmation": 0}}
        armed, committed = False, False
        adjustment = confirm = None
        def commit():
            nonlocal committed
            committed = True
            record = getattr(self.worker, "_record", None)
            if record:
                record("semantic_commit", action="set_production_factory_count")
        if not self.executor.lock.acquire(blocking=False):
            return {**result, "reason": "executor_busy", "duration_ms": 0}
        try:
            if setter:
                if isinstance(factories, bool) or not isinstance(factories, int) or factories < 0:
                    raise ActionError("invalid_factory_count", "rejected")
                target = self.snapshots.lookup(line_id)
                result.update(line_id=line_id, snapshot_version=self.snapshots.version)
            telemetry = self.executor.snapshot()
            if setter and telemetry["latest_seq"] < self.snapshots.view["telemetry_seq"]:
                raise ActionError("production_snapshot_stale", "rejected")
            self.worker.begin(self.executor.timeout)
            armed = True
            deadline = time.monotonic() + self.executor.timeout
            nav = time.monotonic()
            rgb = self.ui.open()
            result["timings_ms"]["navigation"] = round((time.monotonic()-nav)*1000)
            snap = time.monotonic()
            view = self.ui.read(rgb)
            if not telemetry_agrees(telemetry, view):
                raise ActionError("telemetry_ui_disagreement", "uncertain")
            result["timings_ms"]["snapshot"] = round((time.monotonic()-snap)*1000)
            if not setter:
                snapshot = self.snapshots.replace(view, telemetry["latest_seq"])
                result.update(accepted=True, status="confirmed", **snapshot)
                return result
            self.snapshots.validate(view)
            position = target["position"]
            if not target["visible"]:
                raise ActionError("target_not_visible", "rejected")
            if not view["lines"][position].get("action_supported", True):
                raise ActionError("ambiguous_production_identity", "rejected")
            result["before"] = deepcopy(target)
            limit = view["lines"][position]["maximum_assignable_factories"]
            if factories > limit:
                raise ActionError("insufficient_available_factories", "rejected")
            if factories > SUPPORTED_MAX:
                raise ActionError("unsupported_factory_count", "rejected")
            if target["factories"] == factories:
                if getattr(self.ui, "native_physical", False):
                    view = self.ui.verify_target_grid(view, position)
                result.update(accepted=True, status="already_satisfied", after=deepcopy(target),
                              ui_confirmation={"same_equipment_and_position": True,
                                               "readback_factories": factories,
                                               "count_sources": view["factory_count_evidence"]},
                              telemetry_confirmation={"after_seq": telemetry["latest_seq"],
                                                      "military_factories": view["military_factories"],
                                                      "totals_agree": True,
                                                      "per_line_count": "UNKNOWN; confirmation source is GUI"})
                return result
            result["accepted"] = True
            adjustment = time.monotonic()
            original = deepcopy(view)
            # Each click is a distinct one-factory step. Read it back before
            # the next step. A missed or uncertain click is never submitted twice.
            for _ in range(abs(factories-target["factories"])):
                if time.monotonic() >= deadline:
                    raise ActionError("action_timeout", "timed_out")
                self.worker.check()
                now = self.executor.snapshot()
                if now["latest_seq"] < telemetry["latest_seq"]:
                    raise ActionError("timeline_changed", "uncertain")
                if not telemetry_agrees(now, view):
                    raise ActionError("telemetry_ui_disagreement", "uncertain")
                increasing = factories > view["lines"][position]["factories"]
                expected = deepcopy(view)
                expected["lines"][position]["factories"] += 1 if increasing else -1
                expected["assigned_military_factories"] += 1 if increasing else -1
                self.ui.adjust_one(position, increasing, commit, view)
                after = self.ui.observe()
                result["after"] = deepcopy(after["lines"][position])
                if (signature(after) != signature(expected) or
                        after["assigned_military_factories"] != expected["assigned_military_factories"] or
                        after["military_factories"] != original["military_factories"]):
                    raise ActionError("factory_count_not_applied", "uncertain")
                view = after
            result["timings_ms"]["adjustment"] = round((time.monotonic()-adjustment)*1000)
            confirm = time.monotonic()
            # Two independent post-input observations, with fresh telemetry;
            # the log does not expose per-line count, so it is not credited for it.
            after = self.ui.observe()
            current = self.executor.snapshot()
            if current["latest_seq"] < telemetry["latest_seq"]:
                raise ActionError("timeline_changed", "uncertain")
            if not telemetry_agrees(current, after):
                raise ActionError("telemetry_ui_disagreement", "uncertain")
            if signature(after) != signature(view) or after["lines"][position]["factories"] != factories:
                raise ActionError("post_action_ui_mismatch", "uncertain")
            if getattr(self.ui, "native_physical", False):
                after = self.ui.verify_target_grid(after, position)
            self.snapshots.update(after)
            result.update(status="confirmed", after=deepcopy(self.snapshots.view["lines"][position]),
                          ui_confirmation={"same_equipment_and_position": True, "requested_factories": factories,
                                           "readback_factories": factories, "repeated_readback": True,
                                           "count_sources": after["factory_count_evidence"]},
                          telemetry_confirmation={"before_seq": telemetry["latest_seq"], "after_seq": current["latest_seq"],
                                                  "military_factories": after["military_factories"], "totals_agree": True,
                                                  "per_line_count": "UNKNOWN; confirmation source is GUI"})
            result["timings_ms"]["confirmation"] = round((time.monotonic()-confirm)*1000)
            return result
        except ActionError as exc:
            result.update(status=exc.status, reason=exc.reason)
            if committed:
                self.snapshots.invalidate()
                if exc.status in {"failed", "rejected"}:
                    result.update(status="uncertain", accepted=True)
            elif exc.status == "rejected":
                result["accepted"] = False
            if armed:
                result["recovery"] = recover(self.worker)
            return result
        except Exception as exc:
            result.update(status="uncertain" if committed else "failed", reason="executor_error:"+type(exc).__name__)
            if committed:
                self.snapshots.invalidate()
            if armed:
                result["recovery"] = recover(self.worker)
            return result
        finally:
            result["mutation_submitted"] = committed
            if adjustment is not None and not result["timings_ms"]["adjustment"]:
                result["timings_ms"]["adjustment"] = round(((confirm or time.monotonic())-adjustment)*1000)
            if confirm is not None and not result["timings_ms"]["confirmation"]:
                result["timings_ms"]["confirmation"] = round((time.monotonic()-confirm)*1000)
            if armed:
                try:
                    if setter and result["status"] in {"confirmed", "already_satisfied"}:
                        self.ui.close()
                except ActionError:
                    result["cleanup"] = "panel_close_safety_stop"
                finally:
                    self.worker.end()
            result["duration_ms"] = round((time.monotonic()-start)*1000)
            self.executor.lock.release()
