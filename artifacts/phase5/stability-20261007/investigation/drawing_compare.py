import sys,json,cv2,numpy as np
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'src'))
from hoi4_operator.executor.native_map_state import NativeMapState
from hoi4_operator.executor.templates import Templates
from types import SimpleNamespace
HERE=Path(__file__).resolve().parent
r=NativeMapState(SimpleNamespace(),Templates(ROOT/'artifacts/phase5/templates/map'))
result={}
for filename in ['drawing-before.png','drawing-selected.png','drawing-closed.png']:
    if not (HERE/filename).is_file(): continue
    rgb=np.asarray(Image.open(HERE/filename).convert('RGB'))
    data=dict(inspect=r.inspect(rgb),scores={})
    for name,box in r.manifest['anchor_boxes'].items():
        x,y,X,Y=box
        data['scores'][name]=[]
        for v in r.manifest['variants']:
            t=np.asarray(Image.open(r.home.directory/f'{name}_{v}.png').convert('RGB'))
            _,score,_,loc=cv2.minMaxLoc(cv2.matchTemplate(rgb[y:Y,x:X],t,cv2.TM_CCOEFF_NORMED))
            data['scores'][name].append(dict(variant=v,score=score,center=[x+loc[0]+t.shape[1]//2,y+loc[1]+t.shape[0]//2]))
    data['land_mode']=r.templates.find(rgb,'land_mode',(2494,1400,2526,1431),.9)
    data['panel']=Templates(ROOT/'artifacts/phase3/templates').find(rgb,'construction_title',(20,83,150,124),.9)
    result[filename]=data
(HERE/'drawing-comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
