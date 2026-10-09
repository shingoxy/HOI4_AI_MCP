"""Offline stop policy / real-frame classification, never live GUI execution."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from hoi4_operator.executor.modal_stop_matrix import ModalStopState, VerifiedModalStops, stop_policy
from hoi4_operator.executor.native_modal import NativeModalDetector
from hoi4_operator.executor.templates import Templates

@pytest.mark.parametrize('scene,names,route,expected',[
    ('NO_MODAL',[],None,'NO_MODAL'),
    ('UNKNOWN_MODAL',[],None,'UNKNOWN_MODAL'),
    ('OVERLAY_STACK',['world_news','research_complete'],'escape_to_menu','OVERLAY_STACK'),
    ('KNOWN_SAFE_MODAL',['clock_menu'],None,'KNOWN_NONBLOCKING_MODAL'),
    ('KNOWN_BLOCKING_MODAL',['research_complete'],'escape_to_menu','KNOWN_BLOCKING_MODAL_WITH_SAFE_STOP'),
    ('KNOWN_BLOCKING_MODAL',['world_news'],None,'KNOWN_BLOCKING_MODAL_NO_SAFE_STOP'),
    ('KNOWN_BLOCKING_MODAL',['focus_completed_popup'],None,'KNOWN_BLOCKING_MODAL_NO_SAFE_STOP'),
    ('KNOWN_BLOCKING_MODAL',['unexpected_popup'],'escape_to_menu','UNKNOWN_MODAL'),
])
def test_finite_stop_matrix(scene,names,route,expected):
    result=stop_policy(scene,names,route)
    assert result['stop_state']==expected
    if expected in {'UNKNOWN_MODAL','OVERLAY_STACK','KNOWN_BLOCKING_MODAL_NO_SAFE_STOP'}:
        assert result['stop_route'] is None


@pytest.mark.parametrize('file,expected,route',[
    ('tool-20261007/safety-stop-1/before.png','KNOWN_BLOCKING_MODAL_WITH_SAFE_STOP','escape_to_menu'),
    ('tool-20261007/safety-stop-1/after.png','KNOWN_NONBLOCKING_MODAL','menu_pause_readback'),
    ('tool-20261007/final-physical.png','OVERLAY_STACK',None),
    ('time-safety-20261007/preflight-2/physical.png','NO_MODAL',None),
    ('time-safety-20261007/scripted-days30-1/native-audit/time-failure-bb3bc13e-bc8d-4021-bde6-60560861add0/physical.png',
     'KNOWN_BLOCKING_MODAL_NO_SAFE_STOP',None),
])
def test_actual_frames_do_not_enable_unverified_news_route(file,expected,route):
    detector=NativeModalDetector(Templates(ROOT/'artifacts/phase5/templates'))
    detector.stops.records=[]  # This fixture test deliberately has no new live calibration.
    rgb=np.asarray(Image.open(ROOT/'artifacts/phase5'/file).convert('RGB'))
    result=detector.read(rgb)
    assert result['stop_state']==expected
    assert result['stop_route']==route


def test_missing_calibration_keeps_world_news_disabled(tmp_path):
    policy=VerifiedModalStops(Templates(tmp_path/'artifacts/phase5/templates'))
    assert policy.records==[]
    assert policy.route(np.zeros((1600,2560,3),dtype=np.uint8),['world_news']) is None


def test_shallow_missing_template_path_still_fails_closed():
    assert VerifiedModalStops(Templates(Path('missing'))).records==[]


@pytest.mark.parametrize('kind,backend,pump',[
    ('offline_simulation','WindowsNativeBackend','OFF'),
    ('live_windows_native_stop_only','computer_use','OFF'),
    ('live_windows_native_stop_only','WindowsNativeBackend','ON'),
])
def test_non_native_or_offline_descriptor_is_not_live_proof(tmp_path,kind,backend,pump):
    folder=tmp_path/'artifacts/phase5'
    calibration=folder/'templates/modal_stop';calibration.mkdir(parents=True)
    proof=folder/'proof.json'
    proof.write_text(json.dumps(dict(kind=kind,status='confirmed',backend=backend,pump=pump,
        modal='world_news',route='escape_to_menu')),encoding='utf-8')
    (calibration/'manifest.json').write_text(json.dumps(dict(
        capture_profile='GER_2560x1600_DPI120_PHYSICAL',threshold=.9,routes=[dict(
            modal='world_news',route='escape_to_menu',proof='artifacts/phase5/proof.json',
            proof_sha256=hashlib.sha256(proof.read_bytes()).hexdigest())])),encoding='utf-8')
    policy=VerifiedModalStops(Templates(folder/'templates'))
    assert policy.records==[]
    assert policy.rejected


def test_unknown_or_stack_cannot_get_candidate_input_permission():
    for state in (ModalStopState.UNKNOWN_MODAL,ModalStopState.OVERLAY_STACK):
        assert stop_policy(str(state),['world_news'],'escape_to_menu')['candidate_stop_route'] is None
