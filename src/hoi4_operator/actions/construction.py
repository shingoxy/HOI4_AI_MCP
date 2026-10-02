"""Verified installed state IDs and strict one-item construction transitions."""

from ..executor.guard import ActionError

STATES = {64: "勃兰登堡", 65: "萨克森", 66: "下西里西亚"}
BUILDINGS = {"civilian_factory", "military_factory", "infrastructure"}


def order(view):
    return [(item["state_id"], item["building_type"], item["count"]) for item in view["queue"]]


def validate(before, after, action, *, state_id=None, building_type=None, target=None, direction=None):
    old, new = order(before), order(after)
    expected = list(old)
    if action == "build":
        identity = (state_id, building_type, 1)
        if identity in old:
            raise ActionError("readback_ambiguous", "rejected")
        expected.append(identity)
    else:
        identity = (target["state_id"], target["building_type"], target["count"])
        if old.count(identity) != 1:
            raise ActionError("readback_ambiguous", "rejected")
        index = old.index(identity)
        if action == "cancel_construction":
            expected.pop(index)
        else:
            other = index + (-1 if direction == "up" else 1)
            if not 0 <= other < len(old):
                return "already_satisfied"
            expected[index], expected[other] = expected[other], expected[index]
    if new != expected:
        raise ActionError("unexpected_state_change", "uncertain")
    return {"before_order": old, "after_order": new, "exact_transition": True}
