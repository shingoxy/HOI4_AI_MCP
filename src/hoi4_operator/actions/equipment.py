"""Semantic PoC catalog. GUI labels are independent from unproven game IDs."""

EQUIPMENT = {
    "infantry_equipment_1": {"display_identity": "Kar 98k式步枪", "internal_game_id": None,
                             "supported": True, "identity_source": "calibrated GUI title and type I"},
    "support_equipment_1": {"display_identity": "支援装备", "internal_game_id": None,
                            "supported": True, "identity_source": "calibrated GUI title and equipment type"},
    "artillery_equipment_1": {"display_identity": "105毫米18型轻型野...", "internal_game_id": None,
                              "supported": False, "identity_source": "truncated production title; observation only"},
}
