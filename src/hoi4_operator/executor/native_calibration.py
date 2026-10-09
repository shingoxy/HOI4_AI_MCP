"""Exact GDI 2560x1600/DPI120 layout. Limited Germany 1936 gate targets."""
from .non_military_layout import CONSTRUCTION
from .guard import ActionError

PROFILE = 'GER_2560x1600_DPI120_PHYSICAL'
ANCHORS = {'amsterdam':(422,823,513,851), 'copenhagen':(1343,266,1423,289),
           'warsaw':(2360,858,2408,881)}
NATIVE_CONSTRUCTION = {**CONSTRUCTION,
    'state_points':{64:(1385,812)},
    'state_title':(165,952,320,988), 'owner_box':(22,1002,80,1045), 'state_close':(437,971)}


def physical(worker):
    return getattr(getattr(worker,'capture_profile',None),'name',None) == PROFILE


def validate_map(rgb, templates):
    if rgb.shape != (1600,2560,3):
        raise ActionError('unsupported_resolution','rejected')
    # City labels round independently by one physical pixel after a frame update.
    # This does not transform or move a target point.
    if not all(templates.find(rgb,'map_anchor_'+name,(box[0]-1,box[1]-1,box[2]+1,box[3]+1),.9)
               for name,box in ANCHORS.items()):
        raise ActionError('map_target_unresolved','rejected')
    if not templates.find(rgb,'land_mode',(2494,1400,2526,1431),.9):
        raise ActionError('map_target_unresolved','rejected')
