"""Room sizes in tiles, and what a flat or a house floor contains by its area.

Sizes come from the "kinds" table in room_solver.json (square metres), so the
two room models agree. Programmes are lists of Build room kinds, living room
first; split_by_targets (Task 2) cuts a box in proportion to their targets.
"""
import json
import os
import random
from dataclasses import dataclass

TILES_PER_M2 = 1.5      # Settings.room_size: 16 m2 = 24 tiles


@dataclass(frozen=True)
class Size:
    lo: int
    target: int
    hi: int
    aspect: float


# Build kind -> the room_solver.json kind that sets its size.
_FROM_JSON = {
    "bathroom": "bathroom", "bedroom": "bed_double", "kidsbedroom": "bed_single",
    "kitchen": "kitchen", "livingroom": "living", "openplan": "openplan",
    "dining": "dining", "laundry": "utility", "office": "study",
}
# Kinds the json has no single size for (its hall and cupboards are 0-2 m2).
_FALLBACK = {
    "hall": Size(3, 6, 12, 4.0),
    "closet": Size(2, 3, 6, 2.0),
    "storage": Size(3, 6, 12, 3.0),
}


def _load() -> dict[str, Size]:
    with open(os.path.join(os.path.dirname(__file__), "room_solver.json")) as f:
        kinds = json.load(f)["kinds"]
    out = dict(_FALLBACK)
    for build, key in _FROM_JSON.items():
        k = kinds[key]
        lo, hi = k["area"]
        out[build] = Size(*(round(m * TILES_PER_M2) for m in (lo, k["target"], hi)),
                          float(k["aspect"]))
    return out


SIZES: dict[str, Size] = _load()

_BEDS = ("bedroom", "kidsbedroom")


def min_area(programme: list[str]) -> int:
    """Tiles a programme needs for every room to reach its lo."""
    return sum(SIZES[k].lo for k in programme)


def programme_for_flat(area: int, rng: random.Random,
                       open_plan: bool = False) -> list[str] | None:
    """Studio, 1-, 2- or 3-bed flat by area; None when below a studio's lo sum."""
    living = "openplan" if open_plan else "livingroom"
    kitchen = [] if open_plan else ["kitchen"]
    plans = [
        [living, "bathroom"],
        [living, *kitchen, "bedroom", "bathroom"],
        [living, *kitchen, "bedroom", rng.choice(_BEDS), "bathroom"],
        ["hall", living, *kitchen, "bedroom", "bedroom", "kidsbedroom",
         "bathroom", "bathroom"],
    ]
    fit = [i for i, p in enumerate(plans) if area >= min_area(p)]
    if not fit:
        return None
    i = fit[-1]
    # ponytail: a flat just over its minimum sometimes takes the smaller plan.
    if i and area < min_area(plans[i]) * 1.15 and rng.random() < 0.5:
        i -= 1
    return plans[i]


def programme_for_house_floor(area: int, level: int, levels: int,
                              rng: random.Random) -> list[str] | None:
    """Rooms of one house floor (level 0 = ground); None when below its lo sum."""
    if levels == 1:
        rooms = ["hall", "livingroom", "kitchen", "bedroom", "bathroom"]
        extra = [(55, "bedroom"), (70, "dining")]
    elif level == 0:
        rooms = ["hall", "livingroom", "kitchen"]
        extra = [(45, "dining"), (60, "laundry")]
    else:
        rooms = ["hall", "bedroom", "bathroom"]
        extra = [(40, "bedroom"), (55, rng.choice(_BEDS))]
    if area < min_area(rooms):
        return None
    for a, k in extra:
        if area >= max(a, min_area(rooms + [k])):
            rooms.append(k)
    return rooms
