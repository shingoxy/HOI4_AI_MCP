"""Bounded GUI-only home/zoom calibration experiment, zero strategic mutations."""
import json
from pathlib import Path
import sys
from PIL import Image
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'src'))
from hoi4_operator.executor.guard import WindowsProbe
from hoi4_operator.executor.windows_native import WindowsNativeBackend
OUT=Path(__file__).resolve().parent
p=WindowsProbe()
b=WindowsNativeBackend(589988,p.pid(589988),probe=p,audit_directory=OUT/'home-sequence-audit')
try:
    b.begin(22)
    b.capture()
    b.click((2540,1378))
    Image.fromarray(b.capture()).save(OUT/'home-sequence-find.png')
    b.click((2488,1334))
    Image.fromarray(b.capture()).save(OUT/'home-sequence-capital.png')
    b.click((2535,1085))
    b.capture()
    for index in range(1,7):
        b.scroll((1280,800),120)
        Image.fromarray(b.capture()).save(OUT/f'home-step-{index}.png')
    print(json.dumps(dict(pump='OFF',semantic_mutations=0,home_clicks=1,scrolls=6,delta_each=120)))
finally:
    b.close()
