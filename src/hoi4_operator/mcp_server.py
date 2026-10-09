"""Local stdio MCP telemetry and optional, explicitly attached GUI executor."""

import argparse
from contextlib import asynccontextmanager
import json
import math
from pathlib import Path
from typing import Annotated, Any

import anyio
from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.subscriptions import InMemorySubscriptionBus, ResourceUpdated
from mcp.types import ToolAnnotations
from pydantic import Field

from .read_model import ReadModel, UNKNOWN_FIELDS
from .telemetry.paths import default_log_path
from .telemetry.parser import TRACKED_FOCUS, TRACKED_TECHS


STATE_URI = "hoi4://state/current"
CAPABILITIES_URI = "hoi4://telemetry/capabilities"


def create_server(log_path: str | Path, *, interval: float = 0.25,
                  stale_seconds: float = 30, executor=None, production_executor=None,
                  gui_window: int | None = None, non_military: bool = False, construction_executor=None,
                  politics_executor=None, trade_executor=None, military_executor=None, military: bool = False,
                  input_backend: str = "native", capture_space: str = "physical") -> MCPServer:
    if not math.isfinite(interval) or interval <= 0:
        raise ValueError("interval must be finite and positive")
    if not math.isfinite(stale_seconds) or stale_seconds <= 0:
        raise ValueError("stale_seconds must be finite and positive")
    if input_backend not in {"native", "computer-use"}:
        raise ValueError("input_backend must be native or computer-use")
    if capture_space not in {"physical", "legacy"}:
        raise ValueError("capture_space must be physical or legacy")
    bus = InMemorySubscriptionBus()
    runtime: ReadModel | None = None
    action_runtime = executor
    production_runtime = production_executor
    construction_runtime = construction_executor
    politics_runtime = politics_executor
    trade_runtime = trade_executor
    military_runtime = military_executor
    right_drag_attached = False
    api_runtime = None

    async def watch(model: ReadModel) -> None:
        while True:
            await anyio.sleep(interval)
            if model.poll():
                await bus.publish(ResourceUpdated(uri=STATE_URI))

    @asynccontextmanager
    async def lifespan(server: MCPServer):
        nonlocal runtime, action_runtime, production_runtime, construction_runtime, politics_runtime, trade_runtime, military_runtime, right_drag_attached, api_runtime
        model = ReadModel(log_path, stale_seconds=stale_seconds)
        runtime = model
        worker = None
        if gui_window is not None:
            from .executor.guard import WindowsProbe
            from .executor.service import Executor
            from .executor.production_service import ProductionExecutor
            from .executor.production_ui import ProductionUI
            from .executor.templates import Templates
            from .executor.ui_state import UIState
            root = Path(__file__).resolve().parents[2]
            probe = WindowsProbe()
            if input_backend == "native":
                from .executor.windows_native import WindowsNativeBackend
                worker = WindowsNativeBackend(gui_window, probe.pid(gui_window), probe=probe,
                                              capture_space=capture_space,
                                              audit_directory=root / "artifacts/phase5/runtime/native-audit")
                right_drag_attached = military
            else:
                from .executor.worker import ComputerUseWorker
                worker = ComputerUseWorker(gui_window, probe.pid(gui_window), probe=probe,
                                           endpoint_file=root / "artifacts/phase3a/runtime/endpoint.json")
            if military and input_backend == "computer-use":
                from .executor.right_drag import NativeRightDragBackend
                worker = NativeRightDragBackend(worker)
                right_drag_attached = True
            # Independent reader: executor's thread never races the MCP watcher.
            action_model = ReadModel(log_path, stale_seconds=stale_seconds)
            action_runtime = Executor(action_model, worker,
                                      UIState(worker, Templates(root / "artifacts/phase3a/templates"),
                                              Templates(root / "artifacts/phase5/templates") if input_backend == "native" else None))
            production_runtime = ProductionExecutor(action_runtime, ProductionUI(
                action_runtime.ui, Templates(root / "artifacts/phase3b1/templates")))
            if non_military:
                from .executor.production_lines_service import ProductionLineExecutor
                from .executor.production_lines_ui import ProductionLinesUI
                production_runtime = ProductionLineExecutor(action_runtime, ProductionLinesUI(
                    action_runtime.ui, Templates(root / "artifacts/phase3/templates"),
                    root / "artifacts/phase5/templates/production" if input_backend == "native" else None))
                from .executor.construction_service import ConstructionExecutor
                from .executor.construction_ui import ConstructionUI
                construction_runtime = ConstructionExecutor(action_runtime, ConstructionUI(
                    action_runtime.ui, Templates(root / "artifacts/phase3/templates"),
                    Templates(root/'artifacts/phase5/templates/map') if input_backend == 'native' else None))
                from .executor.politics_service import PoliticsExecutor
                from .executor.politics_ui import PoliticsUI
                politics_runtime = PoliticsExecutor(action_runtime, PoliticsUI(
                    action_runtime.ui, Templates(root / "artifacts/phase3/templates")))
                from .executor.trade_service import TradeExecutor
                from .executor.trade_ui import TradeUI
                trade_runtime = TradeExecutor(action_runtime, TradeUI(
                    action_runtime.ui, Templates(root / "artifacts/phase3/templates")))
            if military:
                from .executor.military_service import MilitaryExecutor
                from .executor.military_ui import MilitaryUI
                if input_backend == 'native' and capture_space == 'physical':
                    from .executor.native_military_ui import NativeMilitaryUI
                    military_ui=NativeMilitaryUI(action_runtime.ui,Templates(root/'artifacts/phase4/templates'),
                                                Templates(root/'artifacts/phase5/templates/military'))
                else:
                    military_ui=MilitaryUI(action_runtime.ui,Templates(root/'artifacts/phase4/templates'),
                                           Templates(root/'artifacts/phase4/offensive2048/templates'))
                military_runtime = MilitaryExecutor(action_runtime,military_ui)
        from .operator import OperatorAPI
        if gui_window is not None and input_backend == "native" and capture_space == "physical":
            from .executor.native_runtime import NativeObservationHost
            observation_host = NativeObservationHost(action_runtime.model, action_runtime, production_runtime,
                                                     construction_runtime, military_runtime)
            api_runtime = observation_host.operator
        else:
            api_runtime = OperatorAPI(model, executor=action_runtime, production=production_runtime,
                construction=construction_runtime, politics=politics_runtime, trade=trade_runtime, military=military_runtime)
        async with anyio.create_task_group() as tasks:
            tasks.start_soon(watch, model)
            try:
                yield model
            finally:
                tasks.cancel_scope.cancel()
                runtime = None
                api_runtime = None
                if worker:
                    worker.close()
                    action_runtime = None
                    production_runtime = None
                    construction_runtime = None
                    politics_runtime = None
                    trade_runtime = None
                    military_runtime = None
                    right_drag_attached = False

    server = MCPServer(
        "HOI4 Telemetry and GUI PoC", version="0.9.0", lifespan=lifespan,
        subscriptions=bus,
        instructions=(
            "get_game_state and get_action_catalog provide scoped semantic runtime observations and current targets. "
            "summary/catalog use telemetry and cache; strategic/detailed may navigate GUI pages serially. "
            "The catalog limits the native runtime to the validated physical Germany seven-action subset; "
            "registration of historical tools does not mean all tools are native live verified. "
            "Reads Germany telemetry. select_research/select_focus are normal GUI actions "
            "requiring an explicitly attached guarded backend and fresh v2 telemetry. "
            "Only three tracked technologies and Rhineland are supported at 2560x1080/1.0. "
            "Production supports get_production_lines and set_production_factory_count: "
            "six calibrated visible military lines, GUI session-local IDs and counts 0..15; "
            "truncated equipment labels are observation-only and reject assignment. "
            "Snapshots expire or become invalid on changed order/identity/count. "
            "An explicitly attached --non-military runtime additionally supports calibrated military "
            "line creation/deletion and one-step order changes, with full military list readback. "
            "That runtime also supports construction in German states 64/65/66 (one civilian factory, "
            "military factory or infrastructure), calibrated economy/conscription laws, Schacht, "
            "and SWE steel contracts using 0..2 civilian factories. GUI-derived observations are "
            "scoped and are not complete game telemetry. "
            "An explicitly attached --military runtime supports one first army, three known "
            "GER division names and Manstein, two fixed-camera GER/POL frontlines and whole-plan "
            "switches, one division's supply tooltip, one fighter wing in strategic region 8, "
            "and one twelve-ship task force. IDs are temporary and observations incomplete. "
            "An independently calibrated offensive capability supports two mainland GER/POL directions "
            "for one selected first army containing 1. Panzer-Division. Requires observed existing fronts, "
            "an empty calibrated order viewport, and repeated dedicated order readback. "
            "Province movement and naval mutations reject before input. No console or effects. "
            "Use status and freshness_basis before treating data as current. "
            "A paused game normally becomes stale; startup replay uses file mtime, "
            "an upper bound on frame recency. Dates are localized text. "
            "seq can roll back after load; change revision belongs to this server "
            "process only. Protocol v2 adds research slots, three tracked technologies "
            "and a tracked focus progress interval. Current focus ID, slot assignment, "
            "remaining research time and per-line production are UNKNOWN."
        ),
    )
    read_only = ToolAnnotations(
        read_only_hint=True, destructive_hint=False,
        idempotent_hint=True, open_world_hint=False,
    )
    gui_action = ToolAnnotations(read_only_hint=False, destructive_hint=True,
                                 idempotent_hint=True, open_world_hint=False)
    from .military_mcp import register_military_tools
    register_military_tools(server, lambda: military_runtime)

    @server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False,
                                            idempotent_hint=True, open_world_hint=False), structured_output=True)
    async def get_game_state(detail: str = "strategic") -> dict[str, Any]:
        """Unified semantic state. summary uses telemetry/cache; strategic/detailed may serially navigate calibrated GUI pages. Unknown and incomplete domains remain explicit."""
        if api_runtime is None:
            return {"status": "rejected", "reason": "backend_unavailable"}
        return await anyio.to_thread.run_sync(api_runtime.get_game_state, detail)

    @server.tool(annotations=read_only, structured_output=True)
    async def get_action_catalog() -> dict[str, Any]:
        """Current scoped semantic targets. Tool registration does not imply native runtime availability; snapshot/freshness/profile/backend constraints apply."""
        if api_runtime is None:
            return {"status": "rejected", "reason": "backend_unavailable"}
        return await anyio.to_thread.run_sync(api_runtime.get_action_catalog)

    @server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False,
                                            idempotent_hint=True, open_world_hint=False), structured_output=True)
    async def get_production_lines() -> dict[str, Any]:
        """Read normal Production UI. The calibrated non-military runtime reconciles the complete military list; legacy mode reads six top rows. Generates temporary session IDs."""
        if production_runtime is None:
            return {"accepted": False, "status": "rejected", "reason": "executor_not_connected"}
        return await anyio.to_thread.run_sync(production_runtime.get_production_lines)

    @server.tool(annotations=gui_action, structured_output=True)
    async def set_production_factory_count(line_id: str, factories: Annotated[int, Field(strict=True)]) -> dict[str, Any]:
        """Adjust factories through normal GUI using an ID from this session's latest production snapshot. Confirm exact count through numeric and grid readback."""
        if production_runtime is None:
            return {"accepted": False, "status": "rejected", "reason": "executor_not_connected"}
        return await anyio.to_thread.run_sync(production_runtime.set_production_factory_count, line_id, factories)

    @server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False,
                                            idempotent_hint=True, open_world_hint=False), structured_output=True)
    def get_equipment_catalog() -> dict[str, Any]:
        """Semantic IDs, calibrated display identities and explicit unknown internal game IDs."""
        from .actions.equipment import EQUIPMENT
        return {"equipment": EQUIPMENT, "country": "GER", "scope": "calibrated 1936 PoC"}

    @server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True,
                                            idempotent_hint=False, open_world_hint=False), structured_output=True)
    async def create_production_line(equipment_id: str) -> dict[str, Any]:
        """Create exactly one normal military production line. Confirms before/after list diff; never retries submission."""
        if production_runtime is None or not hasattr(production_runtime, "create_production_line"):
            return {"accepted": False, "status": "rejected", "reason": "backend_unavailable"}
        return await anyio.to_thread.run_sync(production_runtime.create_production_line, equipment_id)

    @server.tool(annotations=gui_action, structured_output=True)
    async def delete_production_line(line_id: str) -> dict[str, Any]:
        """Normally delete a line identified by the latest session snapshot; confirm only that target was removed."""
        if production_runtime is None or not hasattr(production_runtime, "delete_production_line"):
            return {"accepted": False, "status": "rejected", "reason": "backend_unavailable"}
        return await anyio.to_thread.run_sync(production_runtime.delete_production_line, line_id)

    @server.tool(annotations=gui_action, structured_output=True)
    async def reorder_production_line(line_id: str, direction: str) -> dict[str, Any]:
        """Move one step up/down through normal buttons; reconcile the entire calibrated military list order."""
        if production_runtime is None or not hasattr(production_runtime, "reorder_production_line"):
            return {"accepted": False, "status": "rejected", "reason": "backend_unavailable"}
        return await anyio.to_thread.run_sync(production_runtime.reorder_production_line, line_id, direction)

    @server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False,
                                            idempotent_hint=True, open_world_hint=False), structured_output=True)
    async def get_construction() -> dict[str, Any]:
        """Read a complete calibrated GUI queue; replaces session-local queue identities. Progress may remain unknown."""
        if construction_runtime is None:
            return {"accepted": False, "status": "rejected", "reason": "backend_unavailable"}
        return await anyio.to_thread.run_sync(construction_runtime.get_construction)

    @server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True,
                                            idempotent_hint=False, open_world_hint=False), structured_output=True)
    async def build(state_id: Annotated[int, Field(strict=True)], building_type: str,
                    count: Annotated[int, Field(strict=True)] = 1) -> dict[str, Any]:
        """Normally queue one civilian/military factory or infrastructure in calibrated German state 64, 65 or 66."""
        if construction_runtime is None:
            return {"accepted": False, "status": "rejected", "reason": "backend_unavailable"}
        return await anyio.to_thread.run_sync(construction_runtime.build, state_id, building_type, count)

    @server.tool(annotations=gui_action, structured_output=True)
    async def cancel_construction(queue_item_id: str) -> dict[str, Any]:
        """Cancel one item from this session's latest queue snapshot, confirming its exact removal."""
        if construction_runtime is None:
            return {"accepted": False, "status": "rejected", "reason": "backend_unavailable"}
        return await anyio.to_thread.run_sync(construction_runtime.cancel_construction, queue_item_id)

    @server.tool(annotations=gui_action, structured_output=True)
    async def change_construction_priority(queue_item_id: str, direction: str) -> dict[str, Any]:
        """Move one queue item up/down once and confirm the exact adjacent swap."""
        if construction_runtime is None:
            return {"accepted": False, "status": "rejected", "reason": "backend_unavailable"}
        return await anyio.to_thread.run_sync(construction_runtime.change_construction_priority, queue_item_id, direction)

    @server.tool(annotations=gui_action, structured_output=True)
    async def change_economy_law(law_id: str) -> dict[str, Any]:
        """Normal GER economic law selection. Calibrated early/partial mobilisation only; requires PP, war support, enabled option and repeated current-law readback."""
        if politics_runtime is None:
            return {"accepted": False, "status": "rejected", "reason": "backend_unavailable"}
        return await anyio.to_thread.run_sync(politics_runtime.change_economy_law, law_id)

    @server.tool(annotations=gui_action, structured_output=True)
    async def change_conscription_law(law_id: str) -> dict[str, Any]:
        """Normal GER volunteer/limited conscription selection; verifies requirements and law identity. Never retries submission."""
        if politics_runtime is None:
            return {"accepted": False, "status": "rejected", "reason": "backend_unavailable"}
        return await anyio.to_thread.run_sync(politics_runtime.change_conscription_law, law_id)

    @server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False,
                                            idempotent_hint=True, open_world_hint=False), structured_output=True)
    async def get_advisors() -> dict[str, Any]:
        """Read all three calibrated political advisor slots through normal GUI; returns semantic catalog and session-local slot identities."""
        if politics_runtime is None:
            return {"accepted": False, "status": "rejected", "reason": "backend_unavailable"}
        return await anyio.to_thread.run_sync(politics_runtime.get_advisors)

    @server.tool(annotations=gui_action, structured_output=True)
    async def hire_advisor(advisor_id: str) -> dict[str, Any]:
        """Hire calibrated advisor_schacht into the first empty political slot. Requires PP and enabled GUI option; confirms exact complete slot transition."""
        if politics_runtime is None:
            return {"accepted": False, "status": "rejected", "reason": "backend_unavailable"}
        return await anyio.to_thread.run_sync(politics_runtime.hire_advisor, advisor_id)

    @server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False,
                                            idempotent_hint=True, open_world_hint=False), structured_output=True)
    async def get_trade_state() -> dict[str, Any]:
        """Read the calibrated SWE steel contract and available civilian factories. Opens then discards a proposal; never submits. Other contracts remain UNKNOWN."""
        if trade_runtime is None:
            return {"accepted": False, "status": "rejected", "reason": "backend_unavailable"}
        return await anyio.to_thread.run_sync(trade_runtime.get_trade_state)

    @server.tool(annotations=gui_action, structured_output=True)
    async def set_trade_import(resource: str, country: str,
                               civilian_factories: Annotated[int, Field(strict=True)]) -> dict[str, Any]:
        """Normally set SWE steel imports to 0..2 civilian factories. Confirms numeric proposal, commits once, then reopens and verifies contract AND delivered quantity twice."""
        if trade_runtime is None:
            return {"accepted": False, "status": "rejected", "reason": "backend_unavailable"}
        return await anyio.to_thread.run_sync(trade_runtime.set_trade_import, resource, country, civilian_factories)

    @server.tool(annotations=gui_action, structured_output=True)
    async def select_research(slot: int, tech_id: str) -> dict[str, Any]:
        """Normally select a tracked technology in zero-based slot 0..3, then confirm through GUI and telemetry."""
        if action_runtime is None:
            return {"accepted": False, "status": "rejected", "reason": "executor_not_connected"}
        return await anyio.to_thread.run_sync(action_runtime.select_research, slot, tech_id)

    @server.tool(annotations=gui_action, structured_output=True)
    async def select_focus(focus_id: str) -> dict[str, Any]:
        """Normally start GER_remilitarize_the_rhineland; never completes a focus. Confirms GUI and telemetry."""
        if action_runtime is None:
            return {"accepted": False, "status": "rejected", "reason": "executor_not_connected"}
        return await anyio.to_thread.run_sync(action_runtime.select_focus, focus_id)

    @server.tool(annotations=read_only, structured_output=True)
    async def get_summary(ctx: Context) -> dict[str, Any]:
        """Return the latest complete GER state with freshness and parser errors."""
        return ctx.request_context.lifespan_context.summary()

    @server.tool(annotations=read_only, structured_output=True)
    async def get_politics(ctx: Context) -> dict[str, Any]:
        """Read political power, stability and war support, including freshness."""
        return ctx.request_context.lifespan_context.section("politics")

    @server.tool(annotations=read_only, structured_output=True)
    async def get_industry(ctx: Context) -> dict[str, Any]:
        """Read factory totals only; per-line production remains UNKNOWN."""
        return ctx.request_context.lifespan_context.section("industry")

    @server.tool(annotations=read_only, structured_output=True)
    async def get_research(ctx: Context) -> dict[str, Any]:
        """Read research slots and three tracked technologies; slot assignment and remaining time are UNKNOWN."""
        return ctx.request_context.lifespan_context.section("research")

    @server.tool(annotations=read_only, structured_output=True)
    async def get_focus(ctx: Context) -> dict[str, Any]:
        """Read tracked Rhineland completion and progress interval; this is not the current focus ID."""
        return ctx.request_context.lifespan_context.section("focus")

    @server.tool(annotations=read_only, structured_output=True)
    async def get_changes(ctx: Context,
                          after_revision: Annotated[int, Field(ge=0, strict=True)] = 0) -> dict[str, Any]:
        """Read up to 100 retained changes after a revision from this process. Does not consume them."""
        return ctx.request_context.lifespan_context.changes(after_revision)

    @server.tool(annotations=read_only, structured_output=True)
    async def get_diagnostics(ctx: Context) -> dict[str, Any]:
        """Read source errors, parser errors and explicitly unsupported telemetry fields."""
        return ctx.request_context.lifespan_context.diagnostics()

    @server.resource(STATE_URI, mime_type="application/json")
    async def current_state() -> str:
        """Current state; subscribed clients refetch on resource update notifications."""
        assert runtime is not None
        return json.dumps(runtime.summary(), ensure_ascii=False)

    @server.resource(CAPABILITIES_URI, mime_type="application/json")
    def capabilities() -> str:
        return json.dumps({
            "read_only": action_runtime is None and production_runtime is None and military_runtime is None, "telemetry_read_only": True,
            "country": "GER", "protocol_version": 2,
            "accepted_protocol_versions": [1, 2],
            "available": ["politics", "manpower", "factory_totals", "research_slots",
                          "tracked_technology_predicates", "tracked_focus_progress_interval"],
            "tracked_technologies": TRACKED_TECHS, "tracked_focus": TRACKED_FOCUS,
            "extended_fields_live_verified": True,
            "gui_actions": ["select_research", "select_focus", "set_production_factory_count"],
            "non_military_runtime_requested": non_military,
            "military_runtime_requested": military,
            "military_executor_attached": military_runtime is not None,
            "military": {"scope_status": "PARTIAL", "army_scope": "one first army; three named GER divisions",
                         "general_scope": ["GER_erich_von_manstein"], "game_unit_ids": "UNKNOWN",
                         "fronts": "GUI_ONLY; GER_POL_mainland and GER_POL_east_prussia; whole-plan switches",
                         "supply": "GUI_ONLY; 1. Infanterie tooltip; army/front totals UNKNOWN",
                         "air": "GUI_ONLY; fighter wing 132, Brandenburg, region 8, air_superiority or none",
                         "navy": "GUI_ONLY; one twelve-ship task force; missions and region IDs UNKNOWN",
                         "military_telemetry": "UNKNOWN",
                         "right_drag_backend": "WINDOWS_SENDINPUT; guarded right drag only" if right_drag_attached else "NOT_ATTACHED",
                         "offensive_lines": "GUI_ONLY; selected first army / 1. Panzer-Division / no general; two mainland targets; empty order viewport required",
                         "unsupported_actions": ["move_divisions", "assign_fleet_region", "set_naval_mission"],
                         "live_verified_components": ["army", "frontline", "offensive_line", "plan_switch", "division_supply", "air_assignment_and_mission", "navy_observation"]},
            "additional_gui_actions": ["create_production_line", "delete_production_line", "reorder_production_line",
                                       "build", "cancel_construction", "change_construction_priority",
                                       "change_economy_law", "change_conscription_law", "hire_advisor", "set_trade_import"],
            "gui_observations": ["get_production_lines", "get_construction", "get_advisors", "get_trade_state"],
            "production": {"line_identity": "GUI_ONLY; session-local, not stable game ID",
                           "equipment_type": "GUI_ONLY; visible label matched by template, not game equipment ID",
                           "factory_count": "GUI_ONLY; numeric and grid agreement",
                           "truncated_equipment_labels": "PARTIAL; observation only, actions rejected",
                           "maximum_assignable": "PARTIAL; normal line limit and GUI availability",
                           "efficiency": "UNKNOWN", "current_output": "UNKNOWN",
                           "supported_counts": [0, 15], "viewport": "complete calibrated military list (max 10)" if non_military else "six complete top rows"},
            "trade": {"scope": "SWE steel only", "civilian_factories": [0, 1, 2],
                      "complete_trade_state": False, "telemetry_trade_state": "UNKNOWN"},
            "gui_executor_attached": action_runtime is not None,
            "input_backend": input_backend if gui_window is not None else "NOT_ATTACHED",
            "capture_space": capture_space if gui_window is not None and input_backend == "native" else None,
            "computer_use_required": gui_window is not None and input_backend == "computer-use",
            "input_capabilities": dict(getattr(getattr(action_runtime, "worker", None), "capabilities", {})),
            "input_backend_ready": bool(action_runtime and
                getattr(getattr(action_runtime, "worker", None), "ready", lambda: False)()),
            "unknown_fields": UNKNOWN_FIELDS,
            "notifications": "MCP 2026 subscriptions/listen; older clients can poll get_changes",
        })

    return server


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, default=default_log_path())
    parser.add_argument("--interval", type=float, default=0.25)
    parser.add_argument("--stale-seconds", type=float, default=30)
    parser.add_argument("--gui-window", type=int, help="Explicit existing HOI4 window ID; never launches or activates")
    parser.add_argument("--backend", choices=("native", "computer-use"), default="native",
                        help="Independent Windows native backend (default), or optional Computer Use pump")
    parser.add_argument("--capture-space", choices=("physical", "legacy"), default="physical",
                        help="Native physical pixels (default) or exact calibrated legacy DPI mapping")
    parser.add_argument("--non-military", action="store_true", help="Use current Phase 3 calibration and semantic line operations")
    parser.add_argument("--military", action="store_true", help="Use limited Phase 4 military GUI calibration")
    args = parser.parse_args()
    try:
        server = create_server(args.log, interval=args.interval, stale_seconds=args.stale_seconds,
                               gui_window=args.gui_window, non_military=args.non_military, military=args.military,
                               input_backend=args.backend, capture_space=args.capture_space)
    except ValueError as exc:
        parser.error(str(exc))
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
