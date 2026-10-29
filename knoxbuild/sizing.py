"""Room sizes in tiles, and what a flat or a house floor contains by its area.

Sizes come from the "kinds" table in room_solver.json (square metres), so the
two room models agree. Programmes are lists of Build room kinds, living room
first; split_by_targets cuts a box in proportion to their targets.
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


def split_by_targets(box: tuple[int, int, int, int], kinds: list[str],
                     rng: random.Random, mask: list[list[bool]] | None = None,
                     first_edge: str | None = None) -> list | None:
    """Cut box (x0, y0, x1, y1, inclusive) into one room per kind, sized by target.

    Recursive guillotine: kinds (first kept first, the rest shuffled by rng)
    split into two groups, a cut along the longer axis at the ratio of the
    groups' target areas, then each side again. Targets are shares, so they
    scale to the box. Every side stays >= MIN_ROOM; None when no cut allows it.
    first_edge ("N" = y0, "S" = y1, "W" = x0, "E" = x1) makes the first kind's
    room touch that edge of the box. With a mask every room lies wholly inside
    it and the rooms cover exactly the box's masked tiles: a cut is kept only
    where each piece, trimmed to its masked bounding box, ends up as whole
    rectangles - a footprint no guillotine cut can carve gives None (fall back).
    Rooms come back in kinds order, kind set, fixed=True.
    """
    from .layout import MIN_ROOM as M, Room
    if not kinds:
        return None
    t = [SIZES[k].target for k in kinds]
    order = [0] + rng.sample(range(1, len(kinds)), len(kinds) - 1)
    side = {"W": 0, "N": 1, "E": 2, "S": 3}.get(first_edge)
    # ponytail: node cap, backtracking only happens on masked boxes; a mask
    # that needs deeper search falls back instead of stalling the build.
    budget = [400]

    # Masked tiles of any rectangle in O(1): sums over (0, 0)..(x - 1, y - 1).
    pre = None
    if mask is not None:
        pre = [[0] * (box[2] + 2) for _ in range(box[3] + 2)]
        for y in range(box[3] + 1):
            for x in range(box[2] + 1):
                pre[y + 1][x + 1] = (mask[y][x] + pre[y][x + 1] + pre[y + 1][x]
                                     - pre[y][x])

    def tiles(r):
        x0, y0, x1, y1 = r
        if pre is None:
            return (x1 - x0 + 1) * (y1 - y0 + 1)
        return pre[y1 + 1][x1 + 1] - pre[y0][x1 + 1] - pre[y1 + 1][x0] + pre[y0][x0]

    def trim(r):
        if pre is None:
            return r
        x0, y0, x1, y1 = r
        ys = [y for y in range(y0, y1 + 1) if tiles((x0, y, x1, y))]
        xs = [x for x in range(x0, x1 + 1) if tiles((x, y0, x, y1))]
        return (xs[0], ys[0], xs[-1], ys[-1]) if ys else None

    def fits(r, idx):
        w, h = r[2] - r[0] + 1, r[3] - r[1] + 1
        if side is not None and 0 in idx and r[side] != box[side]:
            return False
        return (w // M) * (h // M) >= len(idx) and tiles(r) >= len(idx) * M * M

    def solve(r, idx):
        budget[0] -= 1
        if budget[0] < 0:
            return None
        w, h = r[2] - r[0] + 1, r[3] - r[1] + 1
        if len(idx) == 1:
            return [(idx[0], r)] if tiles(r) == w * h else None
        whole, total = tiles(r), sum(t[i] for i in idx)
        cands = []
        for k in range(1, len(idx)):
            a, b = idx[:k], idx[k:]
            share = sum(t[i] for i in a) / total
            for vertical in (True, False):
                lo, hi = (r[0], r[2]) if vertical else (r[1], r[3])
                for p in range(lo + M, hi - M + 2):
                    low = (r[0], r[1], p - 1, r[3]) if vertical else (r[0], r[1], r[2], p - 1)
                    high = (p, r[1], r[2], r[3]) if vertical else (r[0], p, r[2], r[3])
                    got = tiles(low) / whole
                    low, high = trim(low), trim(high)
                    if low is None or high is None:
                        continue
                    longer = vertical == (w >= h)
                    for g_lo, g_hi, want in ((a, b, share), (b, a, 1 - share)):
                        if fits(low, g_lo) and fits(high, g_hi):
                            cands.append((not longer, abs(got - want), rng.random(),
                                          low, g_lo, high, g_hi))
        cands.sort(key=lambda c: c[:3])
        for *_, low, g_lo, high, g_hi in cands:
            one = solve(low, g_lo)
            two = one and solve(high, g_hi)
            if two:
                return one + two
            if budget[0] < 0:
                return None
        return None

    start = trim(box)
    got = start and fits(start, order) and solve(start, order)
    if not got:
        return None
    return [Room(*r, kind=kinds[i], fixed=True) for i, r in sorted(got)]
