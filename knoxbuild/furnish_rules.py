"""Furnishing rules: what matters most in a room, where people walk, and
whether a new piece would cut the free floor in two. No import of layout."""
import heapq
from collections import deque

ESSENTIAL, SECONDARY, DECORATION = 0, 1, 2

DECORATION_ROLES = (
    "plant", "erika_plant", "lamp", "shelf", "bookshelf", "erika_shelves",
    "painting", "mirror", "erika_art", "erika_ad", "rug", "shag_rug",
    "bath_mat", "corkboard")

_KITCHEN = ("fridge", "stove", "kitchen_sink", "counter")
_BED = ("double_bed", "bed")
ESSENTIALS = {
    "bathroom": ("toilet", "sink", "bath", "shower"),
    "kitchen": _KITCHEN,
    "openplan": _KITCHEN + ("sofa",),
    "livingroom": ("sofa",),
    "bedroom": _BED,
    "kidsbedroom": _BED,
    "motelroom": _BED,
    "laundry": ("washer",),
    "dining": ("dining_table", "round_table"),
    "closet": ("wardrobe",),
}


def priority(role, room_kind):
    """0 essential, 1 secondary, 2 decoration. Decoration is checked first so
    bath_mat is never read as bath."""
    if role.startswith(DECORATION_ROLES):
        return DECORATION
    if role.startswith(ESSENTIALS.get(room_kind, ())):
        return ESSENTIAL
    return SECONDARY


def in_priority_order(roles, room_kind):
    return sorted(roles, key=lambda r: priority(r, room_kind))


def _near(t):
    x, y = t
    return ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))


def _depth(cells):
    """1 for a tile with a 4-neighbour outside cells, +1 per step inward."""
    depth = {t: 1 for t in cells if any(n not in cells for n in _near(t))}
    todo = deque(sorted(depth))
    while todo:
        t = todo.popleft()
        for n in _near(t):
            if n in cells and n not in depth:
                depth[n] = depth[t] + 1
                todo.append(n)
    return depth


def _path(cells, depth, sources, goal):
    """Cheapest path from any source until goal(tile) is first popped: fewest
    tiles, ties away from walls. Returns the path tiles (source excluded from
    cost, included in the list), or None."""
    best = {s: (0, 0) for s in sources}
    parent = {}
    heap = [((0, 0), y, x) for x, y in sources]
    heapq.heapify(heap)
    while heap:
        cost, y, x = heapq.heappop(heap)
        t = (x, y)
        if cost != best[t]:
            continue
        if t not in sources and goal(t):
            path = [t]
            while path[-1] in parent:
                path.append(parent[path[-1]])
            return path
        for n in _near(t):
            if n not in cells:
                continue
            c = (cost[0] + 1, cost[1] + (depth[n] == 1))
            if n not in best or c < best[n]:
                best[n] = c
                parent[n] = t
                heapq.heappush(heap, (c, n[1], n[0]))
    return None


def walkway(cells, entries):
    """Tiles that stay free: a path joining the room's ways in, or for a single
    way in a spine to the farthest tile that is off every wall."""
    terminals = sorted({e for e in entries if e in cells})
    if not terminals:
        return set()
    depth = _depth(cells)
    if len(terminals) == 1:
        start = terminals[0]
        steps = {start: 0}
        todo = deque([start])
        while todo:
            t = todo.popleft()
            for n in _near(t):
                if n in cells and n not in steps:
                    steps[n] = steps[t] + 1
                    todo.append(n)
        inner = [t for t in steps if depth[t] >= 2]
        if not inner:
            return {start}
        target = min(inner, key=lambda t: (-steps[t], t[1], t[0]))
        return set(_path(cells, depth, {start}, lambda t: t == target))
    tree = {terminals[0]}
    pending = set(terminals[1:])
    while pending:
        path = _path(cells, depth, tree, pending.__contains__)
        if path is None:  # unreachable (split cells): leave the rest out
            break
        tree.update(path)
        pending -= tree
    return tree


def keeps_floor_open(cells, blocked, walk, new, pocket):
    """True if placing `new` leaves the walkway untouched and every cut-off
    patch of free floor holds at most `pocket` tiles."""
    if new & walk:
        return False
    free = cells - blocked - new
    seen, comps = set(), []
    for start in sorted(free):
        if start in seen:
            continue
        comp, todo = {start}, [start]
        while todo:
            for n in _near(todo.pop()):
                if n in free and n not in comp:
                    comp.add(n)
                    todo.append(n)
        seen |= comp
        comps.append(comp)
    if not comps:
        return True
    anchor = walk & free
    if anchor:
        main = min(anchor)
        keep = next(c for c in comps if main in c)
    else:
        keep = max(comps, key=len)  # comps are in min-tile order: ties go to the smallest
    return all(len(c) <= pocket for c in comps if c is not keep)
