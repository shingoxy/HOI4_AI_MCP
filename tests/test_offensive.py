"""Independent-profile fixtures and offensive submission/confirmation boundaries."""

from copy import deepcopy
from pathlib import Path
import time

import numpy as np
from PIL import Image
import pytest

from test_executor import FakeModel, FakeWorker, summary
from hoi4_operator.executor.guard import ActionError
from hoi4_operator.executor.map_profile import PROFILES, profile_for_size
from hoi4_operator.executor.map_resolver import MapResolver, OFFENSIVE_ANCHORS, OFFENSIVE_TARGETS
from hoi4_operator.executor.offensive_ui import OffensiveUI
from hoi4_operator.executor.military_service import MilitaryExecutor
from hoi4_operator.executor.service import Executor
from hoi4_operator.executor.templates import Templates

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "artifacts/phase4/offensive2048"
TARGETS = tuple(OFFENSIVE_TARGETS)


def frame(filename):
    return np.asarray(Image.open(DATA / "captures" / filename).convert("RGB"))


def reader(worker=None):
    return OffensiveUI(worker, Templates(DATA / "templates"))


def test_exact_profiles_preserve_old_and_do_not_scale():
    assert profile_for_size((2560,1080)) == PROFILES[0]
    assert profile_for_size((2048,1280)) == PROFILES[1]
    assert PROFILES[1].ui_scale == 1 and len(PROFILES[1].camera_anchor_set) == 3
    old = MapResolver(Templates(ROOT / "artifacts/phase4/templates"))
    old.validate(np.asarray(Image.open(ROOT / "artifacts/phase4/captures/front-v2-mainland.jpg").convert("RGB")))
    with pytest.raises(ActionError, match="unsupported_resolution"):
        profile_for_size((1920,1080))
    # Independently measured Amsterdam differs greatly from a proportional projection.
    assert OFFENSIVE_ANCHORS["amsterdam"][0] != round(815 * 2048/2560)
    with pytest.raises(ActionError, match="map_target_unresolved"):
        reader().map.validate_offensive(np.zeros((1080,2560,3),dtype=np.uint8))


@pytest.mark.parametrize("anchor", OFFENSIVE_ANCHORS)
@pytest.mark.parametrize("damage", ["missing", "shifted"])
def test_three_independent_anchors_reject_bad_and_shifted(anchor, damage):
    rgb = frame("orders-empty.jpg").copy()
    x0,y0,x1,y1 = OFFENSIVE_ANCHORS[anchor]
    crop = rgb[y0:y1,x0:x1].copy()
    rgb[y0:y1,x0:x1] = 0
    if damage == "shifted":
        rgb[y0:y1,x0+5:x1+5] = crop
    with pytest.raises(ActionError, match="map_target_unresolved"):
        reader().map.resolve_offensive(TARGETS[0], rgb)


@pytest.mark.parametrize("target,filename", [(None,"orders-empty.jpg"),
    (TARGETS[0],"order-mainland-only.jpg"), (TARGETS[1],"order-mainland-north-east.jpg")])
def test_real_dedicated_offensive_reader(target,filename):
    view = reader().read(frame(filename))
    assert [o["target_id"] for o in view["offensive_orders"]] == ([] if target is None else [target])
    assert view["armies"][0]["division_names"] == ["1. Panzer-Division"]
    if target:
        assert view["offensive_orders"][0]["front_target_id"] == "GER_POL_mainland"
        assert reader().map.resolve_offensive(target,frame(filename)) == OFFENSIVE_TARGETS[target]


@pytest.mark.parametrize("damage,reason", [("army","identity_mismatch"),
    ("front","requirements_not_met"), ("tool","requirements_not_met"),
    ("extra","readback_ambiguous"), ("arrow_tip","readback_ambiguous")])
def test_reader_rejects_wrong_identity_front_tool_extra_order_and_ambiguous(damage,reason):
    ui = reader()
    rgb = frame("order-mainland-only.jpg").copy()
    key = {"army":"army_panzer_one", "front":"front_mainland_1",
           "tool":"offensive_active", "arrow_tip":"order_poz_tip"}.get(damage)
    if key:
        x0,y0,x1,y1 = ui.boxes[key]
        rgb[y0:y1,x0:x1] = 0
    else:
        # An unexpected arrow outside the target markers must still fail ROI reconciliation.
        rgb[800:810,1600:1740] = (245,70,130)
    with pytest.raises(ActionError, match=reason):
        ui.read(rgb)


@pytest.mark.parametrize("filename", ["mainland_north_east-drag-after.png", "front-tool.jpg"])
def test_real_inactive_or_frontline_tool_is_not_offensive_drawing_mode(filename):
    with pytest.raises(ActionError, match="requirements_not_met"):
        reader().require_tool(frame(filename))


