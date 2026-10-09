"""Bounded native navigation smoke test. No research/focus/order is submitted."""
import argparse
from pathlib import Path
import sys
import json
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from hoi4_operator.executor.guard import WindowsProbe
from hoi4_operator.executor.windows_native import WindowsNativeBackend
from hoi4_operator.executor.templates import Templates
from hoi4_operator.executor.catalog import POINTS

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window",type=int,required=True)
    parser.add_argument("--panel",choices=("research","politics"),default="research")
    args=parser.parse_args()
    probe=WindowsProbe()
    backend=WindowsNativeBackend(args.window,probe.pid(args.window),probe=probe)
    out=ROOT/"artifacts/phase5"
    result={"source":"LIVE native backend / Computer Use pump OFF", "mutation_count":0,
            "panel":args.panel}
    try:
        backend.begin(15)
        backend.capture()
        backend.key("w" if args.panel=="research" else "q")
        rgb=backend.capture()
        Image.fromarray(rgb).save(out/f"captures/native-{args.panel}-logical.png")
        geometry=backend.desktop.geometry()
        raw=backend.desktop.capture(geometry)
        backend.check()
        Image.fromarray(raw).save(out/f"captures/native-{args.panel}-physical.png")
        templates=Templates(ROOT/"artifacts/phase3a/templates")
        title=templates.find(raw,args.panel+"_title",(20,84,220,124),.9)
        result.update(title_match_physical=bool(title),geometry=backend.get_window_geometry(),
                      status="navigation_confirmed" if title else "unconfirmed")
        if args.panel=="research":
            from hoi4_operator.executor.ui_state import UIState
            ui=UIState(backend,templates)
            result["slots_physical"]=[ui.slot(raw,i) for i in range(4)]
        if title:
            backend.click(POINTS["panel_close"])
            closed=backend.capture()
            result["mouse_close_confirmed"]=not bool(templates.find(closed,args.panel+"_title",(20,84,220,124),.9))
        else:
            backend.key("Escape")
            backend.capture()
    finally:
        backend.close()
    (out/f"native-{args.panel}-navigation.json").write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))

if __name__=="__main__": main()
