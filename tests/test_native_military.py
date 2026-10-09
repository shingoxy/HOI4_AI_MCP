"""Real native overview and explicit bottom HUD translation."""
from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
from PIL import Image
import pytest
ROOT=Path(__file__).parents[1]
sys.path.insert(0,str(ROOT/'src'))
from hoi4_operator.executor.native_military_ui import NativeMilitaryUI,HUDWorker
from hoi4_operator.executor.templates import Templates
from hoi4_operator.executor.windows_native import PHYSICAL_PROFILE
from hoi4_operator.executor.guard import ActionError
from hoi4_operator.executor.native_order_ui import NativeOrderReader


def test_real_native_overview_identity_and_no_armies():
    rgb=np.asarray(Image.open(ROOT/'artifacts/phase5/gate-20261006/captures/army-observe-current.png').convert('RGB'))
    ui=NativeMilitaryUI(SimpleNamespace(worker=SimpleNamespace(capture_profile=PHYSICAL_PROFILE)),
        Templates(ROOT/'artifacts/phase4/templates'),Templates(ROOT/'artifacts/phase5/templates/military'))
    divisions=ui.read_divisions(rgb)
    assert [d['name'] for d in divisions]==['1. Infanterie-Division','1. Panzer-Division','10. Infanterie-Division']
    assert all(d['army_name'] is None for d in divisions)
    assert ui.found(rgb,'army_create_plus',(1280,980,1340,1055),.86)
    bad=rgb.copy()
    bad[350:385,100:309]=0
    with pytest.raises(ActionError): ui.read_divisions(bad)


def test_hud_input_translation_is_finite_and_does_not_scale_map_points():
    events=[]
    backend=SimpleNamespace(click=lambda p,**kw:events.append((p,kw)))
    worker=HUDWorker(backend)
    worker.click((1270,1015),button='right')
    worker.click((1750,720))
    assert events==[((1270,1535),{'button':'right'}),((1750,720),{})]


def test_real_native_single_infantry_army_membership_and_unique_card():
    rgb=np.asarray(Image.open(ROOT/'artifacts/phase5/gate-20261006/captures/army-one-native.png').convert('RGB'))
    ui=NativeMilitaryUI(SimpleNamespace(worker=SimpleNamespace(capture_profile=PHYSICAL_PROFILE)),
        Templates(ROOT/'artifacts/phase4/templates'),Templates(ROOT/'artifacts/phase5/templates/military'))
    army=ui.read_army(rgb)
    assert army['name']=='第1集团军' and army['general_id'] is None
    assert army['division_names']==['1. Infanterie-Division']
    assert ui.army_card(rgb)==(1270,1015)
    bad=rgb.copy()
    bad[125:153,62:200]=0
    with pytest.raises(ActionError): ui.read_army(bad)


def test_native_assignment_requires_counter_and_exact_two_distinct_members():
    rgb=np.asarray(Image.open(ROOT/'artifacts/phase5/gate-20261006/captures/army-two-native.png').convert('RGB'))
    ui=NativeMilitaryUI(SimpleNamespace(worker=SimpleNamespace(capture_profile=PHYSICAL_PROFILE)),
        Templates(ROOT/'artifacts/phase4/templates'),Templates(ROOT/'artifacts/phase5/templates/military'))
    assert ui.read_army(rgb)['division_names']==['1. Infanterie-Division','1. Panzer-Division']
    for box in [(351,94,363,109),(180,274,344,306)]:
        bad=rgb.copy(); x0,y0,x1,y1=box; bad[y0:y1,x0:x1]=0
        with pytest.raises(ActionError): ui.read_army(bad)


def test_empty_native_orders_require_border_markers_and_no_extra_order():
    reader=NativeOrderReader(Templates(ROOT/'artifacts/phase5/templates/military'))
    for name in ('front-empty-native.png','front-empty-reobserved.png'):
        rgb=np.asarray(Image.open(ROOT/'artifacts/phase5/gate-20261006/captures'/name).convert('RGB'))
        assert reader.scene(rgb)=='empty'
        bad=rgb.copy();bad[800:820,2070:2090]=[255,20,180]
        with pytest.raises(ActionError):reader.scene(bad)
        bad=rgb.copy();bad[620:660,1900:1940]=0
        with pytest.raises(ActionError):reader.scene(bad)


