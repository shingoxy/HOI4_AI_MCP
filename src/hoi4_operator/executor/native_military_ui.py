"""Limited native physical layout: three known divisions, first army, no general."""
import time
from ..actions.military import DIVISIONS, sourced, land_signature, order_signature
from .military_ui import MilitaryUI
from .guard import ActionError
from .native_calibration import physical, validate_map, PROFILE, ANCHORS
from .templates import Templates
from .native_order_ui import NativeOrderReader,NativeOffensiveUI,OFFENSIVE_TARGET

HUD_NAMES = {'army_extra_plus','army_create_plus','army_create_plus_idle',
             'land_mode_button','land_mode_active','frontline_mode_active',
             'frontline_mode_assignment','frontline_mode_assignment_0',
             'plan_active','plan_stopped','operation_white'}
HUD_POINTS = {(2510,892):(2510,1412),(1270,1015):(1270,1535),
              (1263,885):(1263,1405),(1283,960):(1283,1480),(1248,960):(1248,1480)}


class HUDWorker:
    """Only these calibrated HUD positions move with the 520px taller client."""
    def __init__(self, backend): self.backend=backend
    def __getattr__(self,name): return getattr(self.backend,name)
    def click(self,point,**kwargs):
        return self.backend.click(HUD_POINTS.get(point,point),**kwargs)


