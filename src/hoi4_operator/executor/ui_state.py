"""Scripted hand: inspect each state before a deterministic GUI operation."""

from .catalog import BOXES, POINTS, RESEARCH, SIZE, SLOT_BOXES, SLOT_FRAME_BOXES, SLOTS
from .guard import ActionError


class UIState:
    def __init__(self, worker, templates):
        self.worker, self.templates = worker, templates

    def capture(self):
        rgb = self.worker.capture()
        if (rgb.shape[1], rgb.shape[0]) != SIZE:
            raise ActionError("unsupported_resolution", "rejected")
        return rgb

    def found(self, rgb, name, box=None, threshold=0.90):
        return self.templates.find(rgb, name, box, threshold)

    def open_panel(self, name):
        rgb = self.capture()
        if self.found(rgb, name + "_title", BOXES["panel_title"]):
            return rgb
        # Keyboard first. If this game's input sampling misses the atomic tap,
        # use the verified top-bar entry only after a fresh screenshot.
        self.worker.key("w" if name == "research" else "q")
        rgb = self.capture()
        if not self.found(rgb, name + "_title", BOXES["panel_title"]):
            if self.found(rgb, "tech_bar", BOXES["category_bar"]) or self.found(rgb, "focus_tree_title"):
                self.worker.click(POINTS["tree_close"])
                rgb = self.capture()
            self.worker.click(POINTS[name])
            rgb = self.capture()
        if not self.found(rgb, name + "_title", BOXES["panel_title"]):
            raise ActionError("panel_not_found")
        return rgb

    def slot(self, rgb, slot):
        for tech_id in RESEARCH:
            if self.found(rgb, "slot_" + tech_id, SLOT_BOXES[slot]):
                return tech_id
        if self.found(rgb, "slot_empty", SLOT_BOXES[slot]):
            return "empty"
        return "unknown"

    def choose_research(self, slot, tech_id, on_commit):
        rgb = self.open_panel("research")
        if not self.found(rgb, "slot_frame", SLOT_FRAME_BOXES[slot], threshold=0.85):
            raise ActionError("slot_unavailable", "rejected")
        self.worker.click(SLOTS[slot])
        rgb = self.capture()
        if not self.found(rgb, "tech_bar", BOXES["category_bar"]):
            raise ActionError("technology_tree_not_found")
        target = RESEARCH[tech_id]
        self.worker.click(POINTS[target.category])
        rgb = self.capture()
        x, y = target.point
        point = self.found(rgb, "node_" + tech_id, (x - 50, y - 50, x + 50, y + 50), threshold=0.80)
        if point is None:
            raise ActionError("target_not_found")
        self.worker.click(point)
        rgb = self.capture()
        if not self.found(rgb, "detail_" + tech_id, BOXES["tech_title"]):
            raise ActionError("target_identity_mismatch")
        if not self.found(rgb, "research_start", BOXES["tech_button"]):
            raise ActionError("research_button_not_found")
        on_commit()
        self.worker.key("Return")
        rgb = self.capture()
        if (not self.found(rgb, "replace_title", BOXES["replace_title"]) and
                self.found(rgb, "detail_" + tech_id, BOXES["tech_title"]) and
                self.found(rgb, "research_start", BOXES["tech_button"])):
            self.worker.click(POINTS["tech_start"])
            rgb = self.capture()
        if self.found(rgb, "replace_title", BOXES["replace_title"]):
            if not self.found(rgb, "detail_" + tech_id, BOXES["tech_title"]):
                raise ActionError("replacement_identity_mismatch", "uncertain")
            ok = self.found(rgb, "replace_ok", BOXES["replace_ok"])
            if ok is None:
                raise ActionError("replacement_confirmation_not_found", "uncertain")
            self.worker.click(ok)
            rgb = self.capture()
            if self.found(rgb, "replace_title", BOXES["replace_title"]):
                raise ActionError("replacement_confirmation_remains", "uncertain")
        rgb = self.open_panel("research")
        return self.slot(rgb, slot) == tech_id

    def focus_active(self, rgb):
        return bool(self.found(rgb, "focus_active", BOXES["focus_active"]) and
                    self.found(rgb, "focus_cancel", BOXES["focus_cancel"]))

    def choose_focus(self, on_commit):
        rgb = self.open_panel("politics")
        if not self.found(rgb, "focus_empty", BOXES["focus_empty"]):
            raise ActionError("focus_not_idle", "rejected")
        self.worker.click(POINTS["focus_tree"])
        rgb = self.capture()
        if not self.found(rgb, "focus_tree_title"):
            raise ActionError("focus_tree_not_found")
        point = self.found(rgb, "focus_node", BOXES["focus_nodes"], threshold=0.85)
        if point is None:
            raise ActionError("target_not_found")
        self.worker.click(point)
        rgb = self.capture()
        if not self.found(rgb, "focus_detail", BOXES["tech_title"]):
            raise ActionError("target_identity_mismatch")
        start = self.found(rgb, "focus_start", BOXES["tech_button"])
        if start is None:
            raise ActionError("focus_start_not_found")
        on_commit()
        self.worker.click(start)
        rgb = self.open_panel("politics")
        return self.focus_active(rgb)

    def close_panel(self):
        rgb = self.capture()
        if any(self.found(rgb, name + "_title", BOXES["panel_title"])
               for name in ("research", "politics")):
            self.worker.click(POINTS["panel_close"])
            self.capture()
