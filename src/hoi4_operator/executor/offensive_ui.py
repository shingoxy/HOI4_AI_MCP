"""Offensive-only, independently calibrated selected-army/order reader."""

import json
import time

import cv2
import numpy as np
from PIL import Image

from ..actions.military import sourced, order_signature
from .guard import ActionError
from .map_resolver import MapResolver, OFFENSIVE_TARGETS

ORDER_ROI = (1210,350,1900,1000)
SCENES = {"empty": None, "poz": "GER_POL_mainland_Poznan_east",
          "north_east": "GER_POL_mainland_Poland_north_east"}


def order_mask(rgb):
    x0,y0,x1,y1 = ORDER_ROI
    crop = rgb[y0:y1,x0:x1].astype(np.int16)
    r,g,b = (crop[:,:,i] for i in range(3))
    return ((r > 165) & (r-g > 80) & (b-g > 25)).astype(np.uint8)


def offensive_signature(view):
    return (order_signature(view), sorted((o["target_id"],o["front_target_id"],o["army_name"])
                                          for o in view["offensive_orders"]))


class OffensiveUI:
    def __init__(self, worker, templates):
        self.worker, self.templates = worker, templates
        self.map = MapResolver(None, templates)
        self.boxes = json.loads((templates.directory / "manifest.json").read_text(encoding="utf-8"))["crops"]
        self.masks = {name: np.asarray(Image.open(templates.directory / f"scene_{name}.png")) > 0
                      for name in SCENES}

    def capture(self):
        rgb = self.worker.capture()
        self.map.validate_offensive(rgb)
        return rgb

    def found(self, rgb, name, threshold=.9):
        return self.templates.find(rgb, name, self.boxes[name], threshold)

    def identity(self, rgb):
        if not all(self.found(rgb, key) for key in
                   ("army_name", "army_count_one", "army_no_general", "army_panzer_one")):
            raise ActionError("identity_mismatch", "rejected")
        if not (self.found(rgb, "army_extra_plus", .85) or self.found(rgb, "army_extra_plus_empty")):
            raise ActionError("identity_mismatch", "rejected")
        return sourced({"name": "第1集团军", "general_id": None, "division_names": ["1. Panzer-Division"]})

    def tool_active(self, rgb):
        # HOI4 retains the icon highlight after a drag; the drawing caption must
        # also be present. An icon alone does not prove an active drawing tool.
        return bool(self.found(rgb, "offensive_active") and any(self.found(rgb, name)
                    for name in ("drawing_assignment_zero", "drawing_assignment_selected")))

    def require_tool(self, rgb):
        if not self.tool_active(rgb):
            raise ActionError("requirements_not_met", "rejected")

    def read(self, rgb):
        self.map.validate_offensive(rgb)
        army = self.identity(rgb)
        self.require_tool(rgb)
        if not self.found(rgb, "operation_white"):
            raise ActionError("requirements_not_met", "rejected")
        fronts = []
        for key in ("mainland", "east_prussia"):
            if all(self.found(rgb, f"front_{key}_{i}") for i in range(3)):
                fronts.append(sourced({"target_id": "GER_POL_"+key, "type": "frontline",
                                      "army_name": army["name"], "assigned_divisions": None}))
        if not any(f["target_id"] == "GER_POL_mainland" for f in fronts):
            raise ActionError("requirements_not_met", "rejected")
        mask = order_mask(rgb).astype(bool)
        kernel = np.ones((5,5),np.uint8)
        expanded = cv2.dilate(mask.astype(np.uint8), kernel).astype(bool)
        matches = []
        for scene, expected in self.masks.items():
            allowed = cv2.dilate(expected.astype(np.uint8), kernel).astype(bool)
            # Two-pixel edge/animation tolerance. No unknown arrow or extra line.
            extra, missing = int((mask & ~allowed).sum()), int((expected & ~expanded).sum())
            if extra > 40 or missing > 40:
                continue
            if scene != "empty" and not all(self.found(rgb, f"order_{scene}_{part}")
                                             for part in ("army_label", "origin", "tip", "target")):
                continue
            matches.append(scene)
        if len(matches) != 1:
            raise ActionError("readback_ambiguous", "rejected")
        target = SCENES[matches[0]]
        orders = [] if target is None else [sourced({"target_id": target, "type": "offensive_line",
            "front_target_id": OFFENSIVE_TARGETS[target]["front"], "army_name": army["name"]})]
        division = sourced({"name": "1. Panzer-Division", "unit_type": "armor", "owner": "GER",
                            "army_name": army["name"], "province_id": None, "supply_quality": None})
        return {"armies": [army], "divisions": [division], "fronts": fronts, "offensive_orders": orders,
                "plan_active": None, "operation_name": "白色方案", "scope_status": "LIMITED", "complete": False,
                "unobserved_orders": "UNKNOWN outside calibrated Poland viewport; subpixel/occluded orders UNKNOWN",
                "field_sources": {"armies": "gui", "divisions": "gui", "fronts": "gui", "offensive_orders": "gui"}}

    def observe(self, rgb=None):
        rgb = self.capture() if rgb is None else rgb
        self.map.validate_offensive(rgb)
        self.identity(rgb)
        if not self.tool_active(rgb):
            if not self.found(rgb, "offensive_inactive"):
                raise ActionError("requirements_not_met", "rejected")
            self.worker.click((1039,1123))
            self.capture()
        # Normal navigation clears hover and counter occlusion, never submits an order.
        self.worker.click((1400,14))
        return self.read(self.capture())

    def submit(self, target, before, commit):
        rgb = self.capture()
        resolved = self.map.resolve_offensive(target, rgb)
        if offensive_signature(self.read(rgb)) != offensive_signature(before):
            raise ActionError("snapshot_stale", "rejected")
        self.require_tool(rgb)
        commit()
        self.worker.right_drag(resolved["start"], resolved["end"])
        # Returning requires finally release; an exception prevents all readback.
        time.sleep(.4)
