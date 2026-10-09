"""Measure unchanged feature positions across the real construction overlay."""
from pathlib import Path
import json
import cv2
import numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parent
def load(n): return np.asarray(Image.open(HERE/n).convert('RGB'))
a,b=load('drawing-before.png'),load('drawing-selected.png')
def probe(a,b):
    detector=cv2.SIFT_create(nfeatures=1500)
    ka,da=detector.detectAndCompute(cv2.cvtColor(a[100:1320,750:2420],cv2.COLOR_RGB2GRAY),None)
    kb,db=detector.detectAndCompute(cv2.cvtColor(b[100:1320,750:2420],cv2.COLOR_RGB2GRAY),None)
    pairs=cv2.BFMatcher().knnMatch(da,db,k=2)
    good=[m for m,n in pairs if m.distance < .65*n.distance]
    rows=[dict(point=[ka[m.queryIdx].pt[0]+750,ka[m.queryIdx].pt[1]+100],
        delta=[kb[m.trainIdx].pt[i]-ka[m.queryIdx].pt[i] for i in (0,1)]) for m in good]
    stable=[r for r in rows if max(abs(d) for d in r['delta'])<=1]
    cells=[sum(750+i*1670/3<=r['point'][0]<750+(i+1)*1670/3 for r in stable) for i in range(3)]
    center=sum(1150<=r['point'][0]<=1410 and 650<=r['point'][1]<=970 for r in stable)
    return dict(matches=len(good),stable=len(stable),ratio=len(stable)/max(1,len(good)),cells=cells,center=center)
result=dict(actual=probe(a,b),small_pan=probe(a,np.roll(b,3,axis=1)),wrong_camera=probe(load('current-initial.png'),b))
(HERE/'geometry-probe.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
