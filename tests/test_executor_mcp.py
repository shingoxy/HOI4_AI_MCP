"""Semantic MCP arguments reach the executor without a coordinate API."""

import asyncio
import json

from mcp import Client
from hoi4_operator.mcp_server import create_server


def test_action_tools_call_executor_and_preserve_structured_status(tmp_path):
    class Fake:
        calls = []
        def select_research(self, slot, tech_id):
            self.calls.append((slot, tech_id))
            return {"accepted": True, "status": "confirmed", "action_id": "offline",
                    "duration_ms": 2, "telemetry_confirmation": {"source": "FAKE"}}
        def select_focus(self, focus_id):
            self.calls.append(focus_id)
            return {"accepted": False, "status": "rejected", "reason": "invalid_focus_id"}
    executor = Fake()
    async def check():
        async with Client(create_server(tmp_path / "missing.log", executor=executor)) as client:
            tools = {t.name: t for t in (await client.list_tools()).tools}
            assert set(tools["select_research"].input_schema["properties"]) == {"slot", "tech_id"}
            assert set(tools["select_focus"].input_schema["properties"]) == {"focus_id"}
            assert tools["select_research"].annotations.destructive_hint
            capabilities = json.loads((await client.read_resource("hoi4://telemetry/capabilities")).contents[0].text)
            assert capabilities["telemetry_read_only"] and not capabilities["read_only"]
            assert capabilities["gui_executor_attached"]
            research = (await client.call_tool("select_research", {"slot": 0, "tech_id": "construction1"})).structured_content
            focus = (await client.call_tool("select_focus", {"focus_id": "invalid"})).structured_content
            assert research["status"] == "confirmed" and focus["status"] == "rejected"
            assert executor.calls == [(0, "construction1"), "invalid"]
    asyncio.run(check())
