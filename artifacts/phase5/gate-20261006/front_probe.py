from PIL import Image
import numpy as np
from pathlib import Path
p=Path('artifacts/phase5/gate-20261006/captures/front-empty-native.png')
rgb=np.asarray(Image.open(p).convert('RGB')).astype(np.int16)
r,g,b=rgb[:,:,0],rgb[:,:,1],rgb[:,:,2]
m=(r>165)&(r-g>80)&(b-g>25)
ys,xs=np.where(m[350:1325,1610:2510]);print('red pixels',len(xs));print('range',((xs.min()+1610,xs.max()+1610,ys.min()+350,ys.max()+350) if len(xs) else None))
Image.open(p).crop((1600,350,2480,1320)).save(p.with_name('front-empty-map-crop.png'))
Image.open(p).crop((940,1335,1650,1435)).resize((1065,150)).save(p.with_name('front-empty-bar-crop.png'))
