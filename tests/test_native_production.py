"""Actual GDI font calibration is tested separately from legacy JPEG samples."""
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
from PIL import Image
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))

from hoi4_operator.executor.guard import ActionError
from hoi4_operator.executor.production_lines_ui import ProductionLinesUI
from hoi4_operator.executor.production_ui import HEADER_BOX, text_mask
from hoi4_operator.executor.templates import Templates
from hoi4_operator.executor.windows_native import PHYSICAL_PROFILE
from hoi4_operator.executor.non_military_layout import production_boxes
import hoi4_operator.executor.production_lines_ui as lines_module



def test_real_native_compact_counts_header_and_sum():
    worker = SimpleNamespace(capture_profile=PHYSICAL_PROFILE)
    ui = ProductionLinesUI(SimpleNamespace(worker=worker), Templates(ROOT/'artifacts/phase3/templates'),
                           ROOT/'artifacts/phase5/templates/production')
    rgb = np.asarray(Image.open(ROOT/'artifacts/phase5/gate-20261006/captures/production-compact.png').convert('RGB'))
    result = ui.read(rgb)
    assert [line['factories'] for line in result['lines']] == [10,2,1,2,2,1,1,1]
    assert result['assigned_military_factories'] == 20
    assert result['military_factories'] == 28
    after = np.asarray(Image.open(ROOT/'artifacts/phase5/gate-20261006/captures/production-after-submit.png').convert('RGB'))
    result = ui.read(after)
    assert [line['factories'] for line in result['lines']] == [11,2,1,2,2,1,1,1]
    assert result['assigned_military_factories'] == 21
    expanded = np.asarray(Image.open(ROOT/'artifacts/phase5/gate-20261006/captures/production-after-uncertain.png').convert('RGB'))
    assert ui.grid_count(expanded, 374) == 10
    corrupt = expanded.copy()
    corrupt[406:426,326:351] = 255
    with pytest.raises(ActionError, match='readback_failed'):
        ui.grid_count(corrupt, 374)
    altered = rgb.copy()
    altered[215:236,210:262] = 0
    with pytest.raises(ActionError, match='production_number_unreadable'):
        ui.number(altered, HEADER_BOX, header=True)


CAPTURES = ROOT/'artifacts/phase5/gate-20261006/captures'
CURRENT = ROOT/'artifacts/phase5/reader-20261006/live-read-2'
SAMPLES = {
    10: (CAPTURES/'production-compact.png', CAPTURES/'production-after-uncertain.png'),
    11: (CAPTURES/'production-after-submit.png', CAPTURES/'production-readback-2-production-readback.png'),
    12: (CURRENT/'compact-0.png', CURRENT/'expanded-1.png'),
}


def image(path):
    return np.asarray(Image.open(path).convert('RGB'))


def native_ui(capture=lambda: None):
    worker = SimpleNamespace(capture_profile=PHYSICAL_PROFILE, check=lambda: None)
    return ProductionLinesUI(SimpleNamespace(worker=worker, capture=capture),
                             Templates(ROOT/'artifacts/phase3/templates'), ROOT/'artifacts/phase5/templates/production')


@pytest.mark.parametrize('count', [10, 11, 12])
def test_actual_native_three_sources(count):
    ui = native_ui()
    compact, expanded = map(image, SAMPLES[count])
    view = ui.read(compact)
    assert view['lines'][0]['factories'] == count
    assert ui.expanded_evidence(expanded, view, 0) == dict(
        numeric=count, grid=count, assigned_military_factories=count+10, military_factories=28)


@pytest.mark.parametrize('count', [10, 11, 12])
@pytest.mark.parametrize('variant', ['anti_alias_color', 'shifted_pixel'])
def test_native_numeric_and_header_variants(count, variant):
    ui, rgb = native_ui(), image(SAMPLES[count][0]).copy()
    for box in (production_boxes(374)['count'], HEADER_BOX):
        x0,y0,x1,y1 = box
        original = rgb[y0:y1,x0:x1].copy()
        if variant == 'anti_alias_color':
            # Perturb actual captured intensities without changing segmentation.
            mask = text_mask(original, box == HEADER_BOX)
            modified = original.astype(np.int16)
            modified[mask.astype(bool)] += 3
            modified[~mask.astype(bool)] -= 3
            rgb[y0:y1,x0:x1] = np.clip(modified,0,255).astype(np.uint8)
        else:
            rgb[y0:y1,x0:x1] = 0
            rgb[y0+1:y1,x0+1:x1] = original[:-1,:-1]
    view = ui.read(rgb)
    assert view['lines'][0]['factories'] == count and view['assigned_military_factories'] == count+10


