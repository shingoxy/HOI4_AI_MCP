"""Official SDK live harness, semantic line operations and incremental evidence."""

import argparse
import asyncio
import json
from pathlib import Path
import sys
import time

from mcp import Client
from mcp.client.stdio import StdioServerParameters


async def run(args):
    root = Path(__file__).resolve().parents[1]
    transport = StdioServerParameters(command=sys.executable, args=[str(root / "scripts/run_mcp.py"),
        "--gui-window", str(args.window), "--non-military"])
    evidence = {"source": "LIVE HOI4 / official SDK stdio / semantic API / normal GUI", "actions": []}
    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    async with Client(transport, read_timeout_seconds=180) as client:
        async def call(name, arguments=None):
            result = (await client.call_tool(name, arguments or {})).structured_content
            evidence["actions"].append({"action": name, "arguments": arguments or {}, "result": result})
            save()
            print(json.dumps({"action": name, "status": result.get("status"), "reason": result.get("reason"),
                              "duration_ms": result.get("duration_ms")}), flush=True)
            return result
        # Administrative startup waits for vendor-neutral readiness. This does
        # not arm an action or relax bridge/watchdog/action timeouts.
        deadline = time.monotonic()+240
        while time.monotonic() < deadline:
            capabilities = json.loads((await client.read_resource("hoi4://telemetry/capabilities")).contents[0].text)
            if capabilities["input_backend_ready"]:
                break
            await asyncio.sleep(0.25)
        else:
            evidence["harness_stop"] = "backend_unavailable"
            save()
            return
        evidence["before_telemetry"] = (await client.call_tool("get_summary")).structured_content
        save()
        snapshot = await call("get_production_lines")
        if snapshot["status"] != "confirmed" or args.snapshot_only:
            return
        for equipment in ([] if args.resume_created else ["infantry_equipment_1", "support_equipment_1"]):
            result = await call("create_production_line", {"equipment_id": equipment})
            if result["status"] != "confirmed":
                return
            snapshot = result["after"]
        first = snapshot["lines"][0]
        if not args.cleanup_only:
            result = await call("reorder_production_line", {"line_id": first["line_id"], "direction": "down"})
            if result["status"] != "confirmed":
                return
            snapshot = result["after"]
            result = await call("reorder_production_line", {"line_id": snapshot["lines"][1]["line_id"], "direction": "up"})
            if result["status"] != "confirmed":
                return
            snapshot = result["after"]
        # Newly-created lines are identified by the exact before/after diff and
        # returned snapshot, not remembered screen positions or stale IDs.
        for equipment in ["infantry_equipment_1", "support_equipment_1"]:
            matches = [line for line in snapshot["lines"] if line["equipment_id"] == equipment and line["factories"] < 2]
            if len(matches) != 1:
                evidence["harness_stop"] = "ambiguous_created_line"
                save()
                return
            result = await call("delete_production_line", {"line_id": matches[0]["line_id"]})
            if result["status"] != "confirmed":
                return
            snapshot = result["after"]
        evidence["final_snapshot"] = await call("get_production_lines")
        evidence["after_telemetry"] = (await client.call_tool("get_summary")).structured_content
        save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--snapshot-only", action="store_true")
    parser.add_argument("--resume-created", action="store_true", help="Verify/reorder/delete the two previously confirmed test lines without creating again")
    parser.add_argument("--cleanup-only", action="store_true")
    asyncio.run(run(parser.parse_args()))
