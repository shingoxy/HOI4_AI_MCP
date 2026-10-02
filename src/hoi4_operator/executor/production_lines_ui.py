"""Calibrated complete military list, compact rows and deterministic buttons."""

import cv2
import numpy as np

from ..actions.production import signature
from ..actions.equipment import EQUIPMENT
from .guard import ActionError
from .non_military_layout import PRODUCTION as LAYOUT, production_boxes
from .production_ui import ProductionUI, HEADER_BOX


DISPLAY_NAMES = ("Kar 98k式步枪", "支援装备", "105毫米18型轻型野...", "Panzer II A型",
                 "欧宝 “闪电”", "Bf109 D", "Ju 87", "He 111")
DISPLAY_TYPES = ("步兵装备 I型", "支援装备", "牵引式火炮", "改进型轻型坦克", "卡车",
                 "基础小型机身", "基础近距支援机", "基础中型机身")


class ProductionLinesUI(ProductionUI):
    def row_tops(self, rgb):
        self.found(rgb, "line_delete")  # Populate the ordinary template cache.
        template = self.templates.cache.get("line_delete")
        if template is None:
            raise ActionError("backend_unavailable", "rejected")
        x0, y0, x1, y1 = LAYOUT["delete_strip"]
        scores = cv2.matchTemplate(rgb[y0:y1, x0:x1], template, cv2.TM_CCOEFF_NORMED)
        peaks = []
        while len(peaks) <= LAYOUT["maximum_lines"]:
            _, value, _, (_, y) = cv2.minMaxLoc(scores)
            if value < 0.88:
                break
            peaks.append(y0+y+template.shape[0]//2-13)
            scores[max(0, y-25):y+26] = -1
        return sorted(peaks)

    def name_index(self, rgb, top):
        box = production_boxes(top)["name"]
        matches = [i for i in range(len(DISPLAY_NAMES)) if self.found(rgb, f"line_name_{i}", box)]
        if len(matches) != 1:
            raise ActionError("identity_mismatch", "rejected")
        return matches[0]

    def compact(self, rgb):
        # Only fold controls, never delete/reorder, are used in navigation.
        for _ in range(12):
            expanded = next((top for top in self.row_tops(rgb) if
                self.found(rgb, "line_expanded", production_boxes(top)["fold"], threshold=0.85)), None)
            if expanded is None:
                return rgb
            self.worker.click((LAYOUT["fold_x"], expanded+LAYOUT["fold_y_offset"]))
            rgb = self.ui.capture()
        raise ActionError("ui_timeout", "timed_out")

    def open(self):
        rgb = super().open()
        for i, box in enumerate(LAYOUT["filter_boxes"]):
            wanted = "on" if i < 3 else "off"
            if self.found(rgb, f"line_filter_{i}_{wanted}", box, threshold=0.85):
                continue
            other = "off" if wanted == "on" else "on"
            if not self.found(rgb, f"line_filter_{i}_{other}", box, threshold=0.85):
                raise ActionError("identity_mismatch", "rejected")
            self.worker.click(LAYOUT["filter_points"][i])
            rgb = self.ui.capture()
            self.worker.click(LAYOUT["neutral"])
            rgb = self.ui.capture()
            if not self.found(rgb, f"line_filter_{i}_{wanted}", box, threshold=0.85):
                raise ActionError("readback_failed")
        rgb = self.compact(rgb)
        self.worker.click(LAYOUT["neutral"])
        return self.ui.capture()

    def read(self, rgb):
        if not self.found(rgb, "production_title", (20, 84, 220, 124)):
            raise ActionError("panel_not_found")
        for i, box in enumerate(LAYOUT["filter_boxes"]):
            if not self.found(rgb, f"line_filter_{i}_{'on' if i < 3 else 'off'}", box, threshold=0.85):
                raise ActionError("identity_mismatch", "rejected")
        tops = self.row_tops(rgb)
        if (not tops or len(tops) > LAYOUT["maximum_lines"] or
                tops != [LAYOUT["first_top"] + LAYOUT["compact_pitch"]*i for i in range(len(tops))]):
            raise ActionError("target_not_visible", "rejected")
        used, total = map(int, self.number(rgb, HEADER_BOX, header=True).split("/"))
        lines = []
        for i, top in enumerate(tops):
            boxes = production_boxes(top)
            name = self.name_index(rgb, top)
            if not self.found(rgb, "line_compact", boxes["fold"], threshold=0.85):
                raise ActionError("target_not_visible", "rejected")
            count = int(self.number(rgb, boxes["count"]))
            lines.append({"equipment": DISPLAY_NAMES[name], "equipment_type": DISPLAY_TYPES[name],
                          "equipment_id": next((key for key, value in EQUIPMENT.items()
                                                if value["display_identity"] == DISPLAY_NAMES[name]), None),
                          "equipment_game_id": None, "position": i, "factories": count,
                          "identity_source": "gui", "stable_game_identity": False, "visible": True,
                          "identity_complete": name != 2, "action_supported": name != 2,
                          "maximum_assignable_factories": min(150, count+total-used),
                          "supported_factory_count_max": 15})
        if not 0 <= used <= total <= 150 or sum(line["factories"] for line in lines) != used:
            raise ActionError("readback_failed", "uncertain")
        # With the entire viewport covered, a visible scrollbar would mean hidden
        # rows; reject rather than infer them from the total-factory sum.
        if self.found(rgb, "production_top_scroll", (520, 366, 540, 403), threshold=0.85):
            raise ActionError("target_not_visible", "rejected")
        return {"lines": lines, "military_factories": total, "assigned_military_factories": used,
                "available_military_factories": total-used,
                "scope": "complete military list; <=10 compact calibrated rows; naval lines excluded",
                "source": "GUI", "factory_count_evidence": "every numeric row count AND global assigned total; setters additionally require target numeric AND 15-cell grid"}

    def change(self, action, before, on_commit, *, equipment_id=None, target=None, direction=None):
        rgb = self.ui.capture()
        if signature(self.read(rgb)) != signature(before):
            raise ActionError("snapshot_stale", "rejected")
        if action == "create_production_line":
            if len(before["lines"]) >= LAYOUT["maximum_lines"]:
                raise ActionError("unsupported_target", "rejected")
            self.worker.click(LAYOUT["add_equipment"])
            rgb = self.ui.capture()
            point = self.found(rgb, "picker_"+equipment_id, LAYOUT["picker_box"], threshold=0.92)
            if point is None:
                raise ActionError("target_not_found")
            on_commit()
            self.worker.click(point)
            rgb = self.ui.capture()
            if self.found(rgb, "picker_title", (680, 90, 920, 123)):
                self.worker.click(LAYOUT["picker_close"])
                self.ui.capture()
            return
        top = LAYOUT["first_top"] + target["position"]*LAYOUT["compact_pitch"]
        boxes = production_boxes(top)
        if DISPLAY_NAMES[self.name_index(rgb, top)] != target["equipment"]:
            raise ActionError("identity_mismatch", "rejected")
        if action == "delete_production_line":
            point = self.found(rgb, "line_delete", boxes["delete"], threshold=0.88)
            if point is None:
                raise ActionError("target_not_found")
            on_commit()
            self.worker.click(point)
            rgb = self.ui.capture()
            # The calibrated title and button are both required. Unknown modal
            # means uncertainty; a second delete click is never attempted.
            if self.found(rgb, "delete_modal_title", (1060, 375, 1500, 470)):
                point = self.found(rgb, "delete_modal_ok", (1300, 655, 1460, 701))
                if point is None:
                    raise ActionError("modal_blocked", "uncertain")
                self.worker.click(point)
                self.ui.capture()
        else:
            self.worker.click((LAYOUT["fold_x"], top+LAYOUT["fold_y_offset"]))
            rgb = self.ui.capture()
            self.worker.click(LAYOUT["neutral"])
            rgb = self.ui.capture()
            if not self.found(rgb, "line_expanded", boxes["fold"], threshold=0.85):
                raise ActionError("target_not_visible", "rejected")
            if DISPLAY_NAMES[self.name_index(rgb, top)] != target["equipment"]:
                raise ActionError("identity_mismatch", "rejected")
            point = self.found(rgb, "line_"+direction, boxes[direction], threshold=0.85)
            if point is None:
                raise ActionError("target_not_found")
            on_commit()
            self.worker.click(point)
            self.ui.capture()

    def grid_count(self, rgb, top):
        count = int(self.number(rgb, production_boxes(top)["count"]))
        if count > 15 or not self.found(rgb, "production_scale", (283, top+28, 325, top+103)):
            raise ActionError("unsupported_grid_scale", "rejected")
        cells = []
        for row in range(3):
            for column in range(5):
                x, y = 338+29*column, top+42+22*row
                on = any(self.found(rgb, name, (x-12, y-10, x+13, y+10), threshold=0.85)
                         for name in ("production_grid_on", "production_grid_assigned_alternate"))
                off = int(rgb[y-5:y+6, x-7:x+8].max()) < 80
                if on == off:
                    raise ActionError("readback_failed", "uncertain")
                cells.append(on)
        if cells != [True]*count + [False]*(15-count):
            raise ActionError("readback_failed", "uncertain")
        return count

    def adjust_one(self, position, increasing, on_commit, expected):
        rgb = self.ui.capture()
        if signature(self.read(rgb)) != signature(expected):
            raise ActionError("snapshot_stale", "rejected")
        top = LAYOUT["first_top"] + position*LAYOUT["compact_pitch"]
        self.worker.click((LAYOUT["fold_x"], top+LAYOUT["fold_y_offset"]))
        rgb = self.ui.capture()
        self.worker.click(LAYOUT["neutral"])
        rgb = self.ui.capture()
        if not self.found(rgb, "line_expanded", production_boxes(top)["fold"], threshold=0.85):
            raise ActionError("target_not_visible", "rejected")
        count = self.grid_count(rgb, top)
        if count != expected["lines"][position]["factories"]:
            raise ActionError("snapshot_stale", "rejected")
        point = self.found(rgb, "production_add" if increasing else "production_sub",
                           (460, top, 489, top+26) if increasing else (385, top, 414, top+26), threshold=0.85)
        if point is None:
            raise ActionError("target_not_found")
        on_commit()
        self.worker.click(point)
        rgb = self.ui.capture()
        self.worker.click(LAYOUT["neutral"])
        rgb = self.ui.capture()
        if self.grid_count(rgb, top) != count + (1 if increasing else -1):
            raise ActionError("readback_failed", "uncertain")
        self.worker.click((LAYOUT["fold_x"], top+LAYOUT["fold_y_offset"]))
        self.ui.capture()
