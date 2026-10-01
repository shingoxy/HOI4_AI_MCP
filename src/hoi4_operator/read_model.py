"""Read-only MCP views and bounded changes over the Phase 2A telemetry cache."""

from collections import deque
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import math
from pathlib import Path
from uuid import uuid4

from .telemetry import TelemetryService


UNKNOWN_FIELDS = {
    "active_research": "Only three tracked technologies; slot-to-tech and remaining time are UNKNOWN.",
    "current_focus": "Current focus ID is UNKNOWN; tracked focus progress is a predicate-derived interval.",
    "production_lines": "Per-line equipment, efficiency and progress are not verified.",
}


def _flatten(data: dict, prefix: str = "") -> dict:
    result = {}
    for key, value in data.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(_flatten(value, name))
        else:
            result[name] = value
    return result


class ReadModel:
    def __init__(self, log_path: str | Path, *, stale_seconds: float = 30) -> None:
        if not math.isfinite(stale_seconds) or stale_seconds <= 0:
            raise ValueError("stale_seconds must be finite and positive")
        self.service = TelemetryService(log_path, start_at_end=False)
        self.stale_seconds = stale_seconds
        self.session_id = str(uuid4())
        self.revision = 0
        self.events: deque[dict] = deque(maxlen=100)
        self.service.poll()
        # Existing frames are a baseline, not new events. Never label old data
        # fresh just because this process has started and replayed the file.
        if self.service.cache.latest_state:
            try:
                self.service.cache.received_at = datetime.fromtimestamp(
                    self.service.tailer.path.stat().st_mtime, timezone.utc
                )
            except OSError:
                self.service.cache.received_at = None
        self._previous = self.service.cache.latest_state
        self._freshness_basis = "log_mtime_upper_bound"
        self._notification_key = self._key()

    def _key(self) -> tuple:
        return (self.revision, self.summary()["status"],
                self.service.tailer.last_error, tuple(self.service.parser.errors))

    def _record(self, kind: str, state=None, changes=None) -> None:
        self.revision += 1
        self.events.append({
            "revision": self.revision,
            "kind": kind,
            "seq": state.seq if state else None,
            "game_date": state.game_date if state else None,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "fields": changes or {},
        })

    def poll(self) -> bool:
        generation = self.service.tailer.generation
        states = self.service.poll_states()
        reset = generation != self.service.tailer.generation
        if reset:
            self._previous = None
            self._record("log_reset")
        for state in states:
            previous = self._previous
            rollback = previous is not None and (
                state.seq < previous.seq or state.country != previous.country
            )
            changes = {}
            if previous is not None and not rollback:
                before, after = _flatten(asdict(previous)), _flatten(asdict(state))
                changes = {key: {"before": before.get(key), "after": after.get(key)}
                           for key in before.keys() | after.keys() if before.get(key) != after.get(key)}
            self._record("timeline_reset" if rollback else "state_updated", state, changes)
            self._previous = state
            self._freshness_basis = "frame_received_at"
        key = self._key()
        changed = key != self._notification_key
        self._notification_key = key
        return changed

    def summary(self) -> dict:
        result = self.service.get_summary(stale_after_seconds=self.stale_seconds)
        if self.service.tailer.last_error:
            result["status"] = "unavailable"
        result.update({
            "session_id": self.session_id,
            "revision": self.revision,
            "freshness_basis": self._freshness_basis,
            "log_read_error": self.service.tailer.last_error,
        })
        return result

    def section(self, name: str) -> dict:
        result = self.summary()
        state = result.pop("state")
        result["country"] = state["country"] if state else None
        result[name] = state[name] if state else None
        if name == "industry":
            result["scope"] = "factory_totals_only"
            result["production_lines"] = {"status": "UNKNOWN", "reason": UNKNOWN_FIELDS["production_lines"]}
        elif name == "research":
            result["scope"] = "slot_count_and_three_tracked_technologies"
            result["slot_assignment"] = {"status": "UNKNOWN", "reason": UNKNOWN_FIELDS["active_research"]}
        elif name == "focus":
            result["scope"] = "tracked_focus_only; progress_interval_in_tenths"
            result["current_focus"] = {"status": "UNKNOWN", "reason": UNKNOWN_FIELDS["current_focus"]}
        if name in {"research", "focus"} and result[name] is None:
            result["section_status"] = "unavailable"
            result["section_reason"] = "Requires protocol v2; current frame has no extended telemetry."
        return result

    def changes(self, after_revision: int = 0) -> dict:
        if isinstance(after_revision, bool) or not isinstance(after_revision, int):
            raise ValueError("after_revision must be an integer")
        if not 0 <= after_revision <= self.revision:
            raise ValueError("after_revision is outside this server session")
        first = self.events[0]["revision"] if self.events else self.revision + 1
        return {
            "session_id": self.session_id,
            "latest_revision": self.revision,
            "history_truncated": after_revision < first - 1,
            "events": deepcopy([e for e in self.events if e["revision"] > after_revision]),
        }

    def diagnostics(self) -> dict:
        unknown = {name: {"status": "UNKNOWN", "reason": reason} for name, reason in UNKNOWN_FIELDS.items()}
        state = self.service.cache.latest_state
        if state is None or state.research is None:
            unknown["research_slots"] = {"status": "UNKNOWN", "reason": "Requires a complete protocol v2 frame."}
        return {
            **{key: value for key, value in self.summary().items() if key != "state"},
            "log_path": str(self.service.tailer.path),
            "log_generation": self.service.tailer.generation,
            "unknown_fields": unknown,
        }
