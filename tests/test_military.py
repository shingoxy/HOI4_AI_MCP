"""Military identity, exact transitions, safety and semantic API regression."""

import asyncio
from copy import deepcopy
from pathlib import Path
import time

import numpy as np
from PIL import Image
from mcp import Client
import pytest

from test_executor import FakeModel, FakeWorker, summary
from hoi4_operator.actions.military import DIVISIONS, OBSERVATIONS, expected_land, sourced
from hoi4_operator.executor.map_resolver import MapResolver
from hoi4_operator.executor.guard import ActionError
from hoi4_operator.executor.military_service import MilitaryExecutor
from hoi4_operator.executor.military_ui import MilitaryUI
from hoi4_operator.executor.service import Executor
from hoi4_operator.executor.templates import Templates
from hoi4_operator.mcp_server import create_server
from hoi4_operator.operator import OperatorAPI


class UI:
    def __init__(self):
        self.view = {"armies": [], "divisions": [sourced({**data, "owner": "GER", "army_name": None,
                     "province_id": None, "supply_quality": None}) for data in DIVISIONS.values()]}
        self.calls, self.failure, self.missed, self.wrong = 0, None, False, False
        self.air={"air_wings":[sourced({"name":"第132战斗机联队","unit_type":"fighter","base_name":"勃兰登堡",
            "aircraft_count":80,"capacity":100,"region_id":None,"missions":[],"mission_efficiency":None})]}
    def observe_air(self): return deepcopy(self.air)
    def observe_air_regions(self): return {"air_regions":[{"region_id":8,"name":"东德意志"}]}
    def change_air(self,action,before,commit,target):
        commit()
        self.calls+=1
        if self.failure: raise ActionError(self.failure,"failed")
        if self.missed: return
        self.air=deepcopy(before)
        if action=="assign_air_wing": self.air["air_wings"][0]["region_id"]=target
        else: self.air["air_wings"][0]["missions"]=[] if target=="none" else [target]
        if self.wrong: self.air["air_wings"][0]["base_name"]="unexpected"
    def observe_land(self): return deepcopy(self.view)
    def observe_generals(self): return [{"general_id": "GER_erich_von_manstein", "available": True}]
    def observe_orders(self):
        view = deepcopy(self.view)
        view.setdefault("fronts",[])
        view.setdefault("operation_name",None)
        view.setdefault("plan_active",None)
        return view
    def change_orders(self,action,before,commit,target_id=None):
        commit()
        self.calls += 1
        if self.missed: return
        self.view = deepcopy(before)
        if action == "create_frontline":
            self.view["fronts"].append({"target_id":target_id,"type":"frontline","army_name":"第1集团军","field_sources":{}})
            self.view.update(operation_name="白色方案",plan_active=False)
        else:
            self.view["plan_active"] = action == "execute_plan"
    def change_land(self, action, before, commit, *, division=None, general_id=None):
        commit()
        self.calls += 1
        if self.failure: raise ActionError(self.failure, "failed")
        if self.missed: return
        self.view = expected_land(before, action, division=division, general_id=general_id)
        if self.wrong: self.view["divisions"][-1]["army_name"] = "unexpected"


def setup(status="fresh", failure=None):
    ui, worker = UI(), FakeWorker(failure=failure)
    service = MilitaryExecutor(Executor(FakeModel([summary(status=status)]), worker, None), ui)
    return service, ui, worker


def create(service):
    first = service.get_armies()
    return service.create_army([first["divisions"][0]["division_id"]])["after"]


def test_army_create_assign_remove_and_general_exact_confirmations():
    service, ui, _ = setup()
    view = create(service)
    for index in (1,2):
        result = service.assign_divisions(view["armies"][0]["army_id"], [view["divisions"][index]["division_id"]])
        assert result["status"] == "confirmed" and result["retry_count"] == 0
        view = result["after"]
    result = service.assign_general(view["armies"][0]["army_id"], "GER_erich_von_manstein")
    assert result["status"] == "confirmed" and result["ui_confirmation"]["repeated_readback"]
    view = result["after"]
    result = service.remove_divisions_from_army(view["armies"][0]["army_id"], [view["divisions"][1]["division_id"]])
    assert result["status"] == "confirmed" and ui.calls == 5
    assert result["after"]["divisions"][1]["army_name"] is None
    assert result["after"]["armies"][0]["stable_game_identity"] is False
    assert result["telemetry_confirmation"]["military_state"].startswith("UNKNOWN")


