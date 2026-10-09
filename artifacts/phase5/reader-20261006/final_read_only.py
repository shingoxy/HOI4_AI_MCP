"""Capture/pause inspection and protected-file hashes, with no injected input."""
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'src'))
from hoi4_operator.executor.native_runtime import NativeRuntimeHost
from hoi4_operator.telemetry.paths import default_log_path

OUT = Path(__file__).resolve().parent
original = json.loads((ROOT/'artifacts/phase5/runtime-20261006/final-state.json').read_text(encoding='utf-8'))
run = json.loads((OUT/'scripted-single-2/summary.json').read_text(encoding='utf-8'))
state = dict(pump='OFF', input_count=0, last_confirmed_date=run['end_date'],
             date_source='fresh normalized telemetry in scripted-single-2; not a new fresh telemetry claim',
             production_count=12, production_source='live-read-5 and native strategic getter in scripted-single-2',
             original_status='uncertain')
host = None
try:
    host = NativeRuntimeHost(589988, default_log_path(), ROOT, OUT/'final-native-audit',
        ROOT/'artifacts/phase5/gate-20261006/final/native-final-physical.png')
    host.backend.begin(8)
    Image.fromarray(host.backend.capture()).save(OUT/'final-physical.png')
    state['paused'] = host.time.gui.is_paused()
    state['capture_profile'] = host.backend.capture_profile.name
except Exception as exc:
    state.update(paused='UNKNOWN', blocker=getattr(exc,'reason',type(exc).__name__))
finally:
    if host: host.close()
    files = {Path(p) for p in original['files']}
    save_folder = next(p.parent for p in files if p.suffix == '.hoi4')
    files.update(save_folder.glob('*.hoi4'))
    state['files'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files) if p.is_file()}
    state['changed'] = [p for p,h in original['files'].items() if p in state['files'] and state['files'][p] != h]
    state['added'] = sorted(set(state['files'])-set(original['files']))
    state['removed'] = sorted(set(original['files'])-set(state['files']))
    (OUT/'final-state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in state.items() if k!='files'},ensure_ascii=False))
