"""Both ordinary Python and MCP callers see semantic parameters only."""

import asyncio
from mcp import Client

from test_production_lines import setup
from hoi4_operator.operator import OperatorAPI
from hoi4_operator.mcp_server import create_server


def test_python_api_dispatch_and_reject_raw_input_arguments():
    service, ui, _, _ = setup()
    api = OperatorAPI(service.executor.model, production=service)
    for action, arguments in [("click", {"x": 1, "y": 2}),
                              ("create_production_line", {"equipment_id": "infantry_equipment_1", "x": 42}),
                              ([], {}), ("create_production_line", [])]:
        assert api.execute(action, arguments)["status"] == "rejected"
    assert ui.submits == 0
    assert api.execute("create_production_line", {"equipment_id": "support_equipment_1"})["status"] == "confirmed"


def test_mcp_line_actions_semantic_schema_and_reject_unattached(tmp_path):
    async def check():
        async with Client(create_server(tmp_path / "missing.log")) as client:
            tools = {tool.name: tool for tool in (await client.list_tools()).tools}
            expected = {"create_production_line": {"equipment_id"},
                        "delete_production_line": {"line_id"},
                        "reorder_production_line": {"line_id", "direction"},
                        "get_construction": set(), "build": {"state_id", "building_type", "count"},
                        "cancel_construction": {"queue_item_id"}, "change_construction_priority": {"queue_item_id", "direction"},
                        "change_economy_law": {"law_id"}, "change_conscription_law": {"law_id"},
                        "get_advisors": set(), "hire_advisor": {"advisor_id"},
                        "get_trade_state": set(), "set_trade_import": {"resource", "country", "civilian_factories"}}
            for name, fields in expected.items():
                assert set(tools[name].input_schema["properties"]) == fields
            assert not tools["create_production_line"].annotations.idempotent_hint
            result = (await client.call_tool("create_production_line", {"equipment_id": "support_equipment_1"})).structured_content
            assert result["reason"] == "backend_unavailable"
    asyncio.run(check())


def test_trade_python_and_mcp_contract(tmp_path):
    from test_trade import setup as trade_setup
    service, ui, _ = trade_setup()
    api = OperatorAPI(service.executor.model, trade=service)
    arguments = {"resource": "steel", "country": "SWE", "civilian_factories": 1}
    assert api.execute("set_trade_import", {**arguments, "x": 42})["reason"] == "invalid_arguments"
    assert api.execute("set_trade_import", arguments)["status"] == "confirmed"
    async def check():
        async with Client(create_server(tmp_path/"missing.log", trade_executor=service)) as client:
            result = (await client.call_tool("set_trade_import", arguments)).structured_content
            assert result["status"] == "already_satisfied"
            assert (await client.call_tool("set_trade_import", {**arguments, "civilian_factories": True})).is_error
            assert (await client.call_tool("get_trade_state")).structured_content["status"] == "confirmed"
        async with Client(create_server(tmp_path/"missing.log")) as client:
            assert (await client.call_tool("set_trade_import", arguments)).structured_content["reason"] == "backend_unavailable"
    asyncio.run(check())
    assert ui.calls == 1
