import sys, time, json
from pathlib import Path
sys.path.insert(0, "src")
from hoi4_operator.executor.guard import WindowsProbe
from hoi4_operator.executor.windows_native import WindowsNativeBackend
from PIL import Image
import numpy as np
p = WindowsProbe()
b = WindowsNativeBackend(589988, p.pid(589988), probe=p)
out = Path(__file__).parent/"captures"
frames, first = [], None
try:
    b.begin(10)
    for i in range(7):
        patch = b.capture()[9:30, 2294:2410]
        mask = (patch.min(axis=2)>180) & (patch.max(axis=2)-patch.min(axis=2)<40)
        first = mask if first is None else first
        frames.append({"sample":i, "changed":int(np.sum(mask!=first))})
        Image.fromarray(patch).resize((580,105)).save(out/f"clock-probe-{i}.png")
        time.sleep(.4)
finally:
    b.close()
print(json.dumps(frames))
