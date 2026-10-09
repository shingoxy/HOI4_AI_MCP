"""Read-only checkpoint after failed bootstrap; preserves all historic evidence."""
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from hoi4_operator.executor.native_runtime import NativeRuntimeHost
from hoi4_operator.executor.native_construction_tool import NativeConstructionTool
from hoi4_operator.telemetry.paths import default_log_path

OUT=Path(__file__).resolve().parent/'final-readonly-2'
OUT.mkdir(exist_ok=False)
baseline=json.loads((ROOT/'artifacts/phase5/stability-20261007/final-state.json').read_text(encoding='utf-8'))
host=NativeRuntimeHost(589988,default_log_path(),ROOT,OUT/'final-native-audit',
    ROOT/'artifacts/phase5/gate-20261006/final/native-final-physical.png')
result=dict(pump='OFF',input_count=0,real_model_calls=0,new30='NOT_RUN',
            construction_mutations=0,gui_date_status='UNKNOWN',gui_date=None)
try:
    host.backend.begin(8)
    rgb=host.backend.capture();Image.fromarray(rgb).save(OUT/'final-physical.png')
    result['geometry']=host.backend.get_window_geometry()
    result['map']=host.construction.ui.map_state.inspect(rgb)
    result['modals']={name:NativeConstructionTool.match(rgb,host.time.gui.templates,name,box) for name,box in
        {'clock_menu':(1230,585,1330,620),'world_news':(1050,490,1510,580),
         'focus_completed_popup':(1240,655,1380,710)}.items()}
    try: result['pause_evidence']=host.time.gui.pause_evidence()
    except Exception as exc: result['pause_evidence']=dict(paused='UNKNOWN',reason=getattr(exc,'reason',type(exc).__name__))
    result['paused']=result['pause_evidence']['paused']
    host.model.poll()
    result['read_only_telemetry']=host.model.summary()
except Exception as exc: result['error']=getattr(exc,'reason',type(exc).__name__)
finally:
    host.backend.end();host.close()
    original=baseline['files'];paths={Path(p) for p in original}
    folder=next(p.parent for p in paths if p.suffix=='.hoi4')
    paths.update(folder.glob('*.hoi4'))
    result['files']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths) if p.is_file()}
    result['changed']=[p for p,h in original.items() if result['files'].get(p)!=h]
    result['added']=sorted(set(result['files'])-set(original));result['removed']=sorted(set(original)-set(result['files']))
    manuals=[p for p in original if Path(p).suffix=='.hoi4' and 'autosave' not in Path(p).name.lower()]
    result['manual_save_count']=len(manuals)
    result['manual_saves_unchanged']=all(result['files'].get(p)==original[p] for p in manuals)
    result['mod_selection_unchanged']=all(result['files'].get(p)==h for p,h in original.items() if Path(p).name=='dlc_load.json')
    (OUT/'final-state.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='files'},ensure_ascii=False))
