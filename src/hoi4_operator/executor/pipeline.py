"""Shared bounded transaction. Submission is never retried after it may occur."""

from contextlib import contextmanager
import time

from ..contracts import ActionResult, ActionStatus, public_reason
from .guard import ActionError
from .recovery import recover


class Transaction:
    def __init__(self, executor, action):
        self.executor = executor
        self.result = ActionResult(action)
        self.committed = False
        self.before = None

    @contextmanager
    def stage(self, name):
        start = time.monotonic()
        try:
            self.executor.worker.check()
            yield
        finally:
            self.result.timings_ms[name] += round((time.monotonic() - start) * 1000)

    def commit(self):
        self.executor.worker.check()
        if self.committed:
            raise ActionError('duplicate_submit','uncertain')
        self.committed = True
        self.result.accepted = True
        record=getattr(self.executor.worker,'_record',None)
        if record:
            record('semantic_commit',action=self.result.action)

    def fresh(self):
        current = self.executor.snapshot()
        if self.before and current["latest_seq"] < self.before["latest_seq"]:
            raise ActionError("snapshot_stale", "uncertain" if self.committed else "rejected")
        return current


class ActionPipeline:
    def __init__(self, executor):
        self.executor = executor

    def recovery(self):
        try:
            return recover(self.executor.worker)
        except Exception:
            return "backend_unavailable"

    def run(self, action, operation, *, invalidate=lambda: None, cleanup=None):
        start = time.monotonic()
        tx = Transaction(self.executor, action)
        result = tx.result
        armed = False
        if not self.executor.lock.acquire(blocking=False):
            result.evidence["reason"] = "executor_busy"
            return result.as_dict()
        try:
            precheck = time.monotonic()
            tx.before = self.executor.snapshot()
            self.executor.worker.begin(self.executor.timeout)
            armed = True
            result.timings_ms["precheck"] = round((time.monotonic() - precheck) * 1000)
            operation(tx)
        except ActionError as exc:
            result.status = exc.status
            result.evidence["reason"] = public_reason(exc.reason)
            if tx.committed:
                invalidate()
                result.accepted = True
                if exc.status in {"failed", "rejected"}:
                    result.status = ActionStatus.UNCERTAIN
            elif exc.status == "rejected":
                result.accepted = False
            if armed:
                result.evidence["recovery"] = 'modal_left_open' if exc.reason == 'modal_blocked' else self.recovery()
        except Exception:
            result.status = ActionStatus.UNCERTAIN if tx.committed else ActionStatus.FAILED
            result.evidence["reason"] = "backend_unavailable"
            if tx.committed:
                invalidate()
            if armed:
                result.evidence["recovery"] = self.recovery()
        finally:
            try:
                if armed:
                    try:
                        if cleanup and result.status in {"confirmed", "already_satisfied"}:
                            cleanup()
                    except ActionError:
                        result.evidence["cleanup"] = "safety_stop"
                    except Exception:
                        result.evidence["cleanup"] = "backend_unavailable"
                    finally:
                        try:
                            self.executor.worker.end()
                        except Exception:
                            result.evidence["backend_cleanup"] = "backend_unavailable"
            finally:
                result.evidence["mutation_submitted"] = tx.committed
                result.timings_ms["total"] = round((time.monotonic() - start) * 1000)
                self.executor.lock.release()
        return result.as_dict()
