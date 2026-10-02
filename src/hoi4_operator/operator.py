"""Ordinary Python Agent facade. Only semantic arguments and results cross it."""

import inspect

from .contracts import ActionResult


class OperatorAPI:
    def __init__(self, model, *, executor=None, production=None, construction=None, politics=None, trade=None):
        self.model = model
        self.actions = {}
        groups = ((executor, ("select_research", "select_focus")),
                  (production, ("get_production_lines", "set_production_factory_count", "create_production_line",
                                "delete_production_line", "reorder_production_line")),
                  (construction, ("get_construction", "build", "cancel_construction", "change_construction_priority")),
                  (politics, ("change_economy_law", "change_conscription_law", "get_advisors", "hire_advisor")),
                  (trade, ("get_trade_state", "set_trade_import")))
        for service, names in groups:
            if service is not None:
                for name in names:
                    method = getattr(service, name, None)
                    if method:
                        self.actions[name] = method

    def get_summary(self):
        self.model.poll()
        return self.model.summary()

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
        return method(**arguments)
