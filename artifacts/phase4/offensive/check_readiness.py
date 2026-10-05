"""Read-only attachment/profile evidence; never submits a game action."""

import asyncio
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
from PIL import Image
from mcp import Client
from mcp.client.stdio import StdioServerParameters

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from hoi4_operator.executor.guard import ActionError, WindowsProbe
from hoi4_operator.executor.right_drag import WindowsRightMouse
from hoi4_operator.executor.ui_state import UIState


async def main():
    evidence = {"source": "official SDK stdio metadata and read-only Windows/profile checks",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "offensive_confirmed": 0, "offensive_required": 2,
                "game_action_calls": 0, "native_input_calls": 0, "retry_count": 0,
                "phase4_status": "IN PROGRESS"}
    hwnd = 659082
    probe = WindowsProbe()
    evidence["window"] = {"hwnd": hwnd, "pid": probe.pid(hwnd),
                          "guard_reason": probe.check(hwnd, probe.pid(hwnd))}
    mouse = WindowsRightMouse(hwnd)
    rect = wintypes.RECT()
    mouse.user.GetClientRect(hwnd, ctypes.byref(rect))
    evidence["client_size"] = [rect.right, rect.bottom]
    try:
        mouse.prepare((1200, 500), (1500, 600))
        evidence["native_geometry_precheck"] = "accepted; no input submitted"
    except ActionError as exc:
        evidence["native_geometry_precheck"] = {"status": exc.status, "reason": exc.reason}
    rgb = np.array(Image.open(OUT / "captures/final-paused.jpg").convert("RGB"))
    evidence["capture_size"] = [rgb.shape[1], rgb.shape[0]]
    try:
        UIState(SimpleNamespace(capture=lambda: rgb), None).capture()
        evidence["saved_capture_reader"] = "accepted"
    except ActionError as exc:
        evidence["saved_capture_reader"] = {"status": exc.status, "reason": exc.reason,
            "source": "offline replay of current real screenshot; no GUI navigation"}
    transport = StdioServerParameters(command=sys.executable,
        args=[str(ROOT / "scripts/run_mcp.py"), "--gui-window", str(hwnd), "--military"])
    async with Client(transport, read_timeout_seconds=30) as client:
        tools = (await client.list_tools()).tools
        evidence["tool_names"] = [tool.name for tool in tools]
        offensive = next(tool for tool in tools if tool.name == "create_offensive_line")
        evidence["offensive_input_schema"] = offensive.input_schema
        evidence["capabilities"] = json.loads((await client.read_resource(
            "hoi4://telemetry/capabilities")).contents[0].text)
        evidence["telemetry"] = (await client.call_tool("get_summary")).structured_content
    baseline = json.loads((OUT / "baseline-files.json").read_text(encoding="utf-8"))
    final_hashes = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in baseline}
    evidence["save_and_mod_files"] = {"checked": len(baseline), "unchanged": baseline == final_hashes}
    (OUT / "final-files.json").write_text(json.dumps(final_hashes, indent=2), encoding="utf-8")
    (OUT / "readiness.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"tools": len(evidence["tool_names"]),
        "native_geometry": evidence["native_geometry_precheck"],
        "capture_reader": evidence["saved_capture_reader"],
        "file_hashes": evidence["save_and_mod_files"],
        "right_drag_backend": evidence["capabilities"]["military"]["right_drag_backend"]}))


if __name__ == "__main__":
    asyncio.run(main())
