"""Bounded official SDK military validation; persist every action before continuing."""

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
    evidence = {"source": "LIVE HOI4 / official SDK stdio / military semantic API / normal GUI", "actions": []}
    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    def resolve(value, snapshot):
        if isinstance(value, str) and value.startswith("$snapshot."):
            current = snapshot
            for field in value.split(".")[1:]:
                current = current[int(field)] if isinstance(current,list) else current[field]
            return current
        if isinstance(value,list): return [resolve(item,snapshot) for item in value]
        if isinstance(value,dict): return {key:resolve(item,snapshot) for key,item in value.items()}
        return value
    transport = StdioServerParameters(command=sys.executable, args=[str(root/"scripts/run_mcp.py"),
        "--gui-window", str(args.window), "--backend", "computer-use", "--military"])
    async with Client(transport, read_timeout_seconds=180) as client:
        evidence["tool_names"] = [tool.name for tool in (await client.list_tools()).tools]
        deadline = time.monotonic()+120
        while time.monotonic() < deadline:
            capabilities = json.loads((await client.read_resource("hoi4://telemetry/capabilities")).contents[0].text)
            if capabilities["input_backend_ready"]: break
            await asyncio.sleep(.25)
        else:
            evidence["harness_stop"] = "backend_unavailable"
            save()
            return
        evidence["capabilities"] = capabilities
        # A normal load needs two forward daily frames on the new timeline.
        # Observe readiness before actions; never relax the executor's freshness guard.
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            baseline=(await client.call_tool("get_summary")).structured_content
            if baseline and baseline.get("status")=="fresh" and baseline.get("freshness_basis")=="frame_received_at":
                break
            await asyncio.sleep(.5)
        else:
            evidence["harness_stop"]="telemetry_not_fresh"
            save()
            return
        evidence["before_telemetry"] = baseline
        snapshot = None
        for step in plan:
            arguments = resolve(step.get("arguments",{}),snapshot)
            reply = await client.call_tool(step["action"],arguments)
            result = reply.structured_content or {"status":"rejected","reason":"mcp_tool_error",
                "error":str(reply.content)}
            evidence["actions"].append({"action":step["action"],"arguments":arguments,"result":result})
            save()
            print(json.dumps({"action":step["action"],"status":result.get("status"),"reason":result.get("reason"),
                              "duration_ms":result.get("duration_ms")}),flush=True)
            if result.get("status") not in step.get("expected",["confirmed","already_satisfied"]): return
            if "after" in result: snapshot=result["after"]
            elif "divisions" in result or "air_wings" in result or "fleets" in result: snapshot=result
        evidence["after_telemetry"] = (await client.call_tool("get_summary")).structured_content
        save()


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window",type=int,required=True)
    parser.add_argument("--plan",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    asyncio.run(run(parser.parse_args()))
