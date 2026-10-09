"""SDK lifecycle proves native/optional-CU selection without real Windows input."""
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mcp import Client
from hoi4_operator.mcp_server import create_server


def test_default_native_sdk_does_not_create_computer_use_bridge(tmp_path, monkeypatch):
    from hoi4_operator.executor import guard, windows_native, worker
    from test_windows_native import Desktop, Probe
    class NativeProbe(Probe):
        def pid(self, hwnd): return 2
    class NativeDesktop(Desktop):
        def __init__(self, hwnd): super().__init__()
    def forbidden(*args, **kwargs): raise AssertionError("Computer Use bridge must not be started")
    monkeypatch.setattr(guard, "WindowsProbe", NativeProbe)
    monkeypatch.setattr(windows_native, "WindowsDesktop", NativeDesktop)
    monkeypatch.setattr(worker, "ComputerUseWorker", forbidden)
    async def check():
        async with Client(create_server(tmp_path/"missing.log", gui_window=1, military=True)) as client:
            tools = (await client.list_tools()).tools
            assert len(tools) == 52
            caps = json.loads((await client.read_resource("hoi4://telemetry/capabilities")).contents[0].text)
            assert caps["input_backend"] == "native" and not caps["computer_use_required"]
            assert caps["input_capabilities"]["right_drag"] and caps["input_backend_ready"]
            assert caps["capture_space"] == "physical"
            state = (await client.call_tool("get_summary")).structured_content
            assert state["status"] == "unavailable"
    asyncio.run(check())


def test_computer_use_backend_remains_explicit_optional(tmp_path, monkeypatch):
    from hoi4_operator.executor import guard, worker
    from test_windows_native import Probe
    created = []
    class CUProbe(Probe):
        def pid(self, hwnd): return 2
    class CU:
        capabilities = {"right_drag": False, "capture": True}
        def __init__(self, *args, **kwargs): created.append("created")
        def ready(self): return True
        def close(self): created.append("closed")
    monkeypatch.setattr(guard, "WindowsProbe", CUProbe)
    monkeypatch.setattr(worker, "ComputerUseWorker", CU)
    async def check():
        async with Client(create_server(tmp_path/"missing.log", gui_window=1,
                                       input_backend="computer-use")) as client:
            caps = json.loads((await client.read_resource("hoi4://telemetry/capabilities")).contents[0].text)
            assert caps["computer_use_required"] and caps["input_backend"] == "computer-use"
            assert caps["capture_space"] is None
    asyncio.run(check())
    assert created == ["created", "closed"]
