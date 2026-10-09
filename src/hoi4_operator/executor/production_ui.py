"""Bounded production readback: named rows, numeric count and factory grid agree."""

import cv2
import numpy as np
from PIL import Image

from .catalog import (BOXES, POINTS, PRODUCTION_ROWS, PRODUCTION_BOXES,
                      PRODUCTION_ROW_BOXES, PRODUCTION_GRID)
from .guard import ActionError
from .templates import Templates

PRODUCTION_NAMES = ("Kar 98k式步枪", "支援装备", "105毫米18型轻型野...",
                    "二号轻型坦克A型", "欧宝 “闪电”", "梅塞施密特 Bf-109D...")
PRODUCTION_TYPES = ("步兵装备 I型", "支援装备", "牵引式火炮", "改进型轻型坦克", "卡车", "基础小型机身")
ROW_TOPS = PRODUCTION_ROWS
HEADER_BOX = PRODUCTION_BOXES["header"]
MAX_GAME_FACTORIES = 150  # Installed 1.19.3 defines, ordinary military lines only.
SUPPORTED_MAX = 15


def text_mask(rgb, header=False):
    a = rgb.astype(np.int16)
    if header:
        if np.any((a[:, :, 0] > 130) & (a[:, :, 0] > a[:, :, 1] + 50)):
            return ((a[:, :, 0] > 95) & (a[:, :, 0] > a[:, :, 1] + 30)).astype(np.uint8)
        return (a.max(2) > 140).astype(np.uint8)
    return ((a.min(2) > 170) & (a.max(2) - a.min(2) < 45)).astype(np.uint8)


