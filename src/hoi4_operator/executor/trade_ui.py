"""Normal Swedish steel contract, with independent numeric readback after every edit."""

import numpy as np
from PIL import Image
import time

from ..actions.trade import target
from .guard import ActionError
from .non_military_layout import TRADE as L


def gold_glyphs(rgb):
    rgb = rgb.astype(np.int16)
    mask = (rgb[:,:,0] > 95) & (rgb[:,:,0]-rgb[:,:,2] > 30) & (rgb[:,:,1]-rgb[:,:,2] > 20)
    # Two foreground pixels separate adjacent glyphs despite JPEG ringing.
    active = mask.sum(0) >= 2
    edges = np.diff(np.r_[False, active, False].astype(int))
    glyphs = []
    for start, end in zip(np.where(edges == 1)[0], np.where(edges == -1)[0]):
        glyph = mask[:, start:end]
        ys = np.where(glyph.any(1))[0]
        if glyph.sum() >= 5:
            glyphs.append(glyph[ys[0]:ys[-1]+1])
    return glyphs


class TradeUI:
    def __init__(self, ui, templates):
        self.ui, self.worker, self.templates = ui, ui.worker, templates
        self.digits = None
        self.observation_retries = 0

    def found(self, rgb, name, box=None, threshold=.9):
        return self.templates.find(rgb, name, box, threshold)

    def number(self, rgb, box):
        if self.digits is None:
            self.digits = {digit: [np.asarray(Image.open(path)) > 0 for path in
                           self.templates.directory.glob(f"trade_digit_{digit}_*.png")] for digit in range(10)}
        x0,y0,x1,y1 = box
        glyphs = gold_glyphs(rgb[y0:y1,x0:x1])
        if not 1 <= len(glyphs) <= 3:
            raise ActionError("readback_ambiguous", "rejected")
        value = ""
        for glyph in glyphs:
            matches = [digit for digit, templates in self.digits.items() if any(self.glyph_distance(glyph, t) <= 6 for t in templates)]
            if len(matches) != 1:
                raise ActionError("readback_ambiguous", "rejected")
            value += str(matches[0])
        return int(value)

    @staticmethod
    def glyph_distance(glyph, template):
        if max(glyph.shape) > 15 or max(template.shape) > 15 or abs(glyph.shape[0]-template.shape[0]) > 1 or abs(glyph.shape[1]-template.shape[1]) > 1:
            return 999
        a, b = np.zeros((20,20), dtype=bool), np.zeros((20,20), dtype=bool)
        a[2:2+glyph.shape[0],2:2+glyph.shape[1]] = glyph
        best = 999
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                b[:] = False
                b[2+dy:2+dy+template.shape[0],2+dx:2+dx+template.shape[1]] = template
                best = min(best, int(np.count_nonzero(a ^ b)))
        return best

    def dialog_identity(self, rgb):
        return (self.found(rgb, "trade_swe_title", L["dialog_country"]) and
                self.found(rgb, "trade_swe_flag", L["dialog_flag"], .95) and
                self.found(rgb, "trade_steel_icon", L["dialog_resource"], .95))

    def open(self):
        rgb = self.ui.capture()
        # Discard only a recognized, unsubmitted contract before observing the
        # committed state. No getter ever presses Send.
        if self.dialog_identity(rgb):
            self.close_dialog(rgb)
            rgb = self.ui.capture()
        if not self.found(rgb, "trade_title", L["title"]):
            self.worker.key("r")
            rgb = self.ui.capture()
            if not self.found(rgb, "trade_title", L["title"]):
                self.worker.click(L["entry"])
                rgb = self.ui.capture()
        if not self.found(rgb, "trade_title", L["title"]):
            raise ActionError("panel_not_found")
        if not self.found(rgb, "trade_steel_selected", L["steel_box"], .95):
            self.worker.click(L["steel"])
            self.ui.capture()
        self.worker.click(L["neutral"])
        return self.read_main(self.ui.capture())

    def read_main(self, rgb):
        if not self.found(rgb, "trade_steel_selected", L["steel_box"], .95):
            raise ActionError("identity_mismatch", "rejected")
        point = self.found(rgb, "trade_swe_row", L["country_list"], .95)
        if point is None:
            raise ActionError("target_not_visible", "rejected")
        y = point[1]
        box = (375,y-13,480,y+13)
        separator = self.found(rgb, "trade_quantity_separator", box, .95)
        if separator is None:
            delivered = requested = self.number(rgb, box)
            if delivered != 0:
                raise ActionError("readback_ambiguous", "rejected")
        else:
            # Active imports display delivered/requested, with a white slash.
            # Read both halves independently; concatenating digits is unsafe.
            x = separator[0]
            delivered = self.number(rgb, (375,y-13,x-3,y+13))
            requested = self.number(rgb, (x+4,y-13,480,y+13))
        return {"available_civilian_factories": self.number(rgb, L["available"]),
                "delivered_amount": delivered, "requested_amount": requested, "row_y": y}

    def dialog(self, main):
        self.worker.click((L["contract_select_x"],main["row_y"]))
        self.ui.capture()
        self.worker.click(L["dialog_neutral"])
        return self.settled_dialog()

    def settled_dialog(self):
        # A proposal can repaint its icon while its amount changes. A bounded
        # observation retry sends no input and can never replay submission.
        for attempt in range(2):
            try:
                return self.read_dialog(self.ui.capture())
            except ActionError as exc:
                if attempt or exc.reason != "identity_mismatch": raise
                self.observation_retries += 1
                self.worker.check()
                time.sleep(.25)

    def read_dialog(self, rgb):
        if not self.dialog_identity(rgb):
            raise ActionError("identity_mismatch", "rejected")
        amount, factories = self.number(rgb, L["dialog_amount"]), self.number(rgb, L["dialog_factories"])
        if factories not in (0,1,2) or amount != factories*8:
            raise ActionError("readback_ambiguous", "rejected")
        return {"resource": "steel", "country": "SWE", "civilian_factories": factories, "requested_amount": amount}

    def close_dialog(self, rgb=None):
        rgb = self.ui.capture() if rgb is None else rgb
        point = self.found(rgb, "trade_dialog_close", L["dialog_close_box"], .95)
        if point is None:
            raise ActionError("modal_blocked", "rejected")
        self.worker.click(point)
        self.ui.capture()

    def observe(self):
        main = self.open()
        contract = self.dialog(main)
        self.close_dialog()
        if not contract["requested_amount"] == main["requested_amount"] == main["delivered_amount"]:
            raise ActionError("readback_ambiguous", "rejected")
        contract["delivered_amount"] = main["delivered_amount"]
        return {"imports": [contract], "available_civilian_factories": main["available_civilian_factories"],
                "identity_source": "gui", "stable_game_identity": False, "complete_trade_state": False,
                "scope": "SWE steel only; 0..2 civilian factories; requested AND delivered readback",
                "unknown_fields": ["other_resources_and_countries", "internal_trade_id"]}

    def change(self, before, factories, commit):
        main = self.open()
        contract = self.dialog(main)
        if target({"imports": [contract]}) != target(before):
            raise ActionError("snapshot_stale", "rejected")
        current = contract["civilian_factories"]
        for _ in range(2):
            if current == factories: break
            direction = 1 if factories > current else -1
            key = "plus" if direction > 0 else "minus"
            rgb = self.ui.capture()
            if not self.found(rgb, "trade_"+key, L[key+"_box"], .95):
                raise ActionError("target_not_found")
            self.worker.click(L[key])
            self.ui.capture()
            self.worker.click(L["dialog_neutral"])
            contract = self.settled_dialog()
            if contract["civilian_factories"] != current+direction:
                raise ActionError("readback_failed")
            current = contract["civilian_factories"]
        if current != factories:
            raise ActionError("readback_failed")
        rgb = self.ui.capture()
        point = self.found(rgb, "trade_send", L["send_box"], .95)
        if point is None:
            raise ActionError("requirements_not_met", "rejected")
        commit()
        self.worker.click(point)
        self.ui.capture()

    def close(self):
        rgb = self.ui.capture()
        if self.dialog_identity(rgb):
            self.close_dialog(rgb)
            rgb = self.ui.capture()
        if self.found(rgb, "trade_title", L["title"]):
            self.worker.click(L["close"])
            self.ui.capture()
