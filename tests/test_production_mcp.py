"""The official MCP SDK exposes only semantic production arguments."""

import asyncio
from mcp import Client
from hoi4_operator.mcp_server import create_server


def test_production_tools_are_semantic_and_default_unattached(tmp_path):
    class Fake:
        calls = []
        def get_production_lines(self):
            return {"accepted": True, "status": "confirmed", "lines": [{"line_id": "session-1"}]}
        def set_production_factory_count(self, line_id, factories):
            self.calls.append((line_id, factories))
            return {"accepted": True, "status": "confirmed", "after": {"factories": factories}}
    async def check():
        fake = Fake()
        async with Client(create_server(tmp_path / "missing.log", production_executor=fake)) as client:
            tools = {t.name: t for t in (await client.list_tools()).tools}
            assert tools["get_production_lines"].input_schema["properties"] == {}
            assert set(tools["set_production_factory_count"].input_schema["properties"]) == {"line_id", "factories"}
            assert not tools["get_production_lines"].annotations.read_only_hint  # navigation changes panel
            assert not tools["get_production_lines"].annotations.destructive_hint
            assert (await client.call_tool("get_production_lines")).structured_content["status"] == "confirmed"
            result = (await client.call_tool("set_production_factory_count", {"line_id": "session-1", "factories": 12})).structured_content
            assert result["after"]["factories"] == 12 and fake.calls == [("session-1", 12)]
            assert (await client.call_tool("set_production_factory_count", {"line_id": "session-1", "factories": True})).is_error
        async with Client(create_server(tmp_path / "missing.log")) as client:
            for name, args in [("get_production_lines", {}), ("set_production_factory_count", {"line_id": "session-1", "factories": 12})]:
                assert (await client.call_tool(name, args)).structured_content["reason"] == "executor_not_connected"
    asyncio.run(check())
