"""Serialized semantic actions with bounded navigation retry and telemetry proof."""

import math
import threading
import time
from uuid import uuid4

from ..actions import focus, research
from .catalog import FOCUS, RESEARCH
from .guard import ActionError
from .recovery import recover


class Executor:
    def __init__(self, model, worker, ui, *, timeout=90.0, retries=1, poll_interval=0.25):
        if not math.isfinite(timeout) or timeout <= 0 or retries not in (0, 1):
            raise ValueError("invalid action limits")
        self.model, self.worker, self.ui = model, worker, ui
        self.timeout, self.retries, self.poll_interval = timeout, retries, poll_interval
        self.lock = threading.Lock()

    def snapshot(self):
        self.model.poll()
        summary = self.model.summary()
        if summary.get("status") != "fresh":
            raise ActionError("stale_telemetry" if summary.get("status") == "stale"
                              else "telemetry_unavailable", "rejected")
        if summary.get("parser_errors") or summary.get("log_read_error"):
            raise ActionError("telemetry_error", "rejected")
        state = summary.get("state") or {}
        if state.get("country") != "GER" or state.get("protocol_version") != 2:
            raise ActionError("unsupported_telemetry", "rejected")
        return summary

    def select_research(self, slot, tech_id):
        return self._execute("research", slot=slot, target=tech_id)

    def select_focus(self, focus_id):
        return self._execute("focus", slot=None, target=focus_id)

    def _execute(self, kind, *, slot, target):
        started, action_id = time.monotonic(), str(uuid4())
        result = {"accepted": False, "action_id": action_id, "status": "rejected",
                  "action": "select_" + kind, "target": target, "retry_count": 0,
                  "telemetry_confirmation": {}, "ui_confirmation": False}
        armed = False
        committed = False
        def on_commit():
            nonlocal committed
            committed = True
        if not self.lock.acquire(blocking=False):
            return {**result, "reason": "executor_busy", "duration_ms": 0}
        try:
            if kind == "research":
                if target not in RESEARCH:
                    raise ActionError("invalid_tech_id", "rejected")
                if isinstance(slot, bool) or not isinstance(slot, int) or not 0 <= slot < 4:
                    raise ActionError("invalid_slot", "rejected")
            elif target != FOCUS:
                raise ActionError("invalid_focus_id", "rejected")
            before = self.snapshot()
            if kind == "research":
                if slot >= before["state"]["research"]["slot_count"]:
                    raise ActionError("slot_unavailable", "rejected")
                item = research.technology(before, target)
                if item is None:
                    raise ActionError("target_telemetry_unavailable", "rejected")
                if item["researched"]:
                    raise ActionError("already_researched", "rejected")
            else:
                if before["state"]["focus"]["tracked_id"] != target:
                    raise ActionError("target_telemetry_unavailable", "rejected")
                if before["state"]["focus"]["completed"]:
                    raise ActionError("already_completed", "rejected")
            self.worker.begin(self.timeout)
            armed = True
            end = time.monotonic() + self.timeout
            if kind == "research":
                rgb = self.ui.open_panel("research")
                matches = self.ui.slot(rgb, slot) == target
                if item["researching"]:
                    if not matches:
                        raise ActionError("target_in_other_slot", "rejected")
                    result.update(status="confirmed", accepted=True, reason="already_satisfied",
                                  ui_confirmation=True, telemetry_confirmation={
                                      "seq": before["latest_seq"], "researching": True,
                                      "slot": slot, "ui_slot_matches": True})
                    return result
            else:
                rgb = self.ui.open_panel("politics")
                if self.ui.focus_active(rgb):
                    result.update(status="confirmed", accepted=True, reason="already_satisfied",
                                  ui_confirmation=True, telemetry_confirmation={
                                      "seq": before["latest_seq"], "completed": False,
                                      "ui_active_name_and_cancel": True})
                    return result
            result["accepted"] = True
            for attempt in range(self.retries + 1):
                self.worker.check()
                try:
                    # Only target lookup/navigation can retry. Once the start
                    # click may have happened, never select a second time.
                    matches = (self.ui.choose_research(slot, target, on_commit) if kind == "research"
                               else self.ui.choose_focus(on_commit))
                    break
                except ActionError as exc:
                    if committed or exc.reason not in {"target_not_found", "panel_not_found"} or attempt == self.retries:
                        raise
                    result["retry_count"] += 1
                    recover(self.worker)
            result["ui_confirmation"] = matches
            while time.monotonic() < end:
                self.worker.check()
                after = self.snapshot()
                if after["latest_seq"] < before["latest_seq"]:
                    raise ActionError("timeline_changed", "uncertain")
                valid, evidence = (research.confirmation(before, after, target, slot, matches)
                                   if kind == "research" else focus.confirmation(before, after, target, matches))
                result["telemetry_confirmation"] = evidence
                if valid:
                    # Reobserve after the new log frame: intermediate GUI proof
                    # cannot survive a later save/load or a user changing selection.
                    rgb = self.ui.open_panel("research" if kind == "research" else "politics")
                    matches = (self.ui.slot(rgb, slot) == target if kind == "research"
                               else self.ui.focus_active(rgb))
                    if matches:
                        result.update(status="confirmed", ui_confirmation=True)
                        return result
                    raise ActionError("post_frame_ui_mismatch", "uncertain")
                time.sleep(self.poll_interval)
            raise ActionError("confirmation_timeout", "timed_out")
        except ActionError as exc:
            result.update(status=exc.status, reason=exc.reason)
            if exc.status == "rejected":
                result["accepted"] = False
            if committed and exc.status in {"rejected", "failed"}:
                result.update(status="uncertain", accepted=True)
            if armed:
                result["recovery"] = recover(self.worker)
            return result
        except Exception as exc:
            result.update(status="uncertain" if result["accepted"] else "failed",
                          reason="executor_error:" + type(exc).__name__)
            if armed:
                result["recovery"] = recover(self.worker)
            return result
        finally:
            result["mutation_submitted"] = committed
            if armed:
                try:
                    if result["status"] == "confirmed":
                        self.ui.close_panel()
                except ActionError:
                    result["cleanup"] = "panel_close_safety_stop"
                except Exception:
                    result["cleanup"] = "panel_close_error"
                finally:
                    try:
                        self.worker.end()
                    except Exception:
                        result["cleanup"] = "input_release_safety_stop"
            result["duration_ms"] = round((time.monotonic() - started) * 1000)
            self.lock.release()
