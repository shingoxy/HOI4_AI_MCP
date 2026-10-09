import sys
from pathlib import Path
sys.path.insert(0, 'src')
import numpy as np
from PIL import Image
from hoi4_operator.executor.production_lines_ui import ProductionLinesUI
from hoi4_operator.executor.production_ui import HEADER_BOX
from hoi4_operator.executor.production_ui import text_mask
import cv2
from hoi4_operator.executor.non_military_layout import production_boxes
from hoi4_operator.executor.templates import Templates
from hoi4_operator.executor.guard import ActionError
from types import SimpleNamespace
from hoi4_operator.executor.windows_native import PHYSICAL_PROFILE
u = ProductionLinesUI(SimpleNamespace(worker=SimpleNamespace(capture_profile=PHYSICAL_PROFILE)),
    Templates(Path('artifacts/phase3/templates')), Path('artifacts/phase5/templates/production'))
r = np.asarray(Image.open(Path(__file__).parent/'captures/production-compact.png'))
tops = u.row_tops(r)
print('tops', tops)
for name, box in [('mil', HEADER_BOX), ('dock',(397,215,441,236))]:
    x0,y0,x1,y1=box
    patch=r[y0:y1,x0:x1]
    mask=text_mask(patch, True)
    edges=np.diff(np.r_[False,np.any(mask,axis=0),False].astype(np.int8))
    print(name,list(zip(np.where(edges==1)[0].tolist(),np.where(edges==-1)[0].tolist())))
    Image.fromarray(patch).resize((patch.shape[1]*8,patch.shape[0]*8)).save(Path(__file__).parent/f'{name}-header.png')
    Image.fromarray(mask*255).resize((patch.shape[1]*8,patch.shape[0]*8),Image.Resampling.NEAREST).save(Path(__file__).parent/f'{name}-mask.png')
for label, box, header in [('header', HEADER_BOX, True)]+[(str(i), production_boxes(y)['count'], False) for i,y in enumerate(tops)]:
    try:
        print(label, u.number(r, box, header=header))
    except ActionError as e:
        print(label, e.reason)
print(u.read(r))
