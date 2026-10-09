"""Physical Construction tool truth; pulsing icon borders are sampled passively."""
import json
from pathlib import Path
import time
from uuid import uuid4

import cv2
import numpy as np
from PIL import Image

from .guard import ActionError
from .templates import Templates


class NativeConstructionTool:
    BOX = (497, 266, 545, 314)

    def __init__(self, worker, panels, home, modals, map_inspect=None):
        self.worker, self.panels, self.home, self.modals = worker, panels, home, modals
        self.maps=Templates(home.directory.parent/'map')
        self.map_inspect=map_inspect
        self.evidence = None

    @staticmethod
    def match(rgb, templates, name, box, threshold=.9):
        templates.find(rgb, name, box, threshold)
        template = templates.cache.get(name)
        if template is None:
            return dict(score=None, confirmed=False)
        x0,y0,x1,y1 = box
        crop = rgb[y0:y1,x0:x1]
        if crop.shape[0]<template.shape[0] or crop.shape[1]<template.shape[1]:
            return dict(score=None, confirmed=False)
        _,score,_,_ = cv2.minMaxLoc(cv2.matchTemplate(crop,template,cv2.TM_CCOEFF_NORMED))
        return dict(score=float(score), confirmed=bool(np.isfinite(score) and score>=threshold))

    @staticmethod
    def glow(rgb, box):
        x0,y0,x1,y1 = box
        bright = rgb[y0:y1,x0:x1].min(2)>170
        counts = dict(top=int(bright[:6].sum()), bottom=int(bright[-6:].sum()),
                      left=int(bright[:,:6].sum()), right=int(bright[:,-6:].sum()))
        # Independent sides of the real selected outline, outside the icon core.
        return dict(counts=counts, confirmed=min(counts[k] for k in ('top','left','right'))>=20
                    and counts['bottom']>=3)

    def read(self, rgb):
        if rgb.shape != (1600,2560,3):
            return dict(state='TOOL_UNKNOWN', reason='unsupported_resolution')
        matches = {name:self.match(rgb,self.modals,name,box) for name,box in
            {'clock_menu':(1230,585,1330,620),'world_news':(1050,490,1510,580),
             'focus_completed_popup':(1240,655,1380,710)}.items()}
        matches['construction_modal']=self.match(rgb,self.panels,'construction_modal_title',(1200,370,1360,415))
        title=self.match(rgb,self.panels,'construction_title',(20,83,150,124))
        icon=self.match(rgb,self.panels,'construction_button_civilian_factory',self.BOX)
        legacy=self.match(rgb,self.panels,'construction_selected_civilian_factory',self.BOX)
        mode=self.match(rgb,self.home,'construction_map_mode',(2494,1400,2526,1431))
        land=self.match(rgb,self.maps,'land_mode',(2494,1400,2526,1431))
        outline=self.glow(rgb,self.BOX)
        other_icon=self.match(rgb,self.panels,'construction_button_military_factory',(450,266,498,314))
        other_outline=self.glow(rgb,(450,266,498,314))
        result=dict(state='TOOL_UNKNOWN',reason='tool_evidence_incomplete',
                    panel=title,icon=icon,legacy_selected=legacy,mode=mode,land_mode=land,
                    outline=outline,other_icon=other_icon,other_outline=other_outline,
                    modals=matches,cursor_state='UNKNOWN; GDI capture excludes cursor')
        if any(v['confirmed'] for v in matches.values()):
            result.update(state='TOOL_OCCLUDED',reason='modal_blocked')
        elif not title['confirmed'] or not icon['confirmed']:
            result.update(state='TOOL_OCCLUDED',reason='panel_or_tool_not_visible')
        elif mode['confirmed']:
            if outline['confirmed'] and not other_outline['confirmed']:
                result.update(state='TOOL_SELECTED',reason='civilian_icon_outline_and_construction_mode')
            elif other_icon['confirmed'] and other_outline['confirmed'] and not outline['confirmed']:
                result.update(state='TOOL_NOT_SELECTED',reason='wrong_building_tool')
            else:
                result.update(state='TOOL_ANIMATING',reason='construction_mode_with_outline_pulse_pending')
        elif land['confirmed']:
            result.update(state='TOOL_NOT_SELECTED',reason='normal_map_mode; hover_is_not_selection')
        return result

    def start(self):
        self.evidence=dict(tool='civilian_factory',tool_clicks=0,passive_captures=0,frames=[])
        directory=getattr(self.worker,'audit_directory',None)
        self.path=Path(directory)/('tool-'+str(uuid4())) if directory is not None else None
        if self.path: self.path.mkdir(parents=True,exist_ok=False)

    def save(self, stage, rgb):
        state=self.read(rgb)
        if self.map_inspect: state['map_state']=self.map_inspect(rgb)
        self.evidence['frames'].append(dict(stage=stage,**state))
        if self.path:
            Image.fromarray(rgb).save(self.path/(stage+'.png'))
            Image.fromarray(rgb[266:314,497:545]).save(self.path/(stage+'-roi.png'))
            (self.path/(stage+'.json')).write_text(json.dumps(state,indent=2),encoding='utf-8')
            (self.path/'summary.json').write_text(json.dumps(self.evidence,indent=2),encoding='utf-8')
        return state

    def confirm(self, rgb, wait, *, allow_not_selected=False):
        deadline=time.monotonic()+3
        positives=0
        for _ in range(12):
            self.worker.check()
            state=self.save('passive-'+str(len(self.evidence['frames'])),rgb)
            if state['state']=='TOOL_SELECTED':
                positives+=1
                if positives>=2:
                    self.evidence['state']='TOOL_SELECTED'
                    self.save('confirmed-exact',rgb)
                    return rgb,state
            elif state['state']!='TOOL_ANIMATING':
                if allow_not_selected and state['state']=='TOOL_NOT_SELECTED':
                    return rgb,state
                raise ActionError('construction_tool_'+state['state'].lower(),'rejected')
            if time.monotonic()>=deadline: break
            wait(.12)
            rgb=self.worker.capture()
            self.evidence['passive_captures']+=1
        self.evidence['state']='TOOL_UNKNOWN'
        self.save('failure-exact',rgb)
        raise ActionError('construction_tool_unknown','rejected')
