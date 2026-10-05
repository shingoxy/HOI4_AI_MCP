"""Reproduce military reader crops from real local calibration screenshots."""

import json
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "src"))
CAPTURES = ROOT / "artifacts/phase4/captures"
DEST = ROOT / "artifacts/phase4/templates"


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    crops = {
        "navy-overview.jpg": {"navy_overview_title":(39,94,150,117),"navy_total_6":(175,145,266,163),
            "navy_overview_high_seas":(175,336,233,353),"navy_overview_count_12":(456,328,475,346)},
        "navy-selected.jpg": {"navy_parent_name":(70,94,129,110),"navy_parent_count_3":(355,94,374,111),
            "navy_no_admiral":(80,148,134,165),"navy_home_wilhelmshaven":(257,224,304,240),
            "navy_parent_regions_0":(14,223,133,240),"navy_high_seas":(70,303,126,321),
            "navy_count_12":(22,310,42,326),"navy_docked":(79,343,190,360),
            "land_mode_button":(2494,880,2526,911),
            **{f"navy_ship_{i}":(184,420+41*i,336,437+41*i) for i in range(12)}},
        "land-mode-selected.jpg": {"land_mode_active":(2494,880,2526,911)},
        "air-overview.jpg": {"air_overview_title":(39,93,149,117),"air_total_15":(176,146,269,162),
            "air_overview_132":(150,431,249,446),"air_overview_brandenburg":(312,431,364,446),
            "air_overview_fighter":(14,431,54,447)},
        "air-selected.jpg": {"air_selected_one":(49,152,119,169),"air_base_brandenburg":(76,217,129,232),
            "air_wing_132":(241,259,334,275),"air_count_80_100":(128,256,156,288),
            "air_wing_fighter":(20,261,60,283),"air_standby":(241,279,291,293),
            "air_superiority_off":(68,94,105,120),"air_other_missions_off":(109,94,689,120)},
        "air-superiority.jpg": {"air_region_8":(241,279,291,293),"air_superiority_on":(68,94,105,120),
            "air_anchor_amsterdam":(815,543,909,567),"air_anchor_vienna":(1499,890,1540,912),
            "air_anchor_copenhagen":(1268,264,1336,283)},
        "air-region.jpg": {"air_region_title_8":(1243,323,1308,341)},
        "selected-unassigned-idle.jpg": {"army_create_plus_idle": (1299,1003,1321,1030)},
        "selected-infantry-restored.jpg": {"selected_single_header": (75,94,115,112)},
        "game-menu.jpg": {"game_menu_load": (1241,329,1317,350)},
        "world-news-blocked.jpg": {"world_news_title": (1097,253,1384,294)},
        "map-v2-no-order.jpg": {"map_anchor_amsterdam": (815,543,909,567),
            "map_anchor_warsaw": (1765,559,1797,580), "map_anchor_copenhagen": (1268,264,1336,283)},
        "frontline-mode-active.jpg": {"frontline_mode_active": (1247,870,1280,903),
            "frontline_mode_assignment": (1429,842,1528,862), "map_anchor_amsterdam_drawing": (815,543,909,567)},
        "front-drawing-mainland.jpg": {"frontline_mode_assignment_0": (1429,842,1528,862)},
        "focus-completed-modal.jpg": {"focus_completed_modal": (1265,408,1345,435)},
        "plan-active-stable.jpg": {"plan_active": (1240,950,1261,969)},
        "plan-stop-stable.jpg": {"plan_stopped": (1240,950,1261,969),
            "frontline_button": (1247,870,1280,903), "operation_white": (986,843,1048,862)},
        "infantry-details.jpg": {"supply_infantry_name": (280,398,463,414),
            "supply_label": (280,515,350,534), "supply_100": (359,516,405,534),
            "supply_stockpile_150": (469,516,513,534)},
        "overview-army-one-stable.jpg": {
            "army_overview_title": (39, 94, 149, 116), "division_total_30": (178,145,194,162),
            "division_infantry_1": (134,357,263,374), "division_panzer_1": (134,392,244,409),
            "division_infantry_10": (134,427,272,444), "division_unassigned": (315,392,355,409),
            "overview_army_1": (316,372,376,384),
        },
        "army-one-no-general.jpg": {"army_title": (68,94,126,107), "army_no_general": (70,136,123,150),
            "army_empty_portrait": (22,122,45,168), "army_count_1_no_general": (351,94,363,109)},
        "army-one-manstein.jpg": {"army_manstein_name": (71,136,194,150),
            "army_manstein_portrait": (20,119,53,175), "army_count_1": (344,94,374,109)},
        "army-two-manstein.jpg": {"army_count_2": (344,94,374,109)},
        "army-three-manstein.jpg": {"army_count_3": (344,94,374,109)},
        "selected-panzer.jpg": {"selected_unassigned": (24,187,186,203),
            "unit_remove_button": (370,193,387,211)},
        "general-picker.jpg": {"general_picker_title": (1075,255,1251,273),
            "general_manstein_name": (1197,548,1348,565), "general_manstein_portrait": (1130,527,1187,600)},
        "remove-panzer-modal.jpg": {"remove_division_modal_title": (1201,382,1350,400),
            "remove_division_panzer_1": (1265,440,1395,457), "military_modal_ok": (1363,670,1390,686)},
    }
    for filename, templates in crops.items():
        rgb = Image.open(CAPTURES / filename).convert("RGB")
        for name, box in templates.items():
            rgb.crop(box).save(DEST / (name + ".png"))
    from hoi4_operator.executor.map_resolver import FRONT_TARGETS
    for state,filename in (("empty","map-v2-no-order.jpg"),("empty_drawing","frontline-mode-active.jpg"),
                           ("present","front-drawing-two.jpg"),
                           *((f"empty_phase_{i}",f"front-empty-phase-{i}.jpg") for i in range(4))):
        rgb = Image.open(CAPTURES / filename).convert("RGB")
        for target, data in FRONT_TARGETS.items():
            for index,box in enumerate(data["segments"]):
                rgb.crop(box).save(DEST / f"front_{target}_{state}_{index}.png")
    rgb=Image.open(CAPTURES / "front-drawing-mainland.jpg").convert("RGB")
    for index,box in enumerate(FRONT_TARGETS["GER_POL_east_prussia"]["segments"]):
        rgb.crop(box).save(DEST / f"front_GER_POL_east_prussia_empty_existing_{index}.png")
    for index,box in enumerate(FRONT_TARGETS["GER_POL_mainland"]["segments"]):
        rgb.crop(box).save(DEST / f"front_GER_POL_mainland_present_highlight_{index}.png")
    # Empty and one-army layouts have different centered card positions.
    empty = Image.open(CAPTURES / "selected-unassigned.jpg").convert("RGB")
    empty.crop((1299,1003,1321,1030)).save(DEST / "army_create_plus.png")
    one = Image.open(CAPTURES / "army-one-manstein.jpg").convert("RGB")
    one.crop((1337,998,1370,1035)).save(DEST / "army_extra_plus.png")
    (DEST / "manifest.json").write_text(json.dumps({
        "profile": "HOI4 1.19.3 / GER 1936 / base Chinese / 2560x1080 / scale 1.0",
        "sources": list(dict.fromkeys([*crops,"front-drawing-two.jpg",
            *(f"front-empty-phase-{i}.jpg" for i in range(4)),"selected-unassigned.jpg"])),
        "scope": "three divisions, first army, Manstein, two border markers, one fighter wing, region 8, one 12-ship task force",
        "identity": "session-local GUI objects; general and air region mapped from installed definitions",
    }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
