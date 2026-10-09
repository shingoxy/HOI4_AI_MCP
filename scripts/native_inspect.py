"""Operator-only bounded native GUI preparation; not an Agent/MCP input API."""
import argparse
from pathlib import Path
import json
import sys
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from hoi4_operator.executor.guard import WindowsProbe
from hoi4_operator.executor.windows_native import WindowsNativeBackend

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--window",type=int,required=True)
    p.add_argument("--key")
    p.add_argument("--click",type=int,nargs=2)
    p.add_argument("--scroll",type=int,nargs=3)
    p.add_argument("--hover",type=int,nargs=2)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--ensure-paused",type=Path, help="calibrated paused reference; reobserve clock after GUI navigation")
    args=p.parse_args()
    if sum(v is not None for v in (args.key,args.click,args.scroll,args.hover))>1:
        p.error("at most one input followed by capture")
    probe=WindowsProbe()
    b=WindowsNativeBackend(args.window,probe.pid(args.window),probe=probe)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    evidence={"pump":"OFF","backend":"WindowsNativeBackend"}
    try:
        b.begin(12)
        rgb=b.capture()
        if args.key: b.key(args.key)
        elif args.click: b.click(tuple(args.click))
        elif args.scroll: b.scroll(tuple(args.scroll[:2]),args.scroll[2])
        elif args.hover:
            point,geometry=b._point(tuple(args.hover))
            b._move(point,geometry)
            b._settle(1)
        rgb=b.capture()
        if args.ensure_paused:
            from native_gate import BoundedClock
            clock=BoundedClock(b,args.ensure_paused,args.output.with_suffix('.clock.json'))
            if not clock.stable_clock():
                b.key('space')
            evidence['final_paused']=clock.confirm_pause()
            if not evidence['final_paused']:
                raise RuntimeError('navigation_final_pause_unconfirmed')
            rgb=b.capture()
        Image.fromarray(rgb).save(args.output)
        evidence.update(geometry=b.get_window_geometry(),key=args.key,click=args.click,scroll=args.scroll,hover=args.hover)
    finally:
        b.close()
    args.output.with_suffix(".json").write_text(json.dumps(evidence,indent=2),encoding="utf-8")
    print(json.dumps({"output":str(args.output),"pump":"OFF","input":args.key or args.click or args.scroll}))

if __name__=="__main__":main()