def test_snapshot_version_ttl_wrong_session_and_changed_identity_reject():
    service, ui, _ = setup()
    first = service.get_divisions()["divisions"][0]["division_id"]
    service.get_armies()
    assert service.create_army([first])["reason"] == "snapshot_stale"
    first = service.divisions.view["divisions"][0]["division_id"]
    service.divisions.created = time.monotonic()-121
    assert service.create_army([first])["reason"] == "snapshot_stale"
    assert service.create_army(["division-foreign-0001-0000"])["reason"] == "identity_mismatch"
    first = service.get_armies()["divisions"][0]["division_id"]
    ui.view["divisions"][0]["name"] = "renamed"
    assert service.create_army([first])["reason"] == "snapshot_stale"
    assert ui.calls == 0


@pytest.mark.parametrize("reason", ["loss_of_focus", "emergency_stop", "watchdog_timeout", "ui_timeout", "computer_use_error"])
def test_guard_failure_no_input_before_submission(reason):
    service, ui, _ = setup(failure=reason)
    result = service.get_armies()
    assert result["status"] == "rejected" and ui.calls == 0


@pytest.mark.parametrize("mode", ["failure", "missed", "wrong"])
def test_after_submit_failure_uncertain_invalidates_no_retry(mode):
    service, ui, _ = setup()
    first = service.get_armies()["divisions"][0]["division_id"]
    setattr(ui, mode, "loss_of_focus" if mode == "failure" else True)
    result = service.create_army([first])
    assert result["status"] == "uncertain" and result["accepted"]
    assert ui.calls == 1 and result["retry_count"] == 0
    assert service.armies.view is None and service.divisions.view is None
    assert service.create_army([first])["status"] == "rejected" and ui.calls == 1


def test_stale_telemetry_and_invalid_division_general_and_last_unit():
    service, ui, _ = setup("stale")
    assert service.get_armies()["reason"] == "telemetry_stale" and not ui.calls
    service, ui, _ = setup()
    for ids in (None, [], ["unknown"], [1], ["a","b"], "a"):
        assert service.create_army(ids)["status"] == "rejected"
    view = create(service)
    army = view["armies"][0]["army_id"]
    assert service.assign_general(army, "GER_heinz_guderian")["reason"] == "unsupported_target"
    assert service.remove_divisions_from_army(army, [view["divisions"][0]["division_id"]])["reason"] == "requirements_not_met"


def test_satisfied_assign_and_general_do_not_submit():
    service, ui, _ = setup()
    view = create(service)
    result = service.assign_divisions(view["armies"][0]["army_id"], [view["divisions"][0]["division_id"]])
    assert result["status"] == "already_satisfied" and ui.calls == 1
    view = result["after"]
    view = service.assign_general(view["armies"][0]["army_id"], "GER_erich_von_manstein")["after"]
    result = service.assign_general(view["armies"][0]["army_id"], "GER_erich_von_manstein")
    assert result["status"] == "already_satisfied" and ui.calls == 2


def test_single_object_read_requires_identity():
    service, ui, _ = setup()
    for method in (service.get_army, service.get_division):
        for identity in (None, "", 42):
            assert method(identity)["reason"] == "identity_mismatch"
    assert ui.calls == 0


