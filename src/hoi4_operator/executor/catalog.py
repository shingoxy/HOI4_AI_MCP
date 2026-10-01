"""The single calibrated layout: HOI4 1.19.3, GER, Chinese UI, 2560x1080/1.0."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchTarget:
    category: str
    point: tuple[int, int]


RESEARCH = {
    "basic_machine_tools": ResearchTarget("industry", (270, 350)),
    "construction1": ResearchTarget("industry", (840, 490)),
    "electronic_mechanical_engineering": ResearchTarget("electronics", (295, 350)),
}
FOCUS = "GER_remilitarize_the_rhineland"
SIZE = (2560, 1080)
POINTS = {
    "research": (247, 54), "politics": (42, 45), "production": (465, 55),
    "production_neutral": (185, 103),
    "industry": (776, 111), "electronics": (687, 111),
    "tech_start": (950, 173), "detail_close": (1024, 125),
    "tree_close": (2527, 103), "panel_close": (518, 103),
    "focus_tree": (399, 170),
}
SLOTS = tuple((260, 345 + 100 * n) for n in range(4))
SLOT_BOXES = tuple((55, 308 + 100 * n, 230, 335 + 100 * n) for n in range(4))
SLOT_FRAME_BOXES = tuple((10, 300 + 100 * n, 40, 390 + 100 * n) for n in range(4))
BOXES = {
    "panel_title": (20, 84, 220, 124),
    "category_bar": (10, 84, 830, 137),
    "tech_title": (520, 108, 1000, 145),
    "tech_button": (886, 153, 1010, 192),
    "focus_active": (280, 135, 500, 196),
    "focus_cancel": (500, 138, 524, 162),
    "focus_empty": (280, 135, 500, 196),
    "focus_nodes": (210, 140, 2535, 1050),
    "replace_title": (1050, 355, 1500, 425),
    "replace_ok": (1300, 655, 1450, 700),
}

# Production coordinates are deliberately limited to the calibrated top viewport.
PRODUCTION_ROWS = tuple(374 + 111 * i for i in range(6))
PRODUCTION_BOXES = {"header": (210, 215, 262, 236), "scroll_top": (520, 366, 540, 403)}
PRODUCTION_ROW_BOXES = tuple({
    "name": (42, top, 225, top+24), "type": (10, top+26, 164, top+48),
    "priority": (12, top+4, 34, top+25), "count": (412, top+3, 460, top+25),
    "scale": (283, top+28, 325, top+103),
    "add": (460, top, 489, top+26), "sub": (385, top, 414, top+26),
} for top in PRODUCTION_ROWS)
PRODUCTION_GRID = tuple(tuple({
    "box": (x-13, y-10, x+13, y+10), "interior": (x-7, y-5, x+7, y+6),
} for index in range(15)
    for x, y in [(338+29*(index % 5), top+42+22*(index // 5))]) for top in PRODUCTION_ROWS)
