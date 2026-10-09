"""Operator-only host wiring and GUI observation/time control. No provider access."""

from pathlib import Path
import json
import time
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

import numpy as np
from PIL import Image

from ..operator import OperatorAPI
from ..read_model import ReadModel
from ..game_time import GameTimeController
from .catalog import BOXES, SLOT_FRAME_BOXES
from .guard import ActionError, WindowsProbe
from .windows_native import WindowsNativeBackend, PHYSICAL_PROFILE
from .templates import Templates
from .ui_state import UIState
from .service import Executor
from .production_lines_service import ProductionLineExecutor
from .production_lines_ui import ProductionLinesUI
from .construction_service import ConstructionExecutor
from .construction_ui import ConstructionUI
from .military_service import MilitaryExecutor
from .native_military_ui import NativeMilitaryUI
from .native_modal import NativeModalDetector


class NativeClockGUI:
    DATE, HEADER = (2294, 9, 2410, 30), (2237, 4, 2262, 31)

    def __init__(self, backend, reference, templates):
        self.backend, self.templates = backend, templates
        self.reference = np.asarray(Image.open(reference).convert("RGB"))
        if self.reference.shape != (1600, 2560, 3):
            raise ValueError("calibrated clock reference required")
        self.menu = False
        self.modals=NativeModalDetector(templates)
        self._context=lambda:dict(ownership_state='UNKNOWN',owns_running=False)
        self._telemetry=lambda:{}
        self.safe_map=None
        self.last_rgb=None
        self.last_capture_at=None
        self.last_failure=None
        self.last_pause_source=None
        self.modal_counts={}
        self.reset_stop_budget()

    def bind_time_context(self, context, telemetry):
        self._context,self._telemetry=context,telemetry

    def record_time_state(self, state):
        record=getattr(self.backend,'_record',None)
        if record: record('time_ownership',**state)

    def reset_stop_budget(self):
        self._space_stop_sent=self._escape_stop_sent=False
        self.last_failure=None
        self.evidence_error=None

    def begin_stop(self):
        if not getattr(getattr(self.backend,'guard',None),'active',True):
            self.last_rgb=None
            self.begin(12)
            return True
        return False

    def _capture(self):
        self.last_rgb=None
        self.last_capture_at=datetime.now(timezone.utc).isoformat()
        self.last_rgb=self.backend.capture()
        return self.last_rgb

    def _time_key(self, key):
        # Input may succeed before an exception; the pre-input frame is not a failure frame.
        self.last_rgb=None
        self.last_capture_at=datetime.now(timezone.utc).isoformat()
        self.backend.key(key)

    def _modal_read(self, rgb):
        modal=self.modals.read(rgb)
        if modal['state']!='NO_MODAL':
            for name in modal['names'] or [modal['state']]:
                self.modal_counts[name]=self.modal_counts.get(name,0)+1
            record=getattr(self.backend,'_record',None)
            if record: record('time_modal_observation',**modal)
        return modal

    def save_stop_failure(self, reason, rgb=None, *, captured_at=None):
        if self.last_failure and self.last_failure['reason']==reason and rgb is None:
            self.last_failure['ownership_after_failure']=self._context()
            directory=self.last_failure.get('directory')
            if directory:
                (Path(directory)/'failure.json').write_text(json.dumps(self.last_failure,ensure_ascii=False,indent=2),encoding='utf-8')
            return self.last_failure
        frame=rgb if rgb is not None else self.last_rgb
        guard=getattr(self.backend,'guard',None)
        probe=getattr(guard,'probe',None)
        foreground=None
        if hasattr(probe,'user'): foreground=int(probe.user.GetForegroundWindow() or 0)
        evidence=dict(reason=reason,captured_at=captured_at or self.last_capture_at,
            recorded_at=datetime.now(timezone.utc).isoformat(),ownership=self._context(),
            telemetry=self._telemetry(),hwnd=getattr(guard,'hwnd',None),pid=getattr(guard,'pid',None),
            foreground=foreground,guard_reason=getattr(guard,'reason',None),
            exact_rgb_available=frame is not None,candidate_stop_route=None,gui_date=None,gui_date_status='UNKNOWN')
        if frame is not None:
            evidence['modal']=self.modals.read(frame)
            evidence['candidate_stop_route']=evidence['modal'].get('candidate_stop_route')
        directory=getattr(self.backend,'audit_directory',None)
        if directory:
            path=Path(directory)/('time-failure-'+str(uuid4()));path.mkdir(parents=True,exist_ok=False)
            if frame is not None:
                Image.fromarray(frame).save(path/'physical.png')
                for name,box in {'clock':(2230,0,2460,45),'modal':(850,350,1750,1150),
                                 'menu':(1000,540,1560,1160)}.items():
                    Image.fromarray(frame).crop(box).save(path/(name+'.png'))
            evidence['directory']=str(path)
            (path/'failure.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
        self.last_failure=evidence
        return evidence

    def _clock_error(self, reason, rgb):
        try: self.save_stop_failure(reason,rgb)
        except OSError as exc: self.evidence_error=type(exc).__name__
        raise ActionError(reason,'rejected')

    def begin(self, timeout): self.backend.begin(timeout)
    def check(self): self.backend.check()
    def end(self): self.backend.end()

    def clock_value(self):
        rgb = self._capture()
        if rgb.shape != self.reference.shape:
            self._clock_error('clock_profile_mismatch',rgb)
        # Time control never resumes a modal or an open game menu.
        modal=self._modal_read(rgb)
        if modal['state']!='NO_MODAL':
            self._clock_error('unknown_modal' if modal['state']=='UNKNOWN_MODAL' else 'modal_blocked',rgb)
        x0, y0, x1, y1 = self.HEADER
        if np.mean(abs(rgb[y0:y1, x0:x1].astype(float)-self.reference[y0:y1, x0:x1])) > 8:
            self._clock_error('clock_header_unrecognized',rgb)
        x0, y0, x1, y1 = self.DATE
        text = rgb[y0:y1, x0:x1].astype(float)
        mask = (text.min(axis=2) > 180) & (text.max(axis=2)-text.min(axis=2) < 40)
        if np.count_nonzero(mask) < 16:
            self._clock_error('clock_date_unrecognized',rgb)
        return mask

    def pause_evidence(self):
        rgb = self._capture()
        if self.templates.find(rgb,"clock_menu",(1230,585,1330,620),.9):
            self.last_pause_source='known_game_menu_template'
            return dict(paused=True, pause_source="known_game_menu_template", gui_date_status="UNKNOWN",
                        gui_date=None, resumable=False)
        return dict(paused=self.is_paused(), pause_source="validated_GUI_clock_glyph_stability",
                    gui_date_status="UNKNOWN", gui_date=None, resumable=True)

    def is_paused(self):
        first = self.clock_value()
        deadline = time.monotonic()+2
        while time.monotonic() < deadline:
            self.check()
            time.sleep(.2)
            if np.count_nonzero(first != self.clock_value()) > 8:
                return False
        return True

    def resume(self):
        self.clock_value()  # Recheck profile, modal and clock immediately before the toggle.
        self._time_key('space')
        if self.is_paused():
            raise ActionError("resume_unconfirmed", "uncertain")

    def pause(self):
        # A toggle is allowed only after positive clock movement. Never double tap.
        if not self.is_paused():
            if self._space_stop_sent: raise ActionError('pause_input_already_attempted','uncertain')
            self.clock_value()
            self._space_stop_sent=True
            self._time_key('space')
        deadline = time.monotonic()+4
        while time.monotonic() < deadline:
            if self.is_paused():
                self.last_pause_source='validated_GUI_clock_glyph_stability'
                return True
        return False

    def safe_stop_once(self):
        """Only the calibrated menu route; no popup acknowledgement or strategic input."""
        rgb=self._capture();modal=self._modal_read(rgb)
        if modal['state']=='KNOWN_SAFE_MODAL':
            rgb=self._capture()
            confirmed=self._modal_read(rgb)['state']=='KNOWN_SAFE_MODAL'
            if not confirmed: self._clock_error('safe_stop_menu_unconfirmed',rgb)
            if confirmed:
                self.last_pause_source='known_game_menu_template'
                record=getattr(self.backend,'_record',None)
                if record: record('safe_stop_confirmed',route='known_menu_readback',input_sent=False)
            return confirmed
        allowed=modal['stop_route']=='escape_to_menu'
        if modal['state']=='NO_MODAL' and self.safe_map:
            allowed=self.safe_map(rgb)['state']=='MAP_READY'
        if not allowed:
            self._clock_error('unknown_modal' if modal['state']=='UNKNOWN_MODAL' else 'safe_stop_route_unavailable',rgb)
        if self._escape_stop_sent: raise ActionError('safe_stop_input_already_attempted','uncertain')
        self._escape_stop_sent=True
        self.backend.check()
        self._time_key('Escape')
        record=getattr(self.backend,'_record',None)
        if record: record('safe_stop_menu_open',route='single Escape; stop only')
        rgb=self._capture()
        if self._modal_read(rgb)['state']!='KNOWN_SAFE_MODAL':
            self._clock_error('safe_stop_menu_unconfirmed',rgb)
        rgb=self._capture()
        confirmed=self._modal_read(rgb)['state']=='KNOWN_SAFE_MODAL'
        if not confirmed: self._clock_error('safe_stop_menu_unconfirmed',rgb)
        if confirmed:
            self.last_pause_source='known_game_menu_template'
            if record: record('safe_stop_confirmed',route='single Escape to menu',input_sent=True)
        return confirmed


class NativeObservationHost:
    def __init__(self, model, executor, production, construction, military):
        self.model, self.executor = model, executor
        self.backend = executor.worker
        self.production, self.construction, self.military = production, construction, military
        self.calibration_ready = False
        templates = getattr(getattr(executor, "ui", None), "native_templates", None)
        if templates is not None:
            try:
                manifest = json.loads((templates.directory / "manifest.json").read_text(encoding="utf-8"))
                self.calibration_ready = manifest.get("capture_profile") == PHYSICAL_PROFILE.name
            except (OSError, ValueError):
                pass
        self.operator = OperatorAPI(model, executor=executor, production=production,
            construction=construction, military=military, runtime_capability=self.capability,
            observation_refresh=self.refresh)
        self.last_refresh = []
        self.target_identity_date = None
        self.target_identity_at = None

    def capability(self):
        profile = getattr(self.backend, "capture_profile", None)
        primitives = all(self.backend.capabilities.get(k) for k in ("capture", "click", "key_tap", "right_drag"))
        ready = profile == PHYSICAL_PROFILE and primitives and self.backend.ready() and self.calibration_ready
        reason = ("profile_mismatch" if profile != PHYSICAL_PROFILE else "backend_capability_mismatch" if not primitives
                  or not self.backend.ready() else "calibration_missing" if not self.calibration_ready else "validated_subset")
        action_readiness = {}
        if ready and self.construction and self.construction.ui.map_state:
            ui = self.construction.ui
            armed = False
            try:
                if not self.backend.guard.active:
                    self.backend.begin(5)
                    armed = True
                rgb = self.backend.capture()
                view = ui.map_state.inspect(rgb)
                ui.map_state.record('map_state',stage='capability',state=view['state'],reason=view['reason'])
                identity = ui.target_identity
                target_valid = bool(identity and view["state"] == "MAP_READY" and
                    view["profile"] == identity["profile"] and
                    self.target_identity_at is not None and time.monotonic()-self.target_identity_at <= 120 and
                    self.target_identity_date == self.model.summary().get("game_date") and
                    all(max(abs(a-b) for a,b in zip(view["pose"][k],p)) <= 1 for k,p in identity["pose"].items()))
                action_readiness["build"] = dict(map_state=view["state"],map_reason=view["reason"],
                    profile_calibrated=self.calibration_ready,target_identity_valid=target_valid)
                for action in ("create_frontline", "create_offensive_line"):
                    action_readiness[action] = dict(map_state="MAP_READY" if view["profile"] == "gate" else "MAP_UNRESOLVED",
                        map_reason="current_military_camera_uncalibrated", profile_calibrated=view["profile"] == "gate")
            except ActionError as exc:
                action_readiness["build"] = dict(map_state="MAP_UNRESOLVED", map_reason=exc.reason,
                    profile_calibrated=False, target_identity_valid=False)
            finally:
                if armed:
                    self.backend.end()
        return dict(backend="windows_native", native_subset_ready=ready,
                    reason=reason,
                    validated_actions=7, computer_use_pump="OFF", action_readiness=action_readiness)

    def preflight(self):
        try:
            self.backend.begin(8)
            return self.backend.capture()
        finally:
            self.backend.end()

    def panel_observation(self, domain):
        if not self.executor.lock.acquire(blocking=False):
            raise ActionError("executor_busy", "rejected")
        try:
            self.executor.snapshot()
            self.backend.begin(10)
            ui = self.executor.ui
            panel = "research" if domain == "research_gui" else "politics"
            def read():
                rgb = ui.open_panel(panel)
                if domain == "research_gui":
                    return dict(slots=[dict(slot=i, tech_id=ui.slot(rgb, i)) for i in range(4)
                                      if ui.found(rgb, "slot_frame", SLOT_FRAME_BOXES[i], .85)])
                return dict(active=True, active_focus_id="GER_remilitarize_the_rhineland") if ui.focus_active(rgb) else (
                    dict(active=False, active_focus_id=None) if ui.found(rgb, "focus_empty", BOXES["focus_empty"]) else dict(active=None))
            view = read()
            if view != read():
                raise ActionError("readback_ambiguous", "rejected")
            self.operator.observation.remember(domain, view, complete=False)
            ui.close_panel()
            return dict(status="confirmed", mutation_submitted=False)
        finally:
            if self.backend.guard.active:
                self.backend.end()
            self.executor.lock.release()

    def refresh(self, domains):
        events = []
        for domain in domains:
            if self.model.summary()["status"] != "fresh":
                events.append(dict(domain=domain, status="rejected", reason="telemetry_stale", navigation_required=True))
                break
            try:
                if domain in {"research_gui", "focus_gui"}:
                    result = self.panel_observation(domain)
                else:
                    if getattr(self, domain) is None:
                        events.append(dict(domain=domain, status="unsupported", reason="semantic_implementation_missing", navigation_required=False))
                        continue
                    name = {"production": "get_production_lines", "construction": "get_construction", "military": "get_fronts"}[domain]
                    result = self.operator.execute(name)
                    if result.get("status") == "confirmed":
                        # Restore a known safe map page through that domain's calibrated close control.
                        if domain in {"production", "construction"}:
                            service = getattr(self, domain)
                            self.backend.begin(30 if domain == "construction" and result.get("queue") == [] else 8)
                            try:
                                service.ui.close()
                                if domain == "construction" and result.get("queue") == []:
                                    try:
                                        service.ui.prepare_target_readiness()
                                        self.target_identity_date = self.model.summary().get("game_date")
                                        self.target_identity_at = time.monotonic()
                                        result["target_readiness"] = dict(map_state="MAP_READY", target_identity_valid=True)
                                    except ActionError as exc:
                                        self.target_identity_date = self.target_identity_at = None
                                        result["target_readiness"] = dict(map_state="MAP_UNRESOLVED",
                                            target_identity_valid=False, reason=exc.reason)
                                        if (service.ui.map_state.last_recovery_attempted or
                                                exc.reason not in {"map_target_unresolved", "map_mode_mismatch", "identity_mismatch"}):
                                            raise
                            finally:
                                self.backend.end()
                event = dict(domain=domain, status=result["status"], reason=result.get("reason"), navigation_required=True,
                             duration_ms=result.get("duration_ms"), restored_safe_page=domain != "military" and result["status"] == "confirmed")
                if "target_readiness" in result:
                    event["target_readiness"] = deepcopy(result["target_readiness"])
                if domain == "production" and result.get("status") == "confirmed":
                    view = dict(result)
                    view["available_factories"] = result["available_military_factories"]
                    self.operator.observation.remember(domain, view, complete=False)
                events.append(event)
                if result["status"] != "confirmed":
                    break
            except ActionError as exc:
                events.append(dict(domain=domain, status=exc.status, reason=exc.reason, navigation_required=True, restored_safe_page=False))
                break
        self.last_refresh = events
        return events


class NativeRuntimeHost(NativeObservationHost):
    def __init__(self, window, log_path, root, audit_directory, paused_reference):
        root = Path(root)
        probe = WindowsProbe()
        backend = WindowsNativeBackend(window, probe.pid(window), probe=probe, audit_directory=audit_directory)
        model = ReadModel(log_path)
        templates = Templates(root / "artifacts/phase5/templates")
        ui = UIState(backend, Templates(root / "artifacts/phase3a/templates"), templates)
        executor = Executor(model, backend, ui)
        production = ProductionLineExecutor(executor, ProductionLinesUI(ui, Templates(root / "artifacts/phase3/templates"),
                                                                       root / "artifacts/phase5/templates/production"))
        construction = ConstructionExecutor(executor, ConstructionUI(ui, Templates(root / "artifacts/phase3/templates"),
                                                                    Templates(root / "artifacts/phase5/templates/map")))
        military = MilitaryExecutor(executor, NativeMilitaryUI(ui, Templates(root / "artifacts/phase4/templates"),
                                                              Templates(root / "artifacts/phase5/templates/military")))
        super().__init__(model, executor, production, construction, military)
        self.time = GameTimeController(model, NativeClockGUI(backend, paused_reference, templates))
        self.time.gui.safe_map=construction.ui.map_state.inspect
        backend.save_time_failure=lambda reason,rgb:self.time.gui.save_stop_failure(
            reason,rgb,captured_at=datetime.now(timezone.utc).isoformat())

    def close(self):
        stop=self.time.ensure_game_stopped()
        unsafe=self.time.owns_running
        self.shutdown_report=dict(shutdown='unsafe_stop_failed' if unsafe else 'clean_no_owned_time',
            game_pause=True if stop['paused'] else 'UNKNOWN',
            stop=stop,time_metrics=dict(self.time.metrics,modal_seen_by_type=dict(getattr(getattr(self.time,'gui',None),'modal_counts',{})),
                modal_count_scope='Clock observations; not distinct popup events'),**self.time.contract())
        try:
            return self.shutdown_report
        finally:
            self.backend.close()
