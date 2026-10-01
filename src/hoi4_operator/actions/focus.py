"""A progress interval alone is never proof of the selected focus's identity."""


def confirmation(before, after, focus_id, ui_active):
    focus = (after.get("state") or {}).get("focus") or {}
    newer = after.get("latest_seq", -1) > before.get("latest_seq", -1)
    valid = bool(newer and ui_active and focus.get("tracked_id") == focus_id and
                 focus.get("completed") is False)
    return valid, {
        "before_seq": before.get("latest_seq"), "after_seq": after.get("latest_seq"),
        "focus_id": focus_id, "ui_active_name_and_cancel": ui_active,
        "completed": focus.get("completed"),
        "progress_interval": [focus.get("progress_lower_bound"), focus.get("progress_upper_bound")],
        "active_focus_id_source": "GUI name plus cancel control; telemetry ID remains UNKNOWN",
        "new_frame": newer,
    }
