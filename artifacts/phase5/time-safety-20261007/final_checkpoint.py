"""Zero-input observation after the failed gate; never resumes or clears a popup."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from hoi4_operator.executor.native_runtime import NativeRuntimeHost
from hoi4_operator.telemetry.paths import default_log_path

OUT=Path(__file__).resolve().parent/sys.argv[1]
OUT.mkdir(exist_ok=False)
baseline=json.loads((ROOT/'artifacts/phase5/tool-20261007/final-readonly-2/final-state.json').read_text(encoding='utf-8'))
host=None
result=dict(role='read_only_safety_checkpoint',pump='OFF',input_count=0,semantic_mutations=0,
    real_model_calls=0,gui_date_status='UNKNOWN',gui_date=None,paused='UNKNOWN',
    original_failed_run='c6d10d44-d4f7-4916-8475-e08f81041d35',
    original_shutdown='unsafe_stop_failed',original_ownership='STOP_FAILED_OWNED',
    original_gate_result_unchanged=True)
try:
    host=NativeRuntimeHost(589988,default_log_path(),ROOT,OUT/'native-audit',
        ROOT/'artifacts/phase5/gate-20261006/final/native-final-physical.png')
    host.backend.begin(8)
    result['capture_started_at']=datetime.now(timezone.utc).isoformat()
    rgb=host.time.gui._capture();Image.fromarray(rgb).save(OUT/'physical.png')
    result['capture_finished_at']=datetime.now(timezone.utc).isoformat()
    result['geometry']=host.backend.get_window_geometry()
    result['modal']=host.time.gui.modals.read(rgb)
    result['map']=host.construction.ui.map_state.inspect(rgb)
    if result['modal']['state'] in {'NO_MODAL','KNOWN_SAFE_MODAL'}:
        result['pause_evidence']=host.time.gui.pause_evidence()
        result['paused']=result['pause_evidence']['paused']
    else:result['pause_evidence']=dict(paused='UNKNOWN',reason='modal_blocked')
    host.model.poll();result['read_only_telemetry']=host.model.summary()
except Exception as exc:result['error']=getattr(exc,'reason',type(exc).__name__)
finally:
    if host:
        host.backend.end();host.close()  # This read-only host never acquires running ownership.
    original=baseline['files'];paths={Path(p) for p in original}
    folder=next(p.parent for p in paths if p.suffix=='.hoi4')
    paths.update(folder.glob('*.hoi4'))
    result['files']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths) if p.is_file()}
    result['changed']=[p for p,h in original.items() if result['files'].get(p)!=h]
    result['added']=sorted(set(result['files'])-set(original))
    result['removed']=sorted(set(original)-set(result['files']))
    manuals=[p for p in original if Path(p).suffix=='.hoi4' and 'autosave' not in Path(p).name.lower()]
    result['manual_save_count']=len(manuals)
    result['manual_saves_unchanged']=all(result['files'].get(p)==original[p] for p in manuals)
    result['mod_selection_unchanged']=all(result['files'].get(p)==h for p,h in original.items() if Path(p).name=='dlc_load.json')
    result['current_pause_confirmed']=result['paused'] is True
    result['operator_intervention_still_required']=not result['current_pause_confirmed']
    (OUT/'final-state.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in {'files','geometry'}},ensure_ascii=False))
