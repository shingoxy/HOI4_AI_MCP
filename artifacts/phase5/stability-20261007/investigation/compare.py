"""Offline comparison of actual GDI frames; no inputs or target extrapolation."""
import json
from pathlib import Path
import sys
import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'src'))
from hoi4_operator.executor.native_calibration import ANCHORS

OUT = Path(__file__).resolve().parent
frames = {
    'gate_map': ROOT/'artifacts/phase5/gate-20261006/captures/construction-map-after-close.png',
    'previous_menu': ROOT/'artifacts/phase5/continuation-20261007/final-physical.png',
    **{p.parent.name+'_preflight':p for p in (ROOT/'artifacts/phase5/continuation-20261007').glob('*/preflight.png')},
    **{p.stem:p for p in OUT.glob('*.png') if 'crop' not in p.stem},
}
reference = np.asarray(Image.open(ROOT/'artifacts/phase5/gate-20261006/final/native-final-physical.png').convert('RGB'))
result = {}
for key, path in frames.items():
    rgb = np.asarray(Image.open(path).convert('RGB'))
    item = dict(size=[rgb.shape[1],rgb.shape[0]], anchors={})
    for name, box in {**{'map_anchor_'+k:v for k,v in ANCHORS.items()}, 'land_mode':(2494,1400,2526,1431)}.items():
        t = np.asarray(Image.open(ROOT/'artifacts/phase5/templates/map'/f'{name}.png').convert('RGB'))
        x,y,X,Y = box
        fixed = cv2.matchTemplate(rgb[y-1:Y+1,x-1:X+1], t, cv2.TM_CCOEFF_NORMED)
        _, score, _, loc = cv2.minMaxLoc(cv2.matchTemplate(rgb,t,cv2.TM_CCOEFF_NORMED))
        item['anchors'][name] = dict(fixed_score=float(fixed.max()), global_score=score,
            global_top_left=loc, expected_top_left=[x,y], delta=[loc[0]-x,loc[1]-y], threshold=.9)
    crop = rgb[4:31,2237:2262]
    item['clock_header_mae'] = float(np.abs(crop.astype(float)-reference[4:31,2237:2262]).mean())
    item['clock_header_mae_threshold'] = 8
    t = np.asarray(Image.open(ROOT/'artifacts/phase5/templates/clock_menu.png').convert('RGB'))
    item['menu_score'] = float(cv2.matchTemplate(rgb[585:620,1230:1330],t,cv2.TM_CCOEFF_NORMED).max())
    result[key] = item
(OUT/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
