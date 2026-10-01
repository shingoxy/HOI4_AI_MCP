"""Actual crop lookup and guarded GUI transitions; never sends Windows input."""

import base64
from io import BytesIO
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
from PIL import Image
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hoi4_operator.executor.catalog import RESEARCH
from hoi4_operator.executor.guard import ActionError
from hoi4_operator.executor.templates import Templates
from hoi4_operator.executor.ui_state import UIState
from hoi4_operator.executor.worker import ComputerUseWorker

ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts/phase3a"


def capture(name):
    return np.asarray(Image.open(ARTIFACTS / "captures" / (name + ".jpg")).convert("RGB"))


@pytest.mark.parametrize("tech_id", RESEARCH)
def test_calibrated_target_lookup_and_wrong_tree(tech_id):
    templates = Templates(ARTIFACTS / "templates")
    target = RESEARCH[tech_id]
    x, y = target.point
    box = (x - 50, y - 50, x + 50, y + 50)
    source = "industry-tree" if target.category == "industry" else "electronics-tree"
    assert templates.find(capture(source), "node_" + tech_id, box, 0.8)
    assert templates.find(capture("focus-idle"), "node_" + tech_id, box, 0.8) is None
    detail = {"basic_machine_tools": "basic-detail", "construction1": "construction-detail",
              "electronic_mechanical_engineering": "electronics-detail"}[tech_id]
    assert templates.find(capture(detail), "research_start", (886, 153, 1010, 192))


def test_actual_slot_identity_and_focus_idle_active_are_distinct():
    ui = UIState(None, Templates(ARTIFACTS / "templates"))
    rgb = capture("research-active")
    assert [ui.slot(rgb, n) for n in range(4)] == list(RESEARCH) + ["empty"]
    assert ui.focus_active(capture("focus-confirmed"))
    assert not ui.focus_active(capture("focus-idle"))


class Frames:
    def __init__(self, states):
        self.states, self.events = iter(states), []
    def capture(self):
        return SimpleNamespace(shape=(1080, 2560, 3), names=next(self.states))
    def click(self, point):
        self.events.append(("click", point))
    def key(self, key):
        self.events.append(("key", key))


class NameTemplates:
    def find(self, rgb, name, *args):
        return (950, 173) if name in rgb.names else None


def research_frames(*, wrong_identity=False, missing_ok=False):
    panel = {"research_title", "slot_frame"}
    detail = {"research_start"}
    if not wrong_identity:
        detail.add("detail_basic_machine_tools")
    popup = detail | {"replace_title"}
    if not missing_ok:
        popup.add("replace_ok")
    return [panel, {"tech_bar"}, {"node_basic_machine_tools"}, detail, detail,
            popup, panel, panel | {"slot_basic_machine_tools"}]


def test_start_shortcut_fallback_and_replacement_confirmation():
    worker = Frames(research_frames())
    ui, commits = UIState(worker, NameTemplates()), []
    assert ui.choose_research(0, "basic_machine_tools", lambda: commits.append(True))
    assert commits == [True]
    assert ("key", "Return") in worker.events
    assert len(worker.events) == 6  # slot/category/node, Return/start fallback, OK


@pytest.mark.parametrize("wrong_identity,missing_ok,reason", [
    (True, False, "target_identity_mismatch"),
    (False, True, "replacement_confirmation_not_found"),
])
def test_mismatched_detail_or_missing_confirmation_never_clicks_ok(wrong_identity, missing_ok, reason):
    worker = Frames(research_frames(wrong_identity=wrong_identity, missing_ok=missing_ok))
    commits = []
    with pytest.raises(ActionError, match=reason):
        UIState(worker, NameTemplates()).choose_research(0, "basic_machine_tools", lambda: commits.append(True))
    assert len(worker.events) == (3 if wrong_identity else 5)
    assert bool(commits) != wrong_identity


@pytest.mark.parametrize("image_format", ["JPEG", "PNG"])
def test_worker_decodes_actual_transport_formats(image_format):
    raw = BytesIO()
    Image.new("RGB", (12, 8), (23, 78, 150)).save(raw, format=image_format)
    worker = ComputerUseWorker.__new__(ComputerUseWorker)
    worker.request = lambda *_: {"image_base64": base64.b64encode(raw.getvalue()).decode(),
                                "screenshot_id": "observed"}
    assert worker.capture().shape == (8, 12, 3)
    assert worker.last_capture == "observed"


def test_unarmed_worker_cannot_queue_input():
    worker = ComputerUseWorker.__new__(ComputerUseWorker)
    worker.guard = SimpleNamespace(active=False)
    with pytest.raises(ActionError, match="action_not_armed"):
        worker.request("click", point=[1, 1])


def test_resolution_rejected_before_input():
    worker = Frames([])
    worker.capture = lambda: SimpleNamespace(shape=(1080, 1920, 3))
    with pytest.raises(ActionError, match="unsupported_resolution"):
        UIState(worker, NameTemplates()).open_panel("research")
    assert not worker.events
