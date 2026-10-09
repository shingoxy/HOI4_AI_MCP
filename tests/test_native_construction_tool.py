"""Real physical tool pulse/hover/wrong-tool evidence and one-submit boundaries."""
from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np
from PIL import Image
import pytest

ROOT=Path(__file__).parents[1]
sys.path.insert(0,str(ROOT/'src'))
from hoi4_operator.executor.construction_ui import ConstructionUI
from hoi4_operator.executor.guard import ActionError
from hoi4_operator.executor.native_construction_tool import NativeConstructionTool
from hoi4_operator.executor.templates import Templates
from hoi4_operator.executor.windows_native import PHYSICAL_PROFILE

DATA=ROOT/'artifacts/phase5/tool-20261007'

def load(stage, folder='diagnostic-2'):
    return np.asarray(Image.open(DATA/folder/(stage+'.png')).convert('RGB'))

def reader(worker=None):
    return NativeConstructionTool(worker or SimpleNamespace(check=lambda:None),
        Templates(ROOT/'artifacts/phase3/templates'),
        Templates(ROOT/'artifacts/phase5/templates/map_home'),
        Templates(ROOT/'artifacts/phase5/templates'))

@pytest.mark.parametrize('stage,state',[
    ('02-before-tool','TOOL_NOT_SELECTED'),('02-hover-only','TOOL_NOT_SELECTED'),
    ('06-neutral-stable','TOOL_SELECTED'),('06-passive-1','TOOL_SELECTED'),
    ('06-passive-0','TOOL_ANIMATING'),('04-click-stable','TOOL_ANIMATING'),
    ('00-map','TOOL_OCCLUDED')])
def test_real_physical_tool_states(stage,state):
    assert reader().read(load(stage))['state']==state

def test_pulse_below_old_threshold_is_positive_joint_gui_evidence():
    r=reader().read(load('06-neutral-stable'))
    assert r['legacy_selected']['score']<.9
    assert r['icon']['score']>=.9 and r['mode']['score']>=.9
    assert r['state']=='TOOL_SELECTED' and r['outline']['confirmed']

@pytest.mark.parametrize('stage',['03-click-first','06-neutral-stable','06-passive-1','06-passive-3'])
def test_wrong_building_overlay_is_never_civilian_selected(stage):
    v=reader().read(load(stage,'diagnostic-wrong'))
    assert v['mode']['confirmed'] and v['state']=='TOOL_NOT_SELECTED'
    assert v['reason']=='wrong_building_tool'

@pytest.mark.parametrize('bad',['icon','mode','modal'])
def test_overlay_mismatch_occlusion_or_modal_cannot_confirm(bad):
    rgb=load('06-neutral-stable').copy()
    if bad=='icon': rgb[266:314,497:545]=0
    if bad=='mode': rgb[1400:1431,2494:2526]=0
    if bad=='modal':
        menu=np.asarray(Image.open(ROOT/'artifacts/phase5/continuation-20261007/final-physical.png').convert('RGB'))
        rgb[585:620,1230:1330]=menu[585:620,1230:1330]
    assert reader().read(rgb)['state'] in {'TOOL_OCCLUDED','TOOL_UNKNOWN'}

def test_passive_confirmation_handles_real_pulse_without_input(tmp_path):
    frames=[load('06-neutral-stable'),load('06-passive-0'),load('06-passive-1')]
    waits=[]
    b=SimpleNamespace(check=lambda:None,capture=lambda:frames.pop(0),audit_directory=tmp_path)
    r=reader(b);r.start()
    rgb,state=r.confirm(frames.pop(0),waits.append)
    assert state['state']=='TOOL_SELECTED' and len(waits)==2
    assert r.evidence['tool_clicks']==0 and r.evidence['passive_captures']==2
    assert (r.path/'confirmed-exact.png').is_file()
    assert len(list(r.path.glob('*.json')))>=4

def test_permanent_pulse_or_unknown_expires_with_exact_failure_frame(tmp_path):
    rgb=load('06-passive-0')
    calls=[]
    b=SimpleNamespace(check=lambda:None,capture=lambda:(calls.append('capture') or rgb),audit_directory=tmp_path)
    r=reader(b);r.start()
    with pytest.raises(ActionError,match='construction_tool_unknown'):
        r.confirm(rgb,lambda _:None)
    assert len(calls)<=12 and r.evidence['tool_clicks']==0
    assert (r.path/'failure-exact.png').is_file() and (r.path/'failure-exact-roi.png').is_file()

