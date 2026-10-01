"""Typed values produced by a complete telemetry frame."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PoliticsState:
    political_power: float
    stability: float
    war_support: float


@dataclass(frozen=True)
class ManpowerState:
    # The game exposes manpower_k; whole persons are derived from that value.
    available: int
    source_thousands: float


@dataclass(frozen=True)
class IndustryState:
    civilian_factories: int
    military_factories: int
    dockyards: int


@dataclass(frozen=True)
class TechnologyState:
    tech_id: str
    researching: bool
    researched: bool


@dataclass(frozen=True)
class ResearchState:
    slot_count: int
    tracked_technologies: tuple[TechnologyState, ...]


@dataclass(frozen=True)
class FocusState:
    # A tracked focus is not necessarily the currently selected focus.
    tracked_id: str
    completed: bool
    progress_lower_bound: float
    progress_upper_bound: float


@dataclass(frozen=True)
class GameState:
    protocol_version: int
    seq: int
    game_date: str
    country: str
    politics: PoliticsState
    manpower: ManpowerState
    industry: IndustryState
    origin: str
    research: ResearchState | None = None
    focus: FocusState | None = None
