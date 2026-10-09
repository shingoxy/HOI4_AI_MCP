"""Bounded physical GUI modal classification, never generic popup dismissal."""
import cv2
import json
import numpy as np
from PIL import Image

from .templates import Templates
from .modal_stop_matrix import VerifiedModalStops, stop_policy


class NativeModalDetector:
    def __init__(self, templates):
        self.templates=templates
        self.time=Templates(templates.directory/'time_safety')
        self.stops=VerifiedModalStops(templates)
        self.escape_calibrated=False
        try:
            manifest=json.loads((self.time.directory/'manifest.json').read_text(encoding='utf-8'))
            root=templates.directory.parents[2]
            before=root/manifest['escape_before'];after=root/manifest['escape_after']
            proof=np.asarray(Image.open(after).convert('RGB'))
            self.escape_calibrated=(manifest['capture_profile']=='GER_2560x1600_DPI120_PHYSICAL' and
                manifest['threshold']==.9 and before.is_file() and
                bool(templates.find(proof,'clock_menu',(1230,585,1330,620),.9)))
        except (OSError,ValueError,KeyError,IndexError): pass

    def read(self, rgb):
        result=self._scene(rgb)
        if result['state']=='KNOWN_BLOCKING_MODAL' and result['stop_route'] is None:
            result['stop_route']=self.stops.route(rgb,result['names'])
        return {**result,**stop_policy(result['state'],result['names'],result['stop_route'])}

    def _scene(self, rgb):
        result=dict(state='UNKNOWN_MODAL',names=[],stop_route=None,
                    scope='Calibrated menu/news/focus/research and centered rectangular popup candidates only')
        if rgb.shape!=(1600,2560,3): return result
        names=[]
        for name,box in {'clock_menu':(1230,585,1330,620),'world_news':(1050,490,1510,580),
                         'focus_completed_popup':(1240,655,1380,710)}.items():
            if self.templates.find(rgb,name,box,.9): names.append(name)
        research=bool(self.time.find(rgb,'research_title',(1100,630,1460,750),.9))
        body=bool(self.time.find(rgb,'research_basic_body',(1180,770,1420,860),.9))
        news=bool(self.time.find(rgb,'news_chrome',(980,490,1580,560),.9))
        if research: names.append('research_complete')
        if news and 'world_news' not in names: names.append('world_news')
        result['names']=names
        if 'clock_menu' in names:
            return {**result,'state':'KNOWN_SAFE_MODAL','stop_route':'menu_pause_readback'}
        if len(names)>1: return {**result,'state':'OVERLAY_STACK'}
        if names:
            route='escape_to_menu' if names==['research_complete'] and body and self.escape_calibrated else None
            return {**result,'state':'KNOWN_BLOCKING_MODAL','stop_route':route}
        if self.time.find(rgb,'research_chrome',(980,560,1600,850),.9): return result
        # Conservative unknown popup candidate; no input is derived from this geometry.
        gray=cv2.cvtColor(rgb[350:1150,850:1750],cv2.COLOR_RGB2GRAY)
        contours,_=cv2.findContours(cv2.Canny(gray,60,160),cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            polygon=cv2.approxPolyDP(contour,.02*cv2.arcLength(contour,True),True)
            _,_,w,h=cv2.boundingRect(polygon)
            if len(polygon)==4 and w>=400 and h>=120 and cv2.contourArea(polygon)>=.9*w*h:
                return result
        return {**result,'state':'NO_MODAL'}
