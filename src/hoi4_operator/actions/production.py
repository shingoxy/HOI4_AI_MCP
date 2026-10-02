"""GUI-derived session identities; these are never claimed to be game line IDs."""

from copy import deepcopy
import hashlib
import json
import time
from uuid import uuid4

from ..executor.guard import ActionError


def signature(view):
    return [(line["equipment"], line.get("equipment_type"), line["position"], line["factories"])
            for line in view["lines"]]


def telemetry_agrees(summary, view):
    return summary["state"].get("industry", {}).get("military_factories") == view["military_factories"]


class ProductionSnapshots:
    def __init__(self, ttl=120):
        self.session = uuid4().hex[:12]
        self.version, self.view, self.created = 0, None, 0.0
        self.ttl = ttl

    def replace(self, view, seq):
        self.version += 1
        self.view = deepcopy(view)
        self.created = time.monotonic()
        self.view.update(snapshot_version=self.version, session_id=self.session,
                         telemetry_seq=seq, stable_game_identity=False, ttl_seconds=self.ttl)
        for index, line in enumerate(self.view["lines"], 1):
            line["line_id"] = f"prod-{self.session}-{self.version:04d}-{index:04d}"
            line["identity_signature"] = hashlib.sha256(json.dumps(
                [line["equipment"], line.get("equipment_type"), line["position"], line["factories"]],
                ensure_ascii=False).encode()).hexdigest()
        return deepcopy(self.view)

    def lookup(self, line_id):
        if not isinstance(line_id, str) or not line_id.startswith(f"prod-{self.session}-"):
            raise ActionError("invalid_line_id", "rejected")
        if self.view is None or time.monotonic()-self.created > self.ttl:
            raise ActionError("production_snapshot_stale", "rejected")
        for line in self.view["lines"]:
            if line["line_id"] == line_id:
                return deepcopy(line)
        if line_id.split("-")[2] != f"{self.version:04d}":
            raise ActionError("production_snapshot_stale", "rejected")
        raise ActionError("target_line_not_found", "rejected")

    def validate(self, current):
        if signature(self.view) != signature(current):
            raise ActionError("production_snapshot_stale", "rejected")
        if any(self.view[k] != current[k] for k in ("military_factories", "assigned_military_factories")):
            raise ActionError("production_snapshot_stale", "rejected")

    def update(self, view):
        ids = [line["line_id"] for line in self.view["lines"]]
        metadata = {k: self.view[k] for k in ("snapshot_version", "session_id", "telemetry_seq", "stable_game_identity", "ttl_seconds")}
        self.view = deepcopy(view)
        self.view.update(metadata)
        for line, ident in zip(self.view["lines"], ids):
            line["line_id"] = ident
            line["identity_signature"] = hashlib.sha256(json.dumps(
                [line["equipment"], line.get("equipment_type"), line["position"], line["factories"]],
                ensure_ascii=False).encode()).hexdigest()
        self.created = time.monotonic()

    def invalidate(self):
        self.view = None
