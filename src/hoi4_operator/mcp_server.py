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
                  gui_window: int | None = None) -> MCPServer:
    if not math.isfinite(interval) or interval <= 0:
        raise ValueError("interval must be finite and positive")
    if not math.isfinite(stale_seconds) or stale_seconds <= 0:
        raise ValueError("stale_seconds must be finite and positive")
    bus = InMemorySubscriptionBus()
    runtime: ReadModel | None = None
    action_runtime = executor
    production_runtime = production_executor

    async def watch(model: ReadModel) -> None:
        while True:
            await anyio.sleep(interval)
            if model.poll():
                await bus.publish(ResourceUpdated(uri=STATE_URI))

    @asynccontextmanager
    async def lifespan(server: MCPServer):
        nonlocal runtime, action_runtime, production_runtime
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
            from .executor.worker import ComputerUseWorker
            root = Path(__file__).resolve().parents[2]
            probe = WindowsProbe()
            worker = ComputerUseWorker(gui_window, probe.pid(gui_window), probe=probe,
                                       endpoint_file=root / "artifacts/phase3a/runtime/endpoint.json")
            # Independent reader: executor's thread never races the MCP watcher.
            action_model = ReadModel(log_path, stale_seconds=stale_seconds)
            action_runtime = Executor(action_model, worker,
                                      UIState(worker, Templates(root / "artifacts/phase3a/templates")))
            production_runtime = ProductionExecutor(action_runtime, ProductionUI(
                action_runtime.ui, Templates(root / "artifacts/phase3b1/templates")))
        async with anyio.create_task_group() as tasks:
            tasks.start_soon(watch, model)
            try:
                yield model
            finally:
                tasks.cancel_scope.cancel()
                runtime = None
                if worker:
                    worker.close()
                    action_runtime = None
                    production_runtime = None

    server = MCPServer(
        "HOI4 Telemetry and GUI PoC", version="0.5.0", lifespan=lifespan,
        subscriptions=bus,
        instructions=(
            "Reads Germany telemetry. select_research/select_focus are normal GUI actions "
            "requiring an explicitly attached local Computer Use worker and fresh v2 telemetry. "
            "Only three tracked technologies and Rhineland are supported at 2560x1080/1.0. "
            "Production supports get_production_lines and set_production_factory_count: "
            "six calibrated visible military lines, GUI session-local IDs and counts 0..15; "
            "truncated equipment labels are observation-only and reject assignment. "
            "Snapshots expire or become invalid on changed order/identity/count. "
            "No launch, console, effects, line creation/reordering or military unit actions. "
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

    @server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False,
                                            idempotent_hint=True, open_world_hint=False), structured_output=True)
    async def get_production_lines() -> dict[str, Any]:
        """Open normal Production UI and read six calibrated visible rows. Generates temporary session IDs; replaces prior snapshot. No factory changes."""
        if production_runtime is None:
            return {"accepted": False, "status": "rejected", "reason": "executor_not_connected"}
        return await anyio.to_thread.run_sync(production_runtime.get_production_lines)

    @server.tool(annotations=gui_action, structured_output=True)
    async def set_production_factory_count(line_id: str, factories: Annotated[int, Field(strict=True)]) -> dict[str, Any]:
        """Adjust factories through normal GUI using an ID from this session's latest production snapshot. Confirm exact count through numeric and grid readback."""
        if production_runtime is None:
            return {"accepted": False, "status": "rejected", "reason": "executor_not_connected"}
        return await anyio.to_thread.run_sync(production_runtime.set_production_factory_count, line_id, factories)

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
            "read_only": action_runtime is None and production_runtime is None, "telemetry_read_only": True,
            "country": "GER", "protocol_version": 2,
            "accepted_protocol_versions": [1, 2],
            "available": ["politics", "manpower", "factory_totals", "research_slots",
                          "tracked_technology_predicates", "tracked_focus_progress_interval"],
            "tracked_technologies": TRACKED_TECHS, "tracked_focus": TRACKED_FOCUS,
            "extended_fields_live_verified": True,
            "gui_actions": ["select_research", "select_focus", "set_production_factory_count"],
            "gui_observations": ["get_production_lines"],
            "production": {"line_identity": "GUI_ONLY; session-local, not stable game ID",
                           "equipment_type": "GUI_ONLY; visible label matched by template, not game equipment ID",
                           "factory_count": "GUI_ONLY; numeric and grid agreement",
                           "truncated_equipment_labels": "PARTIAL; observation only, actions rejected",
                           "maximum_assignable": "PARTIAL; normal line limit and GUI availability",
                           "efficiency": "UNKNOWN", "current_output": "UNKNOWN",
                           "supported_counts": [0, 15], "viewport": "six complete top rows"},
            "gui_executor_attached": action_runtime is not None,
            "unknown_fields": UNKNOWN_FIELDS,
            "notifications": "MCP 2026 subscriptions/listen; older clients can poll get_changes",
        })

    return server


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, default=default_log_path())
    parser.add_argument("--interval", type=float, default=0.25)
    parser.add_argument("--stale-seconds", type=float, default=30)
    parser.add_argument("--gui-window", type=int, help="Explicit existing HOI4 window ID; requires Computer Use pump")
    args = parser.parse_args()
    try:
        server = create_server(args.log, interval=args.interval, stale_seconds=args.stale_seconds,
                               gui_window=args.gui_window)
    except ValueError as exc:
        parser.error(str(exc))
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
