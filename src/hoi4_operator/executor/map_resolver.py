"""Private fixed-camera map evidence. Never accepts Agent coordinates."""

from .guard import ActionError
from .map_profile import profile_for_size

OFFENSIVE_ANCHORS = {"amsterdam": (377,648,470,668), "copenhagen": (975,281,1049,302),
                     "konigsberg": (1622,404,1700,425)}
OFFENSIVE_TARGETS = {
    "GER_POL_mainland_Poznan_east": {"front": "GER_POL_mainland", "start": (1360,600), "end": (1360,685)},
    "GER_POL_mainland_Poland_north_east": {"front": "GER_POL_mainland", "start": (1540,600), "end": (1660,600)},
}


FRONT_TARGETS = {
    "GER_POL_mainland": {"point": (1450,538), "segments": [(1474,480,1502,500),(1439,509,1463,535),(1536,605,1562,627)]},
    "GER_POL_east_prussia": {"point": (1710,466), "segments": [(1645,435,1674,456),(1720,456,1740,474),(1836,410,1861,433)]},
}
ANCHORS = {"amsterdam": (815,543,909,567), "warsaw": (1765,559,1797,580),
           "copenhagen": (1268,264,1336,283)}
AIR_ANCHORS={"amsterdam":(815,543,909,567),"vienna":(1499,890,1540,912),
             "copenhagen":(1268,264,1336,283)}


class MapResolver:
    profile = "GER-Europe-2560x1080-fixed-camera-v2"

    def __init__(self, templates, offensive_templates=None):
        self.templates = templates
        self.offensive_templates = offensive_templates

    def validate_offensive(self, rgb):
        profile = profile_for_size((rgb.shape[1], rgb.shape[0]))
        if profile.name != "GER_1936_2048x1280" or self.offensive_templates is None:
            raise ActionError("map_target_unresolved", "rejected")
        if not all(self.offensive_templates.find(rgb, "anchor_"+key, box, .9)
                   for key, box in OFFENSIVE_ANCHORS.items()):
            raise ActionError("map_target_unresolved", "rejected")
        if not self.offensive_templates.find(rgb, "land_mode", (1997,1120,2026,1149), .9):
            raise ActionError("map_target_unresolved", "rejected")
        return profile

    def resolve_offensive(self, target, rgb):
        if not isinstance(target, str) or target not in OFFENSIVE_TARGETS:
            raise ActionError("unsupported_target", "rejected")
        self.validate_offensive(rgb)
        return OFFENSIVE_TARGETS[target].copy()

    def validate(self, rgb):
        if rgb.shape[:2] != (1080,2560):
            raise ActionError("unsupported_resolution", "rejected")
        if not all(self.templates.find(rgb, "map_anchor_"+key, box, .9) or
                key=="amsterdam" and self.templates.find(rgb,"map_anchor_amsterdam_drawing",box,.9)
                for key,box in ANCHORS.items()):
            raise ActionError("map_target_unresolved", "rejected")

    def resolve(self, target, rgb):
        if not isinstance(target,str) or target not in FRONT_TARGETS:
            raise ActionError("unsupported_target", "rejected")
        self.validate(rgb)
        return FRONT_TARGETS[target]["point"]

    def resolve_air(self, region_id, rgb):
        if not isinstance(region_id,int) or isinstance(region_id,bool) or region_id!=8:
            raise ActionError("unsupported_target", "rejected")
        if rgb.shape[:2]!=(1080,2560):
            raise ActionError("unsupported_resolution", "rejected")
        offsets=[]
        for key,(x0,y0,x1,y1) in AIR_ANCHORS.items():
            # Normal load rounded the same camera one pixel vertically. Require
            # all three city labels to agree within two pixels; never accept a pan.
            point=self.templates.find(rgb,"air_anchor_"+key,(x0-2,y0-2,x1+2,y1+2),.9)
            if point is None:
                raise ActionError("map_target_unresolved", "rejected")
            offsets.append((point[0]-(x0+(x1-x0)//2),point[1]-(y0+(y1-y0)//2)))
        if len(set(offsets))!=1:
            raise ActionError("map_target_unresolved", "rejected")
        return (1320+offsets[0][0],502+offsets[0][1])

    def presence(self, rgb, target):
        self.resolve(target, rgb)
        matches = []
        for state in ("empty", "present"):
            variants=("empty","empty_drawing","empty_existing",*(f"empty_phase_{i}" for i in range(4))) if state=="empty" else ("present","present_highlight")
            if all(any(self.templates.find(rgb, f"front_{target}_{variant}_{index}", box, .92) for variant in variants)
                   for index,box in enumerate(FRONT_TARGETS[target]["segments"])):
                matches.append(state)
        if len(matches) != 1:
            raise ActionError("readback_ambiguous", "rejected")
        return matches[0] == "present"