def test_python_and_mcp_schema_reject_raw_backend_arguments(tmp_path):
    service, ui, _ = setup()
    api = OperatorAPI(service.executor.model, military=service)
    assert api.execute("create_army", {"division_ids":[],"x":10})["reason"] == "invalid_arguments"
    assert api.execute("drag", {"from_x":1})["reason"] == "unsupported_target"
    expected = {"create_army":{"division_ids"},"assign_divisions":{"army_id","division_ids"},
                "assign_general":{"army_id","general_id"},"get_army":{"army_id"},"get_division":{"division_id"},
                "remove_divisions_from_army":{"army_id","division_ids"},"assign_air_wing":{"wing_id","region_id"},
                "set_air_mission":{"wing_id","mission"},"create_offensive_line":{"army_id","target"}}
    async def check():
        async with Client(create_server(tmp_path/"missing.log", military_executor=service)) as client:
            tools = {item.name:item for item in (await client.list_tools()).tools}
            for name, fields in expected.items():
                assert set(tools[name].input_schema["properties"]) == fields
            assert not tools["create_army"].annotations.idempotent_hint
            assert not tools["get_armies"].annotations.read_only_hint
            view = (await client.call_tool("get_armies")).structured_content
            result = (await client.call_tool("create_army", {"division_ids":[view["divisions"][0]["division_id"]]})).structured_content
            assert result["status"] == "confirmed"
        async with Client(create_server(tmp_path/"missing.log")) as client:
            for name in OBSERVATIONS:
                args = {"army_id":"unknown"} if name == "get_army" else {"division_id":"unknown"} if name == "get_division" else {}
                assert (await client.call_tool(name,args)).structured_content["reason"] == "backend_unavailable"
    asyncio.run(check())


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("filename,count,general", [("army-one-no-general.jpg",1,None),
    ("army-one-manstein.jpg",1,"GER_erich_von_manstein"),("army-two-manstein.jpg",2,"GER_erich_von_manstein"),
    ("army-three-manstein.jpg",3,"GER_erich_von_manstein")])
def test_actual_army_reader_samples(filename,count,general):
    ui = MilitaryUI(type("Base",(),{"worker":None})(), Templates(ROOT/"artifacts/phase4/templates"))
    rgb = np.asarray(Image.open(ROOT/"artifacts/phase4/captures"/filename).convert("RGB"))
    view = ui.read_army(rgb)
    assert len(view["division_names"]) == count and view["general_id"] == general


def test_actual_division_reader_rejects_unknown_membership():
    ui = MilitaryUI(type("Base",(),{"worker":None})(), Templates(ROOT/"artifacts/phase4/templates"))
    rgb = np.asarray(Image.open(ROOT/"artifacts/phase4/captures/overview-army-one-stable.jpg").convert("RGB")).copy()
    items = ui.read_divisions(rgb)
    assert items[0]["army_name"] == "第1集团军" and items[1]["army_name"] is None
    rgb[350:385,280:459] = 0
    with pytest.raises(ActionError, match="readback_ambiguous"):
        ui.read_divisions(rgb)


@pytest.mark.parametrize("filename,expected", [("frontline-mode-active.jpg",[False,False]),
    ("front-drawing-mainland.jpg",[True,False]),("front-drawing-two.jpg",[True,True])])
def test_real_fixed_map_fronts_and_wrong_camera(filename,expected):
    resolver = MapResolver(Templates(ROOT/"artifacts/phase4/templates"))
    rgb = np.asarray(Image.open(ROOT/"artifacts/phase4/captures"/filename).convert("RGB"))
    assert [resolver.presence(rgb,key) for key in ("GER_POL_mainland","GER_POL_east_prussia")] == expected
    with pytest.raises(ActionError,match="map_target_unresolved"):
        resolver.resolve("GER_POL_mainland",np.roll(rgb,10,axis=1))


def test_frontline_plan_switch_exact_and_submission_not_retried():
    service,ui,_ = setup()
    view = create(service)
    for target in ("GER_POL_mainland","GER_POL_east_prussia"):
        result = service.create_frontline(view["armies"][0]["army_id"],target)
        assert result["status"] == "confirmed"
        view = result["after"]
    assert len(view["fronts"]) == 2 and not view["plan_active"]
    for action,active in ((service.execute_plan,True),(service.stop_plan,False)):
        result = action(view["armies"][0]["army_id"])
        assert result["status"] == "confirmed" and result["retry_count"]==0
        view = result["after"]
        assert view["plan_active"] is active
    assert service.stop_plan(view["armies"][0]["army_id"])["status"] == "already_satisfied"
    view = service.get_fronts()
    ui.missed = True
    result = service.execute_plan(view["armies"][0]["army_id"])
    assert result["status"] == "uncertain" and service.fronts.view is None


