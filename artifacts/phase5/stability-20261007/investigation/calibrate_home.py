"""Repeat the bounded capital recovery; independently read state64 (no build)."""
import json
from pathlib import Path
import sys
import time
from PIL import Image
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'src'))
from hoi4_operator.executor.native_runtime import NativeRuntimeHost
from hoi4_operator.telemetry.paths import default_log_path
OUT=Path(__file__).resolve().parent
attempt=sys.argv[1]
host=NativeRuntimeHost(589988,default_log_path(),ROOT,OUT/('canonical-audit-'+attempt),
    ROOT/'artifacts/phase5/gate-20261006/final/native-final-physical.png')
b=host.backend
def settle(seconds=1):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        b.check()
        time.sleep(.05)
result=dict(pump='OFF',strategic_mutations=0,attempt=attempt)
try:
    b.begin(25)
    b.capture()
    if not host.time.gui.is_paused(): raise RuntimeError('requires_paused_start')
    b.capture(); b.click((2540,1378)); b.capture()
    b.click((2488,1334)); settle(2)
    Image.fromarray(b.capture()).save(OUT/f'canonical-{attempt}-near.png')
    # Do not leave the pointer at the right edge when closing Find View:
    # HOI4 can edge-pan immediately after the panel disappears.
    point,geometry=b._point((1280,800))
    b._move(point,geometry)
    b.key('Escape'); b.capture()
    for _ in range(5):
        b.scroll((1280,800),120)
        settle(1)
        b.capture()
    settle(2)
    Image.fromarray(b.capture()).save(OUT/f'canonical-{attempt}-map.png')
    # Capital position has been visually observed in actual home navigation.
    b.click((1280,800))
    rgb=b.capture()
    Image.fromarray(rgb).save(OUT/f'canonical-{attempt}-state.png')
    ui=host.construction.ui
    result['state64_identity']=bool(ui.found(rgb,'state_title_64',ui.layout['state_title']) and
                                   ui.found(rgb,'state_owner_ger',ui.layout['owner_box']))
    if not result['state64_identity']: raise RuntimeError('state64_identity_unconfirmed')
    b.click(ui.layout['state_close']); settle(1)
    Image.fromarray(b.capture()).save(OUT/f'canonical-{attempt}-restored.png')
    result['paused']=host.time.gui.is_paused()
    result['status']='confirmed'
except Exception as exc:
    result.update(status='blocked',reason=getattr(exc,'reason',type(exc).__name__))
finally:
    b.end();host.close()
    (OUT/f'canonical-{attempt}.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
