"""After critical gate failure: zero input capture, pause evidence and file hashes."""
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from hoi4_operator.executor.native_runtime import NativeRuntimeHost
from hoi4_operator.telemetry.paths import default_log_path
OUT=Path(__file__).resolve().parent
baseline=json.loads((ROOT/'artifacts/phase5/continuation-20261007/final-state.json').read_text(encoding='utf-8'))
run=json.loads((OUT/'construction-single-1/summary.json').read_text(encoding='utf-8'))
result=dict(pump='OFF',input_count=0,last_fresh_telemetry_date=run['end_date'],
    date_source='fresh telemetry in stopped construction-single run; not a new GUI decoded date',
    benchmark_status='NOT_RUN_AFTER_CONSTRUCTION_FAILURE',model_inference_attempts=0)
host=None
try:
    host=NativeRuntimeHost(589988,default_log_path(),ROOT,OUT/'final-native-audit',
        ROOT/'artifacts/phase5/gate-20261006/final/native-final-physical.png')
    host.backend.begin(8)
    rgb=host.backend.capture()
    Image.fromarray(rgb).save(OUT/'final-physical.png')
    result['geometry']=host.backend.get_window_geometry()
    result['pause_evidence']=host.time.gui.pause_evidence()
    result['paused']=result['pause_evidence']['paused']
except Exception as exc:
    result.update(paused='UNKNOWN',reason=getattr(exc,'reason',type(exc).__name__))
finally:
    if host:
        host.backend.end();host.close()
    original=baseline['files']
    paths={Path(p) for p in original}
    save_folder=next(p.parent for p in paths if p.suffix=='.hoi4')
    paths.update(save_folder.glob('*.hoi4'))
    result['files']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths) if p.is_file()}
    result['changed']=[p for p,h in original.items() if result['files'].get(p)!=h]
    result['added']=sorted(set(result['files'])-set(original))
    result['removed']=sorted(set(original)-set(result['files']))
    manuals=[p for p in original if Path(p).suffix=='.hoi4' and 'autosave' not in Path(p).name.lower()]
    result['manual_save_count']=len(manuals)
    result['manual_saves_unchanged']=all(result['files'].get(p)==original[p] for p in manuals)
    mod=next(p for p in original if Path(p).name=='dlc_load.json')
    result['mod_selection_unchanged']=result['files'].get(mod)==original[mod]
    (OUT/'final-state.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='files'},ensure_ascii=False))