class ProductionUI:
    def __init__(self, ui, templates, native_digits=None):
        self.ui, self.worker, self.templates = ui, ui.worker, templates
        self.native_digits = native_digits
        self.native_templates = Templates(native_digits) if native_digits else None
        self.digits = {}

    def found(self, rgb, name, box=None, threshold=0.90):
        point = self.templates.find(rgb, name, box, threshold)
        profile = getattr(self.worker, "capture_profile", None)
        if (point is None and self.native_templates is not None and
                getattr(profile, "name", None) == "GER_2560x1600_DPI120_PHYSICAL"):
            point = self.native_templates.find(rgb, name, box, threshold)
        return point

    @staticmethod
    def glyph_score(glyph, piece, header):
        if not header:
            return float((glyph == piece).mean()) if glyph.shape == piece.shape else 0
        h, w = piece.shape
        gh, gw = glyph.shape
        if abs(gh-h) > 1 or abs(gw-w) > 1:
            return 0
        # JPEG can add a one-pixel edge. Align masks without stretching the
        # character, and compare foreground overlap rather than empty pixels.
        shape = (max(h, gh)+4, max(w, gw)+4)
        observed = np.zeros(shape, dtype=bool)
        observed[2:2+h, 2:2+w] = piece
        best = 0
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                expected = np.zeros(shape, dtype=bool)
                expected[2+dy:2+dy+gh, 2+dx:2+dx+gw] = glyph
                union = np.count_nonzero(observed | expected)
                if union:
                    best = max(best, np.count_nonzero(observed & expected)/union)
        return best

    def number(self, rgb, box, *, header=False):
        x0, y0, x1, y1 = box
        mask = text_mask(rgb[y0:y1, x0:x1], header)
        edges = np.diff(np.r_[False, np.any(mask, axis=0), False].astype(np.int8))
        text = ""
        for start, end in zip(np.where(edges == 1)[0], np.where(edges == -1)[0]):
            piece = mask[:, start:end]
            x, y, w, h = cv2.boundingRect(cv2.findNonZero(piece))
            piece = piece[y:y+h, x:x+w]
            scores = []
            profile = getattr(self.worker, "capture_profile", None)
            native_profile = bool(self.native_digits and getattr(profile, "name", None) == "GER_2560x1600_DPI120_PHYSICAL")
            tokens = list("0123456789/" if header else "0123456789")
            if header and native_profile:
                tokens.extend(("0/", "2/"))  # Independently calibrated native joined pairs.
            for digit in tokens:
                label = {"/": "slash", "0/": "zero_slash", "2/": "two_slash"}.get(digit, digit)
                name = ("header_digit_" if header else "factory_digit_") + label
                if name not in self.digits:
                    paths = (list(self.templates.directory.glob(name + "_*_p*.png")) if header else
                             [self.templates.directory / (name + ".png")])
                    if native_profile:
                        native = (list(self.native_digits.glob(name+"_*_p*.png")) if header else
                                  list(self.native_digits.glob(name+".png")))
                        if native:
                            paths = native
                    self.digits[name] = [np.asarray(Image.open(p)) > 0 for p in paths]
                values = [self.glyph_score(glyph, piece, header) for glyph in self.digits[name]]
                if values:
                    scores.append((max(values), digit))
            scores.sort(reverse=True)
            if (not scores or scores[0][0] < 0.84 or
                    (len(scores) > 1 and scores[0][0] - scores[1][0] < 0.10)):
                raise ActionError("production_number_unreadable")
            text += scores[0][1]
        if not text or len(text) > (7 if header else 3):
            raise ActionError("production_number_unreadable")
        return text

    def open(self):
        rgb = self.ui.capture()
        if not self.found(rgb, "production_title", BOXES["panel_title"]):
            self.worker.key("y")
            rgb = self.ui.capture()
            if not self.found(rgb, "production_title", BOXES["panel_title"]):
                self.worker.click(POINTS["production"])
                rgb = self.ui.capture()
        if not self.found(rgb, "production_title", BOXES["panel_title"]):
            raise ActionError("panel_not_found")
        self.worker.click(POINTS["production_neutral"])
        return self.ui.capture()

    def read(self, rgb):
        if not self.found(rgb, "production_title", BOXES["panel_title"]):
            raise ActionError("panel_not_found")
        if not self.found(rgb, "production_top_scroll", PRODUCTION_BOXES["scroll_top"], threshold=0.85):
            raise ActionError("target_not_visible", "rejected")
        try:
            used, total = map(int, self.number(rgb, HEADER_BOX, header=True).split("/"))
        except ValueError:
            raise ActionError("production_number_unreadable")
        if not 0 <= used <= total <= 150:
            raise ActionError("production_number_unreadable")
        lines = []
        for position, boxes in enumerate(PRODUCTION_ROW_BOXES):
            matches = [n for n in range(6) if
                       self.found(rgb, f"production_name_{n}", boxes["name"]) and
                       self.found(rgb, f"production_type_{n}", boxes["type"])]
            if len(matches) != 1:
                raise ActionError("gui_identity_mismatch", "rejected")
            if not self.found(rgb, f"production_priority_{position}", boxes["priority"]):
                raise ActionError("production_snapshot_stale", "rejected")
            count = int(self.number(rgb, boxes["count"]))
            if count > SUPPORTED_MAX:
                raise ActionError("unsupported_factory_count", "rejected")
            if not self.found(rgb, "production_scale", boxes["scale"]):
                raise ActionError("unsupported_grid_scale", "rejected")
            grid = []
            for cell in PRODUCTION_GRID[position]:
                on = any(self.found(rgb, name, cell["box"], threshold=0.85) is not None
                         for name in ("production_grid_on", "production_grid_assigned_alternate"))
                # Empty cell interiors are dark (<80 in this calibration).
                # Normalized correlation is unsuitable for nearly flat cells.
                x0, y0, x1, y1 = cell["interior"]
                interior = rgb[y0:y1, x0:x1]
                off = interior.size > 0 and int(interior.max()) < 80
                if on == off:
                    raise ActionError("production_grid_unreadable")
                grid.append(on)
            if grid != [True] * count + [False] * (15-count):
                raise ActionError("production_count_disagreement", "uncertain")
            lines.append({"equipment": PRODUCTION_NAMES[matches[0]],
                          "equipment_type": PRODUCTION_TYPES[matches[0]], "equipment_game_id": None,
                          "position": position, "factories": count, "identity_source": "gui",
                          "stable_game_identity": False, "visible": True,
                          "identity_complete": not PRODUCTION_NAMES[matches[0]].endswith("..."),
                          "action_supported": not PRODUCTION_NAMES[matches[0]].endswith("..."),
                          "maximum_assignable_factories": min(MAX_GAME_FACTORIES, count + total-used),
                          "game_line_limit": MAX_GAME_FACTORIES,
                          "supported_factory_count_max": SUPPORTED_MAX,
                          "efficiency": None, "current_output": None})
        if len({line["equipment"] for line in lines}) != len(lines):
            raise ActionError("ambiguous_production_identity", "rejected")
        return {"lines": lines, "assigned_military_factories": used,
                "available_military_factories": total-used, "military_factories": total,
                "scope": "six_complete_top_viewport_military_lines", "source": "GUI",
                "factory_count_evidence": "numeric counter AND unscaled 15-cell factory grid"}

    def observe(self):
        return self.read(self.open())

    def adjust_one(self, position, increasing, on_commit, expected):
        rgb = self.ui.capture()
        from ..actions.production import signature
        current = self.read(rgb)
        if (signature(current) != signature(expected) or
                current["assigned_military_factories"] != expected["assigned_military_factories"] or
                current["military_factories"] != expected["military_factories"]):
            raise ActionError("production_snapshot_stale", "rejected")
        boxes = PRODUCTION_ROW_BOXES[position]
        name, box = (("production_add", boxes["add"]) if increasing else
                     ("production_sub", boxes["sub"]))
        point = self.found(rgb, name, box, threshold=0.85)
        if point is None:
            raise ActionError("factory_button_not_found")
        on_commit()
        self.worker.click(point)
        self.ui.capture()
        self.worker.click(POINTS["production_neutral"])
        self.ui.capture()

    def close(self):
        rgb = self.ui.capture()
        if self.found(rgb, "production_title", BOXES["panel_title"]):
            self.worker.click(POINTS["panel_close"])
            self.ui.capture()
