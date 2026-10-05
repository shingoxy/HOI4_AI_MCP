"""Private, independently calibrated map profiles; no coordinate scaling."""

from dataclasses import dataclass

from .guard import ActionError


@dataclass(frozen=True)
class MapProfile:
    name: str
    capture_width: int
    capture_height: int
    ui_scale: float
    map_mode: str
    camera_anchor_set: tuple[str, ...]
    supported_targets: tuple[str, ...]
    template_set: str

    @property
    def size(self):
        return self.capture_width, self.capture_height


PROFILES = (
    MapProfile("GER_1936_2560x1080", 2560, 1080, 1.0, "land",
        ("amsterdam", "warsaw", "copenhagen"),
        ("GER_POL_mainland", "GER_POL_east_prussia"), "artifacts/phase4/templates"),
    MapProfile("GER_1936_2048x1280", 2048, 1280, 1.0, "land",
        ("amsterdam", "copenhagen", "konigsberg"),
        ("GER_POL_mainland_Poznan_east", "GER_POL_mainland_Poland_north_east"),
        "artifacts/phase4/offensive2048/templates"),
)


def profile_for_size(size):
    for profile in PROFILES:
        if size == profile.size:
            return profile
    raise ActionError("unsupported_resolution", "rejected")
