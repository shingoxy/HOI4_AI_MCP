"""Reproducible local calibration crops; no proprietary atlas is distributed."""

import json
from pathlib import Path
import shutil
import sys
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "artifacts/phase3/templates"


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    for path in (ROOT / "artifacts/phase3b1/templates").glob("*.png"):
        if path.name.startswith(("factory_digit_", "header_digit_")) or path.name in {
                "production_title.png", "production_top_scroll.png", "production_grid_on.png",
                "production_grid_assigned_alternate.png", "production_scale.png",
                "production_add.png", "production_sub.png"}:
            shutil.copy2(path, DEST / path.name)
    captures = ROOT / "artifacts/phase3/captures"
    compact = Image.open(captures / "military-compact.jpg")
    expanded = Image.open(captures / "production-top.jpg")
    all_filters = Image.open(captures / "filters-all.jpg")
    picker = Image.open(captures / "equipment-picker.jpg")
    crops = {
        "line_delete": (493, 378, 511, 396),
        "line_compact": (30, 380, 38, 395),
        "picker_title": (717, 96, 808, 116),
    }
    for name, box in crops.items():
        (picker if name.startswith("picker") else compact).crop(box).save(DEST / (name+".png"))
    expanded.crop((30, 380, 38, 395)).save(DEST / "line_expanded.png")
    expanded.crop((12, 419, 32, 444)).save(DEST / "line_up.png")
    expanded.crop((12, 445, 32, 472)).save(DEST / "line_down.png")
    for i in range(8):
        top = 374 + 63*i
        compact.crop((46, top+1, 222, top+23)).save(DEST / f"line_name_{i}.png")
    for i in range(6):
        # Exclude quantity and hover background where possible; selection arrow
        # and category icon jointly establish the filter state.
        box = (11+85*i, 304, 50+85*i, 332)
        all_filters.crop(box).save(DEST / f"line_filter_{i}_on.png")
        if i >= 3:
            compact.crop(box).save(DEST / f"line_filter_{i}_off.png")
    picker.crop((567, 263, 830, 293)).save(DEST / "picker_infantry_equipment_1.png")
    picker.crop((567, 423, 830, 453)).save(DEST / "picker_support_equipment_1.png")
    modal = Image.open(captures / "delete-modal.jpg")
    modal.crop((1228, 382, 1322, 403)).save(DEST / "delete_modal_title.png")
    modal.crop((1358, 668, 1392, 688)).save(DEST / "delete_modal_ok.png")
    modal.crop((1187, 668, 1221, 688)).save(DEST / "delete_modal_cancel.png")
    queue = Image.open(captures / "construction-three.jpg")
    queue.crop((35, 92, 89, 115)).save(DEST / "construction_title.png")
    queue.crop((24, 241, 108, 261)).save(DEST / "construction_consumer.png")
    queue.crop((377, 294, 398, 316)).save(DEST / "construction_cancel.png")
    queue.crop((326, 396, 342, 423)).save(DEST / "construction_up.png")
    queue.crop((348, 292, 365, 319)).save(DEST / "construction_down.png")
    queue.crop((206, 309, 221, 328)).save(DEST / "construction_one.png")
    for state, index, width in [(65, 0, 50), (66, 1, 98), (64, 2, 66)]:
        top = 281+52*index
        queue.crop((24, top+10, 24+width, top+29)).save(DEST / f"construction_state_{state}.png")
        state_rgb = Image.open(captures / f"state-{state}.jpg")
        state_rgb.crop((174, 436, 315, 462)).save(DEST / f"state_title_{state}.png")
    state_rgb.crop((32, 492, 68, 513)).save(DEST / "state_owner_ger.png")
    state_rgb.crop((1283, 287, 1365, 305)).save(DEST / "construction_map_anchor.png")
    for building, index, point, selected_source in [
            ("civilian_factory", 0, (521, 290), "construction-civilian-65.jpg"),
            ("infrastructure", 1, (474, 197), "construction-infrastructure-66.jpg"),
            ("military_factory", 2, (474, 290), "construction-three.jpg")]:
        top = 281+52*index
        queue.crop((181, top+6, 218, top+28)).save(DEST / f"construction_{building}.png")
        x, y = point
        # Icon interior works across selected/unselected button backgrounds.
        queue.crop((x-13, y-13, x+13, y+13)).save(DEST / f"construction_button_{building}.png")
        selected = Image.open(captures / selected_source)
        selected.crop((x-21, y-21, x+21, y+21)).save(DEST / f"construction_selected_{building}.png")
    for value, index in [(15, 0), (3, 1), (0, 2)]:
        top = 281+52*index
        queue.crop((270 if value == 15 else 274, top+9, 304 if value == 15 else 299, top+24)).save(
            DEST / f"construction_factories_{value}.png")
    cancel_modal = Image.open(captures / "construction-cancel-66.jpg")
    cancel_modal.crop((1235, 379, 1319, 403)).save(DEST / "construction_modal_title.png")
    for state, name_box, building, building_box in [
            (64, (1233, 439, 1295, 459), "military_factory", (1309, 439, 1364, 459)),
            (65, (1242, 439, 1289, 459), "civilian_factory", (1302, 439, 1360, 459)),
            (66, (1229, 439, 1303, 459), "infrastructure", (1316, 439, 1378, 459))]:
        modal = Image.open(captures / f"construction-cancel-{state}.jpg")
        modal.crop(name_box).save(DEST / f"construction_modal_state_{state}.png")
        modal.crop(building_box).save(DEST / f"construction_modal_{building}.png")
    politics = Image.open(captures / "politics-before.jpg")
    politics.crop((84, 529, 158, 551)).save(DEST / "politics_title.png")
    politics.crop((371, 575, 389, 615)).save(DEST / "advisor_empty.png")
    hired = Image.open(captures / "advisor-hired-calibration.jpg")
    hired.crop((279, 576, 302, 611)).save(DEST / "advisor_schacht_portrait.png")
    advisors = Image.open(captures / "advisor-list-before.jpg")
    advisors.crop((733, 85, 802, 104)).save(DEST / "advisor_selector_title.png")
    advisors.crop((853, 278, 975, 299)).save(DEST / "advisor_schacht_name.png")
    advisors.crop((992, 317, 1004, 333)).save(DEST / "advisor_cost_75.png")
    for group, ids in [("economy", ["low_economic_mobilisation", "partial_economic_mobilisation"]),
                       ("conscription", ["volunteer_only", "limited_conscription"])]:
        laws = Image.open(captures / f"{group}-list-before.jpg")
        laws.crop((730, 85, 802, 104)).save(DEST / f"law_{group}_title.png")
        for index, law in enumerate(ids):
            y = 214+75*index
            laws.crop((632, y+20, 725, y+44)).save(DEST / f"law_{law}_name.png")
        laws.crop((819, 243, 842, 259)).save(DEST / "law_cost_150.png")
    laws.crop((568, 289, 620, 295)).save(DEST / "law_selected.png")
    for group, boxes in [("economy", {"partial_economic_mobilisation": (1254,439,1315,459),
                                      "low_economic_mobilisation": (1345,439,1406,459)}),
                         ("conscription", {"limited_conscription": (1246,439,1308,459),
                                          "volunteer_only": (1337,439,1414,459)})]:
        modal = Image.open(captures / f"{group}-confirm.jpg")
        for law, box in boxes.items():
            modal.crop(box).save(DEST / f"law_modal_{law}.png")
    modal.crop((1193,379,1359,403)).save(DEST / "politics_modal_title.png")
    modal.crop((1208,439,1233,459)).save(DEST / "politics_modal_cost_150.png")
    trade = Image.open(captures / "trade-steel-before.jpg")
    trade.crop((38,92,92,116)).save(DEST / "trade_title.png")
    trade.crop((430,162,493,191)).save(DEST / "trade_steel_selected.png")
    trade.crop((15,732,95,754)).save(DEST / "trade_swe_row.png")
    Image.open(captures/"trade-steel-after-one.jpg").crop((431,735,438,749)).save(
        DEST / "trade_quantity_separator.png")
    dialog = Image.open(captures / "trade-swe-dialog-two.jpg")
    dialog.crop((1258,354,1300,376)).save(DEST / "trade_swe_title.png")
    dialog.crop((1449,339,1526,384)).save(DEST / "trade_swe_flag.png")
    dialog.crop((1050,439,1073,454)).save(DEST / "trade_steel_icon.png")
    dialog.crop((1136,643,1148,658)).save(DEST / "trade_minus.png")
    dialog.crop((1418,643,1430,658)).save(DEST / "trade_plus.png")
    dialog.crop((1111,714,1183,733)).save(DEST / "trade_dialog_close.png")
    dialog.crop((1395,713,1463,733)).save(DEST / "trade_send.png")
    # Calibrate digit masks from known, visible numeric strings, never from a
    # proprietary font atlas. Slash glyphs are deliberately excluded.
    sys.path.insert(0, str(ROOT/"src"))
    from hoi4_operator.executor.trade_ui import gold_glyphs
    rgb = np.asarray(trade.convert("RGB"))
    digits = {}
    for value, y in [("529/657",562),("274/282",607),("270/326",652),("77/125",742)]:
        glyphs = gold_glyphs(rgb[y-13:y+13,230:315])
        value = value.replace("/", "")
        if len(glyphs) != len(value):
            raise ValueError(f"digit calibration mismatch: {value}: {len(glyphs)} glyphs")
        for character, glyph in zip(value, glyphs):
            digits.setdefault(character, []).append(glyph)
    if len(digits) != 10: raise ValueError("incomplete trade digit calibration")
    for name, amount, factories in [("zero",0,0),("one",8,1),("two",16,2)]:
        rgb = np.asarray(Image.open(captures/f"trade-swe-dialog-{name}.jpg").convert("RGB"))
        for text, box in [(str(amount),(1207,583,1238,605)),(str(factories),(1223,604,1246,626))]:
            x0,y0,x1,y1 = box
            glyphs = gold_glyphs(rgb[y0:y1,x0:x1])
            if len(glyphs) != len(text): raise ValueError("dialog digit calibration mismatch")
            for digit, glyph in zip(text,glyphs): digits[digit].append(glyph)
    for digit, glyphs in digits.items():
        for index, glyph in enumerate(glyphs):
            Image.fromarray(glyph.astype(np.uint8)*255).save(DEST / f"trade_digit_{digit}_{index}.png")
    (DEST / "manifest.json").write_text(json.dumps({
        "conditions": "1.19.3 / GER 1936 / base Chinese / Telemetry Mod only / 2560x1080 / 1.0",
        "production_scope": "all military rows in compact layout; at most 10; naval excluded",
        "sources": ["military-compact.jpg", "production-top.jpg", "filters-all.jpg", "equipment-picker.jpg"],
        "equipment_game_ids": "UNKNOWN; semantic catalog is independent",
    }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
