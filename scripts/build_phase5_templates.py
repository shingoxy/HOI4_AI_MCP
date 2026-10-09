"""Rebuild exact native capture calibration; never change the game."""
import json
from pathlib import Path
import sys
import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from hoi4_operator.executor.production_ui import text_mask, HEADER_BOX
from hoi4_operator.executor.non_military_layout import production_boxes
from hoi4_operator.executor.native_calibration import ANCHORS
from hoi4_operator.executor.native_order_ui import FRONT_SEGMENTS,ORDER_PARTS,HATCH_BOXES,native_order_mask


def digits(rgb, box, expected, directory, header=False, source='native'):
    x0,y0,x1,y1 = box
    mask = text_mask(rgb[y0:y1,x0:x1], header)
    edges = np.diff(np.r_[False, np.any(mask, axis=0), False].astype(np.int8))
    pieces = list(zip(np.where(edges==1)[0], np.where(edges==-1)[0]))
    if len(pieces) != len(expected):
        raise ValueError(f'{source}: unexpected glyph count {len(pieces)} for {expected}')
    for index, ((a,b), digit) in enumerate(zip(pieces, expected)):
        piece = mask[:,a:b]
        x,y,w,h = cv2.boundingRect(cv2.findNonZero(piece))
        label = {'/':'slash','0/':'zero_slash','2/':'two_slash'}.get(digit,digit)
        name = ('header_digit_' if header else 'factory_digit_') + label
        suffix = f'_{source}_p{index}' if header else ''
        Image.fromarray((piece[y:y+h,x:x+w]*255).astype(np.uint8)).save(directory/(name+suffix+'.png'))