@pytest.mark.parametrize('count', [10, 11, 12])
def test_native_aa_edge_crosses_segmentation_threshold(count):
    ui, rgb = native_ui(), image(SAMPLES[count][0]).copy()
    for box in (production_boxes(374)['count'], HEADER_BOX):
        x0,y0,x1,y1 = box
        roi = rgb[y0:y1,x0:x1]
        mask = text_mask(roi, box == HEADER_BOX)
        # A real foreground edge dims just below segmentation. Preserve its
        # component bounds so this tests glyph tolerance, not whole-pixel shift.
        candidates = [(y,x) for y,x in zip(*np.where(mask)) if
                      0 < y < mask.shape[0]-1 and 0 < x < mask.shape[1]-1 and
                      mask[y].sum() > 1 and mask[:,x].sum() > 1 and
                      not mask[y-1:y+2,x-1:x+2].all()]
        assert candidates
        y,x = candidates[0]
        roi[y,x] = 140 if box == HEADER_BOX else 170
        assert np.count_nonzero(text_mask(roi,box == HEADER_BOX) != mask) == 1
    view = ui.read(rgb)
    assert view['lines'][0]['factories'] == count and view['assigned_military_factories'] == count+10


@pytest.mark.parametrize('box', [production_boxes(374)['count'], HEADER_BOX])
def test_invalid_native_glyph_rejected(box):
    ui, rgb = native_ui(), image(SAMPLES[12][0]).copy()
    x0,y0,x1,y1 = box
    rgb[y0:y1,x0:x1] = 0
    rgb[y0+3:y0+14,x0+5:x0+10] = 255
    with pytest.raises(ActionError, match='production_number_unreadable'):
        ui.number(rgb, box, header=box == HEADER_BOX)


@pytest.mark.parametrize('source', ['numeric', 'grid', 'global'])
def test_three_sources_disagreement_is_ambiguous(source):
    ui = native_ui()
    view = ui.read(image(SAMPLES[12][0]))
    rgb = image(SAMPLES[12][1]).copy()
    if source == 'grid':
        rgb[406:426,326:351] = 255
    else:
        box = production_boxes(374)['count'] if source == 'numeric' else HEADER_BOX
        x0,y0,x1,y1 = box
        rgb[y0:y1,x0:x1] = image(SAMPLES[11][1])[y0:y1,x0:x1]
    with pytest.raises(ActionError, match='readback_ambiguous'):
        ui.expanded_evidence(rgb, view, 0)


def test_complete_numeric_list_global_total_disagreement():
    ui, rgb = native_ui(), image(SAMPLES[12][0]).copy()
    x0,y0,x1,y1 = HEADER_BOX
    rgb[y0:y1,x0:x1] = image(SAMPLES[11][0])[y0:y1,x0:x1]
    with pytest.raises(ActionError, match='readback_ambiguous'):
        ui.read(rgb)


def test_transient_unfold_waits_for_two_frames_without_input():
    frames = iter([image(SAMPLES[12][1]), image(SAMPLES[12][1])])
    ui = native_ui(lambda: next(frames))
    view = ui.read(image(SAMPLES[12][0]))
    evidence = ui.stable_expanded(image(CURRENT/'expanded-0.png'), view, 0)
    assert evidence['numeric'] == evidence['grid'] == 12
    assert not hasattr(ui.worker, 'click')  # This bounded wait cannot submit input.


def test_persistent_disagreement_is_bounded_and_never_resubmits(monkeypatch):
    rgb = image(SAMPLES[12][1]).copy()
    rgb[406:426,326:351] = 255
    ui = native_ui(lambda: rgb)
    view = ui.read(image(SAMPLES[12][0]))
    clock = [0]
    def sleep(seconds): clock[0] += seconds
    monkeypatch.setattr(lines_module, 'time', SimpleNamespace(monotonic=lambda: clock[0], sleep=sleep))
    with pytest.raises(ActionError, match='readback_ambiguous'):
        ui.stable_expanded(rgb, view, 0)
    assert 2 <= clock[0] < 2.2 and not hasattr(ui.worker, 'click')


def test_actual_folded_overlay_refuses_identity_then_passive_valid_frames():
    compact = image(SAMPLES[12][0])
    frames = iter([compact, compact])
    ui = native_ui(lambda: next(frames))
    view = ui.read(compact)
    obscured = image(ROOT/'artifacts/phase5/reader-20261006/live-read-4/folded-first-frame.png')
    with pytest.raises(ActionError, match='identity_mismatch'):
        ui.read(obscured)
    assert ui.stable_compact(obscured, view)['lines'][0]['factories'] == 12
    assert not hasattr(ui.worker, 'click')
