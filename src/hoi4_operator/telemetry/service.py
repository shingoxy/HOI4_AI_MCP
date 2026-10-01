"""Small local query API over a polling log tailer."""

from dataclasses import asdict
from datetime import timedelta
from pathlib import Path

from .cache import StateCache
from .parser import FrameParser
from .tailer import LogTailer
from .models import GameState


class TelemetryService:
    def __init__(self, log_path: str | Path, *, start_at_end: bool = True) -> None:
        self.tailer = LogTailer(log_path, start_at_end=start_at_end)
        self.parser = FrameParser()
        self.cache = StateCache()
        self._generation = 0

    def poll(self) -> int:
        return len(self.poll_states())

    def poll_states(self) -> list[GameState]:
        """Return each accepted frame, preserving updates within one log read."""
        lines = self.tailer.poll()
        if self.tailer.generation != self._generation:
            self.parser.reset()
            self.cache.clear()
            self._generation = self.tailer.generation
        accepted = []
        for line in lines:
            state = self.parser.feed(line)
            if state is not None and self.cache.update(state):
                accepted.append(state)
        return accepted

    def get_summary(self, *, stale_after_seconds: float = 30) -> dict:
        state = self.cache.latest_state
        return {
            "status": self.cache.freshness(max_age=timedelta(seconds=stale_after_seconds)),
            "received_at": self.cache.received_at.isoformat() if self.cache.received_at else None,
            "game_date": self.cache.game_date,
            "latest_seq": self.cache.latest_seq,
            "state": asdict(state) if state else None,
            "parser_errors": list(self.parser.errors),
        }

    def get_politics(self) -> dict | None:
        state = self.cache.latest_state
        return asdict(state.politics) if state else None