class NativeMilitaryUI(MilitaryUI):
    def __init__(self,ui,templates,native_templates):
        super().__init__(ui,templates)
        self.worker=HUDWorker(ui.worker)
        self.native_templates=native_templates
        self.map_templates=Templates(native_templates.directory.parent/'map')
        self.orders=NativeOrderReader(native_templates)
        self.offensive=NativeOffensiveUI(self)

    def found(self,rgb,name,box,threshold=.9):
        if not physical(self.worker):
            raise ActionError('unsupported_resolution','rejected')
        if name in HUD_NAMES:
            x0,y0,x1,y1=box
            box=x0,y0+520,x1,y1+520
        point=super().found(rgb,name,box,threshold)
        point=point or self.native_templates.find(rgb,name,box,threshold)
        if not point and name=='army_extra_plus':
            point=self.native_templates.find(rgb,name+'_selected',box,threshold)
        return point

    def observe_land(self):
        self.ui.capture()
        if not physical(self.worker):
            raise ActionError('unsupported_resolution','rejected')
        # The parent reader remains valid for the fixed top overview. It sees
        # actual RGB pixels; only explicitly named bottom HUD positions move.
        offensive=self.offensive
        try:
            self.offensive=None
            return super().observe_land()
        finally:
            self.offensive=offensive

    def read_army(self,rgb):
        if (not self.found(rgb,'army_title',(60,85,145,110)) or
                not self.found(rgb,'army_no_general',(62,125,200,153))):
            raise ActionError('identity_mismatch','rejected')
        counts=[n for n in (1,2) if self.found(rgb,f'army_count_{n}_no_general',(351,94,363,109),.94)]
        if len(counts)!=1:
            raise ActionError('readback_ambiguous','rejected')
        count=counts[0]
        names=[]
        for index in range(count):
            top=240+34*index
            matches=[]
            for key,data in DIVISIONS.items():
                name='division_'+key
                point=self.found(rgb,name,(180,top,344,top+32),.86)
                if point and 184 <= point[0]-self.templates.cache[name].shape[1]//2 <= 188:
                    matches.append(data['name'])
            if len(matches)!=1 or matches[0] in names:
                raise ActionError('readback_ambiguous','rejected')
            names+=matches
        army=sourced({'name':'第1集团军','general_id':None,'division_names':sorted(names)})
        army['field_sources']['general_id']='gui'
        return army

    def change_land(self,action,before,commit,*,division=None,general_id=None):
        if action not in {'create_army','assign_divisions'}:
            raise ActionError('unsupported_target','rejected')
        if land_signature(self.observe_land())!=land_signature(before):
            raise ActionError('snapshot_stale','rejected')
        rgb=self.select_division(division)
        if (not self.found(rgb,'selected_single_header',(65,85,130,120),.94) or
                not self.found(rgb,'selected_unassigned',(15,178,390,226),.86)):
            raise ActionError('identity_mismatch','rejected')
        if action=='create_army':
            point=(self.found(rgb,'army_create_plus',(1280,980,1340,1055),.94) or
                   self.found(rgb,'army_create_plus_idle',(1280,980,1340,1055),.94))
            if not point:
                raise ActionError('target_not_found','rejected')
            commit()
            self.worker.click(point)
        else:
            point=self.army_card(rgb)
            commit()
            self.worker.click(point,button='right')
        self.ui.capture()

    def observe_orders(self):
        view=self.observe_land()
        if len(view['armies'])!=1 or len(view['armies'][0]['division_names'])!=2:
            raise ActionError('requirements_not_met','rejected')
        rgb=self.ui.capture()
        if not self.found(rgb,'frontline_mode_active',(1247,870,1280,903),.96):
            self.worker.click((1263,885))
            self.ui.capture()
        rgb=self.neutral()
        validate_map(rgb,self.map_templates)
        self.require_front_mode(rgb)
        deadline=time.monotonic()+2
        attempts=0
        while True:
            attempts+=1
            try:
                view=self.read_order_map(rgb,view,self.orders)
                break
            except ActionError as exc:
                if exc.reason!='readback_ambiguous' or time.monotonic()>=deadline:
                    raise
                self.worker._settle(.2)
                rgb=self.ui.capture()
                validate_map(rgb,self.map_templates)
                self.require_front_mode(rgb)
            finally:
                self.worker._record('native_order_read',attempt=attempts,**self.orders.diagnostics)
        if view['offensive_orders']:
            return self.offensive.observe_from_land(view)
        return view

    def read_order_map(self,rgb,view,reader):
        validate_map(rgb,self.map_templates)
        scene=reader.scene(rgb)
        present=scene!='empty'
        active=[s for s in ('active','stopped') if self.found(rgb,'plan_'+s,(1240,950,1261,969),.96)]
        if present and (len(active)!=1 or not self.found(rgb,'operation_white',(980,840,1060,865))):
            raise ActionError('readback_ambiguous','rejected')
        view.update(fronts=([sourced({'target_id':'GER_POL_mainland','type':'frontline',
            'army_name':view['armies'][0]['name'],'owner':'GER','assigned_divisions':None,
            'map_profile':PROFILE})] if present else []),
            plan_active=(active[0]=='active' if present else None),
            operation_name=('白色方案' if present else None),
            map_resolution={'profile':PROFILE,'anchors_verified':list(ANCHORS)},
            offensive_orders=([sourced({'target_id':OFFENSIVE_TARGET,'type':'offensive_line',
                'front_target_id':'GER_POL_mainland','army_name':view['armies'][0]['name']})] if scene=='poz' else []),
            unobserved_orders='UNKNOWN outside calibrated Poland viewport; occluded/subpixel orders UNKNOWN')
        for front in view['fronts']:
            front['field_sources'].update(target_id='derived',owner='derived',map_profile='derived',army_name='derived')
        for order in view['offensive_orders']:
            order['field_sources'].update(target_id='derived',front_target_id='derived',army_name='derived')
        return view

    def require_front_mode(self,rgb):
        if not (self.found(rgb,'frontline_mode_active',(1247,870,1280,903),.96) and
                any(self.native_templates.find(rgb,name,(1429,1358,1528,1384),.96)
                    for name in ('drawing_assignment_two','drawing_assignment_zero'))):
            raise ActionError('requirements_not_met','rejected')

    def change_orders(self,action,before,commit,target_id=None):
        if action!='create_frontline' or target_id!='GER_POL_mainland':
            raise ActionError('unsupported_target','rejected')
        if order_signature(self.observe_orders())!=order_signature(before):
            raise ActionError('snapshot_stale','rejected')
        rgb=self.ui.capture()
        validate_map(rgb,self.map_templates)
        self.require_front_mode(rgb)
        commit()
        self.worker.click((1775,730))
        self.ui.capture()
