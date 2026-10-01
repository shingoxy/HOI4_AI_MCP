"""Strict, line-oriented parser for the Mod's three-line protocol."""

from collections import deque
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re

from .models import (FocusState, GameState, IndustryState, ManpowerState,
                     PoliticsState, ResearchState, TechnologyState)


_TAG = re.compile(r"[A-Z][A-Z0-9]{2}\Z")
_DECIMAL = re.compile(r"-?\d+(?:\.\d+)?\Z")
_REQUIRED = {
    "date", "tag", "political_power", "stability", "war_support", "manpower_k",
    "civilian_factories", "military_factories", "dockyards",
}
TRACKED_TECHS = ("basic_machine_tools", "construction1", "electronic_mechanical_engineering")
TRACKED_FOCUS = "GER_remilitarize_the_rhineland"
_EXTENDED = {"research_slots", "focus_completed", "focus_progress_lower", "focus_progress_upper"}
_EXTENDED.update(f"{prefix}_{tech}" for prefix in ("researching", "researched") for tech in TRACKED_TECHS)


def _fields(payload: str) -> dict[str, str]:
    result = {}
    for part in payload.split("|"):
        key, separator, value = part.partition("=")
        if not separator or not key or not value or key in result:
            raise ValueError(f"malformed or duplicate field: {part!r}")
        result[key] = value
    return result


def _integer(value: str) -> int:
    if len(value) > 40 or not _DECIMAL.fullmatch(value):
        raise ValueError(f"invalid number: {value!r}")
    number = Decimal(value)
    if not number.is_finite() or number != number.to_integral_value():
        raise ValueError(f"not an integer: {value!r}")
    return int(number)


def _number(value: str) -> Decimal:
    if len(value) > 40 or not _DECIMAL.fullmatch(value):
        raise ValueError(f"invalid number: {value!r}")
    number = Decimal(value)
    if not number.is_finite():
        raise ValueError(f"not finite: {value!r}")
    return number


def _boolean(value: str) -> bool:
    number = _integer(value)
    if number not in {0, 1}:
        raise ValueError(f"invalid boolean: {value!r}")
    return bool(number)


class FrameParser:
    """Yield GameState only after matching BEGIN, data, and END lines."""

    def __init__(self) -> None:
        self.errors: deque[str] = deque(maxlen=100)
        self.reset()

    def reset(self) -> None:
        self._begin: dict[str, str] | None = None
        self._data: dict[str, str] | None = None
        self._discarding = False

    def feed(self, line: str) -> GameState | None:
        marker = next((name for name in (
            "CODEX_STATE_BEGIN|", "CODEX_STATE_END|", "CODEX|"
        ) if name in line), None)
        if marker is None:
            return None
        if self._discarding and marker != "CODEX_STATE_BEGIN|":
            return None
        payload = line[line.index(marker) + len(marker):].strip()
        try:
            fields = _fields(payload)
            if marker == "CODEX_STATE_BEGIN|":
                if self._begin is not None:
                    self.errors.append("incomplete frame replaced by BEGIN")
                self.reset()
                if set(fields) != {"version", "seq", "origin"}:
                    raise ValueError("BEGIN fields mismatch")
                if _integer(fields["version"]) not in {1, 2}:
                    raise ValueError("unsupported protocol version")
                if _integer(fields["seq"]) < 0:
                    raise ValueError("negative sequence")
                if _integer(fields["origin"]) not in {0, 1}:
                    raise ValueError("invalid origin")
                self._begin = fields
                return None
            if marker == "CODEX|":
                if self._begin is None or self._data is not None:
                    raise ValueError("data outside frame or repeated")
                self._data = fields
                return None
            if self._begin is None or self._data is None:
                raise ValueError("END without complete frame")
            if set(fields) != {"seq"} or _integer(fields["seq"]) != _integer(self._begin["seq"]):
                raise ValueError("END sequence mismatch")
            state = self._build(self._begin, self._data)
            self.reset()
            return state
        except (ValueError, InvalidOperation) as exc:
            self.errors.append(str(exc))
            self.reset()
            self._discarding = True
            return None

    @staticmethod
    def _build(begin: dict[str, str], data: dict[str, str]) -> GameState:
        version = _integer(begin["version"])
        required = _REQUIRED | _EXTENDED if version == 2 else _REQUIRED
        if set(data) != required:
            raise ValueError(f"data fields mismatch: {sorted(set(data) ^ required)}")
        if not data["date"].strip() or not _TAG.fullmatch(data["tag"]):
            raise ValueError("invalid date or country tag")
        pp = _number(data["political_power"])
        stability = _number(data["stability"])
        war_support = _number(data["war_support"])
        manpower_k = _number(data["manpower_k"])
        if not 0 <= stability <= 1 or not 0 <= war_support <= 1 or manpower_k < 0:
            raise ValueError("politics or manpower out of range")
        factories = tuple(_integer(data[key]) for key in (
            "civilian_factories", "military_factories", "dockyards"
        ))
        if any(value < 0 for value in factories):
            raise ValueError("negative factory count")
        research = focus = None
        if version == 2:
            slots = _integer(data["research_slots"])
            if slots < 0:
                raise ValueError("negative research slots")
            technologies = tuple(TechnologyState(
                tech, _boolean(data[f"researching_{tech}"]), _boolean(data[f"researched_{tech}"])
            ) for tech in TRACKED_TECHS)
            if any(tech.researching and tech.researched for tech in technologies):
                raise ValueError("technology cannot be researching and researched")
            if sum(tech.researching for tech in technologies) > slots:
                raise ValueError("tracked active research exceeds slots")
            completed = _boolean(data["focus_completed"])
            lower, upper = (_number(data[key]) for key in ("focus_progress_lower", "focus_progress_upper"))
            if not 0 <= lower <= upper <= 1 or (completed and (lower != 1 or upper != 1)):
                raise ValueError("invalid focus progress bounds")
            if not completed and (upper - lower != Decimal("0.1") or lower * 10 != (lower * 10).to_integral_value()):
                raise ValueError("focus progress interval must be one tenth")
            research = ResearchState(slots, technologies)
            focus = FocusState(TRACKED_FOCUS, completed, float(lower), float(upper))
        return GameState(
            protocol_version=version,
            seq=_integer(begin["seq"]),
            game_date=data["date"],
            country=data["tag"],
            politics=PoliticsState(float(pp), float(stability), float(war_support)),
            manpower=ManpowerState(
                int((manpower_k * 1000).to_integral_value(rounding=ROUND_HALF_UP)),
                float(manpower_k),
            ),
            industry=IndustryState(*factories),
            origin="startup" if _integer(begin["origin"]) == 1 else "daily",
            research=research,
            focus=focus,
        )
