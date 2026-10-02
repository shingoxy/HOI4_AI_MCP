"""Backend cleanup failures cannot strand the shared action lock or mask proof."""

from test_executor import FakeModel, FakeWorker
from test_production import telemetry
from hoi4_operator.executor.service import Executor
from hoi4_operator.executor.pipeline import ActionPipeline
from hoi4_operator.executor.guard import ActionError


def test_cleanup_failure_preserves_confirmation_and_releases_lock():
    class Worker(FakeWorker):
        def end(self): raise RuntimeError("private vendor error")
    executor = Executor(FakeModel([telemetry()]), Worker(), None)
    pipeline = ActionPipeline(executor)
    def operation(tx):
        tx.commit()
        tx.result.status = "confirmed"
    def cleanup(): raise RuntimeError("private vendor error")
    result = pipeline.run("example", operation, cleanup=cleanup)
    assert result["status"] == "confirmed" and result["accepted"]
    assert result["cleanup"] == result["backend_cleanup"] == "backend_unavailable"
    assert "private vendor" not in str(result) and not executor.lock.locked()
    assert pipeline.run("example", operation)["status"] == "confirmed"


def test_recovery_backend_failure_does_not_mask_uncertain_result():
    class Worker(FakeWorker):
        def key(self, _): raise RuntimeError("private vendor error")
    executor = Executor(FakeModel([telemetry()]), Worker(), None)
    def operation(tx):
        tx.commit()
        raise ActionError("readback_failed")
    result = ActionPipeline(executor).run("example", operation)
    assert result["status"] == "uncertain" and result["reason"] == "readback_failed"
    assert result["recovery"] == "backend_unavailable" and not executor.lock.locked()
