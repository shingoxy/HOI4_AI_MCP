"""Vendor-neutral decisions. Adapters receive JSON-compatible semantic values only."""

from copy import deepcopy
import json
from typing import Protocol, TypedDict


class SemanticAction(TypedDict):
    action: str
    arguments: dict
    rationale: str


class AgentDecision(TypedDict):
    assessment: str
    goals: list[str]
    actions: list[SemanticAction]


class AgentAdapter(Protocol):
    name: str

    def decide(self, observation, action_catalog, history) -> AgentDecision: ...


class DecisionError(ValueError):
    pass


def validate_decision(value, catalog, budget=3):
    if not isinstance(value, dict) or set(value) != {"assessment", "goals", "actions"}:
        raise DecisionError("invalid_decision_schema")
    if not isinstance(value["assessment"], str) or not 1 <= len(value["assessment"]) <= 1200:
        raise DecisionError("invalid_assessment")
    goals = value["goals"]
    if not isinstance(goals, list) or len(goals) > 8 or any(not isinstance(g, str) or not 1 <= len(g) <= 200 for g in goals):
        raise DecisionError("invalid_goals")
    if not isinstance(value["actions"], list) or len(value["actions"]) > budget:
        raise DecisionError("action_budget_exceeded")
    seen = set()
    for item in value["actions"]:
        if not isinstance(item, dict) or set(item) != {"action", "arguments", "rationale"}:
            raise DecisionError("invalid_action_schema")
        name, arguments = item["action"], item["arguments"]
        if not isinstance(name, str) or not isinstance(arguments, dict) or not isinstance(item["rationale"], str) or not 1 <= len(item["rationale"]) <= 400:
            raise DecisionError("invalid_action_schema")
        entry = catalog.get(name)
        if not entry or entry["status"] != "available":
            raise DecisionError("action_unavailable")
        # Compare canonical JSON to distinguish bool from int as well as extra arguments.
        encoded = json.dumps(arguments, sort_keys=True, ensure_ascii=False)
        if encoded not in [json.dumps(o, sort_keys=True, ensure_ascii=False) for o in entry["options"]]:
            raise DecisionError("unsupported_target")
        identity = name + encoded
        if identity in seen:
            raise DecisionError("duplicate_action")
        seen.add(identity)
    return deepcopy(value)


class ScriptedAgent:
    name = "scripted"

    def decide(self, observation, action_catalog, history):
        choices = sorted(action_catalog.items(), key=lambda item: (-item[1]["priority"], item[0]))
        actions = []
        for name, entry in choices:
            if entry["status"] != "available" or not entry["options"]:
                continue
            target = entry.get("recommended", entry["options"][0])
            if target is None:
                continue
            actions.append(dict(action=name, arguments=deepcopy(target), rationale="Use the highest priority known unmet target."))
            break  # One mutation is deliberately conservative for the first native runtime.
        return dict(assessment="Use reliable observations and calibrated available targets only.",
                    goals=["Maintain supported civilian development and research"], actions=actions)


class CodexAdapter:
    """A provider returns a strict decision; it never receives Operator or GUI handles."""
    name = "codex"

    def __init__(self, provider, *, budget=3):
        self.provider, self.budget = provider, budget

    def decide(self, observation, action_catalog, history):
        request = json.dumps(dict(observation=observation, action_catalog=action_catalog, history=history), ensure_ascii=False)
        raw = self.provider(request)
        if not isinstance(raw, str) or len(raw) > 100_000:
            raise DecisionError("invalid_provider_size_or_type")
        try:
            decision = json.loads(raw)
        except (ValueError, TypeError) as exc:
            raise DecisionError("invalid_provider_json") from exc
        return validate_decision(decision, action_catalog, self.budget)
