"""Limited military observation and transition contracts; no backend details."""

from copy import deepcopy

from ..executor.guard import ActionError


DIVISIONS = {
    "infantry_1": {"name": "1. Infanterie-Division", "unit_type": "infantry"},
    "panzer_1": {"name": "1. Panzer-Division", "unit_type": "armor"},
    "infantry_10": {"name": "10. Infanterie-Division", "unit_type": "infantry"},
}
GENERALS = {"GER_erich_von_manstein": {
    "name": "埃里希·冯·曼施坦因", "country": "GER", "rank": "general",
    "identity_source": "derived", "stable_game_identity": True,
    "identity_basis": "installed GER.txt character definition + localisation + GUI name and portrait",
}}
AIR_REGION = {"region_id":8,"name":"东德意志","identity_source":"derived",
              "identity_basis":"installed strategic region 8 + Chinese localisation + GUI region title"}
SHIP_NAMES = ("Deutschland", "Admiral Scheer", "Nürnberg", "Leipzig", "Königsberg",
              "Karlsruhe", "Köln", "Emden", "Jaguar", "Leopard", "Luchs", "Tiger")


def air_signature(view):
    return [(item["name"],item["unit_type"],item["base_name"],item["aircraft_count"],
             item["capacity"],item["region_id"],tuple(item["missions"])) for item in view["air_wings"]]
OBSERVATIONS = ("get_armies", "get_army", "get_divisions", "get_division", "get_generals",
                "get_fronts", "get_supply_status", "get_air_state", "get_navy_state",
                "get_air_wings", "get_air_regions", "get_fleets")
MUTATIONS = ("create_army", "assign_divisions", "remove_divisions_from_army", "assign_general",
             "create_frontline", "create_offensive_line", "execute_plan", "stop_plan",
             "move_divisions", "assign_air_wing", "set_air_mission", "assign_fleet_region", "set_naval_mission")


def sourced(fields, source="gui"):
    return {"field_sources": {name: "unknown" if value is None else source for name, value in fields.items()}, **fields}


def land_signature(view):
    return ([tuple((item["name"], item["general_id"], tuple(item["division_names"]))) for item in view["armies"]],
            [(item["name"], item["unit_type"], item["army_name"]) for item in view["divisions"]])


def order_signature(view):
    return (land_signature(view), sorted((item["target_id"], item["type"], item["army_name"]) for item in view["fronts"]),
            view["plan_active"], view["operation_name"])


def expected_land(before, action, *, division=None, general_id=None):
    expected = deepcopy(before)
    armies = expected["armies"]
    if action == "create_army":
        if armies or division["army_name"] is not None:
            raise ActionError("requirements_not_met", "rejected")
        armies.append(sourced({"name": "第1集团军", "general_id": None, "division_names": [division["name"]]}))
    elif len(armies) != 1:
        raise ActionError("identity_mismatch", "rejected")
    army = armies[0]
    if action == "assign_general":
        army["general_id"] = general_id
    elif action == "assign_divisions":
        if division["army_name"] is not None:
            raise ActionError("requirements_not_met", "rejected")
        army["division_names"].append(division["name"])
    elif action == "remove_divisions_from_army":
        if division["army_name"] != army["name"] or len(army["division_names"]) <= 1:
            raise ActionError("requirements_not_met", "rejected")
        army["division_names"].remove(division["name"])
    for item in expected["divisions"]:
        item["army_name"] = army["name"] if item["name"] in army["division_names"] else None
    army["division_names"].sort()
    return expected


def validate_transition(after, expected):
    if land_signature(after) != land_signature(expected):
        raise ActionError("unexpected_state_change", "uncertain")
