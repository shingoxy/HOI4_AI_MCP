"""Live repaired tool navigation gate, zero semantic mutation and no target click."""
import json
from pathlib import Path
import sys
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from hoi4_operator.executor.native_runtime import NativeRuntimeHost
from hoi4_operator.telemetry.paths import default_log_path

OUT=Path(__file__).resolve().parent/'selector-native-1'
OUT.mkdir(exist_ok=False)
host=NativeRuntimeHost(589988,default_log_path(),ROOT,OUT/'native-audit',
    ROOT/'artifacts/phase5/gate-20261006/final/native-final-physical.png')
ui,b=host.construction.ui,host.backend
result=dict(pump='OFF',mutation_submitted=False,role='tool_navigation_revalidation')
try:
    b.begin(40);b.capture()
    if not host.time.gui.is_paused(): raise RuntimeError('not_paused')
    result['target']=ui.prepare_target_readiness()
    reference=b.capture();view=ui.map_state.require(reference)
    Image.fromarray(reference).save(OUT/'map-reference.png')
    rgb=ui.open();result['queue_before']=ui.read(rgb)['queue']
    if result['queue_before']!=[]: raise RuntimeError('already_satisfied')
    rgb=ui.select_native_tool(rgb,ui.layout['building_points']['civilian_factory'])
    result['tool']=ui.tool_reader.evidence
    result['map']=ui.map_state.require(rgb,same=view,construction_panel=True,reference=reference)
    result['queue_after']=ui.read(rgb)['queue']
    if result['queue_after']!=result['queue_before']: raise RuntimeError('queue_changed_during_navigation')
    result['status']='TOOL_NAVIGATION_CONFIRMED'
except Exception as exc:
    result.update(status='BLOCKED',reason=getattr(exc,'reason',str(exc)),tool=ui.tool_reader.evidence)
finally:
    try:
        ui.close();result['pause_evidence']=host.time.gui.pause_evidence()
    except Exception as exc: result['cleanup_error']=getattr(exc,'reason',str(exc))
    b.end();host.close()
    (OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='tool'}))
    if result.get('status')!='TOOL_NAVIGATION_CONFIRMED': raise SystemExit(2)
