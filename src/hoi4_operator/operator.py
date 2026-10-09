"""Ordinary Python Agent facade. Only semantic arguments and results cross it."""

import inspect

from .contracts import ActionResult


class OperatorAPI:
    def __init__(self, model, *, executor=None, production=None, construction=None, politics=None, trade=None, military=None,
                 runtime_capability=None, observation_refresh=None):
        self.model = model
        self.services = [s for s in (executor, production, construction, politics, trade, military) if s]
        self.runtime_capability = runtime_capability or (lambda: {"backend": "unattached", "native_subset_ready": False})
        from .observation import ObservationAggregator
        self.observation = ObservationAggregator(model, capabilities=self.runtime_capability, refresh=observation_refresh)
        self.actions = {}
        groups = ((executor, ("select_research", "select_focus")),
                  (production, ("get_production_lines", "set_production_factory_count", "create_production_line",
                                "delete_production_line", "reorder_production_line")),
                  (construction, ("get_construction", "build", "cancel_construction", "change_construction_priority")),
                  (politics, ("change_economy_law", "change_conscription_law", "get_advisors", "hire_advisor")),
                  (trade, ("get_trade_state", "set_trade_import")),
                  (military, ("get_armies", "get_army", "get_divisions", "get_division", "get_generals",
                              "create_army", "assign_divisions", "remove_divisions_from_army", "assign_general",
                              "get_fronts", "get_supply_status", "get_air_state", "get_navy_state",
                              "get_air_wings", "get_air_regions", "get_fleets", "create_frontline",
                              "create_offensive_line", "execute_plan", "stop_plan", "move_divisions",
                              "assign_air_wing", "set_air_mission", "assign_fleet_region", "set_naval_mission")))
        for service, names in groups:
            if service is not None:
                for name in names:
                    method = getattr(service, name, None)
                    if method:
                        self.actions[name] = method

    def get_summary(self):
        self.model.poll()
        return self.model.summary()

    def get_game_state(self, detail="strategic"):
        return self.observation.get(detail)

    def get_action_catalog(self):
        from .action_catalog import build_catalog
        return build_catalog(self.get_game_state("summary"), self.actions, self.runtime_capability())

    def invalidate_snapshots(self):
        self.observation.invalidate()
        for service in self.services:
            if hasattr(service, "invalidate"):
                service.invalidate()
            elif hasattr(service, "snapshots"):
                service.snapshots.invalidate()

    def execute(self, action, arguments=None):
        method = self.actions.get(action) if isinstance(action, str) else None
        result = ActionResult(action if isinstance(action, str) else "invalid_action")
        if method is None:
            result.evidence["reason"] = "unsupported_target"
            return result.as_dict()
        arguments = {} if arguments is None else arguments
        try:
            if not isinstance(arguments, dict):
                raise TypeError()
            inspect.signature(method).bind(**arguments)
        except TypeError:
            result.evidence["reason"] = "invalid_arguments"
            return result.as_dict()
        answer = method(**arguments)
        from .action_catalog import DOMAINS
        getters = {"get_production_lines": "production", "get_construction": "construction",
                   "get_armies": "military", "get_divisions": "military", "get_fronts": "military"}
        if answer.get("status") in {"confirmed", "already_satisfied"}:
            domain = getters.get(action)
            if domain:
                self.observation.remember(domain, answer, complete=answer.get("complete", domain == "construction"))
            elif action in DOMAINS:
                # A mutation may change related cached domains and session versions.
                self.observation.invalidate()
        return answer
