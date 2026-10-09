"""Read-only source comparison; temporary investigation, never injects input."""
import ctypes
from pathlib import Path
import sys
import json
import numpy as np
import cv2
from PIL import Image
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from hoi4_operator.executor.native_win32 import WindowsDesktop, BitmapInfo, BitmapHeader
from hoi4_operator.executor.guard import WindowsProbe
d=WindowsDesktop(589988)
p=WindowsProbe()
reason=p.check(589988,p.pid(589988))
if reason: raise RuntimeError(reason)
a=np.array(Image.open(ROOT/"artifacts/phase5/captures/computer-use-baseline.jpg"))
results=[]
for name,hwnd,physical in [("client-physical",589988,True),("client-unaware",589988,False),("desktop-unaware",None,False)]:
    old=d.user.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4 if physical else -1))
    dc=memory=bitmap=previous=None
    try:
        w,h=2048,1280
        dc=d.user.GetDC(hwnd)
        memory=d.gdi.CreateCompatibleDC(dc)
        bitmap=d.gdi.CreateCompatibleBitmap(dc,w,h)
        previous=d.gdi.SelectObject(memory,bitmap)
        ok=d.gdi.BitBlt(memory,0,0,w,h,dc,0,0,0x00CC0020|0x40000000)
        d.gdi.SelectObject(memory,previous)
        previous=None
        info=BitmapInfo(bmiHeader=BitmapHeader(biSize=ctypes.sizeof(BitmapHeader),biWidth=w,biHeight=-h,biPlanes=1,biBitCount=32))
        raw=np.empty((h,w,4),dtype=np.uint8)
        rows=d.gdi.GetDIBits(dc,bitmap,0,h,raw.ctypes.data,ctypes.byref(info),0)
        rgb=raw[:,:,2::-1].copy()
        Image.fromarray(rgb).save(ROOT/f"artifacts/phase5/captures/{name}.png")
        results.append({"name":name,"blit":ok,"rows":rows,"header_mae":float(np.abs(a[:60].astype(float)-rgb[:60]).mean()),"flag_correlation":float(cv2.matchTemplate(rgb[:65,:85],a[:60,:80],cv2.TM_CCOEFF_NORMED).max())})
    finally:
        if previous: d.gdi.SelectObject(memory,previous)
        if bitmap: d.gdi.DeleteObject(bitmap)
        if memory: d.gdi.DeleteDC(memory)
        if dc: d.user.ReleaseDC(hwnd,dc)
        d.user.SetThreadDpiAwarenessContext(old)
(ROOT/"artifacts/phase5/capture-sources.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
print(json.dumps(results))
