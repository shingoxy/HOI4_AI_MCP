"""Native time safety only. No Agent decisions or strategic mutation."""
import json
from pathlib import Path
import sys
import threading
from uuid import uuid4

from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from hoi4_operator.executor.native_runtime import NativeRuntimeHost
from hoi4_operator.telemetry.paths import default_log_path

mode=sys.argv[1]
if mode not in {'A','B','baseline'}:raise ValueError('unsupported gate')
OUT=Path(__file__).resolve().parent/('live-'+mode+'-1')
OUT.mkdir(exist_ok=False)
host=None;timer=None
result=dict(run_id=str(uuid4()),gate=mode,pump='OFF',backend='WindowsNativeBackend',
    capture='GDI_BitBlt_RGB_PHYSICAL',input='SendInput',semantic_mutations=0,
    agent_decisions=0,model_calls=0,status='FAILED')
try:
    host=NativeRuntimeHost(589988,default_log_path(),ROOT,OUT/'native-audit',
        ROOT/'artifacts/phase5/gate-20261006/final/native-final-physical.png')
    b,t=host.backend,host.time
    b.begin(12)
    rgb=t.gui._capture();Image.fromarray(rgb).save(OUT/'before.png')
    result['geometry']=b.get_window_geometry()
    result['initial_modal']=t.gui.modals.read(rgb)
    if mode=='baseline':
        if result['initial_modal']['state']!='KNOWN_SAFE_MODAL':raise RuntimeError('known_menu_required')
    else:
        if result['initial_modal']['state']!='NO_MODAL' or not t.gui.is_paused():
            raise RuntimeError('paused_modal_free_start_required')
        if host.construction.ui.map_state.inspect(rgb)['state']!='MAP_READY':
            raise RuntimeError('calibrated_germany_map_required')
    host.model.poll();result['initial_telemetry']=host.model.summary()
    b.end()
    if mode=='A':
        result['advance']=t.advance_days(1)
        if (result['advance']['status']!='confirmed' or result['advance'].get('stop',{}).get('reason')!='normal_pause_confirmed'
                or not result['advance']['paused'] or t.owns_running):
            raise RuntimeError('normal_bootstrap_not_confirmed')
    else:
        b.begin(14)
        t.acquire_running_ownership()
        timer=threading.Timer(8,t.ensure_game_stopped);timer.start()  # Exists before potential resume.
        if mode=='B':
            t.gui.resume()
            result['running_ownership']=t.contract()
            current=t.gui._capture()
            if (t.gui.modals.read(current)['state']!='NO_MODAL' or
                    host.construction.ui.map_state.inspect(current)['state']!='MAP_READY'):
                raise RuntimeError('controlled_menu_route_not_ready')
            # Controlled known modal, solely to stop time; no popup acknowledgement.
            t.gui._time_key('Escape')
            b._record('controlled_gate_modal',route='single Escape to known menu; Time Gate B only')
        else:
            # Menu exit may resume its underlying clock. Own it BEFORE this input.
            if t.gui.modals.read(t.gui._capture())['state']!='KNOWN_SAFE_MODAL':
                raise RuntimeError('baseline_menu_changed')
            t.gui._time_key('Escape')
            b._record('baseline_menu_exit',possible_resume_owned=True)
        rgb=t.gui._capture();Image.fromarray(rgb).save(OUT/'controlled.png')
        result['controlled_modal']=t.gui.modals.read(rgb)
        result['ownership_before_stop']=t.contract()
        result['stop']=t.ensure_game_stopped()
        if not result['stop']['paused'] or t.owns_running:raise RuntimeError('stop_not_confirmed')
        if mode=='B':
            if (result['controlled_modal']['state']!='KNOWN_SAFE_MODAL' or t.metrics['pause_failures']!=1
                    or t.metrics['safe_stop_successes']!=1):raise RuntimeError('modal_stop_branch_not_exercised')
        timer.cancel();timer.join(timeout=1);timer=None
        b.end()
        if mode=='baseline' and host.model.summary()['status']!='fresh':
            result['fresh_bootstrap']=t.advance_days(1)
            if result['fresh_bootstrap']['status']!='confirmed':raise RuntimeError('baseline_bootstrap_failed')
    b.begin(8)
    rgb=t.gui._capture();Image.fromarray(rgb).save(OUT/'after.png')
    result['pause_proof']=t.gui.pause_evidence()
    result['final_modal']=t.gui.modals.read(rgb)
    host.model.poll();result['final_telemetry']=host.model.summary()
    if not result['pause_proof']['paused'] or t.owns_running:raise RuntimeError('final_pause_not_confirmed')
    if mode=='baseline' and (result['final_modal']['state']!='NO_MODAL' or
            result['final_telemetry']['status']!='fresh' or result['final_telemetry']['freshness_basis']!='frame_received_at'):
        raise RuntimeError('fresh_modal_free_baseline_not_confirmed')
    b.end()
    result['status']='PASSED'
except Exception as exc:
    result['reason']=getattr(exc,'reason',str(exc) or type(exc).__name__)
finally:
    if timer:timer.cancel();timer.join(timeout=1)
    if host:
        # Immediate independent stop before logging/report work on every exit.
        result['shutdown']=host.close()
        result['time_metrics']=dict(host.time.metrics)
        if host.time.owns_running or host.time.contract()['failure_evidence_error']:
            result.update(status='FAILED',operator_intervention_required=host.time.owns_running)
    (OUT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in {'initial_telemetry','final_telemetry','geometry'}},ensure_ascii=False))
    if result['status']!='PASSED':raise SystemExit(2)
