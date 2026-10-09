import sys
from pathlib import Path
sys.path.insert(0,'src')
from types import SimpleNamespace
from PIL import Image
import numpy as np
from hoi4_operator.executor.native_military_ui import NativeMilitaryUI
from hoi4_operator.executor.windows_native import PHYSICAL_PROFILE
from hoi4_operator.executor.templates import Templates
from hoi4_operator.executor.guard import ActionError
from hoi4_operator.executor.production_ui import text_mask
import cv2
u=NativeMilitaryUI(SimpleNamespace(worker=SimpleNamespace(capture_profile=PHYSICAL_PROFILE)),
    Templates(Path('artifacts/phase4/templates')),Templates(Path('artifacts/phase5/templates/military')))
r=np.asarray(Image.open(Path(__file__).parent/'captures/army-one-native.png').convert('RGB'))
for name,box in [('army_title',(60,85,145,110)),('army_no_general',(62,125,200,153)),
                 ('army_count_1_no_general',(320,87,396,113)),('army_extra_plus',(1320,970,1390,1050)),
                 ('division_infantry_1',(180,240,344,272))]:
    print(name,u.found(r,name,box,.85))
try: print(u.read_army(r))
except ActionError as e: print(e.reason)
try: print('numeric',u.counter.number(r,(347,94,369,109)))
except ActionError as e: print('numeric',e.reason)
for name,a in [('observed',r[94:109,347:369]),
               ('legacy1',np.asarray(Image.open('artifacts/phase4/templates/army_count_1.png').convert('RGB'))),
               ('legacy2',np.asarray(Image.open('artifacts/phase4/templates/army_count_2.png').convert('RGB')))]:
    m=text_mask(a)
    edges=np.diff(np.r_[False,np.any(m,axis=0),False].astype(np.int8))
    pieces=list(zip(np.where(edges==1)[0],np.where(edges==-1)[0]))
    print(name,[(int(x),int(y)) for x,y in pieces])
    Image.fromarray(m*255).resize((m.shape[1]*8,m.shape[0]*8)).save(Path(__file__).parent/(name+'-army-mask.png'))
