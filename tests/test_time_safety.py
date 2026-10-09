"""Ownership, bounded stop, real modal evidence and shutdown failure contracts."""
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np
from PIL import Image
import pytest

ROOT=Path(__file__).parents[1]
sys.path.insert(0,str(ROOT/'src'))
from hoi4_operator.game_time import GameTimeController, TimeOwnership
from hoi4_operator.executor.guard import ActionError
from hoi4_operator.executor.native_runtime import NativeClockGUI, NativeRuntimeHost
from hoi4_operator.executor.native_modal import NativeModalDetector
from hoi4_operator.executor.templates import Templates

class GUI:
    def __init__(self,failure=None,safe=False):
        self.running=False;self.failure=failure;self.safe=safe
        self.inputs=[]
    def begin(self,_): pass
    def end(self): pass
    def check(self): pass
    def is_paused(self): return not self.running
    def resume(self): self.running=True;self.inputs.append('resume')
    def pause(self):
        if isinstance(self.failure,Exception): raise self.failure
        if self.failure: return False
        self.inputs.append('pause');self.running=False;return True
    def safe_stop_once(self):
        if not self.safe: return False
        self.inputs.append('safe_stop');self.running=False;return True

def controller(gui):
    model=SimpleNamespace(summary=lambda:dict(game_date='1936-08-03',status='fresh'),poll=lambda:None)
    return GameTimeController(model,gui,timeout=.01,poll_interval=.001)

def acquire(t):
    t.acquire_running_ownership();t.gui.resume()

def test_resume_owned_and_confirmed_pause_release_only_after_readback():
    t=controller(GUI());acquire(t)
    assert t.state==TimeOwnership.RUNNING_OWNED and t.owns_running
    assert t.ensure_game_stopped()['paused']
    assert t.state==TimeOwnership.PAUSED_CONFIRMED and not t.owns_running
    t.ensure_game_stopped()
    assert t.gui.inputs==['resume','pause']
    assert t.metrics['time_ownership_acquired']==t.metrics['time_ownership_released']==1

@pytest.mark.parametrize('failure',[True,RuntimeError('pause_failed'),ActionError('modal_blocked'),
                                    ActionError('unknown_modal'),ActionError('loss_of_focus'),
                                    ActionError('emergency_stop'),TimeoutError('pause_timeout')])
def test_pause_failure_or_exception_retains_responsibility_and_never_retries(failure):
    t=controller(GUI(failure));acquire(t)
    first=t.ensure_game_stopped();t.ensure_game_stopped()
    assert not first['paused'] and t.owns_running and t.state==TimeOwnership.STOP_FAILED_OWNED
    assert t.gui.inputs==['resume'] and t.metrics['pause_attempts']==1
    assert first['operator_intervention_required']

def test_safe_stop_is_independent_of_advance_and_releases_ownership():
    t=controller(GUI(ActionError('modal_blocked'),safe=True));acquire(t)
    assert t.ensure_game_stopped()['paused'] and not t.owns_running
    assert t.gui.inputs==['resume','safe_stop'] and t.metrics['pause_failures']==1
    assert t.metrics['safe_stop_successes']==1

def test_finally_never_discards_ownership_after_advance_failure():
    t=controller(GUI(ActionError('modal_blocked')))
    result=t.advance_days()
    assert result['status']=='failed' and not result['paused'] and result['owns_running']
    assert t.state==TimeOwnership.STOP_FAILED_OWNED
    again=t.advance_days()
    assert again['reason']=='owned_time_not_stopped' and t.gui.inputs==['resume']

def test_resume_exception_is_conservatively_owned_until_stop_confirmed():
    g=GUI(True)
    def broken(): g.running=True;g.inputs.append('maybe_resume');raise RuntimeError('readback_failed')
    g.resume=broken;t=controller(g)
    assert not t.advance_days()['paused'] and t.owns_running

def test_passive_operator_pause_can_release_failed_owned_state_without_another_input():
    t=controller(GUI(True));acquire(t);t.ensure_game_stopped()
    t.gui.running=False
    assert t.ensure_game_stopped()['paused'] and not t.owns_running
    assert t.gui.inputs==['resume']

def load(path): return np.asarray(Image.open(ROOT/path).convert('RGB'))
TEMPLATES=ROOT/'artifacts/phase5/templates'
SINGLE='artifacts/phase5/tool-20261007/safety-stop-1/before.png'
MENU='artifacts/phase5/tool-20261007/safety-stop-1/after.png'
STACK='artifacts/phase5/tool-20261007/final-physical.png'
NORMAL='artifacts/phase5/time-safety-20261007/preflight-2/physical.png'

