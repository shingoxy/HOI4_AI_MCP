"""Scripted hand: inspect each state before a deterministic GUI operation."""

from .catalog import BOXES, POINTS, RESEARCH, SIZE, SLOT_BOXES, SLOT_FRAME_BOXES, SLOTS
from .guard import ActionError
from .native_modal import NativeModalDetector


class UIState:
    def __init__(self, worker, templates, native_templates=None):
        self.worker, self.templates = worker, templates
        self.native_templates = native_templates
        self.native_modals=NativeModalDetector(native_templates) if native_templates else None

    def capture(self):
        rgb = self.worker.capture()
        size = (rgb.shape[1], rgb.shape[0])
        profile = getattr(self.worker, "capture_profile", None)
        native_panel = (size == (2560, 1600) and
                        getattr(profile, "name", None) == "GER_2560x1600_DPI120_PHYSICAL")
        if size != SIZE and not native_panel:
            raise ActionError("unsupported_resolution", "rejected")
        if native_panel and self.native_templates is not None:
            modal=self.native_modals.read(rgb)
            if modal['state']!='NO_MODAL':
                reason='unknown_modal' if modal['state']=='UNKNOWN_MODAL' else 'modal_blocked'
                save=getattr(self.worker,'save_time_failure',None)
                if save:
                    try: save(reason,rgb)
                    except OSError: pass
                raise ActionError(reason,'rejected')
        return rgb

    def centered_box(self, rgb, name):
        x0, y0, x1, y1 = BOXES[name]
        shift = (rgb.shape[0] - SIZE[1]) // 2
        return x0, y0 + shift, x1, y1 + shift

    def found(self, rgb, name, box=None, threshold=0.90):
        point = self.templates.find(rgb, name, box, threshold)
        profile = getattr(self.worker, "capture_profile", None)
        if (point is None and self.native_templates is not None and
                getattr(profile, "name", None) == "GER_2560x1600_DPI120_PHYSICAL"):
            point = self.native_templates.find(rgb, name, box, threshold)
        return point

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
        profile = getattr(self.worker, "capture_profile", None)
        native = getattr(profile, "backend", None) == "windows_native_gdi"
        if native:
            self.worker.click(POINTS["tech_start"])
        else:
            self.worker.key("Return")
        rgb = self.capture()
        if (not native and not self.found(rgb, "replace_title", self.centered_box(rgb, "replace_title")) and
                self.found(rgb, "detail_" + tech_id, BOXES["tech_title"]) and
                self.found(rgb, "research_start", BOXES["tech_button"])):
            self.worker.click(POINTS["tech_start"])
            rgb = self.capture()
        if self.found(rgb, "replace_title", self.centered_box(rgb, "replace_title")):
            if not self.found(rgb, "detail_" + tech_id, BOXES["tech_title"]):
                raise ActionError("replacement_identity_mismatch", "uncertain")
            ok = self.found(rgb, "replace_ok", self.centered_box(rgb, "replace_ok"))
            if ok is None:
                raise ActionError("replacement_confirmation_not_found", "uncertain")
            self.worker.click(ok)
            rgb = self.capture()
            if self.found(rgb, "replace_title", self.centered_box(rgb, "replace_title")):
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
