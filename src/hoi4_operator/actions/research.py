"""Research confirmation requires both slot identity and a tracked predicate."""


def technology(summary, tech_id):
    research = (summary.get("state") or {}).get("research") or {}
    return next((item for item in research.get("tracked_technologies", ())
                 if item["tech_id"] == tech_id), None)


def confirmation(before, after, tech_id, slot, ui_matches):
    item = technology(after, tech_id)
    newer = after.get("latest_seq", -1) > before.get("latest_seq", -1)
    valid = bool(newer and ui_matches and item and item["researching"] and
                 not item["researched"])
    return valid, {
        "before_seq": before.get("latest_seq"), "after_seq": after.get("latest_seq"),
        "tech_id": tech_id, "slot": slot, "ui_slot_matches": ui_matches,
        "researching": item["researching"] if item else None,
        "researched": item["researched"] if item else None,
        "slot_assignment_source": "GUI name template; telemetry mapping remains UNKNOWN",
        "new_frame": newer,
    }
