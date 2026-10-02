"""Calibrated German semantic law/advisor catalog; primary game rules checked."""

LAWS = {
    "low_economic_mobilisation": {"group": "economy", "display": "前期动员", "minimum_war_support": .15, "cost": 150},
    "partial_economic_mobilisation": {"group": "economy", "display": "部分动员", "minimum_war_support": .25, "cost": 150},
    "volunteer_only": {"group": "conscription", "display": "志愿兵役制", "minimum_war_support": 0, "cost": 150},
    "limited_conscription": {"group": "conscription", "display": "有限征兵", "minimum_war_support": .1, "cost": 150},
}
ADVISORS = {"advisor_schacht": {"display": "亚尔马·沙赫特", "cost": 75,
    "game_character_id": "GER_hjalmar_schacht", "identity_source": "gui portrait and localized name",
    "supported": True, "scope": "GER; MEFO present; normal GUI enabled option"}}


def advisor_order(view):
    return [slot["advisor_id"] for slot in view["slots"]]
