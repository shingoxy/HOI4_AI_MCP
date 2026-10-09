"""Strategic semantic views: cheap telemetry and explicitly scoped GUI caches."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import re
import time
import threading


def game_datetime(value):
    """Parse the calibrated Chinese date and English test fixtures; 24:00 rolls over."""
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"(\d{1,2}):(\d{2}),\s*(\d{1,2})\s+(\d{1,2})月,\s*(\d{4})", value.strip())
    if match:
        hour, minute, day, month, year = map(int, match.groups())
        try:
            if hour > 24 or minute > 59 or (hour == 24 and minute):
                return None
            return datetime(year, month, day) + timedelta(hours=hour, minutes=minute)
        except ValueError:
            return None
    for pattern in ("%H:%M, %d %B, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, pattern)
        except ValueError:
            pass
    return None


# Positive allowlist: private UI evidence, paths, pixels and backend tokens never cross it.
SEMANTIC_KEYS = frozenset("""lines line_id equipment equipment_id factories maximum_assignable_factories
    identity_complete action_supported military_factories assigned_factories available_factories
    assigned_military_factories available_military_factories scope unknown_fields progress
    queue queue_item_id state_id building_type count states building_slots available_slots
    armies army_id name general_id general_name division_count division_names
    divisions division_id unit_type army_name fronts front_id target_id type
    offensive_orders order_id front_target_id plan_active operation_name
    air_wings wing_id missions region_id fleets fleet_id ship_count parent_fleet_name
    slots slot tech_id active active_focus_id researched researching tracked_technologies
    slot_count tracked_id completed progress_lower_bound progress_upper_bound
    advisor_slots advisor_id resource_shortages resource shortage idle political_power
    stability war_support civilian_factories dockyards complete scope_status
    total_divisions observed_divisions unobserved_divisions snapshot_version
    session_id ttl_seconds telemetry_seq stable_game_identity""".split())


def semantic(data):
    if isinstance(data, dict):
        return {k: semantic(v) for k, v in data.items() if k in SEMANTIC_KEYS}
    if isinstance(data, (list, tuple)):
        return [semantic(v) for v in data]
    return deepcopy(data)


def section(data=None, *, source="none", freshness="unknown", complete=False,
            navigation_required=False, status=None, observed_at=None):
    if status is None:
        status = ("unknown" if data is None else "stale" if freshness == "stale" else
                  "partial" if not complete else "known_empty" if data in ([], {}) else
                  "known_zero" if type(data) in (int, float) and data == 0 else "known")
    return dict(status=status, data=deepcopy(data), source=source, freshness=freshness,
                complete=complete, navigation_required=navigation_required, observed_at=observed_at)


class ObservationAggregator:
    def __init__(self, model, *, capabilities=lambda: {}, refresh=None, ttl=120, clock=time.monotonic):
        self.model, self.capabilities, self.refresh = model, capabilities, refresh
        self.ttl, self.clock = ttl, clock
        self.cache = {}
        self.epoch, self.event_revision = 0, 0
        self.previous_date = None
        self.lock = threading.RLock()

    def invalidate(self):
        self.cache.clear()

    def remember(self, domain, view, *, complete=False):
        self.cache[domain] = dict(data=semantic(view), complete=complete, created=self.clock(),
                                 observed_at=datetime.now(timezone.utc).isoformat(), game_date=self.model.summary().get("game_date"))

    def _sync(self, summary):
        events = self.model.changes(self.event_revision) if hasattr(self.model, "changes") else {"events": []}
        reset = any(e["kind"] in {"timeline_reset", "log_reset"} for e in events["events"])
        current = game_datetime(summary.get("game_date"))
        reset |= bool(current and self.previous_date and current < self.previous_date)
        self.event_revision = summary.get("revision", self.event_revision)
        self.previous_date = current or self.previous_date
        if reset:
            self.epoch += 1
            self.invalidate()
        return reset

    def get(self, detail="strategic"):
        with self.lock:
            return self._get(detail)

    def _get(self, detail):
        if detail not in {"summary", "strategic", "detailed"}:
            raise ValueError("detail must be summary, strategic or detailed")
        self.model.poll()
        summary = self.model.summary()
        reset = self._sync(summary)
        navigation = []
        if detail != "summary" and self.refresh and summary.get("status") == "fresh":
            domains = ["research_gui", "focus_gui", "production", "construction"]
            if detail == "detailed":
                domains.append("military")
            needed = [d for d in domains if d not in self.cache or self.clock()-self.cache[d]["created"] > self.ttl
                      or self.cache[d]["game_date"] != summary.get("game_date")]
            if needed:
                navigation = self.refresh(needed)
                self.model.poll()
                summary = self.model.summary()
                reset |= self._sync(summary)
        state = summary.get("state") or {}
        fresh = summary.get("status", "unknown")
        caps = self.capabilities()
        stamp = summary.get("received_at")
        result = {"meta": dict(country=state.get("country"), date=(game_datetime(summary.get("game_date")).date().isoformat()
                    if game_datetime(summary.get("game_date")) else None), game_date=summary.get("game_date"),
                    fresh=fresh == "fresh", freshness=fresh, freshness_basis=summary.get("freshness_basis"),
                    received_at=stamp, telemetry_seq=summary.get("latest_seq"),
                    timeline_id=f'{summary.get("session_id", "local")}:{self.epoch}', timeline_reset=reset,
                    backend=caps.get("backend", "unattached"), detail=detail),
                  "capabilities": caps, "navigation": navigation}
        for domain in ("politics", "industry", "research", "focus"):
            result[domain] = section(state.get(domain), source="telemetry_v2", freshness=fresh,
                                    complete=domain in {"politics", "industry"}, observed_at=stamp)
        for domain, scope in {"politics": "political_power_stability_war_support_only", "industry": "factory_totals_only",
                              "research": "slot_count_and_three_tracked_technologies", "focus": "tracked_Rhineland_predicates_only"}.items():
            result[domain]["scope"] = scope
        for domain in ("construction", "trade", "military", "air", "navy", "production", "research_gui", "focus_gui"):
            entry = self.cache.get(domain)
            age = self.clock()-entry["created"] if entry else None
            expired = bool(entry and (age > self.ttl or entry["game_date"] != summary.get("game_date")))
            result[domain] = section(entry["data"] if entry else None, source="GUI_cache" if entry else "none",
                freshness="stale" if expired else "fresh" if entry else "unknown",
                complete=entry["complete"] if entry else False, navigation_required=True,
                observed_at=entry["observed_at"] if entry else None)
            result[domain]["age_seconds"] = age
            if domain == "construction" and entry and entry["complete"] and entry["data"].get("queue") == [] and not expired:
                result[domain]["status"] = "known_empty"
        result["alerts"] = make_alerts(result)
        return result


def make_alerts(observation):
    alerts = []
    def emit(name, **target):
        alerts.append(dict(type=name, **target))
    def known(name):
        value = observation[name]
        return value["data"] if value["freshness"] == "fresh" and value["status"] not in {"unknown", "unsupported"} else None
    if not observation["meta"]["fresh"]:
        emit("telemetry_stale")
        return alerts
    politics = known("politics")
    if politics and politics.get("political_power", 0) >= 150:
        emit("political_power_available")
    research = known("research_gui")
    for slot in (research or {}).get("slots", []):
        if slot["tech_id"] == "empty":
            emit("research_slot_available", slot=slot["slot"])
    focus = known("focus_gui")
    if focus and focus.get("active") is False:
        emit("focus_missing")
    construction = known("construction")
    if construction is not None and observation["construction"]["complete"] and construction.get("queue") == []:
        emit("construction_queue_empty")
    production = known("production")
    if production and production.get("available_factories", 0) > 0:
        emit("unused_military_factory", count=production["available_factories"])
    for slot in (politics or {}).get("advisor_slots", []):
        if slot.get("advisor_id") is None:
            emit("advisor_slot_empty", slot=slot["slot"])
    for shortage in (known("trade") or {}).get("resource_shortages", []):
        if shortage.get("shortage", 0) > 0:
            emit("resource_shortage", resource=shortage["resource"])
    military = known("military") or {}
    for army in military.get("armies", []):
        if "general_id" in army and army["general_id"] is None:
            emit("army_without_general", army_id=army["army_id"])
        # Only the calibrated viewport can prove this absence for a known army.
        if "fronts" in military and not any(f["army_id"] == army["army_id"] for f in military["fronts"]):
            emit("army_without_front", army_id=army["army_id"])
    for wing in (known("air") or {}).get("air_wings", []):
        if wing.get("missions") == []:
            emit("idle_air_wing", wing_id=wing["wing_id"])
    return alerts