@pytest.mark.parametrize('path,state,route',[(SINGLE,'KNOWN_BLOCKING_MODAL','escape_to_menu'),
    (MENU,'KNOWN_SAFE_MODAL','menu_pause_readback'),(STACK,'OVERLAY_STACK',None),(NORMAL,'NO_MODAL',None)])
def test_real_modal_types_are_not_generic_dismissal_permission(path,state,route):
    result=NativeModalDetector(Templates(TEMPLATES)).read(load(path))
    assert result['state']==state and result['stop_route']==route

def native_gui(frames,tmp_path,inputs):
    def key(key):
        # The triggering failure RGB must be durable before safe stop input.
        assert list(tmp_path.glob('time-failure-*/physical.png'))
        inputs.append(key)
    backend=SimpleNamespace(capture=lambda:frames.pop(0),key=key,check=lambda:None,audit_directory=tmp_path,
        guard=SimpleNamespace(active=True,hwnd=589988,pid=16820,reason=None,
            probe=SimpleNamespace(user=SimpleNamespace(GetForegroundWindow=lambda:589988))))
    gui=NativeClockGUI(backend,ROOT/'artifacts/phase5/gate-20261006/final/native-final-physical.png',Templates(TEMPLATES))
    return gui

def test_exact_modal_rgb_saved_before_calibrated_single_escape_recovery(tmp_path):
    single,menu=load(SINGLE),load(MENU)
    inputs=[];gui=native_gui([single,single,menu,menu],tmp_path,inputs)
    t=controller(gui);t.acquire_running_ownership()
    result=t.ensure_game_stopped()
    assert result['paused'] and not t.owns_running and inputs==['Escape']
    file=next(tmp_path.glob('time-failure-*/physical.png'))
    assert np.array_equal(load(file.relative_to(ROOT)) if file.is_relative_to(ROOT) else np.asarray(Image.open(file)),single)
    data=json.loads(file.with_name('failure.json').read_text(encoding='utf-8'))
    assert data['ownership']['owns_running'] and data['reason']=='modal_blocked'
    assert data['hwnd']==data['foreground']==589988 and data['pid']==16820
    assert data['captured_at'] and data['telemetry']['game_date']=='1936-08-03'
    assert all(file.with_name(name+'.png').is_file() for name in ['clock','modal','menu'])
    t.ensure_game_stopped();assert inputs==['Escape']

def test_unknown_modal_has_exact_evidence_and_no_escape_or_space(tmp_path):
    unknown=load(SINGLE).copy();unknown[673:702,1235:1395]=0
    assert NativeModalDetector(Templates(TEMPLATES)).read(unknown)['state']=='UNKNOWN_MODAL'
    inputs=[];gui=native_gui([unknown,unknown],tmp_path,inputs);t=controller(gui);t.acquire_running_ownership()
    assert not t.ensure_game_stopped()['paused'] and t.owns_running and inputs==[]
    assert np.array_equal(np.asarray(Image.open(next(tmp_path.glob('time-failure-*/physical.png')))),unknown)

def test_overlay_stack_is_not_allowed_escape_for_single_research_popup(tmp_path):
    stack=load(STACK);inputs=[];gui=native_gui([stack,stack],tmp_path,inputs)
    t=controller(gui);t.acquire_running_ownership()
    assert not t.ensure_game_stopped()['paused'] and inputs==[] and t.owns_running

@pytest.mark.parametrize('problem',['header','date'])
def test_clock_failure_frame_is_the_trigger_not_a_later_capture(tmp_path,problem):
    rgb=load(NORMAL).copy()
    if problem=='header':rgb[4:31,2237:2262]=0
    else:rgb[9:30,2294:2410]=0
    gui=native_gui([rgb,load(MENU)],tmp_path,[])
    with pytest.raises(ActionError):gui.clock_value()
    image=next(tmp_path.glob('time-failure-*/physical.png'))
    assert np.array_equal(np.asarray(Image.open(image)),rgb)