def main():
    dest = ROOT/'artifacts/phase5/templates'
    prod = dest/'production'
    prod.mkdir(parents=True, exist_ok=True)
    captures = ROOT/'artifacts/phase5/gate-20261006/captures'
    tree = Image.open(captures/'research-tree-nav.png')
    tree.crop((25,95,210,129)).save(dest/'tech_bar.png')
    Image.open(captures/'construction-stop-current.png').crop((1240,590,1320,610)).save(dest/'clock_menu.png')
    Image.open(captures/'return-menu-cancelled.png').crop((1090,505,1410,550)).save(dest/'world_news.png')
    Image.open(captures/'game-menu-closed.png').crop((1260,670,1348,696)).save(dest/'focus_completed_popup.png')
    rgb = np.asarray(Image.open(captures/'production-compact.png').convert('RGB'))
    digits(rgb, HEADER_BOX, ['2','0/','2','8'], prod, True)
    digits(rgb, (397,215,441,236), '10/10', prod, True, 'dock')
    for i, expected in enumerate(['10','2','1','2','2','1','1','1']):
        digits(rgb, production_boxes(374+63*i)['count'], expected, prod)
    expanded = Image.open(captures/'production-after-uncertain.png')
    expanded.crop((326,406,351,426)).save(prod/'production_grid_on.png')
    after = np.asarray(Image.open(captures/'production-after-submit.png').convert('RGB'))
    digits(after, HEADER_BOX, '21/28', prod, True, 'after')
    after12_path = ROOT/'artifacts/phase5/reader-20261006/live-read-2/compact-0.png'
    after12 = np.asarray(Image.open(after12_path).convert('RGB'))
    digits(after12, HEADER_BOX, ['2','2/','2','8'], prod, True, 'after12')
    map_dir = dest/'map'
    map_dir.mkdir(exist_ok=True)
    map_rgb = Image.open(captures/'map-zoom-out-3.png')
    for name,box in ANCHORS.items():
        map_rgb.crop(box).save(map_dir/('map_anchor_'+name+'.png'))
    map_rgb.crop((2494,1400,2526,1431)).save(map_dir/'land_mode.png')
    Image.open(captures/'construction-after-submit.png').crop((206,309,221,328)).save(map_dir/'construction_one.png')
    military=dest/'military'
    military.mkdir(exist_ok=True)
    army=Image.open(captures/'army-one-native.png')
    for name,box in {'army_title':(68,94,128,108),'army_no_general':(70,136,140,151),
                     'army_count_1_no_general':(351,94,363,109),
                     'army_extra_plus_selected':(1337,1518,1370,1555)}.items():
        army.crop(box).save(military/(name+'.png'))
    Image.open(captures/'army-prepare-current.png').crop((1337,1518,1370,1555)).save(military/'army_extra_plus.png')
    Image.open(captures/'army-two-native.png').crop((351,94,363,109)).save(military/'army_count_2_no_general.png')
    empty=Image.open(captures/'front-empty-native.png')
    empty.crop((1251,1394,1276,1418)).save(military/'frontline_mode_active.png')
    empty.crop((1430,1359,1518,1382)).save(military/'drawing_assignment_two.png')
    for i,box in enumerate(FRONT_SEGMENTS):
        empty.crop(box).save(military/f'front_empty_{i}.png')
    Image.fromarray((native_order_mask(np.asarray(empty))*255).astype(np.uint8)).save(military/'scene_empty.png')
    front=Image.open(captures/'front-present-native.png')
    for name,box in {'drawing_assignment_zero':(1430,1359,1518,1382),
                     'operation_white':(986,1363,1049,1381),'plan_stopped':(1243,1474,1258,1488)}.items():
        front.crop(box).save(military/(name+'.png'))
    for i,box in enumerate(FRONT_SEGMENTS):
        front.crop(box).save(military/f'front_present_{i}.png')
    Image.fromarray((native_order_mask(np.asarray(front))*255).astype(np.uint8)).save(military/'scene_front.png')
    offensive=Image.open(captures/'offensive-empty-native.png')
    offensive.crop((1288,1394,1310,1418)).save(military/'offensive_active.png')
    for i,box in enumerate(FRONT_SEGMENTS):
        offensive.crop(box).save(military/f'offensive_front_present_{i}.png')
    Image.fromarray((native_order_mask(np.asarray(offensive))*255).astype(np.uint8)).save(military/'offensive_scene_front.png')
    for prefix,source in [('', 'offensive-present-front-native.png'),('offensive_', 'offensive-present-native.png')]:
        image=Image.open(captures/source)
        Image.fromarray((native_order_mask(np.asarray(image))*255).astype(np.uint8)).save(military/(prefix+'scene_poz.png'))
        for part,box in ORDER_PARTS.items():
            image.crop(box).save(military/(prefix+'order_poz_'+part+'.png'))
    (dest/'manifest.json').write_text(json.dumps({'capture_profile':'GER_2560x1600_DPI120_PHYSICAL',
        'tech_bar':{'source':str(captures/'research-tree-nav.png'),'box':[25,95,210,129]},
        'production':{'source':str(captures/'production-compact.png'),'known_counts':[10,2,1,2,2,1,1,1],
                      'header':'20/28','dock_header':'10/10','factory_digits':[0,1,2],
                      'thresholds_unchanged':True,
                      'count_12_source':str(after12_path), 'header_12':'22/28',
                      'joined_header_tokens':['0/','2/'], 'glyph_score_minimum':0.84,
                      'glyph_score_margin':0.10},
        'map':{'source':str(captures/'map-zoom-out-3.png'),'anchors':ANCHORS,
               'label_rounding_tolerance_px':1,'state_64_point':[1385,812]},
        'military':{'army_sources':['army-one-native.png','army-two-native.png'],
                    'known_divisions':['1. Infanterie-Division','1. Panzer-Division','10. Infanterie-Division'],
                    'counts':[1,2],'general':None,'hud_offset_y':520},
        'frontline':{'empty_source':'front-empty-native.png','present_source':'front-present-native.png',
                     'target':'GER_POL_mainland','point':[1775,730],'segments':FRONT_SEGMENTS},
        'offensive':{'empty_source':'offensive-empty-native.png',
                      'front_read_source':'offensive-present-front-native.png',
                      'drawing_read_source':'offensive-present-native.png','parts':ORDER_PARTS,
                      'tool_hatching_boxes':HATCH_BOXES,'start':[2030,760],'end':[2030,870]},
        'order_mask':{'roi':[1610,350,2510,1325],'edge_tolerance_px':2,'maximum_extra_or_missing_pixels':40,
                      'passive_render_wait_seconds':2,'submit_retry':False},
        'known_modals':['clock_menu','world_news','focus_completed_popup']}, indent=2), encoding='utf-8')


if __name__=='__main__': main()
