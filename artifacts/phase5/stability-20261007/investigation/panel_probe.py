"""Authorized guarded navigation only: compare actual construction open/close."""
import json
from pathlib import Path
import sys
from PIL import Image
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'src'))
from hoi4_operator.executor.native_runtime import NativeRuntimeHost
from hoi4_operator.telemetry.paths import default_log_path
OUT=Path(__file__).resolve().parent
host=NativeRuntimeHost(589988,default_log_path(),ROOT,OUT/'panel-audit',
    ROOT/'artifacts/phase5/gate-20261006/final/native-final-physical.png')
result=dict(pump='OFF',semantic_mutations=0,scope='construction navigation and pause evidence only')
try:
    host.backend.begin(14)
    Image.fromarray(host.backend.capture()).save(OUT/'panel-before.png')
    result['paused_before']=host.time.gui.is_paused()
    if not result['paused_before']: raise RuntimeError('requires_paused_start')
    rgb=host.construction.ui.open()
    Image.fromarray(rgb).save(OUT/'panel-open.png')
    result['construction']=host.construction.ui.read(rgb)
    host.construction.ui.close()
    Image.fromarray(host.backend.capture()).save(OUT/'panel-closed.png')
    result['paused_after']=host.time.gui.is_paused()
    result['status']='confirmed'
except Exception as exc:
    result.update(status='blocked',reason=getattr(exc,'reason',type(exc).__name__))
finally:
    host.backend.end()
    host.close()
    (OUT/'panel-probe.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
