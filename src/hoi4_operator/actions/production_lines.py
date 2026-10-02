"""Exact production list transitions, including duplicate-equipment ambiguity."""

from collections import Counter

from ..executor.guard import ActionError


def identity(line):
    return (line["equipment"], line.get("equipment_type"), line["factories"])


def order(view):
    return [identity(line) for line in view["lines"]]


def unique_target(view, target):
    key = identity(target)
    if order(view).count(key) != 1:
        raise ActionError("readback_ambiguous", "rejected")
    return order(view).index(key)


def validate_transition(before, after, action, *, target=None, equipment=None, direction=None):
    old, new = order(before), order(after)
    if before["military_factories"] != after["military_factories"]:
        raise ActionError("unexpected_state_change", "uncertain")
    if action == "create_production_line":
        added, removed = Counter(new) - Counter(old), Counter(old) - Counter(new)
        if sum(added.values()) != 1 or removed or len(new) != len(old) + 1:
            raise ActionError("unexpected_state_change", "uncertain")
        added_key = next(iter(added))
        if added_key[0] != equipment or new.count(added_key) != 1:
            raise ActionError("readback_ambiguous", "uncertain")
        # Existing relative order and all non-target factory counts must persist.
        reduced = list(new)
        reduced.remove(added_key)
        if reduced != old or after["assigned_military_factories"] != before["assigned_military_factories"] + added_key[2]:
            raise ActionError("unexpected_state_change", "uncertain")
        return {"added": [after["lines"][new.index(added_key)]], "removed": []}
    index = unique_target(before, target)
    expected = list(old)
    if action == "delete_production_line":
        expected.pop(index)
        assigned = before["assigned_military_factories"] - target["factories"]
    else:
        neighbour = index + (-1 if direction == "up" else 1)
        if not 0 <= neighbour < len(expected):
            raise ActionError("already_satisfied", "already_satisfied")
        expected[index], expected[neighbour] = expected[neighbour], expected[index]
        assigned = before["assigned_military_factories"]
    if new != expected or after["assigned_military_factories"] != assigned:
        raise ActionError("unexpected_state_change", "uncertain")
    return {"removed": [target] if action == "delete_production_line" else [], "before_order": old, "after_order": new}