class FakeOffensive:
    def __init__(self, worker):
        self.offensive = self
        self.worker = worker
        self.view = reader().read(frame("orders-empty.jpg"))
        self.submits, self.reads = 0, 0
        self.mode = None
    def observe(self):
        self.reads += 1
        if self.submits and self.mode == "ambiguous":
            raise ActionError("readback_ambiguous", "rejected")
        return deepcopy(self.view)
    observe_land = observe
    observe_orders = observe
    def submit(self, target, before, commit):
        if self.mode == "inactive":
            raise ActionError("requirements_not_met", "rejected")
        commit()
        self.submits += 1
        self.worker.events.append("right_drag")
        if self.mode == "release_failure":
            raise ActionError("native_input_failed")
        if self.mode == "missing":
            return
        self.view = reader().read(frame("order-mainland-only.jpg" if target == TARGETS[0]
                                        else "order-mainland-north-east.jpg"))
        if self.mode == "wrong":
            self.view["offensive_orders"][0]["target_id"] = "unexpected"
        elif self.mode == "extra":
            self.view["offensive_orders"].append(deepcopy(self.view["offensive_orders"][0]))


def setup():
    worker = FakeWorker()
    ui = FakeOffensive(worker)
    service = MilitaryExecutor(Executor(FakeModel([summary()]),worker,None),ui)
    army = service.get_fronts()["armies"][0]["army_id"]
    return service,ui,worker,army


@pytest.mark.parametrize("target",TARGETS)
def test_one_submission_repeated_exact_confirmation_and_gui_session_order_identity(target):
    service,ui,worker,army = setup()
    reads = ui.reads
    result = service.create_offensive_line(army,target)
    assert result["status"] == "confirmed" and result["retry_count"] == 0
    assert ui.submits == worker.events.count("right_drag") == result["submit_count"] == 1
    assert ui.reads-reads == 4 and result["mouse_release_confirmed"]
    order = result["after"]["offensive_orders"][0]
    assert not order["stable_game_identity"] and order["order_id"].startswith("order-")
    assert order["front_id"] == result["after"]["fronts"][0]["front_id"]
    assert result["after"]["ttl_seconds"] == 120 and order["identity_signature"]


@pytest.mark.parametrize("mode",["missing","wrong","extra","ambiguous","release_failure"])
def test_post_submit_uncertain_invalidates_all_snapshots_and_never_resubmits(mode):
    service,ui,worker,army = setup()
    ui.mode = mode
    result = service.create_offensive_line(army,TARGETS[0])
    assert result["status"] == "uncertain" and result["accepted"] and result["retry_count"] == 0
    assert ui.submits == 1 and service.armies.view is service.fronts.view is service.offensive_orders.view is None
    assert "release" in worker.events
    assert service.create_offensive_line(army,TARGETS[0])["status"] == "rejected" and ui.submits == 1
    if mode == "release_failure":
        assert "mouse_release_confirmed" not in result


@pytest.mark.parametrize("mode",["inactive","army_mismatch","front_absent","expired_front","expired_army","bad_target"])
def test_pre_submit_failures_have_zero_right_drag(mode):
    service,ui,worker,army = setup()
    target = TARGETS[0]
    if mode == "inactive": ui.mode = mode
    elif mode == "army_mismatch": ui.view["armies"][0]["name"] = "other"
    elif mode == "front_absent": ui.view["fronts"] = []
    elif mode == "expired_front": service.fronts.created = time.monotonic()-121
    elif mode == "expired_army": service.armies.created = time.monotonic()-121
    elif mode == "bad_target": target = "GER_POL_east_prussia_south"
    result = service.create_offensive_line(army,target)
    assert result["status"] == "rejected" and not result["accepted"] and ui.submits == 0
    assert "right_drag" not in worker.events


@pytest.mark.parametrize("target", TARGETS)
def test_real_ui_submit_resolves_one_drag_and_refuses_changed_pre_submit_frame(target):
    class Worker:
        def __init__(self): self.rgb, self.drags = frame("orders-empty.jpg"), []
        def capture(self): return self.rgb
        def right_drag(self,start,end): self.drags.append((start,end))
    worker = Worker()
    ui = reader(worker)
    before = ui.read(worker.rgb)
    commits = []
    ui.submit(target,before,lambda:commits.append(True))
    assert commits == [True] and worker.drags == [(OFFENSIVE_TARGETS[target]["start"],OFFENSIVE_TARGETS[target]["end"])]
    worker.rgb = frame("order-mainland-only.jpg")
    with pytest.raises(ActionError,match="snapshot_stale"):
        ui.submit(target,before,lambda:commits.append(True))
    assert len(commits) == len(worker.drags) == 1
