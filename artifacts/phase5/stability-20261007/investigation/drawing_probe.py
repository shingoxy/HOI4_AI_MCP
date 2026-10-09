"""Construction tool navigation only, inspect the last pre-submit camera; no build."""
import json
from pathlib import Path
import sys
from PIL import Image
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'src'))
from hoi4_operator.executor.native_runtime import NativeRuntimeHost
from hoi4_operator.telemetry.paths import default_log_path
OUT=Path(__file__).resolve().parent
prefix=sys.argv[1] if len(sys.argv)>1 else 'drawing'
host=NativeRuntimeHost(589988,default_log_path(),ROOT,OUT/(prefix+'-audit'),
    ROOT/'artifacts/phase5/gate-20261006/final/native-final-physical.png')
ui=host.construction.ui;b=host.backend
result=dict(pump='OFF',semantic_mutations=0,role='GUI_map_calibration')
try:
    b.begin(16)
    rgb=b.capture()
    view=ui.map_state.require(rgb)
    point,geometry=b._point((900,100));b._move(point,geometry);b._settle(1)
    rgb=b.capture()
    Image.fromarray(rgb).save(OUT/(prefix+'-before.png'))
    before=ui.read(ui.open())
    if before['queue']!=[]: raise RuntimeError('queue_not_empty')
    rgb=ui.ui.capture()
    if (not ui.found(rgb,'construction_selected_civilian_factory',(497,266,545,314),.9) or
            not ui.map_state.home.find(rgb,'construction_map_mode',(2494,1400,2526,1431),.9)):
        b.click(ui.layout['building_points']['civilian_factory']);b.capture()
        ui.map_state.wait(1)
    b.click(ui.layout['neutral']);rgb=b.capture()
    ui.map_state.wait(1);rgb=b.capture()
    Image.fromarray(rgb).save(OUT/(prefix+'-selected.png'))
    result['selected']=bool(ui.found(rgb,'construction_selected_civilian_factory',(497,266,545,314),.9))
    reference=__import__('numpy').asarray(Image.open(OUT/(prefix+'-before.png')).convert('RGB'))
    result['map_readiness']=ui.map_state.require(rgb,same=view,construction_panel=True,reference=reference)
    result['queue_after_selection']=ui.read(rgb)['queue']
    ui.close()
    Image.fromarray(b.capture()).save(OUT/(prefix+'-closed.png'))
    result['paused']=host.time.gui.is_paused()
    result['status']='confirmed'
except Exception as exc:
    result.update(status='blocked',reason=getattr(exc,'reason',type(exc).__name__))
    try: ui.close()
    except Exception: pass
finally:
    b.end();host.close()
    (OUT/(prefix+'-probe.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
