"""Loopback bridge authorization and command expiration; no Computer Use input."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hoi4_operator.executor.guard import ActionError
from hoi4_operator.executor.worker import ComputerUseWorker


class Probe:
    reason = None
    def check(self, *_):
        return self.reason


@pytest.fixture
def worker(tmp_path):
    result = ComputerUseWorker(1, 1, endpoint_file=tmp_path / "endpoint.json", probe=Probe())
    yield result
    result.close()
    assert not (tmp_path / "endpoint.json").exists()


def post(worker, path, body, *, token=None):
    request = Request(f"http://127.0.0.1:{worker.server.server_port}" + path,
                      data=json.dumps(body).encode(), headers={
                          "Authorization": "Bearer " + (token or worker.token),
                          "Content-Type": "application/json"})
    with urlopen(request, timeout=2) as response:
        return json.load(response)


def test_unknown_commands_and_malformed_requests_rejected(worker):
    with pytest.raises(HTTPError) as unauthorized:
        post(worker, "/next", {}, token="wrong")
    assert unauthorized.value.code == 403
    for body in ({"id": "invented"}, []):
        with pytest.raises(HTTPError) as invalid:
            post(worker, "/permit", body)
        assert invalid.value.code == 409


def test_focus_loss_invalidates_pending_command_and_skips_input(worker):
    worker.begin(5)
    with ThreadPoolExecutor(max_workers=1) as pool:
        result = pool.submit(worker.request, "capture")
        command = post(worker, "/next", {})
        assert post(worker, "/permit", {"id": command["id"]})["allowed"]
        worker.guard.probe.reason = "loss_of_focus"
        with pytest.raises(HTTPError) as stop:
            post(worker, "/permit", {"id": command["id"]})
        assert stop.value.code == 409
        with pytest.raises(ActionError, match="loss_of_focus"):
            result.result(timeout=2)
        assert not worker.pending
        assert not post(worker, "/result", {"id": command["id"], "result": {}})["accepted"]
    worker.end()
