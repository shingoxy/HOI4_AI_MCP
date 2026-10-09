"""Real GDI camera/clock regressions; fake input boundaries never prove live recovery."""
from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np
from PIL import Image
import pytest

ROOT=Path(__file__).parents[1]
sys.path.insert(0,str(ROOT/'src'))
from hoi4_operator.executor.guard import ActionError
from hoi4_operator.executor.native_map_state import NativeMapState
from hoi4_operator.executor.native_runtime import NativeClockGUI
from hoi4_operator.executor.templates import Templates
from hoi4_operator.action_catalog import build_catalog, VALIDATED_ACTIONS
from hoi4_operator.agent import ScriptedAgent
from test_agent_runtime import setup_observation

INV=ROOT/'artifacts/phase5/stability-20261007/investigation'
MAP=ROOT/'artifacts/phase5/templates/map'
def load(path): return np.asarray(Image.open(path).convert('RGB'))
def resolver(worker=None): return NativeMapState(worker or SimpleNamespace(),Templates(MAP))

@pytest.mark.parametrize('n',[1,2,3,4])
def test_actual_home_camera_and_independent_identity(n):
    view=resolver().require(load(INV/f'canonical-{n}-map.png'))
    assert view['profile']=='home' and NativeMapState.target_point(view)==(1280,800)
    rgb=load(INV/f'canonical-{n}-state.png')
    t=Templates(ROOT/'artifacts/phase3/templates')
    assert t.find(rgb,'state_title_64',(165,952,320,988),.9)
    assert t.find(rgb,'state_owner_ger',(22,1002,80,1045),.9)

def test_actual_original_gate_camera_remains_valid():
    view=resolver().require(load(ROOT/'artifacts/phase5/gate-20261006/captures/construction-map-after-close.png'))
    assert view['profile']=='gate' and NativeMapState.target_point(view)==(1385,812)

@pytest.mark.parametrize('name',['current-initial.png','panel-before.png','panel-open.png','panel-closed.png'])
def test_actual_drift_and_panel_navigation_do_not_become_ready(name):
    view=resolver().inspect(load(INV/name))
    assert view['state'] in {'MAP_RECOVERABLE','MAP_UNRESOLVED'}

@pytest.mark.parametrize('shift',[2,5,35,180])
def test_pose_change_after_identity_rejects_even_if_new_view_is_readable(shift):
    r=resolver()
    rgb=load(INV/'canonical-3-map.png')
    pose=r.require(rgb)
    changed=rgb.copy()
    changed[80:1350]=np.roll(changed[80:1350],shift,axis=1)
    with pytest.raises(ActionError): r.require(changed,same=pose)

@pytest.mark.parametrize('which',['amsterdam','copenhagen','warsaw','mode','modal'])
def test_wrong_anchor_mode_and_occlusion_never_ready(which):
    r=resolver()
    rgb=load(INV/'canonical-3-map.png').copy()
    if which=='modal':
        menu=load(ROOT/'artifacts/phase5/continuation-20261007/final-physical.png')
        rgb[585:620,1230:1330]=menu[585:620,1230:1330]
    else:
        box=(2494,1400,2526,1431) if which=='mode' else r.manifest['anchor_boxes'][which]
        x,y,X,Y=box;rgb[y:Y,x:X]=0
    assert r.inspect(rgb)['state']!='MAP_READY'
    with pytest.raises(ActionError): r.require(rgb)

@pytest.mark.parametrize('state',['MAP_UNRESOLVED','MAP_RECOVERABLE'])
def test_catalog_blocks_implemented_supported_but_currently_unready_build(state):
    _,agg,_,caps=setup_observation()
    cap=caps();cap['action_readiness']['build'].update(map_state=state,map_reason='camera_unresolved')
    cat=build_catalog(agg.get('summary'),VALIDATED_ACTIONS,cap)
    assert cat['build']['status']=='temporarily_blocked' and cat['build']['options']==[]
    assert cat['build']['readiness']['semantic_implemented'] and cat['build']['readiness']['backend_supported']
    decision=ScriptedAgent().decide(agg.get('summary'),cat,{})
    assert all(a['action']!='build' for a in decision['actions'])

def test_catalog_rechecks_identity_and_current_capability():
    _,agg,_,caps=setup_observation()
    cap=caps()
    assert build_catalog(agg.get('summary'),VALIDATED_ACTIONS,cap)['build']['status']=='available'
    cap['action_readiness']['build']['target_identity_valid']=False
    assert build_catalog(agg.get('summary'),VALIDATED_ACTIONS,cap)['build']['reason']=='target_identity_unverified'
    cap['native_subset_ready']=False
    assert build_catalog(agg.get('summary'),VALIDATED_ACTIONS,cap)['build']['status']=='unsupported'

def test_catalog_rejects_a_ready_map_with_uncalibrated_current_profile():
    _,agg,_,caps=setup_observation()
    cap=caps();cap['action_readiness']['build']['profile_calibrated']=False
    entry=build_catalog(agg.get('summary'),VALIDATED_ACTIONS,cap)['build']
    assert entry['status']=='unsupported' and entry['options']==[]
    assert entry['reason']=='current_map_profile_uncalibrated'

def test_second_real_drawing_fixture_is_currently_confirmed():
    r=resolver()
    before=load(INV/'drawing4-before.png')
    after=load(INV/'drawing4-selected.png')
    result=r.require(after,same=r.require(before),construction_panel=True,reference=before)
    assert result['geometry']['confirmed'] and result['geometry']['unchanged_ratio']>=.9

