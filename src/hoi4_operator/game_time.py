"""Bounded semantic game time. The GUI driver is private to the Operator host."""

from datetime import timedelta
from enum import StrEnum
import threading
import time

from .observation import game_datetime


class TimeOwnership(StrEnum):
    UNKNOWN = 'UNKNOWN'
    PAUSED_CONFIRMED = 'PAUSED_CONFIRMED'
    RUNNING_OWNED = 'RUNNING_OWNED'
    STOPPING = 'STOPPING'
    STOP_FAILED_OWNED = 'STOP_FAILED_OWNED'


class GameTimeController:
    def __init__(self, model, gui, *, timeout=20, poll_interval=.15):
        self.model, self.gui = model, gui
        self.timeout, self.poll_interval = timeout, poll_interval
        self.state = TimeOwnership.UNKNOWN
        self._lock = threading.RLock()
        self._stop_attempted = False
        self.evidence_error=None
        self.metrics = dict(time_ownership_acquired=0,time_ownership_released=0,
            pause_attempts=0,pause_failures=0,safe_stop_attempts=0,safe_stop_successes=0,
            modal_block_count=0,unknown_modal_count=0,operator_safety_interventions=0)
        bind=getattr(gui,'bind_time_context',None)
        if bind: bind(self.contract,model.summary)

    @property
    def owns_running(self):
        return self.state in {TimeOwnership.RUNNING_OWNED,TimeOwnership.STOPPING,TimeOwnership.STOP_FAILED_OWNED}

    def contract(self):
        return dict(ownership_state=str(self.state),owns_running=self.owns_running,
                    operator_intervention_required=self.state==TimeOwnership.STOP_FAILED_OWNED,
                    failure_evidence_error=self.evidence_error or getattr(self.gui,'evidence_error',None))

    def _transition(self, state):
        self.state=state
        record=getattr(self.gui,'record_time_state',None)
        if record: record(self.contract())

    def acquire_running_ownership(self):
        """Before any potentially successful resume input, including menu exit."""
        with self._lock:
            if self.owns_running: raise RuntimeError('owned_time_not_stopped')
            self._stop_attempted=False
            self.evidence_error=None
            reset=getattr(self.gui,'reset_stop_budget',None)
            if reset: reset()
            self.metrics['time_ownership_acquired']+=1
            self._transition(TimeOwnership.RUNNING_OWNED)

    def _pause_confirmed(self):
        if self.owns_running: self.metrics['time_ownership_released']+=1
        self._transition(TimeOwnership.PAUSED_CONFIRMED)

    def _failure(self, reason):
        self._transition(TimeOwnership.STOP_FAILED_OWNED)
        self.metrics['modal_block_count']+=reason=='modal_blocked'
        self.metrics['unknown_modal_count']+=reason=='unknown_modal'
        save=getattr(self.gui,'save_stop_failure',None)
        if save:
            try: save(reason)
            except Exception as exc:
                self.evidence_error=type(exc).__name__  # Never abandon stop for evidence I/O.

    def ensure_game_stopped(self):
        """Bounded independent stop responsibility; repeated calls never resend input."""
        with self._lock:
            if not self.owns_running:
                return dict(status='confirmed' if self.state==TimeOwnership.PAUSED_CONFIRMED else 'not_owned',
                            paused=self.state==TimeOwnership.PAUSED_CONFIRMED,**self.contract())
            armed=False
            result=dict(status='failed',paused=False,reason='stop_unconfirmed')
            try:
                begin=getattr(self.gui,'begin_stop',None)
                if begin: armed=begin()
                if self._stop_attempted:
                    # A later operator pause may be observed, but never another toggle.
                    proof=getattr(self.gui,'pause_evidence',None)
                    paused=(proof()['paused'] is True) if proof else self.gui.is_paused()
                    if paused:
                        self._pause_confirmed()
                        result.update(status='confirmed',paused=True,reason='passive_pause_confirmed')
                    return {**result,**self.contract()}
                self._stop_attempted=True
                self._transition(TimeOwnership.STOPPING)
                self.metrics['pause_attempts']+=1
                try:
                    if self.gui.pause():
                        self._pause_confirmed()
                        result.update(status='confirmed',paused=True,reason='normal_pause_confirmed')
                        return {**result,**self.contract()}
                    reason='pause_unconfirmed'
                except Exception as exc:
                    reason=getattr(exc,'reason',str(exc) or 'pause_failed')
                self.metrics['pause_failures']+=1
                self._failure(reason)  # Save the triggering frame BEFORE any recovery input.
                result['reason']=reason
                safe=getattr(self.gui,'safe_stop_once',None)
                if safe:
                    self.metrics['safe_stop_attempts']+=1
                    if safe():
                        self.metrics['safe_stop_successes']+=1
                        self._pause_confirmed()
                        result.update(status='confirmed',paused=True,reason='safe_stop_confirmed')
            except Exception as exc:
                reason=getattr(exc,'reason',str(exc) or 'stop_failed')
                self._stop_attempted=True
                self._failure(reason)
                result['reason']=reason
            finally:
                if armed:
                    try: self.gui.end()
                    except Exception: result['cleanup_error']='stop_guard_cleanup_failed'
            return {**result,**self.contract()}

    def pause_owned(self):
        return self.ensure_game_stopped()['paused']

    def advance_days(self, days=1):
        if type(days) is not int or not 1 <= days <= 7:
            raise ValueError("days must be 1..7")
        started = time.monotonic()
        self.model.poll()
        before = self.model.summary()
        initial = game_datetime(before.get("game_date"))
        result = dict(status="rejected", reason="game_date_unknown", start_date=before.get("game_date"),
                      start_date_freshness=before.get("status"), start_date_source="telemetry_last_known",
                      end_date=None, end_date_source=None, gui_date=None, gui_date_status="UNKNOWN",
                      paused=False, pause_source=None, pump="OFF")
        if self.owns_running:
            return {**result,'reason':'owned_time_not_stopped',**self.contract()}
        if initial is None:
            return result
        stop = threading.Event()
        errors = []
        def watchdog():
            if not stop.wait(self.timeout):
                try:
                    result["watchdog_stop"] = self.ensure_game_stopped()
                    result["watchdog_paused"] = result['watchdog_stop']['paused']
                except Exception as exc:
                    errors.append(getattr(exc, "reason", "pause_failed"))
        timer = None
        try:
            self.gui.begin(self.timeout+12)
            if not self.gui.is_paused():
                result["reason"] = "requires_paused_start"
                return result
            self._transition(TimeOwnership.PAUSED_CONFIRMED)
            timer = threading.Thread(target=watchdog, daemon=False)
            timer.start()  # Independent stop path exists before resume.
            with self._lock:
                # Ownership covers a possibly successful input even if subsequent observation fails.
                self.acquire_running_ownership()
                self.gui.resume()
            goal = initial.date()+timedelta(days=days)
            while time.monotonic()-started < self.timeout:
                self.gui.check()
                self.model.poll()
                after = self.model.summary()
                current = game_datetime(after.get("game_date"))
                changes = self.model.changes(before.get("revision", 0)) if hasattr(self.model, "changes") else {"events": []}
                reset = any(e["kind"] in {"timeline_reset", "log_reset"} for e in changes["events"])
                if reset or current and current < initial:
                    result.update(status="failed", reason="timeline_reset")
                    break
                if current and current.date() >= goal and after.get("status") == "fresh" and after.get("freshness_basis") == "frame_received_at":
                    result.update(status="confirmed", reason="fresh_date_advanced", end_date=after["game_date"],
                                  end_date_source="fresh_telemetry_frame_received_at")
                    break
                time.sleep(self.poll_interval)
            else:
                result.update(status="timed_out", reason="game_time_timeout")
        except Exception as exc:
            result.update(status="failed", reason=getattr(exc, "reason", "game_time_backend_error"))
        finally:
            stop.set()
            if self.owns_running:
                result['stop']=self.ensure_game_stopped()
                result['paused']=result['stop']['paused']
                if not result['paused']: errors.append(result['stop']['reason'])
            else:
                result['paused']=self.state==TimeOwnership.PAUSED_CONFIRMED
            if result["paused"]:
                result["pause_source"] = getattr(self.gui,'last_pause_source',None) or 'validated_GUI_clock'
            if timer:
                timer.join(timeout=6)
                if timer.is_alive():
                    errors.append("pause_watchdog_unfinished")
            try:
                self.gui.end()
            except Exception:
                errors.append("game_time_cleanup_error")
            if errors or not result["paused"] and result["status"] == "confirmed":
                result.update(status="failed", reason=errors[0] if errors else "pause_unconfirmed")
            result["duration_ms"] = round((time.monotonic()-started)*1000)
            result.update(self.contract())
        return result
