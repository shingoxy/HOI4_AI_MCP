"""Recovery never reacquires focus or retries a potentially committed selection."""

from .guard import ActionError


def recover(worker):
    try:
        worker.check()
        worker.key("Escape")
        return "escape_sent"
    except ActionError:
        return "skipped_safety_stop"
    finally:
        worker.release()
