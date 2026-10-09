"""Guarded Germany/state64 map readiness. No inferred or scaled target points."""

import json
from pathlib import Path
import time
from uuid import uuid4

import cv2
from PIL import Image

from .guard import ActionError
from .native_calibration import ANCHORS, PROFILE, validate_map
from .templates import Templates
from .native_modal import NativeModalDetector


class NativeMapState:
    def __init__(self, worker, templates):
        self.worker, self.templates = worker, templates
        self.home = Templates(templates.directory.parent / "map_home")
        self.modals = Templates(templates.directory.parent)
        self.modal_detector=NativeModalDetector(self.modals)
        self.manifest = None
        self.last_recovery_attempted = False
        try:
            value = json.loads((self.home.directory / "manifest.json").read_text(encoding="utf-8"))
            if (value.get("status") == "LIVE_NAVIGATION_CALIBRATED" and
                    value.get("capture_profile") == PROFILE and value.get("threshold") == .9 and
                    value.get("state_point") == [1280, 800] and
                    all(s.get("identity_proof") for s in value.get("samples", []))):
                self.manifest = value
        except (OSError, ValueError):
            pass

    def inspect(self, rgb):
        result = dict(state="MAP_UNRESOLVED", reason="map_target_unresolved", profile=None, pose=None)
        if rgb.shape != (1600, 2560, 3):
            return {**result, "reason": "unsupported_resolution"}
        modal=self.modal_detector.read(rgb)
        if modal['state']!='NO_MODAL':
            return {**result,'reason':'unknown_modal' if modal['state']=='UNKNOWN_MODAL' else 'modal_blocked'}
        if not self.templates.find(rgb, "land_mode", (2494,1400,2526,1431), .9):
            return {**result, "reason": "map_mode_mismatch"}
        try:
            validate_map(rgb, self.templates)
            pose = {k:self.templates.find(rgb,"map_anchor_"+k,(b[0]-1,b[1]-1,b[2]+1,b[3]+1),.9)
                    for k,b in ANCHORS.items()}
            return dict(state="MAP_READY", reason="calibrated_gate_camera", profile="gate", pose=pose)
        except ActionError:
            pass
        if self.manifest:
            pose = {name:next((p for v in self.manifest["variants"]
                    if (p := self.home.find(rgb, f"{name}_{v}", box, .9))), None)
                    for name,box in self.manifest["anchor_boxes"].items()}
            geometry_ok = all(pose.values())
            if geometry_ok:
                for a,b in (("amsterdam","copenhagen"),("copenhagen","warsaw"),("amsterdam","warsaw")):
                    for axis in (0,1):
                        spans = [(s["anchors"][b]["box"][axis]+s["anchors"][b]["box"][axis+2])/2-
                                 (s["anchors"][a]["box"][axis]+s["anchors"][a]["box"][axis+2])/2
                                 for s in self.manifest["samples"]]
                        geometry_ok &= min(spans)-1 <= pose[b][axis]-pose[a][axis] <= max(spans)+1
            if geometry_ok and self.home.find(rgb, "country_ger", (8,10,87,70), .9):
                return dict(state="MAP_READY", reason="calibrated_capital_camera_range", profile="home", pose=pose)
            if (self.home.find(rgb,"country_ger",(8,10,87,70),.9) and
                    self.home.find(rgb,"find_entry",(2520,1359,2557,1390),.9)):
                return {**result, "state": "MAP_RECOVERABLE", "reason": "guarded_capital_navigation_required"}
        return result

    def evidence(self, rgb, state, stage):
        directory = getattr(self.worker, "audit_directory", None)
        if directory is not None:
            path = Path(directory) / ("map-" + stage + "-" + str(uuid4()))
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(rgb).save(path.with_suffix(".png"))
            path.with_suffix(".json").write_text(json.dumps(state,indent=2),encoding="utf-8")

    def record(self, op, **fields):
        record=getattr(self.worker,'_record',None)
        if record: record(op,**fields)

    @staticmethod
    def drawing_geometry(before, after):
        # Construction mode hides city labels and changes land colors. Compare
        # feature positions, not a fitted transform or a projected target point.
        # The 1500-feature cap starved state64 of samples in fresh real frames.
        # Increase extraction coverage; all match/count/displacement gates stay fixed.
        sift = cv2.SIFT_create(nfeatures=3000)
        ka,da = sift.detectAndCompute(cv2.cvtColor(before[100:1320,750:2420],cv2.COLOR_RGB2GRAY),None)
        kb,db = sift.detectAndCompute(cv2.cvtColor(after[100:1320,750:2420],cv2.COLOR_RGB2GRAY),None)
        if da is None or db is None or len(db) < 2:
            return dict(confirmed=False, matches=0, unchanged=0)
        candidates = [pair[0] for pair in cv2.BFMatcher().knnMatch(da,db,k=2)
                      if len(pair)==2 and pair[0].distance < .65*pair[1].distance]
        # Different descriptor orientations must not inflate the evidence.
        unique = {}
        for m in candidates:
            point = tuple(round(v,1) for v in ka[m.queryIdx].pt)
            unique.setdefault(point,m)
        unchanged = [ka[m.queryIdx].pt for m in unique.values()
            if max(abs(ka[m.queryIdx].pt[i]-kb[m.trainIdx].pt[i]) for i in (0,1)) <= 1]
        sectors = [sum(i*1670/3<=p[0]<(i+1)*1670/3 for p in unchanged) for i in range(3)]
        # Calibrated state64 scene around its fixed capital point, rather than
        # the city glyphs which the construction overlay deliberately removes.
        center = sum(250<=p[0]<=750 and 500<=p[1]<=970 for p in unchanged)
        ratio = len(unchanged)/max(1,len(unique))
        return dict(confirmed=len(unique)>=100 and ratio>=.9 and min(sectors)>=10 and center>=10,
            matches=len(unique), unchanged=len(unchanged), unchanged_ratio=ratio,
            sectors=sectors, target_neighborhood_matches=center, maximum_displacement_pixels=1,
            target_transform_used=False)

    def require(self, rgb, *, same=None, construction_panel=False, reference=None):
        state = self.inspect(rgb)
        if construction_panel and same and reference is not None:
            self.require(reference,same=same)
            panels = Templates(self.templates.directory.parents[2] / "phase3/templates")
            geometry = self.drawing_geometry(reference,rgb)
            if (panels.find(rgb,"construction_title",(20,83,150,124),.9) and
                    panels.find(rgb,"construction_button_civilian_factory",(497,266,545,314),.9) and
                    self.home.find(rgb,"construction_map_mode",(2494,1400,2526,1431),.9) and geometry["confirmed"]):
                state = dict(state="MAP_READY",reason="known_construction_mode_unchanged_geometry",
                    profile=same["profile"],pose=same["pose"],geometry=geometry,
                    city_anchor_source="all three revalidated before opening construction mode",
                    current_mode="known_construction_overlay; tool selection independently verified")
            else:
                state["drawing_geometry"] = geometry
        valid = state["state"] == "MAP_READY"
        if same is not None:
            valid &= state["profile"] == same["profile"] and state["pose"] is not None
            valid &= bool(valid and all(max(abs(a-b) for a,b in zip(state["pose"][k],point)) <= 1
                                       for k,point in same["pose"].items()))
        if not valid:
            self.record('map_state',stage='require',state='MAP_UNRESOLVED',reason=state['reason'])
            self.evidence(rgb, state, "rejected")
            raise ActionError("map_target_unresolved" if same is not None else state["reason"], "rejected")
        self.record('map_state',stage='require',state=state['state'],reason=state['reason'])
        return state

    def wait(self, seconds):
        deadline = time.monotonic()+seconds
        while time.monotonic() < deadline:
            self.worker.check()
            time.sleep(.05)

    def prepare(self, rgb):
        self.last_recovery_attempted = False
        state = self.inspect(rgb)
        self.record('map_state',stage='prepare',state=state['state'],reason=state['reason'])
        if state["state"] == "MAP_READY":
            return state
        if state["state"] != "MAP_RECOVERABLE":
            return self.require(rgb)
        started=time.monotonic()
        self.last_recovery_attempted=True
        self.record('map_recovery_started',route='Find View -> Go to Capital -> five bounded wheel steps')
        try:
            resolved=self._recover(rgb,state)
        except Exception as exc:
            self.record('map_recovery',succeeded=False,duration_ms=round((time.monotonic()-started)*1000),
                        reason=getattr(exc,'reason',type(exc).__name__))
            raise
        self.record('map_recovery',succeeded=True,duration_ms=round((time.monotonic()-started)*1000))
        return resolved

    def _recover(self, rgb, state):
        self.evidence(rgb, state, "before-recovery")
        # One bounded navigation attempt. No mutation or retry is hidden here.
        self.worker.click(self.home.find(rgb,"find_entry",(2520,1359,2557,1390),.9))
        rgb = self.worker.capture()
        point = self.home.find(rgb,"home_button",(2435,1326,2537,1345),.9)
        if not self.home.find(rgb,"find_header",(2283,1063,2319,1110),.9) or point is None:
            self.evidence(rgb, dict(reason="capital_navigation_unrecognized"), "recovery-failed")
            raise ActionError("map_target_unresolved", "rejected")
        self.worker.click(point)
        self.wait(2)
        self.worker.capture()
        # Existing guarded native pointer primitive; keep it off the screen edge
        # before Escape closes the positively recognized Find View.
        point, geometry = self.worker._point((1280,800))
        self.worker._move(point,geometry)
        self.worker.key("Escape")
        rgb = self.worker.capture()
        if self.home.find(rgb,"find_header",(2283,1063,2319,1110),.9):
            raise ActionError("map_target_unresolved", "rejected")
        for _ in range(5):
            self.worker.scroll((1280,800),120)
            self.wait(1)
            self.worker.capture()
        self.wait(2)
        rgb = self.worker.capture()
        state = self.require(rgb)
        self.evidence(rgb, state, "recovered")
        return state

    @staticmethod
    def target_point(state):
        return (1280,800) if state["profile"] == "home" else (1385,812)
