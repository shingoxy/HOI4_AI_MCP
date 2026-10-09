"""Operator diagnostic: GUI navigation/capture only, never calls a setter."""
import json
from pathlib import Path
import sys
import time
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
from hoi4_operator.executor.native_runtime import NativeRuntimeHost
from hoi4_operator.executor.production_ui import HEADER_BOX
from hoi4_operator.executor.non_military_layout import PRODUCTION, production_boxes
from hoi4_operator.executor.guard import ActionError
from hoi4_operator.telemetry.paths import default_log_path

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=False)
result = dict(backend='WindowsNativeBackend', pump='OFF', mutation_count=0, original_status='uncertain',
              original_action_id='4d8accb9-2765-465c-be7a-86259134d317', samples=[], telemetry_not_used=True)
host = None
started = time.monotonic()
def attempt(fn):
    try: return dict(status='read', value=fn())
    except ActionError as exc: return dict(status='unknown', reason=exc.reason)
try:
    host = NativeRuntimeHost(589988, default_log_path(), ROOT, out/'native-audit',
                             ROOT/'artifacts/phase5/gate-20261006/final/native-final-physical.png')
    b, ui = host.backend, host.production.ui
    b.begin(25)
    rgb = ui.open()
    for index in range(2):
        if index: rgb = ui.ui.capture()
        Image.fromarray(rgb).save(out/f'compact-{index}.png')
        result['samples'].append(dict(kind='compact', file=f'compact-{index}.png',
            view=attempt(lambda: ui.read(rgb)),
            numeric=attempt(lambda: ui.number(rgb, production_boxes(374)['count'])),
            header=attempt(lambda: ui.number(rgb, HEADER_BOX, header=True))))
    compact_view = ui.read(rgb)
    if ui.name_index(rgb,374) != 0 or not ui.found(rgb,'line_compact',production_boxes(374)['fold'],.85):
        raise ActionError('identity_mismatch','rejected')
    b.click((PRODUCTION['fold_x'],374+PRODUCTION['fold_y_offset']))
    rgb=ui.ui.capture()
    b.click(PRODUCTION['neutral'])
    for index in range(2):
        rgb=ui.ui.capture()
        Image.fromarray(rgb).save(out/f'expanded-{index}.png')
        result['samples'].append(dict(kind='expanded',file=f'expanded-{index}.png',
            numeric=attempt(lambda: ui.number(rgb,production_boxes(374)['count'])),
            grid=attempt(lambda: ui.grid_count(rgb,374)),
            header=attempt(lambda: ui.number(rgb,HEADER_BOX,header=True))))
    evidence = ui.stable_expanded(rgb, compact_view, 0)
    b.click((PRODUCTION['fold_x'],374+PRODUCTION['fold_y_offset']))
    folded = ui.ui.capture()
    Image.fromarray(folded).save(out/'folded-first-frame.png')
    b.click(PRODUCTION['neutral'])
    repeated = ui.stable_compact(ui.ui.capture(), compact_view)
    if ([line['factories'] for line in repeated['lines']] != [line['factories'] for line in compact_view['lines']] or
            repeated['assigned_military_factories'] != compact_view['assigned_military_factories'] or
            repeated['military_factories'] != compact_view['military_factories']):
        raise ActionError('readback_ambiguous','uncertain')
    result.update(status='confirmed', later_readback=evidence['numeric'], evidence=evidence,
                  repeated_readback=True, native_capture='GDI BitBlt physical 2560x1600 DPI120',
                  native_input_primitive='SendInput navigation only', readback_source='numeric AND grid AND complete-list assigned MIL')
    ui.close()
    result['restored_safe_page']=True
except ActionError as exc:
    result.update(status='blocked',reason=exc.reason)
finally:
    if host: host.close()
    result['duration_ms'] = round((time.monotonic()-started)*1000)
    (out/'readback.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
