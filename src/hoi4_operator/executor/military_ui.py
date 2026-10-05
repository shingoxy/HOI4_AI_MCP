"""Private fixed-profile military reader and normal player-equivalent input."""

from ..actions.military import AIR_REGION, DIVISIONS, GENERALS, SHIP_NAMES, sourced, land_signature, order_signature, air_signature
from .guard import ActionError
from .map_resolver import MapResolver, FRONT_TARGETS, ANCHORS


class MilitaryUI:
    def __init__(self, ui, templates, offensive_templates=None):
        self.ui, self.worker, self.templates = ui, ui.worker, templates
        self.map = MapResolver(templates)
        self.offensive = None
        if offensive_templates is not None:
            from .offensive_ui import OffensiveUI
            self.offensive = OffensiveUI(self.worker, offensive_templates)

    def found(self, rgb, name, box, threshold=.9):
        return self.templates.find(rgb, name, box, threshold)

    def neutral(self):
        self.worker.click((1700, 12))
        return self.ui.capture()

    def ensure_no_modal(self, rgb):
        # The common central dialog frame is shared with Phase 3 modals.
        # Never dismiss an unknown dialog as if it were ordinary navigation.
        if self.found(rgb, "military_modal_ok", (1320,640,1445,710), .85):
            raise ActionError("modal_blocked", "rejected")
        if self.found(rgb, "general_picker_title", (1050,240,1400,285)):
            raise ActionError("modal_blocked", "rejected")
        if self.found(rgb, "world_news_title", (1000,235,1510,315), .85):
            raise ActionError("modal_blocked", "rejected")
        if self.found(rgb, "game_menu_load", (1200,325,1360,358), .9):
            raise ActionError("modal_blocked", "rejected")
        if self.found(rgb,"focus_completed_modal",(1250,395,1370,450),.9):
            raise ActionError("modal_blocked", "rejected")

    def open_overview(self):
        rgb = self.ui.capture()
        self.ensure_no_modal(rgb)
        if not any(self.found(rgb,name,(2494,880,2526,911),.94)
                   for name in ("land_mode_button","land_mode_active")):
            raise ActionError("panel_not_found", "rejected")
        self.worker.click((2510,892))
        rgb=self.ui.capture()
        if not self.found(rgb, "army_overview_title", (10,85,180,125)):
            self.worker.click((2302,62))
            self.ui.capture()
        rgb = self.neutral()
        if not self.found(rgb, "army_overview_title", (10,85,180,125)):
            raise ActionError("panel_not_found", "rejected")
        return rgb

    def read_divisions(self, rgb):
        if not self.found(rgb, "army_overview_title", (10,85,180,125)):
            raise ActionError("panel_not_found", "rejected")
        if not self.found(rgb, "division_total_30", (135,139,225,167), .93):
            raise ActionError("identity_mismatch", "rejected")
        items = []
        for index, (key, data) in enumerate(DIVISIONS.items()):
            top = 350+35*index
            point = self.found(rgb, "division_"+key, (100,top,309,top+34), .87)
            if point is None:
                raise ActionError("identity_mismatch", "rejected")
            # Column positions follow the found full name, avoiding transient panel width shifts.
            assigned = self.found(rgb, "overview_army_1", (280,top,459,top+36), .88)
            unassigned = self.found(rgb, "division_unassigned", (280,top,459,top+36), .9)
            if bool(assigned) == bool(unassigned):
                raise ActionError("readback_ambiguous", "rejected")
            item = sourced({"name": data["name"], "unit_type": data["unit_type"], "owner": "GER",
                            "army_name": "第1集团军" if assigned else None, "province_id": None,
                            "supply_quality": None})
            item["field_sources"].update(unit_type="derived", owner="derived", army_name="gui")
            items.append(item)
        return items

    def army_card(self, rgb):
        # The extra plus must remain in its one-army position. Additional armies shift it.
        if not self.found(rgb, "army_extra_plus", (1320,970,1390,1050), .85):
            raise ActionError("identity_mismatch", "rejected")
        return (1270,1015)

    def read_army(self, rgb):
        if not self.found(rgb, "army_title", (60,85,145,110)):
            raise ActionError("identity_mismatch", "rejected")
        if self.found(rgb, "army_no_general", (62,125,200,153)):
            general = None
        elif (self.found(rgb, "army_manstein_name", (62,130,203,155), .87) and
              self.found(rgb, "army_manstein_portrait", (10,110,62,184), .85)):
            general = "GER_erich_von_manstein"
        else:
            raise ActionError("identity_mismatch", "rejected")
        counts = ([1] if general is None and self.found(rgb, "army_count_1_no_general", (320,87,396,113), .94)
                  else [n for n in (1,2,3) if self.found(rgb, f"army_count_{n}", (320,87,396,113), .94)])
        if len(counts) != 1:
            raise ActionError("readback_ambiguous", "rejected")
        names = []
        for index in range(counts[0]):
            top = 240+34*index
            matches = []
            for key, data in DIVISIONS.items():
                template_name = "division_"+key
                point = self.found(rgb, template_name, (180,top,344,top+32), .86)
                # A name substring must not turn 10. Infanterie into 1. Infanterie.
                if point and 184 <= point[0]-self.templates.cache[template_name].shape[1]//2 <= 188:
                    matches.append(data["name"])
            if len(matches) != 1 or matches[0] in names:
                raise ActionError("readback_ambiguous", "rejected")
            names += matches
        army = sourced({"name": "第1集团军", "general_id": general, "division_names": sorted(names)})
        army["field_sources"].update(general_id="derived" if general else "gui", division_names="gui")
        return army

    def observe_land(self):
        if self.offensive is not None:
            rgb = self.worker.capture()
            from .map_profile import profile_for_size
            profile = profile_for_size((rgb.shape[1], rgb.shape[0]))
            if profile.name == "GER_1936_2048x1280":
                return self.offensive.observe(rgb)
        rgb = self.open_overview()
        divisions = self.read_divisions(rgb)
        assigned = sorted(item["name"] for item in divisions if item["army_name"])
        armies = []
        if assigned:
            self.worker.click(self.army_card(rgb))
            self.ui.capture()
            army = self.read_army(self.neutral())
            if army["division_names"] != assigned:
                raise ActionError("identity_mismatch", "rejected")
            armies.append(army)
        elif not self.found(rgb, "army_create_plus", (1280,980,1340,1055), .86):
            raise ActionError("identity_mismatch", "rejected")
        return {"armies": armies, "divisions": divisions, "scope_status": "LIMITED", "complete": False,
                "total_divisions": 30, "unobserved_divisions": 27,
                "field_sources": {"armies": "gui", "divisions": "gui", "total_divisions": "gui",
                                  "unobserved_divisions": "derived", "complete": "derived"}}

    def select_division(self, division):
        rgb = self.open_overview()
        items = self.read_divisions(rgb)
        index = next(i for i, item in enumerate(items) if item["name"] == division["name"])
        if items[index]["army_name"] != division["army_name"]:
            raise ActionError("identity_mismatch", "rejected")
        self.worker.click((210,365+35*index))
        rgb = self.neutral_after_capture()
        if not self.found(rgb, "division_"+list(DIVISIONS)[index], (180,140,344,330), .87):
            raise ActionError("identity_mismatch", "rejected")
        return rgb

    def neutral_after_capture(self):
        self.ui.capture()
        return self.neutral()

    def observe_orders(self):
        view = self.observe_land()
        if "offensive_orders" in view:
            return view
        if (len(view["armies"]) != 1 or view["armies"][0]["general_id"] != "GER_erich_von_manstein" or
                len(view["armies"][0]["division_names"]) != 3):
            raise ActionError("unsupported_target", "rejected")
        # Normal drawing navigation hides moving counters that can cover borders.
        # It is exited before returning and never clicks a map target here.
        self.worker.click((1263,885))
        self.ui.capture()
        rgb = self.neutral()
        self.ensure_no_modal(rgb)
        self.map.validate(rgb)
        self.require_front_mode(rgb)
        # Border highlights animate. Only read/navigation can repeat; submission cannot.
        for attempt in range(4):
            try:
                present=[target for target in FRONT_TARGETS if self.map.presence(rgb,target)]
                break
            except ActionError as exc:
                if exc.reason!="readback_ambiguous" or attempt==3:
                    raise
                rgb=self.neutral()
                self.ensure_no_modal(rgb)
                self.require_front_mode(rgb)
        view["fronts"] = [sourced({"target_id": target, "type": "frontline", "owner": "GER",
            "army_name": view["armies"][0]["name"], "assigned_divisions": None,
            "map_profile": self.map.profile}) for target in present]
        for front in view["fronts"]:
            front["field_sources"].update(target_id="derived", owner="derived", army_name="derived", map_profile="derived")
        active = [state for state in ("active","stopped") if self.found(rgb,"plan_"+state,(1240,950,1261,969),.96)]
        if view["fronts"]:
            if len(active) != 1 or not self.found(rgb,"operation_white",(980,840,1060,865)):
                raise ActionError("readback_ambiguous", "rejected")
        view.update(plan_active=active[0]=="active" if len(active)==1 else None,
                    operation_name="白色方案" if view["fronts"] else None,
                    marker_read_retries=attempt,
                    map_resolution={"profile": self.map.profile, "anchors_verified": list(ANCHORS)},
                    unobserved_orders="UNKNOWN; only two calibrated border markers are observed")
        self.worker.click((1263,885))
        self.ui.capture()
        return view

    def require_front_mode(self,rgb):
        if (not self.found(rgb,"frontline_mode_active",(1247,870,1280,903),.96) or
                not any(self.found(rgb,name,(1429,842,1528,862),.96)
                        for name in ("frontline_mode_assignment","frontline_mode_assignment_0"))):
            raise ActionError("requirements_not_met", "rejected")

    def change_orders(self, action, before, commit, target_id=None):
        repeated = self.observe_orders()
        if order_signature(repeated) != order_signature(before):
            raise ActionError("snapshot_stale", "rejected")
        rgb = self.ui.capture()
        if action == "create_frontline":
            point = self.map.resolve(target_id, rgb)
            self.worker.click((1263,885))
            self.ui.capture()
            rgb = self.neutral()
            self.map.validate(rgb)
            self.require_front_mode(rgb)
            commit()
            self.worker.click(point)
        else:
            if not before["fronts"]:
                raise ActionError("requirements_not_met", "rejected")
            self.map.validate(rgb)
            commit()
            self.worker.click((1283,960) if action == "execute_plan" else (1248,960))
        self.ui.capture()

    def observe_supply(self):
        view = self.observe_land()
        if not view["armies"] or DIVISIONS["infantry_1"]["name"] not in view["armies"][0]["division_names"]:
            raise ActionError("target_not_visible", "rejected")
        self.worker.click((240,251))
        rgb = self.ui.capture()
        fields = {"supply_infantry_name": (275,392,470,418), "supply_label": (275,511,355,537),
                  "supply_100": (355,512,410,538), "supply_stockpile_150": (465,512,520,538)}
        if not all(self.found(rgb,name,box,.94) for name,box in fields.items()):
            raise ActionError("readback_ambiguous", "rejected")
        return {"land":view,"supply": sourced({"division_name":DIVISIONS["infantry_1"]["name"],
            "army_name":view["armies"][0]["name"], "supply_ratio":1.0,"stockpile_ratio":1.5,
            "army_supply_ratio":None,"front_supply_ratio":None}),
            "scope_status":"LIMITED","complete":False,"unobserved_divisions":29}

    def picker(self):
        rgb = self.ui.capture()
        if not self.found(rgb, "army_title", (60,85,145,110)):
            raise ActionError("identity_mismatch", "rejected")
        self.worker.click((32,145))
        rgb = self.neutral_after_capture()
        if not self.found(rgb, "general_picker_title", (1050,240,1400,285)):
            raise ActionError("target_not_visible", "rejected")
        name = self.found(rgb, "general_manstein_name", (1190,515,1390,600), .88)
        portrait = self.found(rgb, "general_manstein_portrait", (1120,510,1195,612), .85)
        if not name or not portrait:
            raise ActionError("requirements_not_met", "rejected")
        return rgb, name

    def read_air_wing(self,rgb):
        fields={"air_selected_one":(40,142,130,178),"air_base_brandenburg":(65,205,150,242),
                "air_wing_132":(235,251,345,277),"air_count_80_100":(120,250,160,295),
                "air_wing_fighter":(15,251,95,293),"air_other_missions_off":(109,94,689,120)}
        if not all(self.found(rgb,name,box,.96) for name,box in fields.items()):
            raise ActionError("identity_mismatch", "rejected")
        states=[state for state in ("on","off") if self.found(rgb,"air_superiority_"+state,(68,94,105,120),.96)]
        regions=[state for state,name in ((None,"air_standby"),(8,"air_region_8"))
                 if self.found(rgb,name,(235,275,310,298),.94)]
        if len(states)!=1 or len(regions)!=1:
            raise ActionError("readback_ambiguous", "rejected")
        wing=sourced({"name":"第132战斗机联队","unit_type":"fighter","owner":"GER",
            "base_name":"勃兰登堡","aircraft_count":80,"capacity":100,"region_id":regions[0],
            "missions":["air_superiority"] if states[0]=="on" else [],"mission_efficiency":None})
        wing["field_sources"].update(unit_type="derived",owner="derived",region_id="derived" if regions[0] else "gui")
        return wing

    def observe_air(self):
        rgb=self.ui.capture()
        self.ensure_no_modal(rgb)
        if not self.found(rgb,"air_overview_title",(10,85,180,125)):
            self.worker.click((2398,62))
            self.ui.capture()
        rgb=self.neutral()
        fields={"air_overview_title":(10,85,180,125),"air_total_15":(170,140,280,168),
            "air_overview_132":(140,424,276,455),"air_overview_brandenburg":(300,424,396,455),
            "air_overview_fighter":(10,425,90,455)}
        if not all(self.found(rgb,name,box,.94) for name,box in fields.items()):
            raise ActionError("identity_mismatch", "rejected")
        self.worker.click((205,441))
        self.ui.capture()
        wing=self.read_air_wing(self.neutral())
        return {"air_wings":[wing],"scope_status":"LIMITED","complete":False,
                "total_air_wings":15,"unobserved_air_wings":14,
                "field_sources":{"air_wings":"gui","total_air_wings":"gui",
                                 "unobserved_air_wings":"derived","complete":"derived"}}

    def observe_air_regions(self):
        self.observe_air()
        rgb=self.ui.capture()
        self.worker.click(self.map.resolve_air(8,rgb))
        self.ui.capture()
        rgb=self.neutral()
        if not self.found(rgb,"air_region_title_8",(1235,316,1320,348),.94):
            raise ActionError("identity_mismatch", "rejected")
        self.worker.click((1528,333))
        self.ui.capture()
        region=sourced({**AIR_REGION,"air_superiority":None,"mission_efficiency":None})
        region["field_sources"].update(region_id="derived",identity_source="derived",identity_basis="derived")
        return {"air_regions":[region],"scope_status":"LIMITED","complete":False}

    def read_fleet(self,rgb):
        fields={"navy_parent_name":(60,85,145,118),"navy_parent_count_3":(348,86,385,118),
            "navy_no_admiral":(70,140,145,173),"navy_home_wilhelmshaven":(245,215,320,247),
            "navy_parent_regions_0":(10,215,145,247),"navy_high_seas":(60,295,140,328),
            "navy_count_12":(15,302,49,334),"navy_docked":(70,335,200,368)}
        if not all(self.found(rgb,name,box,.94) for name,box in fields.items()):
            raise ActionError("identity_mismatch", "rejected")
        for index in range(len(SHIP_NAMES)):
            if not self.found(rgb,f"navy_ship_{index}",(180,416+41*index,343,443+41*index),.94):
                raise ActionError("identity_mismatch", "rejected")
        fleet=sourced({"name":"公海舰队","object_type":"task_force","parent_fleet_name":"德国海军",
            "owner":"GER","parent_task_force_count":3,"admiral_id":None,"home_port_name":"威廉港",
            "parent_assigned_region_count":0,"ship_count":12,"ship_names":list(SHIP_NAMES),
            "docked":True,"region_ids":None,"mission":None,"supply_ratio":None})
        fleet["field_sources"].update(object_type="derived",owner="derived",admiral_id="gui")
        return fleet

    def observe_navy(self):
        rgb=self.ui.capture()
        self.ensure_no_modal(rgb)
        if not self.found(rgb,"navy_overview_title",(10,85,180,125)):
            self.worker.click((2350,62))
            self.ui.capture()
        rgb=self.neutral()
        fields={"navy_overview_title":(10,85,180,125),"navy_total_6":(170,140,280,170),
            "navy_overview_high_seas":(170,330,320,360),"navy_overview_count_12":(450,325,480,350)}
        if not all(self.found(rgb,name,box,.94) for name,box in fields.items()):
            raise ActionError("identity_mismatch", "rejected")
        self.worker.click((235,345))
        self.ui.capture()
        fleet=self.read_fleet(self.neutral())
        return {"fleets":[fleet],"scope_status":"LIMITED","complete":False,"total_task_forces":6,
            "unobserved_task_forces":5,"field_sources":{"fleets":"gui","total_task_forces":"gui",
            "unobserved_task_forces":"derived","complete":"derived"}}

    def change_air(self,action,before,commit,target):
        if air_signature(self.observe_air())!=air_signature(before):
            raise ActionError("snapshot_stale", "rejected")
        if action=="assign_air_wing":
            # Verify the region's visible title before selecting the wing again.
            if self.observe_air_regions()["air_regions"][0]["region_id"]!=target:
                raise ActionError("identity_mismatch", "rejected")
            if air_signature(self.observe_air())!=air_signature(before):
                raise ActionError("snapshot_stale", "rejected")
            point=self.map.resolve_air(target,self.ui.capture())
            commit()
            self.worker.click(point,button="right")
        else:
            commit()
            self.worker.click((89,106))
        self.ui.capture()

    def observe_generals(self):
        view = self.observe_land()
        if not view["armies"]:
            raise ActionError("target_not_visible", "rejected")
        assigned = view["armies"][0]["general_id"] == "GER_erich_von_manstein"
        if not assigned:
            self.picker()
        result = [{"general_id": key, **value, "available": not assigned,
                   "assigned_army_name": view["armies"][0]["name"] if assigned else None,
                   "field_sources": {"general_id": "derived", "name": "gui", "available": "gui",
                                     "assigned_army_name": "gui", "rank": "derived", "country": "derived"}} for key,value in GENERALS.items()]
        if not assigned:
            self.worker.click((1583,264))
            self.ui.capture()
        return result

    def change_land(self, action, before, commit, *, division=None, general_id=None):
        # Reject unsupported readbacks before input can change game state.
        if action == "assign_divisions" and before["armies"][0]["general_id"] is None:
            raise ActionError("unsupported_target", "rejected")
        if action == "remove_divisions_from_army" and division["name"] != DIVISIONS["panzer_1"]["name"]:
            raise ActionError("unsupported_target", "rejected")
        # Re-observe before any selecting or committing input.
        if land_signature(self.observe_land()) != land_signature(before):
            raise ActionError("snapshot_stale", "rejected")
        if action == "assign_general":
            _, point = self.picker()
            commit()
            self.worker.click(point)
            self.ui.capture()
            return
        rgb = self.select_division(division)
        if action == "create_army":
            point = (self.found(rgb, "army_create_plus", (1280,980,1340,1055), .94) or
                     self.found(rgb, "army_create_plus_idle", (1280,980,1340,1055), .94))
            if (point is None or not self.found(rgb, "selected_single_header", (65,85,130,120), .94) or
                    not self.found(rgb, "selected_unassigned", (15,178,390,226), .86)):
                raise ActionError("identity_mismatch", "rejected")
            commit()
            self.worker.click(point)
        elif action == "assign_divisions":
            point = self.army_card(rgb)
            if (not self.found(rgb, "selected_single_header", (65,85,130,120), .94) or
                    not self.found(rgb, "selected_unassigned", (15,178,390,226), .86)):
                raise ActionError("identity_mismatch", "rejected")
            commit()
            self.worker.click(point, button="right")
        else:
            if not self.found(rgb, "army_title", (60,85,145,110)):
                raise ActionError("identity_mismatch", "rejected")
            self.worker.click((378,202))
            rgb = self.neutral_after_capture()
            key = next(key for key,data in DIVISIONS.items() if data["name"] == division["name"])
            ok = self.found(rgb, "military_modal_ok", (1320,640,1445,710), .9)
            if (not self.found(rgb, "remove_division_modal_title", (1160,370,1400,420)) or
                    not self.found(rgb, "remove_division_"+key, (1090,430,1470,480)) or not ok):
                raise ActionError("identity_mismatch", "rejected")
            commit()
            self.worker.click(ok)
        self.ui.capture()
