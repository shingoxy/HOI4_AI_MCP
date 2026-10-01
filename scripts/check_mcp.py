"""Exercise the local MCP server over stdio; never starts HOI4."""

import argparse
import asyncio
import json
import math
from pathlib import Path
import sys

from mcp import Client
from mcp.client.stdio import StdioServerParameters
from mcp.client.subscriptions import ResourceUpdated


STATE_URI = "hoi4://state/current"


def emit_json(value: dict) -> None:
    print(json.dumps(value, ensure_ascii=False), flush=True)


async def watch(client: Client, seconds: float, emit=emit_json) -> None:
    """Keep one server session alive; report notifications and refetched changes."""
    counts = {"notifications": 0, "state_updated": 0, "timeline_reset": 0,
              "log_reset": 0, "stale_seen": False}
    async with client.listen(resource_subscriptions=[STATE_URI]) as subscription:
        baseline = (await client.call_tool("get_summary")).structured_content
        cursor = baseline["revision"]
        emit({"event": "baseline", "summary": baseline})
        try:
            async with asyncio.timeout(seconds):
                async for notification in subscription:
                    if not isinstance(notification, ResourceUpdated) or notification.uri != STATE_URI:
                        continue
                    summary = json.loads((await client.read_resource(STATE_URI)).contents[0].text)
                    reply = await client.call_tool("get_changes", {"after_revision": cursor})
                    if reply.is_error:
                        raise RuntimeError(f"get_changes: {reply.content}")
                    changes = reply.structured_content
                    cursor = changes["latest_revision"]
                    counts["notifications"] += 1
                    for event in changes["events"]:
                        counts[event["kind"]] += 1
                    counts["stale_seen"] |= summary["status"] == "stale"
                    emit({"event": "resource_updated", "summary": summary, "changes": changes})
        except TimeoutError:
            pass
    emit({"event": "watch_finished", "counts": counts,
          "diagnostics": (await client.call_tool("get_diagnostics")).structured_content})


async def check(log_path: Path | None, watch_seconds: float | None = None) -> dict:
    script = Path(__file__).resolve().with_name("run_mcp.py")
    args = [str(script)]
    if log_path is not None:
        args += ["--log", str(log_path)]
    transport = StdioServerParameters(command=sys.executable, args=args)
    async with Client(transport, read_timeout_seconds=10) as client:
        result = {"tools": [tool.name for tool in (await client.list_tools()).tools]}
        for name in ("get_summary", "get_politics", "get_industry", "get_research", "get_focus", "get_changes", "get_diagnostics"):
            reply = await client.call_tool(name)
            if reply.is_error:
                raise RuntimeError(f"{name}: {reply.content}")
            result[name] = reply.structured_content
        if watch_seconds is not None:
            await watch(client, watch_seconds)
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--watch", type=float, metavar="SECONDS",
                        help="Subscribe in one server session for this many seconds (JSON lines)")
    args = parser.parse_args()
    if args.watch is not None and (not math.isfinite(args.watch) or args.watch <= 0):
        parser.error("--watch must be finite and positive")
    try:
        result = asyncio.run(check(args.log, args.watch))
    except KeyboardInterrupt:
        return
    if args.watch is None:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