def test_native_front_navigation_emits_diagnostics_without_submission():
    rgb=np.asarray(Image.open(ROOT/'artifacts/phase5/gate-20261006/captures/front-empty-native.png').convert('RGB'))
    events=[]
    backend=SimpleNamespace(capture_profile=PHYSICAL_PROFILE,click=lambda p,**kw:events.append(('click',p)),
                            _record=lambda op,**kw:events.append((op,kw)))
    ui=NativeMilitaryUI(SimpleNamespace(worker=backend,capture=lambda:rgb),
        Templates(ROOT/'artifacts/phase4/templates'),Templates(ROOT/'artifacts/phase5/templates/military'))
    ui.observe_land=lambda:{'armies':[ui.read_army(rgb)],'divisions':[]}
    assert ui.observe_orders()['fronts']==[]
    assert all(e[0]!='semantic_commit' for e in events)
    assert any(e[0]=='native_order_read' for e in events)


def test_native_front_present_requires_exact_viewport_and_stopped_plan():
    rgb=np.asarray(Image.open(ROOT/'artifacts/phase5/gate-20261006/captures/front-present-native.png').convert('RGB'))
    backend=SimpleNamespace(capture_profile=PHYSICAL_PROFILE,click=lambda p,**kw:None,_record=lambda *a,**kw:None)
    ui=NativeMilitaryUI(SimpleNamespace(worker=backend,capture=lambda:rgb),
        Templates(ROOT/'artifacts/phase4/templates'),Templates(ROOT/'artifacts/phase5/templates/military'))
    ui.observe_land=lambda:{'armies':[ui.read_army(rgb)],'divisions':[]}
    view=ui.observe_orders()
    assert [f['target_id'] for f in view['fronts']]==['GER_POL_mainland']
    assert view['operation_name']=='白色方案' and view['plan_active'] is False
    bad=rgb.copy();bad[760:790,2030:2060]=[255,20,180]
    with pytest.raises(ActionError):ui.orders.scene(bad)


def test_native_offensive_gate_requires_hatching_and_one_right_drag():
    rgb=np.asarray(Image.open(ROOT/'artifacts/phase5/gate-20261006/captures/offensive-empty-native.png').convert('RGB'))
    inputs=[]
    backend=SimpleNamespace(capture_profile=PHYSICAL_PROFILE,right_drag=lambda a,b:inputs.append((a,b)))
    ui=NativeMilitaryUI(SimpleNamespace(worker=backend,capture=lambda:rgb),
        Templates(ROOT/'artifacts/phase4/templates'),Templates(ROOT/'artifacts/phase5/templates/military'))
    land={'armies':[ui.read_army(rgb)],'divisions':[]}
    before=ui.offensive.read(rgb,land)
    assert before['offensive_orders']==[] and len(before['fronts'])==1
    bad=rgb.copy();bad[700:780,2030:2110]=0
    assert not ui.offensive.tool_active(bad)
    inactive=np.asarray(Image.open(ROOT/'artifacts/phase5/gate-20261006/captures/front-present-native.png').convert('RGB')).copy()
    inactive[1394:1418,1288:1310]=rgb[1394:1418,1288:1310]
    assert not ui.offensive.tool_active(inactive)
    commits=[]
    ui.offensive.submit('GER_POL_mainland_Poznan_east',before,lambda:commits.append(True))
    assert commits==[True] and inputs==[((2030,760),(2030,870))]
    with pytest.raises(ActionError):ui.offensive.submit('GER_POL_mainland_Poland_north_east',before,lambda:commits.append(True))
    assert len(commits)==1 and len(inputs)==1


def test_native_offensive_readback_requires_target_label_and_no_extra_order():
    rgb=np.asarray(Image.open(ROOT/'artifacts/phase5/gate-20261006/captures/offensive-present-native.png').convert('RGB'))
    backend=SimpleNamespace(capture_profile=PHYSICAL_PROFILE)
    ui=NativeMilitaryUI(SimpleNamespace(worker=backend),Templates(ROOT/'artifacts/phase4/templates'),
        Templates(ROOT/'artifacts/phase5/templates/military'))
    land={'armies':[ui.read_army(rgb)],'divisions':[]}
    view=ui.offensive.read(rgb,land)
    assert view['offensive_orders'][0]['target_id']=='GER_POL_mainland_Poznan_east'
    assert view['offensive_orders'][0]['front_target_id']=='GER_POL_mainland'
    for box in [(2020,741,2048,879),(1914,841,2018,884),(2300,860,2330,890)]:
        bad=rgb.copy();x0,y0,x1,y1=box;bad[y0:y1,x0:x1]=[255,20,180]
        with pytest.raises(ActionError):ui.offensive.read(bad,land)
