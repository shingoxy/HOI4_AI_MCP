"""Calibrate only the observed Germany capital camera range, from actual GDI."""
import json
from pathlib import Path
import sys
import cv2
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'src'))
from hoi4_operator.executor.native_calibration import ANCHORS, PROFILE
OUT=ROOT/'artifacts/phase5/templates/map_home'
OUT.mkdir(exist_ok=True)
HERE=Path(__file__).resolve().parent
samples=[]
positions={n:[] for n in ANCHORS}
for number in range(1,5):
    proof=json.loads((HERE/f'canonical-{number}.json').read_text())
    assert proof['state64_identity'] and proof['paused'] and proof['strategic_mutations']==0
    path=HERE/f'canonical-{number}-map.png'
    rgb=np.asarray(Image.open(path).convert('RGB'))
    sample=dict(source=str(path.relative_to(ROOT)),identity_proof=str((HERE/f'canonical-{number}.json').relative_to(ROOT)),anchors={})
    for name,old_box in ANCHORS.items():
        t=np.asarray(Image.open(ROOT/'artifacts/phase5/templates/map'/f'map_anchor_{name}.png').convert('RGB'))
        _,score,_,(x,y)=cv2.minMaxLoc(cv2.matchTemplate(rgb,t,cv2.TM_CCOEFF_NORMED))
        h,w=t.shape[:2]
        box=[x,y,x+w,y+h]
        Image.fromarray(rgb[y:y+h,x:x+w]).save(OUT/f'{name}_{number}.png')
        positions[name].append(box)
        sample['anchors'][name]=dict(box=box,historical_template_score=score,
            identity_source='actual Chinese city label, visually inspected; unchanged NCC .9 for new templates')
    samples.append(sample)
boxes={name:[min(b[0] for b in bs)-1,min(b[1] for b in bs)-1,
                  max(b[2] for b in bs)+1,max(b[3] for b in bs)+1] for name,bs in positions.items()}
for name,path,box in [
    ('find_entry',HERE/'current-initial.png',(2520,1359,2557,1390)),
    ('find_header',HERE/'find-view.png',(2283,1063,2319,1110)),
    ('home_button',HERE/'find-view.png',(2435,1326,2537,1345)),
    ('country_ger',HERE/'current-initial.png',(8,10,87,70)),
]:
    Image.open(path).convert('RGB').crop(box).save(OUT/f'{name}.png')
manifest=dict(status='LIVE_NAVIGATION_CALIBRATED',capture_profile=PROFILE,scope='Germany1936 capital only; state64; observed home camera range only',
    threshold=.9,anchor_boxes=boxes,variants=[1,2,3,4],state_point=[1280,800],
    navigation=dict(find_entry=[2540,1378],home_button=[2488,1334],close='park pointer then Escape',
        wheel_point=[1280,800],wheel_delta=120,wheel_events=5),
    samples=samples,exact_pixel_recovery=False,requires_independent_state_identity=True,
    requires_same_anchor_pose_before_commit=True)
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(dict(anchor_boxes=boxes,status=manifest['status'],scope=manifest['scope'])))
