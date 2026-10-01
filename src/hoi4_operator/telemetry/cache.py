"""Latest complete state and its wall-clock freshness."""

from datetime import datetime, timedelta, timezone

from .models import GameState


class StateCache:
    def __init__(self) -> None:
        self.clear()

    def clear(self) -> None:
        self.latest_state: GameState | None = None
        self.latest_seq: int | None = None
        self.received_at: datetime | None = None
        self.game_date: str | None = None
        self._rollback_candidate: GameState | None = None

    def update(self, state: GameState, *, received_at: datetime | None = None) -> bool:
        if self.latest_state == state:
            return False
        if self.latest_seq is not None:
            if state.origin == "daily" and state.seq <= self.latest_seq:
                if state.seq == self.latest_seq:
                    return False
                previous = self._rollback_candidate
                if not (previous and previous.country == state.country
                        and previous.seq < state.seq < self.latest_seq
                        and previous.game_date != state.game_date):
                    # One older frame may be a replay. A second advancing day confirms
                    # that the game has loaded an earlier save without a startup frame.
                    self._rollback_candidate = state
                    return False
        self._rollback_candidate = None
        timestamp = received_at or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            raise ValueError("received_at must include a timezone")
        self.latest_state = state
        self.latest_seq = state.seq
        self.received_at = timestamp
        self.game_date = state.game_date
        return True

    def freshness(self, *, max_age: timedelta = timedelta(seconds=30),
                  now: datetime | None = None) -> str:
        if self.received_at is None:
            return "unavailable"
        current = now or datetime.now(timezone.utc)
        return "fresh" if current - self.received_at <= max_age else "stale"
