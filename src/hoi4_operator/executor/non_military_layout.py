"""Private calibrated layout: HOI4 1.19.3 Chinese, 2560x1080, scale 1.0."""

PRODUCTION = {
    "first_top": 374, "compact_pitch": 63, "maximum_lines": 10,
    "list_box": (8, 373, 516, 1066), "delete_strip": (490, 373, 516, 1066),
    "filter_points": [(28+85*i, 317) for i in range(6)],
    "filter_boxes": [(10+85*i, 303, 53+85*i, 332) for i in range(6)],
    "neutral": (180, 103), "add_equipment": (51, 263),
    "picker_box": (550, 168, 1010, 742), "picker_close": (999, 99),
    "fold_x": 33, "fold_y_offset": 13,
}


def production_boxes(top):
    return {"name": (43, top, 225, top+24), "count": (412, top+3, 460, top+25),
            "priority": (14, top+3, 29, top+25), "fold": (28, top+5, 40, top+23),
            "delete": (490, top, 515, top+26),
            "up": (10, top+42, 34, top+72), "down": (10, top+69, 34, top+103)}


CONSTRUCTION = {
    "entry": (414, 55), "close": (665, 103), "neutral": (180, 103),
    "first_top": 281, "pitch": 52, "max_items": 8,
    "cancel_strip": (374, 280, 403, 1040),
    "state_points": {64: (1290, 550), 65: (1274, 595), 66: (1515, 650)},
    "state_title": (165, 432, 320, 468), "owner_box": (22, 482, 80, 525),
    "state_close": (437, 451), "map_anchor_box": (1240, 276, 1380, 308),
    "building_points": {"civilian_factory": (521, 290), "military_factory": (474, 290),
                        "infrastructure": (474, 197)},
    "modal_title": (1200, 370, 1360, 415), "modal_body": (1100, 435, 1460, 465),
    "modal_ok": (1340, 660, 1410, 700),
}


def construction_boxes(top):
    return {"state": (20, top+6, 173, top+30), "building": (178, top+2, 220, top+47),
            "count": (206, top+28, 221, top+47), "factories": (255, top+3, 311, top+29),
            "up": (322, top+8, 345, top+43), "down": (345, top+8, 369, top+43),
            "cancel": (374, top+8, 403, top+43)}


POLITICS = {
    "entry": (48, 42), "close": (518, 103), "neutral": (180, 103),
    "title": (20, 84, 150, 123), "selector_close": (1005, 102),
    "selector_title": (700, 80, 850, 112),
    "law_slots": {"economy": (220, 594), "conscription": (59, 594)},
    "law_rows": {"low_economic_mobilisation": 214, "partial_economic_mobilisation": 289,
                 "volunteer_only": 214, "limited_conscription": 289},
    "law_select_x": 685, "law_select_y_offset": 33,
    "advisor_points": [(300+80*i, 594) for i in range(3)],
    "advisor_boxes": [(275+80*i, 567, 327+80*i, 626) for i in range(3)],
    "advisor_target": (785, 272, 1008, 340),
    "advisor_select": (906, 305), "advisor_cross_box": (967,313,990,338),
    "modal_title": (1160, 375, 1400, 415), "modal_body": (1100, 435, 1460, 465),
    "modal_ok": (1340, 660, 1410, 700),
}


TRADE = {
    "entry": (356,55), "close": (662,103), "neutral": (180,103),
    "title": (25,85,115,125), "steel": (462,176), "steel_box": (430,162,493,191),
    "country_list": (12,543,177,1070), "available": (510,132,620,156),
    "contract_select_x": 435,
    "dialog_country": (1200,342,1350,388), "dialog_flag": (1440,334,1534,393),
    "dialog_resource": (1044,435,1078,459), "dialog_neutral": (1060,480),
    "dialog_amount": (1207,583,1238,605), "dialog_factories": (1223,604,1246,626),
    "dialog_close": (1149,723), "dialog_close_box": (1088,705,1210,742),
    "send_box": (1365,705,1490,742), "plus": (1425,650), "minus": (1141,650),
    "plus_box": (1413,637,1436,664), "minus_box": (1129,637,1154,664),
}
