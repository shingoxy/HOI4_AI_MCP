"""Post-stop capture and hashes only; zero game inputs or fresh bootstrap."""
import hashlib
import json
from pathlib import Path
import sys
import cv2
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from hoi4_operator.executor.native_runtime import NativeRuntimeHost
from hoi4_operator.executor.native_calibration import ANCHORS
from hoi4_operator.executor.templates import Templates
from hoi4_operator.telemetry.paths import default_log_path

baseline=json.loads((ROOT/'artifacts/phase5/reader-20261006/final-state.json').read_text(encoding='utf-8'))
run=json.loads((OUT/'scripted-days30-1/summary.json').read_text(encoding='utf-8'))
result=dict(pump='OFF',input_count=0,last_confirmed_date=run['end_date'],
    date_source='fresh final observation in stopped days30 run; no new freshness claim',
    benchmark_status=run['status'],benchmark_game_days=run['game_days'],native_anchor_probe={})
host=None
try:
    host=NativeRuntimeHost(589988,default_log_path(),ROOT,OUT/'final-native-audit',
        ROOT/'artifacts/phase5/gate-20261006/final/native-final-physical.png')
    host.backend.begin(8)
    rgb=host.backend.capture()
    Image.fromarray(rgb).save(OUT/'final-physical.png')
    templates=Templates(ROOT/'artifacts/phase5/templates/map')
    for name,box in {**{'map_anchor_'+n:(b[0]-1,b[1]-1,b[2]+1,b[3]+1) for n,b in ANCHORS.items()},
                     'land_mode':(2494,1400,2526,1431)}.items():
        point=templates.find(rgb,name,box,.9)
        template=templates.cache.get(name)
        x,y,X,Y=box
        score=float(cv2.matchTemplate(rgb[y:Y,x:X],template,cv2.TM_CCOEFF_NORMED).max())
        result['native_anchor_probe'][name]=dict(matched=point is not None,score=score,threshold=.9)
    result['probe_scope']='Post-recovery map capture, not the exact failed build frame; no target click.'
    result['paused']=host.time.gui.is_paused()
    result['capture_profile']=host.backend.capture_profile.name
except Exception as exc:
    result.update(paused='UNKNOWN',blocker=getattr(exc,'reason',type(exc).__name__))
finally:
    if host: host.close()
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
    result['save_mutation_by_operator']=False
    (OUT/'final-state.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='files'},ensure_ascii=False))
