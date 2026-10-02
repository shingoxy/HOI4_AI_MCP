"""Vendor-neutral action results. Backend details never belong to this contract."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4


class ActionStatus(StrEnum):
    REJECTED = "rejected"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    UNCERTAIN = "uncertain"
    CONFIRMED = "confirmed"
    ALREADY_SATISFIED = "already_satisfied"


class ActionReason(StrEnum):
    TELEMETRY_STALE = "telemetry_stale"
    UNSUPPORTED_TARGET = "unsupported_target"
    TARGET_NOT_FOUND = "target_not_found"
    TARGET_NOT_VISIBLE = "target_not_visible"
    IDENTITY_MISMATCH = "identity_mismatch"
    SNAPSHOT_STALE = "snapshot_stale"
    REQUIREMENTS_NOT_MET = "requirements_not_met"
    INSUFFICIENT_POLITICAL_POWER = "insufficient_political_power"
    INSUFFICIENT_FACTORY = "insufficient_factory"
    INSUFFICIENT_RESOURCE = "insufficient_resource"
    MODAL_BLOCKED = "modal_blocked"
    READBACK_FAILED = "readback_failed"
    READBACK_AMBIGUOUS = "readback_ambiguous"
    UNEXPECTED_STATE_CHANGE = "unexpected_state_change"
    LOSS_OF_FOCUS = "loss_of_focus"
    EMERGENCY_STOP = "emergency_stop"
    WATCHDOG_TIMEOUT = "watchdog_timeout"
    UI_TIMEOUT = "ui_timeout"
    BACKEND_UNAVAILABLE = "backend_unavailable"


REASON_ALIASES = {
    "stale_telemetry": "telemetry_stale", "production_snapshot_stale": "snapshot_stale",
    "gui_identity_mismatch": "identity_mismatch", "computer_use_error": "backend_unavailable",
    "worker_timeout": "ui_timeout", "action_timeout": "ui_timeout",
}


@dataclass
class ActionResult:
    action: str
    accepted: bool = False
    status: str = ActionStatus.REJECTED
    action_id: str = field(default_factory=lambda: str(uuid4()))
    retry_count: int = 0
    evidence: dict[str, Any] = field(default_factory=dict)
    timings_ms: dict[str, int] = field(default_factory=lambda: dict.fromkeys(
        ("precheck", "navigation", "target_lookup", "submit", "readback", "confirmation", "total"), 0))

    def as_dict(self):
        return {"action": self.action, "accepted": self.accepted, "status": str(self.status),
                "action_id": self.action_id, "retry_count": self.retry_count,
                "duration_ms": self.timings_ms["total"], "timings_ms": dict(self.timings_ms),
                **self.evidence}


def public_reason(reason):
    # Do not leak vendor exceptions, arguments, HWNDs or screenshot tokens.
    prefix = reason.split(":", 1)[0]
    return REASON_ALIASES.get(prefix, prefix)
