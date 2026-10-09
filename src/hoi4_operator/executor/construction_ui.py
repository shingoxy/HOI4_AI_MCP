"""Fixed-camera, three-state deterministic construction UI, fail closed."""

import cv2
import numpy as np

from ..actions.construction import STATES, BUILDINGS, order
from .guard import ActionError
from .non_military_layout import CONSTRUCTION as L, construction_boxes
from .native_calibration import NATIVE_CONSTRUCTION, physical
from .native_map_state import NativeMapState
from .native_construction_tool import NativeConstructionTool


class ConstructionUI:
    def __init__(self, ui, templates, native_templates=None):
        self.ui, self.worker, self.templates = ui, ui.worker, templates
        self.native_templates = native_templates
        self.map_state = NativeMapState(self.worker, native_templates) if native_templates else None
        self.target_identity = None
        self.tool_reader = (NativeConstructionTool(self.worker,templates,self.map_state.home,
            self.map_state.modals,self.map_state.inspect) if self.map_state else None)

    @property
    def layout(self):
        return NATIVE_CONSTRUCTION if self.native_templates and physical(self.worker) else L

    def found(self, rgb, name, box=None, threshold=0.90):
        point = self.templates.find(rgb, name, box, threshold)
        if point is None and self.native_templates and physical(self.worker):
            point = self.native_templates.find(rgb, name, box, threshold)
        return point

    def open(self):
        rgb = self.ui.capture()
        if not self.found(rgb, "construction_title", (20, 83, 150, 124)):
            self.worker.key("t")
            rgb = self.ui.capture()
            if not self.found(rgb, "construction_title", (20, 83, 150, 124)):
                self.worker.click(self.layout["entry"])
                rgb = self.ui.capture()
        self.worker.click(self.layout["neutral"])
        rgb = self.ui.capture()
        if not self.found(rgb, "construction_title", (20, 83, 150, 124)):
            raise ActionError("panel_not_found")
        return rgb

    def tops(self, rgb):
        self.found(rgb, "construction_cancel")
        template = self.templates.cache.get("construction_cancel")
        if template is None:
            raise ActionError("backend_unavailable", "rejected")
        x0, y0, x1, y1 = self.layout["cancel_strip"]
        scores = cv2.matchTemplate(rgb[y0:y1, x0:x1], template, cv2.TM_CCOEFF_NORMED)
        peaks = []
        while len(peaks) <= self.layout["max_items"]:
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
        if self.found(rgb, "construction_modal_title", self.layout["modal_title"]):
            raise ActionError("modal_blocked", "rejected")
        if not self.found(rgb, "construction_title", (20, 83, 150, 124)):
            raise ActionError("panel_not_found")
        tops = self.tops(rgb)
        if len(tops) > self.layout["max_items"] or tops != [self.layout["first_top"]+self.layout["pitch"]*i for i in range(len(tops))]:
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
        one = self.white(self._load_one())
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
        templates = (self.native_templates if self.native_templates and physical(self.worker) and
                     (self.native_templates.directory/'construction_one.png').is_file() else self.templates)
        if 'construction_one' not in templates.cache:
            templates.cache["construction_one"] = np.asarray(Image.open(
                templates.directory / "construction_one.png").convert("RGB"))
        return templates.cache["construction_one"]

    def observe(self):
        self.worker.click(self.layout["neutral"])
        return self.read(self.ui.capture())

    def cancel_confirmation(self, rgb, target):
        # Match the actual dialog target before OK, rather than trusting the
        # queue row or a generic confirmation button beneath an unrelated modal.
        states = [s for s in STATES if self.found(rgb, f"construction_modal_state_{s}", self.layout["modal_body"])]
        buildings = [b for b in BUILDINGS if self.found(rgb, "construction_modal_"+b, self.layout["modal_body"])]
        point = self.found(rgb, "delete_modal_ok", self.layout["modal_ok"])
        if (not self.found(rgb, "construction_modal_title", self.layout["modal_title"]) or
                states != [target["state_id"]] or buildings != [target["building_type"]] or point is None):
            raise ActionError("identity_mismatch", "uncertain")
        return point

    def change(self, action, before, on_commit, *, state_id=None, building_type=None, target=None, direction=None):
        if action=='build' and self.tool_reader:
            self.tool_reader.evidence=None
        rgb = self.ui.capture()
        if order(self.read(rgb)) != order(before):
            raise ActionError("snapshot_stale", "rejected")
        if action == "build":
            if state_id not in self.layout['state_points']:
                raise ActionError('unsupported_target','rejected')
            if len(before["queue"]) >= self.layout["max_items"]:
                raise ActionError("unsupported_target", "rejected")
            self.close()
            rgb = self.ui.capture()
            if self.native_templates and physical(self.worker):
                map_view = self.map_state.prepare(rgb)
                state_point = self.map_state.target_point(map_view)
            elif not self.found(rgb, "construction_map_anchor", self.layout["map_anchor_box"], .9):
                raise ActionError("target_not_visible", "rejected")
            else:
                map_view, state_point = None, self.layout["state_points"][state_id]
            # Read the normal state panel before selecting build mode. This is
            # the state-ID verification, independent of the after-queue diff.
            self.worker.click(state_point)
            rgb = self.ui.capture()
            if (not self.found(rgb, f"state_title_{state_id}", self.layout["state_title"]) or
                    not self.found(rgb, "state_owner_ger", self.layout["owner_box"])):
                raise ActionError("identity_mismatch", "rejected")
            self.worker.click(self.layout["state_close"])
            rgb = self.ui.capture()
            if map_view:
                self.map_state.require(rgb, same=map_view)
                map_reference = rgb.copy()
            rgb = self.open()
            if order(self.read(rgb)) != order(before):
                raise ActionError("snapshot_stale", "rejected")
            button = self.layout["building_points"][building_type]
            x, y = button
            if not self.found(rgb, "construction_button_"+building_type, (x-24, y-24, x+24, y+24), .85):
                raise ActionError("target_not_found")
            if map_view:
                if building_type != 'civilian_factory':
                    raise ActionError('unsupported_target','rejected')
                rgb=self.select_native_tool(rgb,button)
            else:
                if not self.found(rgb,"construction_selected_"+building_type,(x-24,y-24,x+24,y+24),.9):
                    self.worker.click(button)
                    self.ui.capture()
                self.worker.click(self.layout['neutral'])
                rgb=self.ui.capture()
                if not self.found(rgb,"construction_selected_"+building_type,(x-24,y-24,x+24,y+24),.9):
                    raise ActionError('requirements_not_met','rejected')
            if map_view:
                # Catalog/identity prechecks never replace this last camera check.
                self.map_state.require(rgb, same=map_view, construction_panel=True, reference=map_reference)
                if order(self.read(rgb)) != order(before):
                    raise ActionError('snapshot_stale','rejected')
            on_commit()
            self.worker.click(state_point)
            self.ui.capture()
        else:
            top = self.layout["first_top"]+target["position"]*self.layout["pitch"]
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

    def select_native_tool(self, rgb, button):
        """One selection at most, positive truth twice; no construction target input."""
        self.tool_reader.start()
        tool=self.tool_reader.save('before-selection',rgb)
        if tool['state']=='TOOL_ANIMATING':
            rgb,tool=self.tool_reader.confirm(rgb,self.map_state.wait,allow_not_selected=True)
        if tool['state']=='TOOL_NOT_SELECTED':
            self.worker.click(button)
            self.tool_reader.evidence['tool_clicks']=1
            rgb=self.ui.capture()
            self.tool_reader.save('click-first',rgb)
        elif tool['state']!='TOOL_SELECTED':
            raise ActionError('construction_tool_'+tool['state'].lower(),'rejected')
        self.worker.click(self.layout['neutral'])
        rgb=self.ui.capture()
        self.tool_reader.save('neutral-first',rgb)
        rgb,_=self.tool_reader.confirm(rgb,self.map_state.wait)
        return rgb

    def close(self):
        rgb = self.ui.capture()
        if self.found(rgb, "construction_title", (20, 83, 150, 124)):
            self.worker.click(self.layout["close"])
            self.ui.capture()

    def prepare_target_readiness(self):
        """Private navigation only; current state identity before a catalog offer."""
        self.target_identity = None
        self.close()
        rgb = self.ui.capture()
        view = self.map_state.prepare(rgb)
        self.worker.click(self.map_state.target_point(view))
        rgb = self.ui.capture()
        if (not self.found(rgb,"state_title_64",self.layout["state_title"]) or
                not self.found(rgb,"state_owner_ger",self.layout["owner_box"])):
            raise ActionError("identity_mismatch", "rejected")
        self.worker.click(self.layout["state_close"])
        self.map_state.require(self.ui.capture(), same=view)
        self.target_identity = view
        return dict(map_state="MAP_READY", target_identity_valid=True, state_id=64)
