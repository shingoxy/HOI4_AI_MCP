from PIL import Image
import numpy as n
p='artifacts/phase5/gate-20261006/captures/'
ms=[]
for f in ['offensive-empty-native.png','front-present-native.png']:
 c=n.asarray(Image.open(p+f)).astype(n.int16);r,g,b=c[:,:,0],c[:,:,1],c[:,:,2]
 ms.append((r>130)&(g>100)&(r-b>10)&(g-b>15))
for xa,xb,ya,yb in [(2030,2150,630,710),(1810,1940,780,900),(2100,2240,1130,1210)]:
 candidates=[]
 for x in range(xa,xb,10):
  for y in range(ya,yb,10):
   on=int(ms[0][y:y+80,x:x+80].sum()); off=int(ms[1][y:y+80,x:x+80].sum())
   if off<10:candidates.append((on,off,(x,y,x+80,y+80)))
 print(max(candidates))
