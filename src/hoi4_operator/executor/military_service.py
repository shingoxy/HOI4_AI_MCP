"""Military semantic facade sharing the existing guarded transaction."""

from copy import deepcopy

from ..actions.military import GENERALS, land_signature, order_signature, air_signature, expected_land, validate_transition
from ..actions.snapshots import SessionSnapshots
from ..contracts import ActionResult
from .guard import ActionError
from .pipeline import ActionPipeline


class MilitaryExecutor:
    def __init__(self, executor, ui):
        self.executor, self.ui = executor, ui
        self.pipeline = ActionPipeline(executor)
        self.armies = SessionSnapshots("army", "armies", "army_id", ("name", "general_id", "division_names"))
        self.divisions = SessionSnapshots("division", "divisions", "division_id", ("name", "unit_type", "army_name"))
        self.divisions.session = self.armies.session
        self.fronts = SessionSnapshots("front", "fronts", "front_id", ("target_id", "type", "army_name"))
        self.fronts.session = self.armies.session
        self.offensive_orders = SessionSnapshots("order", "offensive_orders", "order_id",
            ("target_id", "front_target_id", "army_name"))
        self.offensive_orders.session = self.armies.session
        self.air_wings=SessionSnapshots("wing","air_wings","wing_id",
            ("name","unit_type","base_name","aircraft_count","capacity","region_id","missions"))
        self.air_wings.session=self.armies.session
        self.fleets=SessionSnapshots("fleet","fleets","fleet_id",
            ("name","object_type","parent_fleet_name","home_port_name","ship_count","ship_names"))
        self.fleets.session=self.armies.session

    def invalidate(self):
        self.armies.invalidate()
        self.divisions.invalidate()
        self.fronts.invalidate()
        self.offensive_orders.invalidate()
        self.air_wings.invalidate()
        self.fleets.invalidate()

    def publish(self, view, seq):
        result = self.armies.replace(view, seq)
        result["divisions"] = self.divisions.replace(view, seq)["divisions"]
        by_name = {item["name"]: item["army_id"] for item in result["armies"]}
        for division in result["divisions"]:
            division["army_id"] = by_name.get(division["army_name"])
            division["field_sources"]["army_id"] = "derived"
        if "fronts" in view:
            result["fronts"] = self.fronts.replace(view,seq)["fronts"]
            for front in result["fronts"]:
                front["army_id"] = by_name[front["army_name"]]
                front["field_sources"]["army_id"] = "derived"
        else:
            self.fronts.invalidate()
        if "offensive_orders" in view:
            result["offensive_orders"] = self.offensive_orders.replace(view, seq)["offensive_orders"]
            for order in result["offensive_orders"]:
                order["army_id"] = by_name[order["army_name"]]
                order["front_id"] = next(f["front_id"] for f in result["fronts"]
                                         if f["target_id"] == order["front_target_id"])
                order["field_sources"].update(army_id="derived", front_id="derived")
        else:
            self.offensive_orders.invalidate()
        return result

    def observe(self, action, identity=None):
        def operation(tx):
            target = None
            if action in {"get_army", "get_division"}:
                target = (self.armies if action == "get_army" else self.divisions).lookup(identity)
            with tx.stage("navigation"):
                before = self.ui.observe_land()
            with tx.stage("readback"):
                repeated = self.ui.observe_land()
                if land_signature(before) != land_signature(repeated):
                    raise ActionError("readback_ambiguous", "rejected")
                telemetry = tx.fresh()
                if target:
                    self.armies.validate(repeated, telemetry["latest_seq"])
                    self.divisions.validate(repeated, telemetry["latest_seq"])
                published = self.publish(repeated, telemetry["latest_seq"])
                tx.result.evidence.update(published)
                if target:
                    collection = "armies" if action == "get_army" else "divisions"
                    tx.result.evidence["object"] = next(item for item in published[collection] if item["name"] == target["name"])
                tx.result.evidence["ui_confirmation"] = {"repeated_readback": True}
            tx.result.accepted, tx.result.status = True, "confirmed"
        return self.pipeline.run(action, operation, invalidate=self.invalidate)

    def get_armies(self): return self.observe("get_armies")
    def get_army(self, army_id): return self.observe("get_army", army_id)
    def get_divisions(self): return self.observe("get_divisions")
    def get_division(self, division_id): return self.observe("get_division", division_id)

    def get_generals(self):
        def operation(tx):
            with tx.stage("navigation"):
                choices = self.ui.observe_generals()
            with tx.stage("readback"):
                repeated = self.ui.observe_generals()
                if choices != repeated:
                    raise ActionError("readback_ambiguous", "rejected")
                tx.fresh()
                tx.result.evidence.update(generals=choices, scope_status="LIMITED", complete=False)
            tx.result.accepted, tx.result.status = True, "confirmed"
        return self.pipeline.run("get_generals", operation)

    def create_army(self, division_ids):
        return self.change("create_army", division_ids=division_ids)

    def assign_divisions(self, army_id, division_ids):
        return self.change("assign_divisions", army_id, division_ids)

    def remove_divisions_from_army(self, army_id, division_ids):
        return self.change("remove_divisions_from_army", army_id, division_ids)

    def assign_general(self, army_id, general_id):
        return self.change("assign_general", army_id, general_id=general_id)

    def change(self, action, army_id=None, division_ids=None, general_id=None):
        def operation(tx):
            army, division = None, None
            if action == "assign_general":
                if not isinstance(general_id, str) or general_id not in GENERALS:
                    raise ActionError("unsupported_target", "rejected")
            else:
                if not isinstance(division_ids, list) or len(division_ids) != 1:
                    raise ActionError("unsupported_target", "rejected")
                division = self.divisions.lookup(division_ids[0])
            if action != "create_army":
                army = self.armies.lookup(army_id)
            with tx.stage("navigation"):
                before = self.ui.observe_land()
            with tx.stage("target_lookup"):
                self.armies.validate(before, tx.before["latest_seq"])
                self.divisions.validate(before, tx.before["latest_seq"])
                if army and (len(before["armies"]) != 1 or before["armies"][0]["name"] != army["name"]):
                    raise ActionError("identity_mismatch", "rejected")
                tx.result.evidence["before"] = deepcopy(before)
                satisfied = (action == "assign_general" and army["general_id"] == general_id or
                             action == "assign_divisions" and division["army_name"] == army["name"])
                if satisfied:
                    tx.result.accepted, tx.result.status = True, "already_satisfied"
                    tx.result.evidence["after"] = self.publish(before, tx.fresh()["latest_seq"])
                    return
                expected = expected_land(before, action, division=division, general_id=general_id)
                tx.fresh()
            with tx.stage("submit"):
                self.ui.change_land(action, before, tx.commit, division=division, general_id=general_id)
            with tx.stage("readback"):
                after = self.ui.observe_land()
                validate_transition(after, expected)
            with tx.stage("confirmation"):
                repeated, telemetry = self.ui.observe_land(), tx.fresh()
                validate_transition(repeated, expected)
                tx.result.status = "confirmed"
                tx.result.evidence.update(after=self.publish(repeated, telemetry["latest_seq"]),
                    ui_confirmation={"exact_membership_and_general_transition": True, "repeated_readback": True},
                    telemetry_confirmation={"before_seq": tx.before["latest_seq"], "after_seq": telemetry["latest_seq"],
                                            "military_state": "UNKNOWN; GUI confirmation"})
        return self.pipeline.run(action, operation, invalidate=self.invalidate)

    def get_fronts(self):
        def operation(tx):
            with tx.stage("navigation"):
                before = self.ui.observe_orders()
            with tx.stage("readback"):
                repeated = self.ui.observe_orders()
                if order_signature(before) != order_signature(repeated):
                    raise ActionError("readback_ambiguous", "rejected")
                if 'offensive_orders' in before or 'offensive_orders' in repeated:
                    from .offensive_ui import offensive_signature
                    if offensive_signature(before)!=offensive_signature(repeated):
                        raise ActionError('readback_ambiguous','rejected')
                tx.result.evidence.update(self.publish(repeated,tx.fresh()["latest_seq"]))
                tx.result.evidence['ui_confirmation']={'repeated_readback':True,'same_front_and_offensive_signature':True}
            tx.result.accepted, tx.result.status = True, "confirmed"
        return self.pipeline.run("get_fronts", operation, invalidate=self.invalidate)

    def create_frontline(self, army_id, target_id):
        return self.change_orders("create_frontline",army_id,target_id)

    def execute_plan(self, army_id): return self.change_orders("execute_plan",army_id)
    def stop_plan(self, army_id): return self.change_orders("stop_plan",army_id)

    def change_orders(self, action, army_id, target_id=None):
        def operation(tx):
            army = self.armies.lookup(army_id)
            if action == "create_frontline" and (not isinstance(target_id,str) or
                    target_id not in {"GER_POL_mainland","GER_POL_east_prussia"}):
                raise ActionError("unsupported_target", "rejected")
            with tx.stage("navigation"):
                before = self.ui.observe_orders()
            with tx.stage("target_lookup"):
                self.armies.validate(before,tx.before["latest_seq"])
                self.divisions.validate(before,tx.before["latest_seq"])
                tx.result.evidence["before"] = deepcopy(before)
                expected = deepcopy(before)
                if action == "create_frontline":
                    satisfied = any(item["target_id"]==target_id for item in before["fronts"])
                    if not satisfied:
                        if before["plan_active"] is True:
                            raise ActionError("requirements_not_met", "rejected")
                        expected["fronts"].append({"target_id":target_id,"type":"frontline","army_name":army["name"]})
                        expected.update(operation_name="白色方案", plan_active=False)
                else:
                    if not before["fronts"] or before["plan_active"] is None:
                        raise ActionError("requirements_not_met", "rejected")
                    expected["plan_active"] = action == "execute_plan"
                    satisfied = expected["plan_active"] == before["plan_active"]
                if satisfied:
                    tx.result.accepted,tx.result.status = True,"already_satisfied"
                    tx.result.evidence["after"] = self.publish(before,tx.fresh()["latest_seq"])
                    return
                tx.fresh()
            with tx.stage("submit"):
                self.ui.change_orders(action,before,tx.commit,target_id)
            with tx.stage("readback"):
                after = self.ui.observe_orders()
                if order_signature(after) != order_signature(expected):
                    raise ActionError("unexpected_state_change", "uncertain")
            with tx.stage("confirmation"):
                repeated = self.ui.observe_orders()
                if order_signature(repeated) != order_signature(expected):
                    raise ActionError("unexpected_state_change", "uncertain")
                tx.result.evidence.update(after=self.publish(repeated,tx.fresh()["latest_seq"]),
                    ui_confirmation={"army_identity":True,"known_front_transition":True,"plan_switch":True,"repeated_readback":True},
                    telemetry_confirmation={"military_state":"UNKNOWN; GUI confirmation"})
                tx.result.status = "confirmed"
        return self.pipeline.run(action,operation,invalidate=self.invalidate)

    def create_offensive_line(self, army_id, target):
        from .map_resolver import OFFENSIVE_TARGETS
        from .offensive_ui import offensive_signature
        def operation(tx):
            ui = getattr(self.ui, "offensive", None)
            if ui is None:
                raise ActionError("map_target_unresolved", "rejected")
            if not isinstance(target, str) or target not in OFFENSIVE_TARGETS:
                raise ActionError("unsupported_target", "rejected")
            army = self.armies.lookup(army_id)
            front_target = OFFENSIVE_TARGETS[target]["front"]
            if self.fronts.view is None:
                raise ActionError("snapshot_stale", "rejected")
            fronts = [f for f in self.fronts.view["fronts"] if f["target_id"] == front_target]
            if len(fronts) != 1:
                raise ActionError("requirements_not_met", "rejected")
            self.fronts.lookup(fronts[0]["front_id"])
            with tx.stage("navigation"):
                before = ui.observe()
                repeated = ui.observe()
            with tx.stage("target_lookup"):
                if offensive_signature(before) != offensive_signature(repeated):
                    raise ActionError("readback_ambiguous", "rejected")
                self.armies.validate(repeated, tx.before["latest_seq"])
                self.divisions.validate(repeated, tx.before["latest_seq"])
                self.fronts.validate(repeated, tx.before["latest_seq"])
                if len(repeated["armies"]) != 1 or repeated["armies"][0]["name"] != army["name"]:
                    raise ActionError("identity_mismatch", "rejected")
                if repeated["offensive_orders"]:
                    raise ActionError("requirements_not_met", "rejected")
                tx.result.evidence["before"] = deepcopy(repeated)
                tx.fresh()
            with tx.stage("submit"):
                ui.submit(target, repeated, tx.commit)
                tx.result.evidence.update(submit_count=1, mouse_release_confirmed=True)
            def validate(view):
                orders = view["offensive_orders"]
                if (order_signature(view) != order_signature(before) or len(orders) != 1 or
                    orders[0]["target_id"] != target or orders[0]["front_target_id"] != front_target or
                    orders[0]["army_name"] != army["name"]):
                    raise ActionError("unexpected_state_change", "uncertain")
            with tx.stage("readback"):
                validate(ui.observe())
            with tx.stage("confirmation"):
                after = ui.observe()
                validate(after)
                telemetry = tx.fresh()
                tx.result.evidence.update(after=self.publish(after, telemetry["latest_seq"]),
                    ui_confirmation={"same_army": True, "same_frontline": True, "new_offensive_order": True,
                        "expected_direction_and_region": True, "no_extra_order_in_calibrated_viewport": True,
                        "repeated_readback": True, "identity_source": "GUI_ONLY"},
                    telemetry_confirmation={"military_state": "UNKNOWN; GUI confirmation",
                        "before_seq": tx.before["latest_seq"], "after_seq": telemetry["latest_seq"]})
                tx.result.status = "confirmed"
        return self.pipeline.run("create_offensive_line", operation, invalidate=self.invalidate)

    def move_divisions(self, division_ids, province_id):
        result = ActionResult("move_divisions")
        result.evidence.update(reason="unsupported_target", limitation="Province identity and movement-order readback are uncalibrated")
        return result.as_dict()
    def get_supply_status(self, army_id=None, front_id=None):
        def operation(tx):
            if front_id is not None:
                self.fronts.lookup(front_id)
                raise ActionError("unsupported_target", "rejected")
            target = self.armies.lookup(army_id) if army_id is not None else None
            with tx.stage("navigation"):
                before = self.ui.observe_supply()
            with tx.stage("readback"):
                repeated = self.ui.observe_supply()
                if before != repeated:
                    raise ActionError("readback_ambiguous", "rejected")
                telemetry = tx.fresh()
                if target:
                    self.armies.validate(repeated["land"],telemetry["latest_seq"])
                repeated.pop("land")
                tx.result.evidence.update(repeated, ui_confirmation={"repeated_readback":True})
            tx.result.accepted,tx.result.status = True,"confirmed"
        return self.pipeline.run("get_supply_status",operation)
    def get_air_state(self): return self.observe_air("get_air_state")
    def get_navy_state(self): return self.observe_navy("get_navy_state")
    def get_air_wings(self): return self.observe_air("get_air_wings")
    def get_air_regions(self): return self.observe_air("get_air_regions")
    def get_fleets(self): return self.observe_navy("get_fleets")

    def observe_navy(self,action):
        def operation(tx):
            with tx.stage("navigation"):
                before=self.ui.observe_navy()
            with tx.stage("readback"):
                repeated=self.ui.observe_navy()
                if before!=repeated:
                    raise ActionError("readback_ambiguous", "rejected")
                tx.result.evidence.update(self.fleets.replace(repeated,tx.fresh()["latest_seq"]),
                    ui_confirmation={"parent_and_task_force_identity":True,"all_twelve_ship_names":True,
                                     "repeated_readback":True})
            tx.result.accepted,tx.result.status=True,"confirmed"
        return self.pipeline.run(action,operation,invalidate=self.fleets.invalidate)

    def assign_fleet_region(self,fleet_id,region_id):
        result=ActionResult("assign_fleet_region")
        result.evidence.update(reason="unsupported_target",limitation="Sea-region identity and normal task-force assignment readback are uncalibrated")
        return result.as_dict()

    def set_naval_mission(self,fleet_id,mission):
        result=ActionResult("set_naval_mission")
        result.evidence.update(reason="unsupported_target",limitation="Normal naval mission selection and readback are uncalibrated")
        return result.as_dict()

    def observe_air(self,action):
        def operation(tx):
            reader=self.ui.observe_air_regions if action=="get_air_regions" else self.ui.observe_air
            with tx.stage("navigation"):
                before=reader()
            with tx.stage("readback"):
                repeated=reader()
                if before!=repeated:
                    raise ActionError("readback_ambiguous", "rejected")
                telemetry=tx.fresh()
                published=repeated if action=="get_air_regions" else self.air_wings.replace(repeated,telemetry["latest_seq"])
                tx.result.evidence.update(published,ui_confirmation={"repeated_readback":True})
            tx.result.accepted,tx.result.status=True,"confirmed"
        return self.pipeline.run(action,operation,invalidate=self.air_wings.invalidate)

    def assign_air_wing(self,wing_id,region_id):
        return self.change_air("assign_air_wing",wing_id,region_id)

    def set_air_mission(self,wing_id,mission):
        return self.change_air("set_air_mission",wing_id,mission)

    def change_air(self,action,wing_id,target):
        def operation(tx):
            self.air_wings.lookup(wing_id)
            if (action=="assign_air_wing" and (not isinstance(target,int) or isinstance(target,bool) or target!=8) or
                    action=="set_air_mission" and (not isinstance(target,str) or target not in {"none","air_superiority"})):
                raise ActionError("unsupported_target", "rejected")
            with tx.stage("navigation"):
                before=self.ui.observe_air()
            with tx.stage("target_lookup"):
                self.air_wings.validate(before,tx.before["latest_seq"])
                if len(before["air_wings"])!=1:
                    raise ActionError("identity_mismatch", "rejected")
                tx.result.evidence["before"]=deepcopy(before)
                expected=deepcopy(before)
                if action=="assign_air_wing":
                    expected["air_wings"][0]["region_id"]=target
                else:
                    if before["air_wings"][0]["region_id"]!=8:
                        raise ActionError("requirements_not_met", "rejected")
                    expected["air_wings"][0]["missions"]=[] if target=="none" else [target]
                if air_signature(before)==air_signature(expected):
                    tx.result.accepted,tx.result.status=True,"already_satisfied"
                    tx.result.evidence["after"]=self.air_wings.replace(before,tx.fresh()["latest_seq"])
                    return
                tx.fresh()
            with tx.stage("submit"):
                self.ui.change_air(action,before,tx.commit,target)
            with tx.stage("readback"):
                after=self.ui.observe_air()
                if air_signature(after)!=air_signature(expected):
                    raise ActionError("unexpected_state_change", "uncertain")
            with tx.stage("confirmation"):
                repeated=self.ui.observe_air()
                if air_signature(repeated)!=air_signature(expected):
                    raise ActionError("unexpected_state_change", "uncertain")
                tx.result.evidence.update(after=self.air_wings.replace(repeated,tx.fresh()["latest_seq"]),
                    ui_confirmation={"wing_name_type_base_count":True,"region_and_missions":True,"repeated_readback":True},
                    telemetry_confirmation={"military_state":"UNKNOWN; GUI confirmation"})
                tx.result.status="confirmed"
        return self.pipeline.run(action,operation,invalidate=self.air_wings.invalidate)