@pytest.mark.parametrize('can_stop',[False,True])
def test_native_host_shutdown_reports_unsafe_owned_time_and_stops_before_backend_close(can_stop):
    t=controller(GUI(None if can_stop else True));acquire(t)
    host=object.__new__(NativeRuntimeHost);host.time=t
    host.backend=SimpleNamespace(close=lambda:None)
    result=host.close()
    assert result['owns_running']==(not can_stop)
    assert result['shutdown']==('clean_no_owned_time' if can_stop else 'unsafe_stop_failed')
    assert result['operator_intervention_required']==(not can_stop)

def test_circuit_breaker_stops_owned_game_before_clearing_plan(tmp_path):
    from test_agent_runtime import runtime
    rt,_,audit=runtime(tmp_path)
    t=controller(GUI());acquire(t);rt.time_controller=t
    rt.plan=[dict(action='build')]
    rt.pause('uncertain')
    assert t.gui.inputs==['resume','pause'] and rt.status=='AGENT_PAUSED' and rt.plan==[]
    assert not t.owns_running and audit.summary['circuit_breaker']=='uncertain'

def test_native_normal_space_pause_is_one_input_even_on_repeated_stop(tmp_path):
    gui=native_gui([load(NORMAL)],tmp_path,[])
    inputs=[];gui.backend.key=inputs.append
    states=iter([False,True]);gui.is_paused=lambda:next(states)
    t=controller(gui);t.acquire_running_ownership()
    assert t.ensure_game_stopped()['paused']
    t.ensure_game_stopped()
    assert inputs==['space']

def test_circuit_failure_remains_owned_and_explicitly_requires_operator(tmp_path):
    from test_agent_runtime import runtime
    rt,_,audit=runtime(tmp_path)
    t=controller(GUI(True));acquire(t);rt.time_controller=t
    rt.pause('uncertain');rt.close()
    assert t.owns_running and rt.status=='AGENT_PAUSED'
    assert audit.summary['shutdown']=='unsafe_stop_failed' and audit.summary['operator_intervention_required']
    assert t.gui.inputs==['resume']

def test_backend_cleanup_exception_cannot_erase_the_unsafe_shutdown_report():
    t=controller(GUI(True));acquire(t)
    host=object.__new__(NativeRuntimeHost);host.time=t
    def broken():raise OSError('release_failed')
    host.backend=SimpleNamespace(close=broken)
    with pytest.raises(OSError):host.close()
    assert host.shutdown_report['shutdown']=='unsafe_stop_failed' and t.owns_running

def test_guard_blocked_rgb_is_marked_unavailable_not_replaced_by_old_capture(tmp_path):
    gui=native_gui([load(NORMAL)],tmp_path,[])
    gui._capture()
    def blocked():raise ActionError('loss_of_focus')
    gui.backend.capture=blocked
    with pytest.raises(ActionError):gui._capture()
    proof=gui.save_stop_failure('loss_of_focus')
    assert proof['exact_rgb_available'] is False
    assert not list(tmp_path.glob('time-failure-*/physical.png'))

def test_failed_input_never_labels_the_pre_input_frame_as_exact_failure(tmp_path):
    gui=native_gui([load(NORMAL)],tmp_path,[])
    gui.clock_value()
    def failed(_):raise ActionError('loss_of_focus')
    gui.backend.key=failed
    with pytest.raises(ActionError):gui._time_key('space')
    assert not gui.save_stop_failure('loss_of_focus')['exact_rgb_available']

def test_submitted_pause_uncertainty_never_submits_space_twice(tmp_path):
    gui=native_gui([load(NORMAL)],tmp_path,[])
    inputs=[];gui.backend.key=inputs.append
    states=iter([False,ActionError('pause_readback_unknown','uncertain')])
    def paused():
        value=next(states)
        if isinstance(value,Exception):raise value
        return value
    gui.is_paused=paused
    t=controller(gui);t.acquire_running_ownership()
    # Safe fallback observation is guard-blocked: neither Escape nor another Space.
    original=gui.backend.capture
    def capture():
        if inputs:raise ActionError('loss_of_focus')
        return original()
    gui.backend.capture=capture
    assert not t.ensure_game_stopped()['paused'] and t.owns_running
    t.ensure_game_stopped()
    assert inputs==['space']

def test_failure_evidence_io_error_cannot_prevent_safe_stop_and_is_reported():
    g=GUI(ActionError('modal_blocked'),safe=True)
    def denied(_):raise PermissionError('evidence denied')
    g.save_stop_failure=denied
    t=controller(g);acquire(t)
    result=t.ensure_game_stopped()
    assert result['paused'] and not t.owns_running and result['failure_evidence_error']=='PermissionError'
