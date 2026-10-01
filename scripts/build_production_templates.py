"""Rebuild local production crops and bounded numeric recognition fixtures."""

import json
from pathlib import Path
import re

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / "artifacts/phase3b1"
FONT = Path("D:/Software/Steam/steamapps/common/Hearts of Iron IV/gfx/fonts/chinese/hoi_18_1of4")
NAMES = ["Kar 98k式步枪", "支援装备", "105毫米18型轻型野...", "二号轻型坦克A型",
         "欧宝 “闪电”", "梅塞施密特 Bf-109D..."]


def text_mask(rgb, header=False):
    a = np.asarray(rgb).astype(np.int16)
    if header:
        if np.any((a[:, :, 0] > 130) & (a[:, :, 0] > a[:, :, 1] + 50)):
            return ((a[:, :, 0] > 95) & (a[:, :, 0] > a[:, :, 1] + 30)).astype(np.uint8)
        return (a.max(2) > 140).astype(np.uint8)
    return ((a.min(2) > 170) & (a.max(2) - a.min(2) < 45)).astype(np.uint8)


def glyphs(mask):
    edges = np.diff(np.r_[False, np.any(mask, axis=0), False].astype(np.int8))
    result = []
    for start, end in zip(np.where(edges == 1)[0], np.where(edges == -1)[0]):
        crop = mask[:, start:end]
        x, y, w, h = cv2.boundingRect(cv2.findNonZero(crop))
        result.append(crop[y:y+h, x:x+w])
    return result


def main():
    directory = ROOT / "templates"
    directory.mkdir(parents=True, exist_ok=True)
    image = Image.open(ROOT / "captures/production-before.jpg")
    crops = {"production_title": (35, 89, 95, 119),
             "production_top_scroll": (523, 369, 537, 400),
             "production_add": (463, 376, 485, 398),
             "production_sub": (388, 376, 411, 398),
             "production_grid_on": (328, 409, 349, 425),
             "production_scale": (286, 404, 321, 473)}
    for position in range(6):
        top = 374 + 111 * position
        crops[f"production_name_{position}"] = (46, top+1, 220, top+22)
        crops[f"production_type_{position}"] = (13, top+28, 160, top+46)
        crops[f"production_priority_{position}"] = (14, top+6, 31, top+23)
    for name, box in crops.items():
        image.crop(box).save(directory / (name + ".png"))
    Image.open(ROOT / "captures/readback-11-failure.jpg").crop((328, 453, 349, 469)).save(
        directory / "production_grid_assigned_alternate.png")
    # Tiny digit masks are derived from this installed game's Chinese font;
    # no font atlas or proprietary game files are copied into the project.
    atlas = np.asarray(Image.open(str(FONT) + ".dds"))
    lines = FONT.with_suffix(".fnt").read_text().splitlines()
    for digit in "0123456789":
        line = next(x for x in lines if re.match(r"char id=" + str(ord(digit)) + r"\s", x))
        values = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", line)}
        x, y, w, h = (values[k] for k in ("x", "y", "width", "height"))
        mask = (atlas[y:y+h, x:x+w, 3] > 170).astype(np.uint8)
        gx, gy, gw, gh = cv2.boundingRect(cv2.findNonZero(mask))
        Image.fromarray(mask[gy:gy+gh, gx:gx+gw] * 255).save(directory / f"factory_digit_{digit}.png")
    # Header glyphs use their observed colored font, not a guessed font.
    sources = [("production-before", "20/28")] + [(f"calibration-{n}", f"{n}/28") for n in [*range(11, 20), 23]]
    for source, label in sources:
        pieces = glyphs(text_mask(Image.open(ROOT / "captures" / (source + ".jpg")).crop((210, 215, 262, 236)), header=True))
        if len(pieces) != len(label):
            raise ValueError("header calibration segmentation failed")
        for index, (char, mask) in enumerate(zip(label, pieces)):
            name = "slash" if char == "/" else char
            Image.fromarray(mask * 255).save(directory / f"header_digit_{name}_{source}_p{index}.png")
    (directory / "manifest.json").write_text(json.dumps({
        "conditions": "HOI4 1.19.3 / GER / Chinese / 2560x1080 / scale 1.0 / top viewport",
        "source": "production-before.jpg", "crops": crops, "equipment_names": NAMES,
        "factory_digits": "0123456789", "header_digits": "0123456789/",
        "font_source": str(FONT), "factory_range": [0, 15],
        "alternate_grid_source": "readback-11-failure.jpg / first line's 11th assigned factory",
        "identity_note": "Visible GUI labels, including truncation; not equipment game IDs",
        "action_identity_note": "Truncated equipment labels are observation-only; assignment rejected",
    }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
