"""Normal political UI: law list, explicit law modal and three advisor slots."""

from ..actions.politics import LAWS, advisor_order
from .guard import ActionError
from .non_military_layout import POLITICS as L


class PoliticsUI:
    def __init__(self, ui, templates):
        self.ui, self.worker, self.templates = ui, ui.worker, templates

    def found(self, rgb, name, box=None, threshold=.9):
        return self.templates.find(rgb, name, box, threshold)

    def open(self):
        rgb = self.ui.capture()
        if not self.found(rgb, "politics_title", (70, 520, 175, 563)):
            self.worker.key("q")
            rgb = self.ui.capture()
            if not self.found(rgb, "politics_title", (70, 520, 175, 563)):
                self.worker.click(L["entry"])
                rgb = self.ui.capture()
        self.worker.click(L["neutral"])
        rgb = self.ui.capture()
        if not self.found(rgb, "politics_title", (70, 520, 175, 563)):
            raise ActionError("panel_not_found")
        if self.found(rgb, "politics_modal_title", L["modal_title"]):
            raise ActionError("modal_blocked", "rejected")
        return rgb

    def open_laws(self, group):
        rgb = self.open()
        if not self.found(rgb, "law_"+group+"_title", L["selector_title"]):
            self.worker.click(L["law_slots"][group])
            self.ui.capture()
        self.worker.click(L["neutral"])
        return self.read_laws(self.ui.capture(), group)

    def read_laws(self, rgb, group):
        if not self.found(rgb, "law_"+group+"_title", L["selector_title"]):
            raise ActionError("target_not_found")
        current, choices = [], {}
        for law, data in LAWS.items():
            if data["group"] != group: continue
            top = L["law_rows"][law]
            if not self.found(rgb, "law_"+law+"_name", (625, top+15, 780, top+50)):
                raise ActionError("identity_mismatch", "rejected")
            selected = bool(self.found(rgb, "law_selected", (558, top-3, 630, top+8), .9))
            if selected: current.append(law)
            # A disabled row shows grey cost/red cross; it cannot pass the
            # calibrated yellow 150 cost template and explicit red-cross check.
            cost = self.found(rgb, "law_cost_150", (814, top+20, 846, top+47), .95)
            cross = rgb[top+20:top+48, 788:814]
            red = ((cross[:,:,0] > 130) & (cross[:,:,1] < 100) & (cross[:,:,2] < 100)).sum() > 8
            choices[law] = {"selected": selected, "enabled": bool(cost and not red), "cost": 150}
        if len(current) != 1:
            raise ActionError("readback_ambiguous", "rejected")
        return {"current_law": current[0], "choices": choices, "identity_source": "gui", "stable_game_identity": True}

    def law_confirmation(self, rgb, old, target):
        point = self.found(rgb, "delete_modal_ok", L["modal_ok"])
        if (not self.found(rgb, "politics_modal_title", L["modal_title"]) or
                not self.found(rgb, "law_modal_"+old, (1220,435,1335,465)) or
                not self.found(rgb, "law_modal_"+target, (1328,435,1450,465)) or
                not self.found(rgb, "politics_modal_cost_150", L["modal_body"], .95) or point is None):
            raise ActionError("identity_mismatch", "uncertain")
        return point

    def change_law(self, group, target, before, commit):
        current = self.read_laws(self.ui.capture(), group)
        if current != before or not current["choices"][target]["enabled"]:
            raise ActionError("requirements_not_met", "rejected")
        commit()
        self.worker.click((L["law_select_x"], L["law_rows"][target]+L["law_select_y_offset"]))
        rgb = self.ui.capture()
        self.worker.click(self.law_confirmation(rgb, before["current_law"], target))
        self.ui.capture()

    def read_advisors(self, rgb):
        if not self.found(rgb, "politics_title", (70,520,175,563)):
            raise ActionError("panel_not_found")
        slots = []
        for i, box in enumerate(L["advisor_boxes"]):
            empty = self.found(rgb, "advisor_empty", box, .95)
            schacht = self.found(rgb, "advisor_schacht_portrait", box, .95)
            if bool(empty) == bool(schacht):
                raise ActionError("identity_mismatch", "rejected")
            slots.append({"position": i, "advisor_id": "advisor_schacht" if schacht else None})
        return {"slots": slots, "identity_source": "gui", "stable_game_identity": False,
                "scope": "three political advisor slots; empty or calibrated Schacht only"}

    def advisors(self):
        return self.read_advisors(self.open())

    def advisor_option(self, rgb):
        x0,y0,x1,y1 = L["advisor_cross_box"]
        cross = rgb[y0:y1,x0:x1]
        red = ((cross[:,:,0] > 130) & (cross[:,:,1] < 100) & (cross[:,:,2] < 100)).sum() > 8
        return (self.found(rgb, "advisor_selector_title", L["selector_title"]) and
                self.found(rgb, "advisor_schacht_name", L["advisor_target"]) and
                self.found(rgb, "advisor_cost_75", L["advisor_target"], .95) and not red)

    def hire(self, target, before, commit):
        if advisor_order(self.advisors()) != advisor_order(before):
            raise ActionError("snapshot_stale", "rejected")
        position = next(i for i, a in enumerate(before["slots"]) if a["advisor_id"] is None)
        self.worker.click(L["advisor_points"][position])
        self.ui.capture()
        self.worker.click(L["neutral"])
        rgb = self.ui.capture()
        if not self.advisor_option(rgb):
            raise ActionError("requirements_not_met", "rejected")
        commit()
        # Empty slot selection commits immediately in this game version.
        self.worker.click(L["advisor_select"])
        self.ui.capture()

    def close(self):
        rgb = self.ui.capture()
        if any(self.found(rgb, name, L["selector_title"]) for name in
               ("law_economy_title", "law_conscription_title", "advisor_selector_title")):
            self.worker.click(L["selector_close"])
            rgb = self.ui.capture()
        if self.found(rgb, "politics_title", (70,520,175,563)):
            self.worker.click(L["close"])
            self.ui.capture()
