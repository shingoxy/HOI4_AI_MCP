"""Fixed-camera, three-state deterministic construction UI, fail closed."""

import cv2
import numpy as np

from ..actions.construction import STATES, BUILDINGS, order
from .guard import ActionError
from .non_military_layout import CONSTRUCTION as L, construction_boxes


class ConstructionUI:
    def __init__(self, ui, templates):
        self.ui, self.worker, self.templates = ui, ui.worker, templates

    def found(self, rgb, name, box=None, threshold=0.90):
        return self.templates.find(rgb, name, box, threshold)

    def open(self):
        rgb = self.ui.capture()
        if not self.found(rgb, "construction_title", (20, 83, 150, 124)):
            self.worker.key("t")
            rgb = self.ui.capture()
            if not self.found(rgb, "construction_title", (20, 83, 150, 124)):
                self.worker.click(L["entry"])
                rgb = self.ui.capture()
        self.worker.click(L["neutral"])
        rgb = self.ui.capture()
        if not self.found(rgb, "construction_title", (20, 83, 150, 124)):
            raise ActionError("panel_not_found")
        return rgb

    def tops(self, rgb):
        self.found(rgb, "construction_cancel")
        template = self.templates.cache.get("construction_cancel")
        if template is None:
            raise ActionError("backend_unavailable", "rejected")
        x0, y0, x1, y1 = L["cancel_strip"]
        scores = cv2.matchTemplate(rgb[y0:y1, x0:x1], template, cv2.TM_CCOEFF_NORMED)
        peaks = []
        while len(peaks) <= L["max_items"]:
            _, score, _, (_, y) = cv2.minMaxLoc(scores)
            if score < .9:
                break
            peaks.append(y0+y+template.shape[0]//2-24)
            scores[max(0, y-25):y+26] = -1
        return sorted(peaks)

    @staticmethod
    def white(rgb):
        rgb = rgb.astype(np.int16)
        return (rgb.min(2) > 170) & (rgb.max(2)-rgb.min(2) < 45)

    def read(self, rgb):
        if self.found(rgb, "construction_modal_title", L["modal_title"]):
            raise ActionError("modal_blocked", "rejected")
        if not self.found(rgb, "construction_title", (20, 83, 150, 124)):
            raise ActionError("panel_not_found")
        tops = self.tops(rgb)
        if len(tops) > L["max_items"] or tops != [L["first_top"]+L["pitch"]*i for i in range(len(tops))]:
            raise ActionError("target_not_visible", "rejected")
        # Validate the consumer-goods prefix and a truly empty tail. Unknown
        # repairs, hidden entries or other queue types must not disappear from
        # the observation merely because a target-name template is absent.
        if not self.found(rgb, "construction_consumer", (8, 230, 175, 273)):
            raise ActionError("identity_mismatch", "rejected")
        tail = rgb[281+52*len(tops):1020, 20:390].astype(np.int16)
        if tail.size and (np.mean(tail.max(2)-tail.min(2) > 35) > .015 or
                          np.count_nonzero(tail.max(2) > 100) > 8):
            raise ActionError("readback_ambiguous", "rejected")
        queue = []
        one = self.white(self.templates.cache.get("construction_one") if "construction_one" in self.templates.cache else
                         self._load_one())
        for index, top in enumerate(tops):
            boxes = construction_boxes(top)
            states = [state for state in STATES if self.found(rgb, f"construction_state_{state}", boxes["state"])]
            buildings = [building for building in BUILDINGS if self.found(rgb, "construction_"+building, boxes["building"], .9)]
            if len(states) != 1 or len(buildings) != 1:
                raise ActionError("identity_mismatch", "rejected")
            x0, y0, x1, y1 = boxes["count"]
            count = self.white(rgb[y0:y1, x0:x1])
            if count.shape != one.shape or np.count_nonzero(count ^ one) > 3:
                raise ActionError("readback_ambiguous", "rejected")
            assigned = next((value for value in (0, 3, 15) if self.found(
                rgb, f"construction_factories_{value}", boxes["factories"], .95)), None)
            queue.append({"state_id": states[0], "state_display": STATES[states[0]],
                          "building_type": buildings[0], "count": 1, "position": index,
                          "assigned_civilian_factories": assigned, "progress": None})
        if len(set(order({"queue": queue}))) != len(queue):
            raise ActionError("readback_ambiguous", "rejected")
        return {"queue": queue, "identity_source": "gui", "stable_game_identity": False,
                "scope": "complete visible queue; <=8 one-building rows; states 64/65/66 only",
                "unknown_fields": ["numeric_progress", "uncalibrated_factory_allocations", "internal_queue_id"]}

    def _load_one(self):
        from PIL import Image
        self.templates.cache["construction_one"] = np.asarray(Image.open(
            self.templates.directory / "construction_one.png").convert("RGB"))
        return self.templates.cache["construction_one"]

    def observe(self):
        self.worker.click(L["neutral"])
        return self.read(self.ui.capture())

    def cancel_confirmation(self, rgb, target):
        # Match the actual dialog target before OK, rather than trusting the
        # queue row or a generic confirmation button beneath an unrelated modal.
        states = [s for s in STATES if self.found(rgb, f"construction_modal_state_{s}", L["modal_body"])]
        buildings = [b for b in BUILDINGS if self.found(rgb, "construction_modal_"+b, L["modal_body"])]
        point = self.found(rgb, "delete_modal_ok", L["modal_ok"])
        if (not self.found(rgb, "construction_modal_title", L["modal_title"]) or
                states != [target["state_id"]] or buildings != [target["building_type"]] or point is None):
            raise ActionError("identity_mismatch", "uncertain")
        return point

    def change(self, action, before, on_commit, *, state_id=None, building_type=None, target=None, direction=None):
        rgb = self.ui.capture()
        if order(self.read(rgb)) != order(before):
            raise ActionError("snapshot_stale", "rejected")
        if action == "build":
            if len(before["queue"]) >= L["max_items"]:
                raise ActionError("unsupported_target", "rejected")
            self.close()
            rgb = self.ui.capture()
            if not self.found(rgb, "construction_map_anchor", L["map_anchor_box"], .9):
                raise ActionError("target_not_visible", "rejected")
            # Read the normal state panel before selecting build mode. This is
            # the state-ID verification, independent of the after-queue diff.
            self.worker.click(L["state_points"][state_id])
            rgb = self.ui.capture()
            if (not self.found(rgb, f"state_title_{state_id}", L["state_title"]) or
                    not self.found(rgb, "state_owner_ger", L["owner_box"])):
                raise ActionError("identity_mismatch", "rejected")
            self.worker.click(L["state_close"])
            self.ui.capture()
            rgb = self.open()
            if order(self.read(rgb)) != order(before):
                raise ActionError("snapshot_stale", "rejected")
            button = L["building_points"][building_type]
            x, y = button
            if not self.found(rgb, "construction_button_"+building_type, (x-24, y-24, x+24, y+24), .85):
                raise ActionError("target_not_found")
            self.worker.click(button)
            rgb = self.ui.capture()
            self.worker.click(L["neutral"])
            rgb = self.ui.capture()
            if not self.found(rgb, "construction_selected_"+building_type, (x-24, y-24, x+24, y+24), .9):
                raise ActionError("requirements_not_met", "rejected")
            on_commit()
            self.worker.click(L["state_points"][state_id])
            self.ui.capture()
        else:
            top = L["first_top"]+target["position"]*L["pitch"]
            boxes = construction_boxes(top)
            name = "construction_cancel" if action == "cancel_construction" else "construction_"+direction
            box = boxes["cancel" if action == "cancel_construction" else direction]
            point = self.found(rgb, name, box, .9)
            if point is None:
                raise ActionError("requirements_not_met", "rejected")
            on_commit()
            self.worker.click(point)
            rgb = self.ui.capture()
            if action == "cancel_construction":
                self.worker.click(self.cancel_confirmation(rgb, target))
                self.ui.capture()

    def close(self):
        rgb = self.ui.capture()
        if self.found(rgb, "construction_title", (20, 83, 150, 124)):
            self.worker.click(L["close"])
            self.ui.capture()
