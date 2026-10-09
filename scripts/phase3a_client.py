"""Real SDK stdio client for a selected existing HOI4 window; one semantic action."""

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
                                                                   "--gui-window", str(args.window), "--backend", "computer-use"])
    async with Client(transport, read_timeout_seconds=120) as client:
        before = (await client.call_tool("get_summary")).structured_content
        payload = ({"slot": args.slot, "tech_id": args.target} if args.action == "research"
                   else {"focus_id": args.target})
        result = (await client.call_tool("select_" + args.action, payload)).structured_content
        after = (await client.call_tool("get_summary")).structured_content
        evidence = {"source": "LIVE HOI4 / SDK stdio / Computer Use", "before": before,
                    "action_result": result, "after": after}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("research", "focus"))
    parser.add_argument("target")
    parser.add_argument("--slot", type=int, default=0)
    parser.add_argument("--window", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
