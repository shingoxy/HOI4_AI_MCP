"""Exact current native map and bottom anchored state panel calibration."""
from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
from PIL import Image
import pytest
ROOT=Path(__file__).parents[1]
sys.path.insert(0,str(ROOT/'src'))
from hoi4_operator.executor.native_calibration import validate_map, NATIVE_CONSTRUCTION, ANCHORS
from hoi4_operator.executor.windows_native import PHYSICAL_PROFILE
from hoi4_operator.executor.templates import Templates
from hoi4_operator.executor.construction_ui import ConstructionUI
from hoi4_operator.executor.guard import ActionError


def load(name):
    return np.asarray(Image.open(ROOT/'artifacts/phase5/gate-20261006/captures'/name).convert('RGB'))


def test_native_construction_empty_queue_and_verified_state():
    ui=ConstructionUI(SimpleNamespace(worker=SimpleNamespace(capture_profile=PHYSICAL_PROFILE)),
        Templates(ROOT/'artifacts/phase3/templates'),Templates(ROOT/'artifacts/phase5/templates/map'))
    assert ui.read(load('construction-nav.png'))['queue']==[]
    state=load('state-64-nav.png')
    assert ui.found(state,'state_title_64',ui.layout['state_title'])
    assert ui.found(state,'state_owner_ger',ui.layout['owner_box'])
    assert set(ui.layout['state_points']) == {64}
    built=ui.read(load('construction-after-submit.png'))
    assert [(q['state_id'],q['building_type'],q['count']) for q in built['queue']] == [(64,'civilian_factory',1)]
    corrupt=load('construction-after-submit.png').copy()
    corrupt[309:328,206:221]=255
    with pytest.raises(ActionError,match='readback_ambiguous'): ui.read(corrupt)


def test_native_map_rejects_pan_bad_anchor_and_wrong_mode():
    rgb=load('map-zoom-out-3.png')
    templates=Templates(ROOT/'artifacts/phase5/templates/map')
    validate_map(rgb,templates)
    validate_map(load('construction-map-after-close.png'),templates)
    for box in [*ANCHORS.values(),(2494,1400,2526,1431)]:
        bad=rgb.copy()
        x0,y0,x1,y1=box
        bad[y0:y1,x0:x1]=0
        with pytest.raises(ActionError,match='map_target_unresolved'):
            validate_map(bad,templates)
    with pytest.raises(ActionError): validate_map(rgb[:1080],templates)
    shifted=np.roll(rgb,5,axis=1)
    with pytest.raises(ActionError): validate_map(shifted,templates)
