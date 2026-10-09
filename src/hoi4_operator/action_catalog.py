"""Finite current targets, rather than a list of merely registered tools."""

VALIDATED_ACTIONS = ("select_research", "select_focus", "build", "set_production_factory_count",
                     "assign_divisions", "create_frontline", "create_offensive_line")
DOMAINS = dict(select_research="research_gui", select_focus="focus_gui", build="construction",
               set_production_factory_count="production", assign_divisions="military",
               create_frontline="military", create_offensive_line="military")


def build_catalog(observation, implemented, capability):
    catalog = {name: dict(status="unsupported", reason="outside_validated_native_subset", options=[], priority=0)
               for name in set(implemented) | set(VALIDATED_ACTIONS) | {"move_divisions", "set_naval_mission"}}
    for priority, name in enumerate(VALIDATED_ACTIONS):
        entry = catalog[name] = dict(status="unknown", reason="observation_required", options=[], priority=100-priority)
        readiness = capability.get("action_readiness", {}).get(name, {})
        entry["readiness"] = dict(semantic_implemented=name in implemented,
            backend_supported=bool(capability.get("native_subset_ready")),
            profile_calibrated=readiness.get("profile_calibrated", False if name in {"build","create_frontline","create_offensive_line"}
                else bool(capability.get("native_subset_ready"))),
            map_state=readiness.get("map_state", "MAP_UNRESOLVED" if name in {"build","create_frontline","create_offensive_line"} else "not_required"),
            target_identity_valid=readiness.get("target_identity_valid", False))
        if name not in implemented:
            entry.update(status="unsupported", reason="semantic_implementation_missing")
            continue
        if not capability.get("native_subset_ready"):
            entry.update(status="unsupported", reason=capability.get("reason", "backend_capability_mismatch"))
            continue
        if not observation["meta"]["fresh"]:
            entry.update(status="temporarily_blocked", reason="telemetry_stale")
            continue
        domain = observation[DOMAINS[name]]
        if domain["freshness"] == "stale":
            entry.update(status="temporarily_blocked", reason="snapshot_stale")
            continue
        data = domain["data"]
        if data is None:
            continue
        options = []
        satisfied = False
        if name == "select_research":
            tracked = (observation["research"]["data"] or {}).get("tracked_technologies", [])
            tech = next((t for t in tracked if t["tech_id"] == "basic_machine_tools"), None)
            if tech and (tech["researched"] or tech["researching"]):
                satisfied = True
            elif tech:
                options = [dict(slot=s["slot"], tech_id="basic_machine_tools") for s in data.get("slots", [])
                           if s["tech_id"] == "empty"]
        elif name == "select_focus":
            focus = observation["focus"]["data"] or {}
            satisfied = bool(focus.get("completed") or data.get("active"))
            if not satisfied and data.get("active") is False:
                options = [dict(focus_id="GER_remilitarize_the_rhineland")]
        elif name == "build":
            # The native reader supports one full queue item. Never add a second.
            satisfied = bool(data.get("queue"))
            if domain["complete"] and data.get("queue") == []:
                options = [dict(state_id=64, building_type="civilian_factory", count=1)]
        elif name == "set_production_factory_count":
            line = next((l for l in data.get("lines", []) if l.get("equipment_id") == "infantry_equipment_1"), None)
            if line and line.get("identity_complete") and line.get("action_supported"):
                # Keep the first runtime within independently calibrated native digit identities.
                current = line["factories"]
                options = [dict(line_id=line["line_id"], factories=n) for n in (10, 11, 12)
                           if abs(n-current) == 1 and n <= line["maximum_assignable_factories"]]
                entry["recommended"] = next((o for o in options if o["factories"] > current), None)
        else:
            armies = data.get("armies", [])
            if len(armies) == 1:
                army = armies[0]
                if name == "assign_divisions":
                    target = next((d for d in data.get("divisions", []) if d["name"] == "1. Panzer-Division"), None)
                    satisfied = bool(target and target.get("army_id") == army["army_id"])
                    if target and target.get("army_id") is None and len(army.get("division_names", [])) == 1:
                        options = [dict(army_id=army["army_id"], division_ids=[target["division_id"]])]
                elif "fronts" in data:
                    fronts = data["fronts"]
                    satisfied = any(f["target_id"] == "GER_POL_mainland" for f in fronts)
                    if name == "create_frontline" and not fronts and len(army.get("division_names", [])) == 2:
                        options = [dict(army_id=army["army_id"], target_id="GER_POL_mainland")]
                    elif name == "create_offensive_line":
                        satisfied = bool(data.get("offensive_orders"))
                        if not satisfied and "offensive_orders" in data and len(fronts) == 1 and len(army.get("division_names", [])) == 2:
                            options = [dict(army_id=army["army_id"], target="GER_POL_mainland_Poznan_east")]
        if name != "build":
            entry["readiness"]["target_identity_valid"] = bool(satisfied or options)
        if satisfied:
            entry.update(status="already_satisfied", reason="known_target_satisfied")
        elif options:
            if name in {"build", "create_frontline", "create_offensive_line"} and readiness.get("profile_calibrated") is not True:
                entry.update(status="unsupported", reason="current_map_profile_uncalibrated")
            elif name in {"build", "create_frontline", "create_offensive_line"} and readiness.get("map_state") != "MAP_READY":
                entry.update(status="temporarily_blocked", reason=readiness.get("map_reason", "map_observation_required"))
            elif name == "build" and readiness.get("target_identity_valid") is not True:
                entry.update(status="temporarily_blocked", reason="target_identity_unverified")
            else:
                entry.update(status="available", reason="current_calibrated_target", options=options)
        else:
            entry.update(status="temporarily_blocked", reason="requirements_not_met")
    return catalog
