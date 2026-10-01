"""Real SDK production session; snapshot, three changes and normal restoration."""

import argparse
import asyncio
import json
from pathlib import Path
import sys

from mcp import Client
from mcp.client.stdio import StdioServerParameters


async def run(args):
    root = Path(__file__).resolve().parents[1]
    transport = StdioServerParameters(command=sys.executable, args=[str(root / "scripts/run_mcp.py"),
                                                                   "--gui-window", str(args.window)])
    evidence = {"source": "LIVE HOI4 / official SDK stdio / semantic Executor / Computer Use",
                "actions": []}
    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    async with Client(transport, read_timeout_seconds=120) as client:
        evidence["before_telemetry"] = (await client.call_tool("get_summary")).structured_content
        snapshot = (await client.call_tool("get_production_lines")).structured_content
        evidence["initial_snapshot"] = snapshot
        save()
        if snapshot["status"] != "confirmed" or args.snapshot_only:
            print(json.dumps(snapshot, ensure_ascii=False), flush=True)
            return
        first, second = snapshot["lines"][:2]
        original_a, original_b = first["factories"], second["factories"]
        # A increases, B decreases, C changes a different real line.
        requests = [("A", first, original_a+2), ("B", first, original_a),
                    ("C", second, original_b+1), ("RESTORE", second, original_b)]
        for label, line, count in requests:
            result = (await client.call_tool("set_production_factory_count", {
                "line_id": line["line_id"], "factories": count})).structured_content
            evidence["actions"].append({"test": label, "result": result})
            save()
            print(json.dumps({"test": label, "status": result["status"], "reason": result.get("reason"),
                              "duration_ms": result["duration_ms"]}, ensure_ascii=False), flush=True)
            if result["status"] != "confirmed":
                break
        evidence["final_snapshot"] = (await client.call_tool("get_production_lines")).structured_content
        evidence["after_telemetry"] = (await client.call_tool("get_summary")).structured_content
        save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--snapshot-only", action="store_true")
    asyncio.run(run(parser.parse_args()))
