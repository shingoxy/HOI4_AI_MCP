"""Order evidence in the exact native Poland viewport; no Agent coordinates."""
import cv2
import numpy as np
from PIL import Image
import time

from .guard import ActionError
from .native_calibration import validate_map

ORDER_ROI=(1610,350,2510,1325)
FRONT_SEGMENTS=((1900,620,1940,660),(1725,805,1765,845),(1985,985,2025,1025))
ORDER_PARTS={'origin':(1780,881,1835,924),'tip':(2015,799,2056,857),
             'army_label':(1914,841,2018,884),'target':(2020,741,2048,879)}


def native_order_mask(rgb):
    x0,y0,x1,y1=ORDER_ROI
    crop=rgb[y0:y1,x0:x1].astype(np.int16)
    r,g,b=crop[:,:,0],crop[:,:,1],crop[:,:,2]
    return (r>165)&(r-g>80)&(b-g>25)


class NativeOrderReader:
    def __init__(self,templates,prefix=''):
        self.templates=templates
        self.prefix=prefix
        self.diagnostics={}

    def scene(self,rgb):
        mask=native_order_mask(rgb)
        kernel=np.ones((5,5),np.uint8)
        expanded=cv2.dilate(mask.astype(np.uint8),kernel).astype(bool)
        matches=[]
        self.diagnostics={'scenes':{},'red_pixels':int(mask.sum())}
        for name in ('empty','front','poz'):
            path=self.templates.directory/f'{self.prefix}scene_{name}.png'
            if not path.is_file():
                continue
            expected=np.asarray(Image.open(path))>0
            allowed=cv2.dilate(expected.astype(np.uint8),kernel).astype(bool)
            extra=int((mask&~allowed).sum()); missing=int((expected&~expanded).sum())
            detail={'extra':extra,'missing':missing}
            self.diagnostics['scenes'][name]=detail
            if extra>40 or missing>40:
                continue
            if name=='empty':
                counts=[]
                for x0,y0,x1,y1 in FRONT_SEGMENTS:
                    crop=rgb[y0:y1,x0:x1].astype(np.int16)
                    r,g,b=crop[:,:,0],crop[:,:,1],crop[:,:,2]
                    yellow=(r>130)&(g>125)&(r-b>20)&(g-b>20)&(abs(r-g)<50)
                    counts.append(int(yellow.sum()))
                    if counts[-1]<30:
                        break
                else:
                    matches.append(name)
                detail['yellow_counts']=counts
            elif all(self.templates.find(rgb,f'{self.prefix}front_present_{i}',box,.92)
                     for i,box in enumerate(FRONT_SEGMENTS)):
                parts=ORDER_PARTS if self.prefix else {k:v for k,v in ORDER_PARTS.items() if k!='target'}
                if name=='poz' and not all(self.templates.find(rgb,f'{self.prefix}order_poz_{part}',box,.9)
                                           for part,box in parts.items()):
                    continue
                matches.append(name)
        self.diagnostics['matches']=matches
        if len(matches)!=1:
            raise ActionError('readback_ambiguous','rejected')
        return matches[0]


HATCH_BOXES=((2030,700,2110,780),(1900,780,1980,860),(2220,1140,2300,1220))
OFFENSIVE_TARGET='GER_POL_mainland_Poznan_east'


class NativeOffensiveUI:
    def __init__(self,military):
        self.military=military
        self.worker=military.worker
        self.reader=NativeOrderReader(military.native_templates,'offensive_')

    def tool_active(self,rgb):
        if not self.military.native_templates.find(rgb,'offensive_active',(1285,1391,1315,1421),.96):
            return False
        for x0,y0,x1,y1 in HATCH_BOXES:
            c=rgb[y0:y1,x0:x1].astype(np.int16);r,g,b=c[:,:,0],c[:,:,1],c[:,:,2]
            yellow=(r>130)&(g>100)&(r-b>10)&(g-b>15)
            if int(yellow.sum())<100:
                return False
        return True

    def read(self,rgb,land):
        if not self.tool_active(rgb):
            raise ActionError('requirements_not_met','rejected')
        if self.military.read_army(rgb)['division_names']!=land['armies'][0]['division_names']:
            raise ActionError('identity_mismatch','rejected')
        view=self.military.read_order_map(rgb,land,self.reader)
        if not view['fronts'] or view['plan_active'] is not False:
            raise ActionError('requirements_not_met','rejected')
        return view

    def observe(self):
        land=self.military.observe_land()
        return self.observe_from_land(land)

    def observe_from_land(self,land):
        if len(land['armies'])!=1 or len(land['armies'][0]['division_names'])!=2:
            raise ActionError('identity_mismatch','rejected')
        rgb=self.military.ui.capture()
        if not self.tool_active(rgb):
            self.worker.click((1299,1405))
            self.military.ui.capture()
        rgb=self.military.neutral()
        deadline=time.monotonic()+2
        while True:
            try:
                return self.read(rgb,land)
            except ActionError as exc:
                if exc.reason not in {'requirements_not_met','readback_ambiguous'} or time.monotonic()>=deadline:
                    raise
                self.worker._settle(.2)
                rgb=self.military.ui.capture()

    def submit(self,target,before,commit):
        from .offensive_ui import offensive_signature
        if target!=OFFENSIVE_TARGET:
            raise ActionError('unsupported_target','rejected')
        rgb=self.military.ui.capture()
        validate_map(rgb,self.military.map_templates)
        if offensive_signature(self.read(rgb,before))!=offensive_signature(before):
            raise ActionError('snapshot_stale','rejected')
        commit()
        self.worker.right_drag((2030,760),(2030,870))
