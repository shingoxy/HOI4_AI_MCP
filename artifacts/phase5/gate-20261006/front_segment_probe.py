import sys,cv2,numpy as np
from pathlib import Path
from PIL import Image
sys.path.insert(0,'src')
from hoi4_operator.executor.native_military_ui import FRONT_SEGMENTS
from hoi4_operator.executor.templates import Templates
p=Path('artifacts/phase5/gate-20261006/captures')
t=Templates(Path('artifacts/phase5/templates/military'))
for f in ['front-empty-native.png','front-empty-reobserved.png']:
 rgb=np.asarray(Image.open(p/f).convert('RGB')); print(f)
 for i,box in enumerate(FRONT_SEGMENTS):
  x0,y0,x1,y1=box;c=rgb[y0:y1,x0:x1].astype(np.int16); r,g,b=c[:,:,0],c[:,:,1],c[:,:,2]
  yellow=(r>150)&(g>140)&(b<120)&(abs(r-g)<70)
  red=(r>165)&(r-g>80)&(b-g>25)
  print(i,t.find(rgb,f'front_empty_{i}',box,.92),'yellow',yellow.sum(),'red',red.sum())
