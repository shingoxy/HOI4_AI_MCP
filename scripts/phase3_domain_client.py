"""Official SDK semantic test plans; each bounded plan persists every result."""

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
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    evidence = {"source": "LIVE HOI4 / official SDK stdio / semantic API / normal GUI", "actions": []}
    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    transport = StdioServerParameters(command=sys.executable, args=[str(root/"scripts/run_mcp.py"),
        "--gui-window", str(args.window), "--non-military"])
    async with Client(transport, read_timeout_seconds=180) as client:
        deadline = time.monotonic()+240
        while time.monotonic() < deadline:
            capabilities = json.loads((await client.read_resource("hoi4://telemetry/capabilities")).contents[0].text)
            if capabilities["input_backend_ready"]: break
            await asyncio.sleep(.25)
        else:
            evidence["harness_stop"] = "backend_unavailable"
            save()
            return
        # Backend readiness does not imply a new daily frame after unpausing.
        # Wait for the existing freshness contract; never relax the guard.
        fresh_deadline = time.monotonic()+30
        while True:
            evidence["before_telemetry"] = (await client.call_tool("get_summary")).structured_content
            if evidence["before_telemetry"].get("status") == "fresh":
                break
            if time.monotonic() >= fresh_deadline:
                evidence["harness_stop"] = "telemetry_stale"
                save()
                return
            await asyncio.sleep(.25)
        snapshot = None
        for step in plan:
            arguments = dict(step.get("arguments", {}))
            for key, value in list(arguments.items()):
                if isinstance(value, str) and value.startswith("$snapshot."):
                    resolved = snapshot
                    for field in value.split(".")[1:]:
                        resolved = resolved[int(field)] if isinstance(resolved, list) else resolved[field]
                    arguments[key] = resolved
            result = (await client.call_tool(step["action"], arguments)).structured_content
            evidence["actions"].append({"action": step["action"], "arguments": arguments, "result": result})
            save()
            print(json.dumps({"action": step["action"], "status": result.get("status"),
                              "reason": result.get("reason"), "duration_ms": result.get("duration_ms")}), flush=True)
            if result.get("status") not in step.get("expected", ["confirmed", "already_satisfied"]): return
            snapshot = result.get("after", result)
        evidence["after_telemetry"] = (await client.call_tool("get_summary")).structured_content
        save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window", type=int, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(run(parser.parse_args()))