@pytest.mark.parametrize("filename,count,active",[("map-three-no-order.jpg",0,None),
    ("front-two-stable.jpg",2,False),("plan-active-stable.jpg",2,True),("plan-stop-stable.jpg",2,False)])
def test_real_orders_reader_controls(filename,count,active):
    rgb = np.asarray(Image.open(ROOT/"artifacts/phase4/captures"/filename).convert("RGB"))
    worker = type("Worker",(),{"click":lambda *args,**kwargs:None})()
    ui = MilitaryUI(type("Base",(),{"worker":worker,"capture":lambda *args:rgb})(),Templates(ROOT/"artifacts/phase4/templates"))
    ui.observe_land = lambda: {"armies":[{"name":"第1集团军","general_id":"GER_erich_von_manstein",
        "division_names":[data["name"] for data in DIVISIONS.values()]}]}
    # Historical v1 samples exercise the plan controls independently of camera v2.
    ui.map.validate=lambda _:None
    ui.map.presence=lambda _,target: count==2
    ui.require_front_mode=lambda _:None
    result = ui.observe_orders()
    assert len(result["fronts"])==count and result["plan_active"] is active


def test_real_news_blocks_before_navigation_and_supply_numbers():
    templates=Templates(ROOT/"artifacts/phase4/templates")
    rgb=np.asarray(Image.open(ROOT/"artifacts/phase4/captures/world-news-blocked.jpg").convert("RGB"))
    ui=MilitaryUI(type("Base",(),{"worker":None})(),templates)
    with pytest.raises(ActionError,match="modal_blocked"):
        ui.ensure_no_modal(rgb)
    rgb=np.asarray(Image.open(ROOT/"artifacts/phase4/captures/infantry-details.jpg").convert("RGB"))
    ui=MilitaryUI(type("Base",(),{"worker":type("Worker",(),{"click":lambda *args:None})(),"capture":lambda *args:rgb})(),templates)
    ui.observe_land=lambda:{"armies":[{"name":"第1集团军","division_names":["1. Infanterie-Division"]}]}
    assert ui.observe_supply()["supply"]["supply_ratio"]==1.0
    assert ui.observe_supply()["supply"]["stockpile_ratio"]==1.5


def test_restored_menu_blocks_and_create_button_animation_keeps_single_selection():
    templates=Templates(ROOT/"artifacts/phase4/templates")
    ui=MilitaryUI(type("Base",(),{"worker":None})(),templates)
    rgb=np.asarray(Image.open(ROOT/"artifacts/phase4/captures/game-menu.jpg").convert("RGB"))
    with pytest.raises(ActionError,match="modal_blocked"):
        ui.ensure_no_modal(rgb)
    service,_,_=setup()
    before=service.ui.observe_land()
    for filename in ("selected-infantry-restored.jpg","selected-unassigned-idle.jpg"):
        rgb=np.asarray(Image.open(ROOT/"artifacts/phase4/captures"/filename).convert("RGB")).copy()
        clicks=[]
        ui=MilitaryUI(type("Base",(),{"worker":type("Worker",(),{"click":lambda _,p:clicks.append(p)})(),
            "capture":lambda _:rgb})(),templates)
        ui.observe_land=lambda:before
        ui.select_division=lambda _:rgb
        ui.change_land("create_army",before,lambda:None,division=before["divisions"][0])
        assert len(clicks)==1
        clicks.clear()
        rgb[85:120,65:130]=0
        with pytest.raises(ActionError,match="identity_mismatch"):
            ui.change_land("create_army",before,lambda:None,division=before["divisions"][0])
        assert not clicks


def test_frontline_invalid_target_and_active_plan_reject_before_mutation():
    service,ui,_=setup()
    view=create(service)
    assert service.create_frontline(view["armies"][0]["army_id"],{})["reason"]=="unsupported_target"
    view=service.create_frontline(view["armies"][0]["army_id"],"GER_POL_mainland")["after"]
    view=service.execute_plan(view["armies"][0]["army_id"])["after"]
    calls=ui.calls
    assert service.create_frontline(view["armies"][0]["army_id"],"GER_POL_east_prussia")["reason"]=="requirements_not_met"
    assert ui.calls==calls


