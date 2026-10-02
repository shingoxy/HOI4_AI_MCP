"""Versioned, expiring session-local GUI objects; no claimed game identities."""

from copy import deepcopy
import hashlib
import json
import time
from uuid import uuid4

from ..executor.guard import ActionError


class SessionSnapshots:
    def __init__(self, prefix, collection, id_field, identity_fields, ttl=120):
        self.prefix, self.collection, self.id_field = prefix, collection, id_field
        self.fields, self.ttl = identity_fields, ttl
        self.session, self.version = uuid4().hex[:12], 0
        self.view, self.created = None, 0.0

    def signature(self, view):
        return [tuple(item.get(field) for field in self.fields) for item in view[self.collection]]

    def replace(self, view, seq):
        self.version += 1
        self.view, self.created = deepcopy(view), time.monotonic()
        self.view.update(session_id=self.session, snapshot_version=self.version,
                         ttl_seconds=self.ttl, telemetry_seq=seq, stable_game_identity=False)
        for index, item in enumerate(self.view[self.collection]):
            item.update(position=index, identity_source="gui", stable_game_identity=False)
            item[self.id_field] = f"{self.prefix}-{self.session}-{self.version:04d}-{index:04d}"
            item["identity_signature"] = hashlib.sha256(json.dumps(
                [item.get(field) for field in self.fields]+[index], ensure_ascii=False).encode()).hexdigest()
        return deepcopy(self.view)

    def lookup(self, identity):
        if not isinstance(identity, str) or not identity.startswith(f"{self.prefix}-{self.session}-"):
            raise ActionError("identity_mismatch", "rejected")
        if self.view is None or time.monotonic()-self.created > self.ttl:
            raise ActionError("snapshot_stale", "rejected")
        item = next((item for item in self.view[self.collection] if item[self.id_field] == identity), None)
        if item is None:
            raise ActionError("snapshot_stale", "rejected")
        return deepcopy(item)

    def validate(self, view, seq):
        if self.view is None or seq < self.view["telemetry_seq"] or self.signature(self.view) != self.signature(view):
            raise ActionError("snapshot_stale", "rejected")

    def invalidate(self):
        self.view = None
