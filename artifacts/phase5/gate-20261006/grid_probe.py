import sys
from pathlib import Path
sys.path.insert(0,'src')
from types import SimpleNamespace
import cv2
import numpy as np
from PIL import Image
from hoi4_operator.executor.production_lines_ui import ProductionLinesUI
from hoi4_operator.executor.templates import Templates
from hoi4_operator.executor.windows_native import PHYSICAL_PROFILE
u=ProductionLinesUI(SimpleNamespace(worker=SimpleNamespace(capture_profile=PHYSICAL_PROFILE)),
    Templates(Path('artifacts/phase3/templates')),Path('artifacts/phase5/templates/production'))
p=Path(__file__).parent/'captures/production-readback-1-production-readback.png'
r=np.asarray(Image.open(p).convert('RGB'))
print('count',u.number(r,(412,377,460,399)))
for row in range(3):
    for col in range(5):
        x,y=338+29*col,416+22*row
        box=(x-12,y-10,x+13,y+10)
        on=any(u.found(r,n,box,.85) for n in ('production_grid_on','production_grid_assigned_alternate'))
        print(row,col,'on',on,'max',int(r[y-5:y+6,x-7:x+8].max()))