def test_fixed_camera_drawing_mode_and_moving_counters_keep_border_identity():
    resolver=MapResolver(Templates(ROOT/"artifacts/phase4/templates"))
    rgb=np.asarray(Image.open(ROOT/"artifacts/phase4/captures/frontline-mode-active.jpg").convert("RGB"))
    assert resolver.resolve("GER_POL_mainland",rgb)==(1450,538)
    rgb=np.asarray(Image.open(ROOT/"artifacts/phase4/captures/front-drawing-mainland.jpg").convert("RGB"))
    assert resolver.presence(rgb,"GER_POL_mainland")
    assert not resolver.presence(rgb,"GER_POL_east_prussia")
    # Damaging an independent border segment must still reject, not infer presence.
    rgb=rgb.copy()
    rgb[456:474,1720:1740]=0
    with pytest.raises(ActionError,match="readback_ambiguous"):
        resolver.presence(rgb,"GER_POL_east_prussia")


def test_focus_completion_modal_blocks_navigation():
    ui=MilitaryUI(type("Base",(),{"worker":None})(),Templates(ROOT/"artifacts/phase4/templates"))
    rgb=np.asarray(Image.open(ROOT/"artifacts/phase4/captures/focus-completed-modal.jpg").convert("RGB"))
    with pytest.raises(ActionError,match="modal_blocked"):
        ui.ensure_no_modal(rgb)


@pytest.mark.parametrize("filename,region,missions",[("air-selected.jpg",None,[]),
    ("air-assigned.jpg",8,[]),("air-superiority.jpg",8,["air_superiority"])])
def test_real_air_wing_reader_and_identity_or_camera_damage(filename,region,missions):
    ui=MilitaryUI(type("Base",(),{"worker":None})(),Templates(ROOT/"artifacts/phase4/templates"))
    rgb=np.asarray(Image.open(ROOT/"artifacts/phase4/captures"/filename).convert("RGB"))
    wing=ui.read_air_wing(rgb)
    assert wing["name"]=="第132战斗机联队" and wing["base_name"]=="勃兰登堡"
    assert wing["aircraft_count"]==80 and wing["capacity"]==100
    assert wing["region_id"]==region and wing["missions"]==missions
    assert wing["mission_efficiency"] is None and wing["field_sources"]["mission_efficiency"]=="unknown"
    assert ui.map.resolve_air(8,rgb)==(1320,502)
    with pytest.raises(ActionError,match="map_target_unresolved"):
        ui.map.resolve_air(8,np.roll(rgb,10,axis=1))
    for box in ((241,259,334,275),(49,152,119,169),(128,256,156,288),(109,94,689,120)):
        damaged=rgb.copy()
        x0,y0,x1,y1=box
        damaged[y0:y1,x0:x1]=0
        with pytest.raises(ActionError,match="identity_mismatch"):
            ui.read_air_wing(damaged)


def test_real_air_reinforcement_count_outside_calibration_rejects():
    ui=MilitaryUI(type("Base",(),{"worker":None})(),Templates(ROOT/"artifacts/phase4/templates"))
    rgb=np.asarray(Image.open(ROOT/"artifacts/phase4/captures/air-count-changed-81.jpg").convert("RGB"))
    with pytest.raises(ActionError,match="identity_mismatch"):
        ui.read_air_wing(rgb)