def make_ui(frames, tmp_path=None):
    clicks=[]
    b=SimpleNamespace(check=lambda:None,capture=lambda:frames.pop(0),
        click=clicks.append,capture_profile=PHYSICAL_PROFILE,audit_directory=tmp_path)
    ui=ConstructionUI(SimpleNamespace(worker=b,capture=b.capture),
        Templates(ROOT/'artifacts/phase3/templates'),Templates(ROOT/'artifacts/phase5/templates/map'))
    ui.map_state.wait=lambda _:None
    return ui,clicks

def test_one_tool_click_then_passive_truth_with_no_state_click():
    frames=[load('03-click-first'),load('06-passive-0'),load('06-neutral-stable'),load('06-passive-1')]
    ui,clicks=make_ui(frames)
    ui.select_native_tool(load('02-before-tool'),(521,290))
    assert clicks==[(521,290),(180,103)]
    assert ui.tool_reader.evidence['tool_clicks']==1

def test_unknown_after_one_tool_click_never_reselects(tmp_path):
    pulse=load('06-passive-0')
    ui,clicks=make_ui([pulse.copy() for _ in range(15)],tmp_path)
    with pytest.raises(ActionError,match='construction_tool_unknown'):
        ui.select_native_tool(load('02-before-tool'),(521,290))
    assert clicks==[(521,290),(180,103)]
    assert (ui.tool_reader.path/'failure-exact.png').exists()

@pytest.mark.parametrize('moved',[False,True])
def test_build_one_submit_or_changed_map_zero_submit(moved):
    before=load('02-before-tool')
    normal=load('01-map-reference')
    identity=np.asarray(Image.open(ROOT/'artifacts/phase5/stability-20261007/investigation/canonical-3-state.png').convert('RGB'))
    final=load('06-passive-1').copy()
    if moved: final[100:1320,750:2420]=np.roll(final[100:1320,750:2420],5,axis=1)
    frames=[before,normal,identity,normal,load('03-click-first'),load('06-neutral-stable'),final,before]
    ui,clicks=make_ui(frames)
    ui.open=lambda:before
    ui.close=lambda:None
    commits=[]
    if moved:
        with pytest.raises(ActionError,match='map_target_unresolved'):
            ui.change('build',ui.read(before),lambda:commits.append('commit'),state_id=64,building_type='civilian_factory')
        assert commits==[] and clicks.count((1280,800))==1
    else:
        ui.change('build',ui.read(before),lambda:commits.append('commit'),state_id=64,building_type='civilian_factory')
        assert commits==['commit'] and clicks.count((1280,800))==2  # identity, then one build
    assert clicks.count((521,290))==1

def test_exact_queue_mutation_has_no_extra_or_repeated_rows():
    from hoi4_operator.actions.construction import validate
    before={'queue':[]}
    after={'queue':[dict(state_id=64,building_type='civilian_factory',count=1)]}
    assert validate(before,after,'build',state_id=64,building_type='civilian_factory')['exact_transition']
    for bad in [{'queue':after['queue']*2},{'queue':[dict(state_id=64,building_type='military_factory',count=1)]}]:
        with pytest.raises(ActionError): validate(before,bad,'build',state_id=64,building_type='civilian_factory')

def test_30_day_map_metrics_keep_recovery_audit_separate(tmp_path):
    import json
    from hoi4_operator.executor.native_audit import map_metrics
    events=[dict(op='map_state',state=s) for s in ['MAP_READY','MAP_READY','MAP_RECOVERABLE','MAP_UNRESOLVED']]
    events.extend([dict(op='map_recovery_started'),dict(op='map_recovery',succeeded=True,duration_ms=12500),
                   dict(op='map_recovery_started'),dict(op='map_recovery',succeeded=False,duration_ms=2000)])
    (tmp_path/'trace.json').write_text(json.dumps(dict(events=events)),encoding='utf-8')
    value=map_metrics(tmp_path)
    assert (value['MAP_READY'],value['MAP_RECOVERABLE'],value['MAP_UNRESOLVED'])==(2,1,1)
    assert (value['recovery_attempted'],value['recovery_succeeded'],value['recovery_failed'])==(2,1,1)
    assert value['recovery_duration_ms']==14500 and value['clock_recovery_count']==0
