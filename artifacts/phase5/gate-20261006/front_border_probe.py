from PIL import Image
import numpy as np
from pathlib import Path
p=Path('artifacts/phase5/gate-20261006/captures'); prev=np.asarray(Image.open(p/'front-preview-native.png')).astype(np.int16); empty=np.asarray(Image.open(p/'front-empty-native.png')).astype(np.int16)
r,g,b=prev[:,:,0],prev[:,:,1],prev[:,:,2];green=(g>180)&(g-r>60)&(g-b>50)
for ya,yb in [(570,670),(770,880),(960,1040)]:
 for x in range(1700,2050,10):
  for y in range(ya,yb,10):
   a=green[y:y+40,x:x+40].sum()
   if a>100:
    c=empty[y:y+40,x:x+40];r,g,b=c[:,:,0],c[:,:,1],c[:,:,2];m=(r>130)&(g>125)&(r-b>20)&(g-b>20)&(abs(r-g)<50)
    print((x,y,x+40,y+40),int(a),int(m.sum()));break
  else:continue
  break
