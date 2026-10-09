import sys
from pathlib import Path
sys.path.insert(0,'src')
import cv2
import numpy as np
from PIL import Image
from hoi4_operator.executor.native_calibration import ANCHORS
for filename in ('map-zoom-out-3.png','focus-notification-closed.png','construction-map-after-close.png'):
    r=np.asarray(Image.open(Path(__file__).parent/'captures'/filename).convert('RGB'))
    print(filename)
    for name,box in {**{('map_anchor_'+k):v for k,v in ANCHORS.items()},'land_mode':(2494,1400,2526,1431)}.items():
        t=np.asarray(Image.open(Path('artifacts/phase5/templates/map')/(name+'.png')).convert('RGB'))
        x0,y0,x1,y1=box
        print(name,float(cv2.matchTemplate(r[y0:y1,x0:x1],t,cv2.TM_CCOEFF_NORMED).max()))
        scores=cv2.matchTemplate(r[max(0,y0-12):y1+12,max(0,x0-12):x1+12],t,cv2.TM_CCOEFF_NORMED)
        _,score,_,loc=cv2.minMaxLoc(scores)
        print('local',score,tuple(v-12 for v in loc))