def test_air_exact_assignment_mission_stop_satisfied_and_stale_ids():
    service,ui,_=setup()
    view=service.get_air_wings()
    wing=view["air_wings"][0]["wing_id"]
    assert service.set_air_mission(wing,"air_superiority")["reason"]=="requirements_not_met"
    assert service.assign_air_wing(wing,9)["reason"]=="unsupported_target"
    assert not ui.calls
    result=service.assign_air_wing(wing,8)
    assert result["status"]=="confirmed" and ui.calls==1
    assert service.set_air_mission(wing,"air_superiority")["reason"]=="snapshot_stale"
    wing=result["after"]["air_wings"][0]["wing_id"]
    result=service.set_air_mission(wing,"air_superiority")
    assert result["status"]=="confirmed" and ui.calls==2
    assert result["after"]["air_wings"][0]["missions"]==["air_superiority"]
    result=service.set_air_mission(result["after"]["air_wings"][0]["wing_id"],"air_superiority")
    assert result["status"]=="already_satisfied" and ui.calls==2
    result=service.set_air_mission(result["after"]["air_wings"][0]["wing_id"],"none")
    assert result["status"]=="confirmed" and not result["after"]["air_wings"][0]["missions"]
    wing=result["after"]["air_wings"][0]["wing_id"]
    service.air_wings.created=time.monotonic()-121
    assert service.assign_air_wing(wing,8)["reason"]=="snapshot_stale"


@pytest.mark.parametrize("mode",["failure","missed","wrong"])
def test_air_uncertain_no_resubmit_or_reuse_identity(mode):
    service,ui,_=setup()
    wing=service.get_air_wings()["air_wings"][0]["wing_id"]
    setattr(ui,mode,"loss_of_focus" if mode=="failure" else True)
    result=service.assign_air_wing(wing,8)
    assert result["status"]=="uncertain" and result["retry_count"]==0 and ui.calls==1
    assert service.air_wings.view is None
    assert service.assign_air_wing(wing,8)["status"]=="rejected" and ui.calls==1


def test_real_navy_identity_all_ships_and_unknown_missions():
    ui=MilitaryUI(type("Base",(),{"worker":None})(),Templates(ROOT/"artifacts/phase4/templates"))
    rgb=np.asarray(Image.open(ROOT/"artifacts/phase4/captures/navy-selected.jpg").convert("RGB"))
    fleet=ui.read_fleet(rgb)
    assert fleet["object_type"]=="task_force" and fleet["parent_fleet_name"]=="德国海军"
    assert fleet["ship_count"]==12 and len(fleet["ship_names"])==12 and fleet["docked"]
    assert fleet["home_port_name"]=="威廉港" and fleet["admiral_id"] is None
    for field in ("region_ids","mission","supply_ratio"):
        assert fleet[field] is None and fleet["field_sources"][field]=="unknown"
    for box in ((70,94,129,110),(70,303,126,321),(184,420,336,437),(184,871,336,888)):
        damaged=rgb.copy()
        x0,y0,x1,y1=box
        damaged[y0:y1,x0:x1]=0
        with pytest.raises(ActionError,match="identity_mismatch"):
            ui.read_fleet(damaged)


def test_air_load_pixel_rounding_requires_three_consistent_city_anchors():
    resolver=MapResolver(Templates(ROOT/"artifacts/phase4/templates"))
    rgb=np.asarray(Image.open(ROOT/"artifacts/phase4/captures/air-fresh-selected.jpg").convert("RGB"))
    assert resolver.resolve_air(8,rgb)==(1320,501)
    with pytest.raises(ActionError,match="map_target_unresolved"):
        resolver.resolve_air(8,np.roll(rgb,10,axis=1))
    rgb=rgb.copy()
    rgb[888:914,1497:1542]=0
    with pytest.raises(ActionError,match="map_target_unresolved"):
        resolver.resolve_air(8,rgb)


def test_navy_observation_repeated_identity_and_unimplemented_mutations():
    service,ui,_=setup()
    ui.observe_navy=lambda:{"fleets":[sourced({"name":"公海舰队","object_type":"task_force",
        "parent_fleet_name":"德国海军","home_port_name":"威廉港","ship_count":12,"ship_names":["Deutschland"]})]}
    result=service.get_fleets()
    assert result["status"]=="confirmed" and not result["stable_game_identity"]
    identity=result["fleets"][0]["fleet_id"]
    assert service.assign_fleet_region(identity,7)["reason"]=="unsupported_target"
    assert service.set_naval_mission(identity,"patrol")["reason"]=="unsupported_target"
    assert not ui.calls
    reads=[ui.observe_navy(),{"fleets":[]}]
    ui.observe_navy=lambda:reads.pop(0)
    assert service.get_navy_state()["reason"]=="readback_ambiguous" and not ui.calls
