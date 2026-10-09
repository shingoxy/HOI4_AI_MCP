from pathlib import Path
import json
import sys
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'src'))
from hoi4_operator.executor.native_map_state import NativeMapState
from hoi4_operator.executor.templates import Templates
from types import SimpleNamespace
HERE=Path(__file__).resolve().parent
r=NativeMapState(SimpleNamespace(),Templates(ROOT/'artifacts/phase5/templates/map'))
for prefix in ['drawing','drawing2','drawing3']:
    before=np.asarray(Image.open(HERE/(prefix+'-before.png')).convert('RGB'))
    after=np.asarray(Image.open(HERE/(prefix+'-selected.png')).convert('RGB'))
    result=dict(geometry=r.drawing_geometry(before,after),normal=r.inspect(before),
        selected=Templates(ROOT/'artifacts/phase3/templates').find(after,'construction_selected_civilian_factory',(497,266,545,314),.9),
        mode=r.home.find(after,'construction_map_mode',(2494,1400,2526,1431),.9))
    print(prefix,json.dumps(result))
