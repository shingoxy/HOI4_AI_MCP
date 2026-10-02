"""MCP protocol checks with the official SDK and a real stdio subprocess."""

import asyncio
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_telemetry import frame
from test_read_model import append
from test_extended_telemetry import extended_frame


HAS_MCP = importlib.util.find_spec("mcp") is not None
if HAS_MCP:
    from mcp import Client
    from mcp.client.subscriptions import ResourceUpdated
    from hoi4_operator.mcp_server import create_server, STATE_URI
    check_spec = importlib.util.spec_from_file_location(
        "check_mcp", Path(__file__).resolve().parents[1] / "scripts" / "check_mcp.py"
    )
    check_mcp = importlib.util.module_from_spec(check_spec)
    check_spec.loader.exec_module(check_mcp)


@unittest.skipUnless(HAS_MCP, "Install requirements-dev.txt to run MCP protocol tests")
class MCPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "game.log"

    async def test_tools_and_resources_missing_log_and_read_only_annotations(self):
        server = create_server(self.path, interval=0.02)
        async with Client(server) as client:
            tools = (await client.list_tools()).tools
            self.assertEqual({t.name for t in tools}, {
                "get_summary", "get_politics", "get_industry", "get_research", "get_focus", "get_changes", "get_diagnostics",
                "select_research", "select_focus", "get_production_lines", "set_production_factory_count",
                "get_equipment_catalog", "create_production_line", "delete_production_line", "reorder_production_line",
                "get_construction", "build", "cancel_construction", "change_construction_priority",
                "change_economy_law", "change_conscription_law", "get_advisors", "hire_advisor",
                "get_trade_state", "set_trade_import",
            })
            self.assertTrue(all(t.annotations.read_only_hint for t in tools if t.name.startswith("get_") and
                                t.name not in {"get_production_lines", "get_construction", "get_advisors", "get_trade_state"}))
            self.assertFalse(next(t for t in tools if t.name == "get_production_lines").annotations.read_only_hint)
            self.assertTrue(all(not t.annotations.read_only_hint for t in tools if t.name.startswith("select_")))
            rejected = (await client.call_tool("select_focus", {"focus_id": "GER_remilitarize_the_rhineland"})).structured_content
            self.assertEqual(rejected["reason"], "executor_not_connected")
            result = await client.call_tool("get_summary")
            self.assertFalse(result.is_error)
            self.assertEqual(result.structured_content["status"], "unavailable")
            self.assertIsNone(result.structured_content["state"])
            resource = await client.read_resource(STATE_URI)
            self.assertEqual(json.loads(resource.contents[0].text)["status"], "unavailable")
            industry = (await client.call_tool("get_industry")).structured_content
            self.assertEqual(industry["production_lines"]["status"], "UNKNOWN")
            self.assertTrue((await client.call_tool("get_changes", {"after_revision": -1})).is_error)
            self.assertTrue((await client.call_tool("get_changes", {"after_revision": True})).is_error)
            self.assertTrue((await client.call_tool("nonexistent")).is_error)
        self.assertFalse(self.path.exists())

    async def test_subscription_refetch_and_changes_on_new_frame(self):
        append(self.path, frame(date="1 1月, 1936"))
        server = create_server(self.path, interval=0.02)
        async with Client(server) as client:
            async with client.listen(resource_subscriptions=[STATE_URI]) as subscription:
                append(self.path, frame(706641, pp="54", date="2 1月, 1936"))
                event = await asyncio.wait_for(anext(subscription), timeout=3)
                self.assertIsInstance(event, ResourceUpdated)
                self.assertEqual(event.uri, STATE_URI)
                result = json.loads((await client.read_resource(event.uri)).contents[0].text)
                self.assertEqual(result["latest_seq"], 706641)
                self.assertEqual(result["game_date"], "2 1月, 1936")
                changes = (await client.call_tool("get_changes")).structured_content
                self.assertEqual(changes["events"][0]["fields"]["politics.political_power"]["after"], 54)
                again = (await client.call_tool("get_changes")).structured_content
                self.assertEqual(changes, again)

    async def test_extended_sections_after_protocol_upgrade_notify_and_keep_unknowns(self):
        append(self.path, frame())
        async with Client(create_server(self.path, interval=0.02)) as client:
            legacy = (await client.call_tool("get_research")).structured_content
            self.assertEqual(legacy["section_status"], "unavailable")
            async with client.listen(resource_subscriptions=[STATE_URI]) as subscription:
                append(self.path, extended_frame(706641, researching_construction1="1"))
                await asyncio.wait_for(anext(subscription), timeout=3)
                research = (await client.call_tool("get_research")).structured_content
                focus = (await client.call_tool("get_focus")).structured_content
                self.assertEqual(research["research"]["slot_count"], 4)
                self.assertTrue(research["research"]["tracked_technologies"][1]["researching"])
                self.assertEqual(research["slot_assignment"]["status"], "UNKNOWN")
                self.assertEqual(focus["focus"]["progress_lower_bound"], 0.2)
                self.assertEqual(focus["current_focus"]["status"], "UNKNOWN")
                changes = (await client.call_tool("get_changes")).structured_content
                self.assertEqual(changes["events"][0]["fields"]["research.slot_count"]["after"], 4)

    async def test_fresh_to_stale_notifies_without_a_new_frame(self):
        append(self.path, frame())
        async with Client(create_server(self.path, interval=0.02, stale_seconds=0.5)) as client:
            async with client.listen(resource_subscriptions=[STATE_URI]) as subscription:
                self.assertEqual((await client.call_tool("get_summary")).structured_content["status"], "fresh")
                await asyncio.wait_for(anext(subscription), timeout=3)
                result = (await client.call_tool("get_summary")).structured_content
                self.assertEqual(result["status"], "stale")
                self.assertEqual(result["revision"], 0)

    async def test_live_check_watch_reports_rollback_and_stale(self):
        append(self.path, frame(706650, date="11 1月, 1936"))
        records = []
        baseline = asyncio.Event()

        def emit(record):
            records.append(record)
            if record["event"] == "baseline":
                baseline.set()

        async with Client(create_server(self.path, interval=0.02, stale_seconds=0.2)) as client:
            task = asyncio.create_task(check_mcp.watch(client, 0.6, emit))
            try:
                await asyncio.wait_for(baseline.wait(), timeout=3)
                append(self.path, frame(706645, date="6 1月, 1936"),
                       frame(706646, date="7 1月, 1936"),
                       frame(706647, date="8 1月, 1936"))
                await asyncio.wait_for(task, timeout=3)
            finally:
                if not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
        result = records[-1]
        self.assertEqual(result["event"], "watch_finished")
        self.assertEqual(result["counts"]["timeline_reset"], 1)
        self.assertEqual(result["counts"]["state_updated"], 1)
        self.assertTrue(result["counts"]["stale_seen"])
        self.assertEqual(result["diagnostics"]["latest_seq"], 706647)
        self.assertEqual(result["diagnostics"]["parser_errors"], [])

    async def test_live_check_watch_times_out_without_claiming_updates(self):
        append(self.path, frame())
        records = []
        async with Client(create_server(self.path, interval=0.02)) as client:
            await asyncio.wait_for(check_mcp.watch(client, 0.08, records.append), timeout=3)
        self.assertEqual([record["event"] for record in records], ["baseline", "watch_finished"])
        self.assertEqual(records[-1]["counts"]["notifications"], 0)
        self.assertFalse(records[-1]["counts"]["stale_seen"])

    async def test_legacy_initialize_tools_and_utf8_over_stdio(self):
        append(self.path, frame(date="1 1月, 1936"))
        before = self.path.read_bytes(), self.path.stat().st_mtime_ns
        requests = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2025-11-25", "capabilities": {},
                "clientInfo": {"name": "phase2b-test", "version": "1"},
            }},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "get_summary", "arguments": {}}},
        ]
        script = Path(__file__).resolve().parents[1] / "scripts" / "run_mcp.py"
        process = await asyncio.create_subprocess_exec(
            sys.executable, str(script), "--log", str(self.path),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        responses = {}
        try:
            for request in requests:
                process.stdin.write((json.dumps(request) + "\n").encode("utf-8"))
                await process.stdin.drain()
                if "id" in request:
                    line = await asyncio.wait_for(process.stdout.readline(), timeout=5)
                    self.assertTrue(line, "MCP server closed stdout before responding")
                    response = json.loads(line)
                    self.assertEqual(response["id"], request["id"])
                    responses[response["id"]] = response
        finally:
            process.stdin.close()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
        self.assertEqual(process.returncode, 0)
        self.assertEqual(responses[1]["result"]["protocolVersion"], "2025-11-25")
        self.assertEqual(len(responses[2]["result"]["tools"]), 25)
        self.assertEqual(responses[3]["result"]["structuredContent"]["game_date"], "1 1月, 1936")
        self.assertEqual(before, (self.path.read_bytes(), self.path.stat().st_mtime_ns))


if __name__ == "__main__":
    unittest.main()