def test_failure_frame_is_persisted_before_any_future_action(tmp_path):
    r=resolver(SimpleNamespace(audit_directory=tmp_path))
    with pytest.raises(ActionError): r.require(load(INV/'current-initial.png'))
    assert len(list(tmp_path.glob('map-rejected-*.png')))==1
    assert len(list(tmp_path.glob('map-rejected-*.json')))==1

def test_unknown_camera_without_verified_recovery_controls_rejects_without_input():
    r=resolver()
    rgb=load(INV/'current-initial.png').copy();rgb[1359:1390,2520:2557]=0
    with pytest.raises(ActionError): r.prepare(rgb)

def test_recovery_failure_never_clicks_a_state_or_submits_build():
    rgb=load(INV/'current-initial.png')
    events=[]
    b=SimpleNamespace(click=lambda p:events.append(('click',p)),capture=lambda:rgb,
        check=lambda:None)
    r=resolver(b)
    with pytest.raises(ActionError): r.prepare(rgb)
    assert len(events)==1 and events[0][1]!=(1280,800)

def test_known_menu_pause_and_unknown_date_are_separate_and_cannot_resume():
    rgb=load(ROOT/'artifacts/phase5/continuation-20261007/final-physical.png')
    events=[]
    b=SimpleNamespace(capture=lambda:rgb,key=lambda key:events.append(key))
    gui=NativeClockGUI(b,ROOT/'artifacts/phase5/gate-20261006/final/native-final-physical.png',Templates(ROOT/'artifacts/phase5/templates'))
    evidence=gui.pause_evidence()
    assert evidence['paused'] and evidence['gui_date_status']=='UNKNOWN' and evidence['gui_date'] is None
    assert evidence['resumable'] is False
    with pytest.raises(ActionError,match='modal_blocked'): gui.is_paused()
    with pytest.raises(ActionError,match='modal_blocked'): gui.resume()
    assert events==[]

def test_actual_menu_closed_clock_header_remains_calibrated():
    rgb=load(INV/'current-initial.png')
    gui=NativeClockGUI(SimpleNamespace(capture=lambda:rgb),
        ROOT/'artifacts/phase5/gate-20261006/final/native-final-physical.png',Templates(ROOT/'artifacts/phase5/templates'))
    assert gui.clock_value().shape==(21,116)

def test_unknown_clock_glyphs_cannot_resume_or_supply_a_gui_date():
    rgb=load(INV/'current-initial.png').copy()
    rgb[9:30,2294:2410]=0
    events=[]
    gui=NativeClockGUI(SimpleNamespace(capture=lambda:rgb,key=lambda key:events.append(key)),
        ROOT/'artifacts/phase5/gate-20261006/final/native-final-physical.png',Templates(ROOT/'artifacts/phase5/templates'))
    with pytest.raises(ActionError,match='clock_date_unrecognized'): gui.resume()
    assert events==[]

def test_real_construction_mode_changes_labels_but_preserves_camera_geometry():
    r=resolver()
    before=load(INV/'drawing-before.png')
    after=load(INV/'drawing-selected.png')
    pose=r.require(before)
    assert r.inspect(after)['state']=='MAP_UNRESOLVED'
    result=r.require(after,same=pose,construction_panel=True,reference=before)
    assert result['geometry']['confirmed'] and not result['geometry']['target_transform_used']

@pytest.mark.parametrize('change',['small_pan','large_pan','wrong_camera','target_occluded','missing_selected_tool','wrong_mode'])
def test_drawing_state_change_or_occlusion_rejects_before_commit(change):
    r=resolver()
    before=load(INV/'drawing-before.png')
    after=load(INV/'drawing-selected.png').copy()
    pose=r.require(before)
    if change in {'small_pan','large_pan'}:
        after[100:1320]=np.roll(after[100:1320],3 if change=='small_pan' else 180,axis=1)
    elif change=='wrong_camera': before=load(INV/'current-initial.png')
    elif change=='target_occluded': after[600:1070,1000:1500]=0
    elif change=='missing_selected_tool': after[266:314,497:545]=0
    elif change=='wrong_mode': after[1400:1431,2494:2526]=0
    with pytest.raises(ActionError): r.require(after,same=pose,construction_panel=True,reference=before)

@pytest.mark.parametrize('final_ready',[True,False])
def test_one_recovery_navigation_and_fresh_validation_are_required(final_ready):
    start=load(INV/'current-initial.png')
    final=load(INV/'canonical-3-map.png') if final_ready else start
    frames=[load(INV/'find-view.png'),load(INV/'canonical-3-near.png'),final]+[final]*6
    events=[]
    b=SimpleNamespace(click=lambda p:events.append(('click',p)),capture=lambda:frames.pop(0),
        check=lambda:None,key=lambda k:events.append(('key',k)),scroll=lambda p,d:events.append(('wheel',p,d)),
        _point=lambda p:(p,None),_move=lambda p,g:events.append(('move',p)),
        _record=lambda op,**fields:events.append(('audit',op,fields)))
    r=resolver(b);r.wait=lambda seconds:None
    if final_ready:
        assert r.prepare(start)['state']=='MAP_READY'
    else:
        with pytest.raises(ActionError): r.prepare(start)
    assert len([e for e in events if e[0]=='wheel'])==5
    assert len([e for e in events if e[0]=='key'])==1
    assert len([e for e in events if e[0]=='click'])==2
    recovery=[e for e in events if e[:2]==('audit','map_recovery')]
    assert len(recovery)==1 and recovery[0][2]['succeeded']==final_ready
    assert len([e for e in events if e[:2]==('audit','map_recovery_started')])==1
