"""Exact native Construction navigation diagnostics; never click a build target."""
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
from hoi4_operator.executor.native_runtime import NativeRuntimeHost
from hoi4_operator.telemetry.paths import default_log_path

OUT = Path(__file__).resolve().parent / sys.argv[1]
OUT.mkdir(exist_ok=False)
tool = sys.argv[2] if len(sys.argv)>2 else 'civilian_factory'
if tool not in {'civilian_factory','military_factory'}:
    raise ValueError('unsupported diagnostic tool')
host = NativeRuntimeHost(589988, default_log_path(), ROOT, OUT/'native-audit',
    ROOT/'artifacts/phase5/gate-20261006/final/native-final-physical.png')
ui, b = host.construction.ui, host.backend
result = dict(role='tool_navigation_diagnostic', pump='OFF', mutation_submitted=False,
              tool_clicks=0, requested_tool=tool, frames=[])
started = time.monotonic()

def score(rgb, templates, name, box):
    templates.find(rgb, name, box, .9)
    template = templates.cache.get(name)
    if template is None:
        return None
    x0,y0,x1,y1 = box
    crop = rgb[y0:y1,x0:x1]
    if min(crop.shape[:2]) < min(template.shape[:2]):
        return None
    _, value, _, location = cv2.minMaxLoc(cv2.matchTemplate(crop,template,cv2.TM_CCOEFF_NORMED))
    return dict(score=value, location=[x0+location[0],y0+location[1]])

def save(stage, rgb):
    Image.fromarray(rgb).save(OUT/(stage+'.png'))
    Image.fromarray(rgb[266:314,497:545]).save(OUT/(stage+'-tool.png'))
    evidence = dict(stage=stage, seconds=round(time.monotonic()-started,3),
        map_state=ui.map_state.inspect(rgb), scores={},
        construction_mode=score(rgb,ui.map_state.home,'construction_map_mode',(2494,1400,2526,1431)))
    for name,box in [('construction_title',(20,83,150,124)),
                     ('construction_selected_civilian_factory',(497,266,545,314)),
                     ('construction_button_civilian_factory',(497,266,545,314)),
                     ('construction_modal_title',ui.layout['modal_title'])]:
        evidence['scores'][name] = {label:score(rgb,t,name,box)
            for label,t in [('phase3',ui.templates),('native',ui.native_templates)]}
    evidence['modals']={name:score(rgb,ui.map_state.modals,name,box) for name,box in
        {'clock_menu':(1230,585,1330,620),'world_news':(1050,490,1510,580),
         'focus_completed_popup':(1240,655,1380,710)}.items()}
    (OUT/(stage+'.json')).write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    result['frames'].append(evidence)

try:
    b.begin(50)
    rgb=b.capture(); save('00-map',rgb)
    if not host.time.gui.is_paused():
        raise RuntimeError('game_not_paused')
    # Same normal state identity navigation as the executor, before opening tool mode.
    result['identity']=ui.prepare_target_readiness()
    rgb=b.capture(); save('01-map-reference',rgb)
    rgb=ui.open(); result['queue_before']=ui.read(rgb)['queue']; save('02-before-tool',rgb)
    if result['queue_before'] != []:
        raise RuntimeError('queue_not_empty')
    button=ui.layout['building_points'][tool]
    x,y=button
    if not ui.found(rgb,'construction_button_'+tool,(x-24,y-24,x+24,y+24),.85):
        raise RuntimeError('tool_button_not_found')
    point, geometry=b._point(button); b._move(point,geometry)
    ui.map_state.wait(.6); save('02-hover-only',b.capture())
    b.click(button); result['tool_clicks']=1
    rgb=b.capture(); save('03-click-first',rgb)
    ui.map_state.wait(.6); rgb=b.capture(); save('04-click-stable',rgb)
    b.click(ui.layout['neutral']); rgb=b.capture(); save('05-neutral-first',rgb)
    ui.map_state.wait(.6); rgb=b.capture(); save('06-neutral-stable',rgb)
    for i in range(8):
        ui.map_state.wait(.25); rgb=b.capture(); save('06-passive-'+str(i),rgb)
    result['queue_after']=ui.read(rgb)['queue']
    result['status']='DIAGNOSTIC_CAPTURED'
except Exception as exc:
    result.update(status='BLOCKED',reason=getattr(exc,'reason',str(exc)))
    try: save('failure-exact',b.capture())
    except Exception as capture_error: result['capture_error']=str(capture_error)
finally:
    try:
        ui.close()
        result['pause_evidence']=host.time.gui.pause_evidence()
        save('07-closed',b.capture())
    except Exception as exc: result['cleanup_error']=getattr(exc,'reason',str(exc))
    b.end(); host.close()
    (OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='frames'}))
