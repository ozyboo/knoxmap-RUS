import copy
import random
import unittest
from unittest import mock

from knoxbuild import catalog, layout
from knoxbuild import furnish_rules as FR
from knoxbuild.furnish_rules import (
    DECORATION, DECORATION_ROLES, ESSENTIAL, ESSENTIALS, SECONDARY,
    in_priority_order, keeps_floor_open, priority, walkway)


def rect(w, h):
    return {(x, y) for x in range(w) for y in range(h)}


def connected(tiles):
    if not tiles:
        return True
    start = min(tiles)
    seen, todo = {start}, [start]
    while todo:
        x, y = todo.pop()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n in tiles and n not in seen:
                seen.add(n)
                todo.append(n)
    return seen == set(tiles)


def _sample():
    for kind in ("house", "apartment"):
        for seed in range(30):
            rng = random.Random(seed)
            w = rng.randint(9, 20)
            h = rng.randint(8, 16)
            levels = rng.randint(1, 3) if kind == "house" else rng.randint(3, 5)
            yield kind, seed, dict(width=w, height=h, levels=levels, kind=kind, seed=seed)


# 30 houses + 30 flat blocks: (kind, seed, build_building kwargs).
SAMPLE = list(_sample())


def furnish_time_builds():
    """SAMPLE as furnished: no windows (doors stay put), nothing cleared."""
    with mock.patch.object(layout, "_place_windows", lambda *a, **k: None), \
            mock.patch.object(layout, "_clear_the_way", lambda *a, **k: 0):
        return [(kind, seed, layout.build_building(**args))
                for kind, seed, args in SAMPLE]


class PriorityTable(unittest.TestCase):
    def test_priorities(self):
        cases = [
            ("toilet", "bathroom", ESSENTIAL),
            ("sink_public", "bathroom", ESSENTIAL),
            ("bath_mat", "bathroom", DECORATION),
            ("double_bed_black", "bedroom", ESSENTIAL),
            ("wardrobe_oak", "bedroom", SECONDARY),
            ("wardrobe", "closet", ESSENTIAL),
            ("erika_plant_3", "livingroom", DECORATION),
            ("counter_4", "kitchen", ESSENTIAL),
            ("counter_4", "livingroom", SECONDARY),
            ("sofa_7", "livingroom", ESSENTIAL),
            ("dresser", "grocery", SECONDARY),
        ]
        for role, kind, want in cases:
            with self.subTest(role=role, kind=kind):
                self.assertEqual(priority(role, kind), want)

    def test_order_is_stable(self):
        got = in_priority_order(
            ["plant", "dresser", "double_bed", "lamp", "wardrobe"], "bedroom")
        self.assertEqual(
            got, ["double_bed", "dresser", "wardrobe", "plant", "lamp"])

    def test_every_prefix_names_real_furniture(self):
        prefixes = set(DECORATION_ROLES)
        for group in ESSENTIALS.values():
            prefixes.update(group)
        for p in sorted(prefixes):
            with self.subTest(prefix=p):
                self.assertTrue(any(k.startswith(p) for k in catalog.FURNITURE))
        for kind in layout.ROOM_STYLE:
            for role in catalog.FURNITURE:
                self.assertIn(priority(role, kind), {0, 1, 2})


class Walkway(unittest.TestCase):
    def test_two_doors_joined_by_shortest_path(self):
        w = walkway(rect(7, 5), [(0, 2), (6, 2)])
        self.assertTrue({(0, 2), (6, 2)} <= w)
        self.assertTrue(connected(w))
        self.assertEqual(len(w), 7)

    def test_three_doors_all_joined(self):
        w = walkway(rect(7, 5), [(0, 2), (6, 2), (3, 0)])
        self.assertTrue({(0, 2), (6, 2), (3, 0)} <= w)
        self.assertTrue(connected(w))
        self.assertLessEqual(len(w), 10)

    def test_one_door_gets_a_spine(self):
        w = walkway(rect(5, 5), [(0, 2)])
        self.assertIn((0, 2), w)
        self.assertIn((3, 1), w)
        self.assertTrue(connected(w))
        self.assertEqual(len(w), 5)

    def test_spine_keeps_off_walls(self):
        w = walkway(rect(7, 5), [(0, 2)])
        for x, y in w - {(0, 2)}:
            self.assertTrue(1 <= x <= 5 and 1 <= y <= 3, (x, y))

    def test_narrow_room_gets_only_the_door(self):
        self.assertEqual(walkway(rect(2, 6), [(0, 0)]), {(0, 0)})

    def test_three_wide_room_gets_only_the_door(self):
        # A spine down the one inner row leaves nothing two deep (a double
        # bed) room on either side.
        self.assertEqual(walkway(rect(3, 7), [(1, 0)]), {(1, 0)})

    def test_no_entries(self):
        self.assertEqual(walkway(rect(4, 4), []), set())
        self.assertEqual(walkway(rect(4, 4), [(9, 9)]), set())

    def test_l_shape_stays_inside(self):
        cells = rect(6, 3) | {(x, y) for x in range(3) for y in range(3, 6)}
        w = walkway(cells, [(5, 1), (1, 5)])
        self.assertTrue(w <= cells)
        self.assertTrue({(5, 1), (1, 5)} <= w)
        self.assertTrue(connected(w))

    def test_deterministic(self):
        entries = [(0, 2), (6, 2), (3, 0)]
        self.assertEqual(walkway(rect(7, 5), entries),
                         walkway(rect(7, 5), entries))


class FloorStaysOpen(unittest.TestCase):
    cells = rect(5, 5)
    walk = {(2, 4), (2, 3), (2, 2)}

    def test_walkway_is_never_blocked(self):
        self.assertIs(keeps_floor_open(self.cells, set(), self.walk, {(2, 3)}, 2), False)

    def test_corner_cut_off(self):
        self.assertIs(keeps_floor_open(
            self.cells, {(2, 0), (2, 1)}, self.walk, {(0, 2), (1, 2)}, 2), False)

    def test_small_pocket_allowed(self):
        self.assertIs(keeps_floor_open(
            self.cells, {(1, 0)}, self.walk, {(0, 1)}, 2), True)

    def test_nothing_new(self):
        self.assertIs(keeps_floor_open(self.cells, set(), self.walk, set(), 2), True)



class WalkwayIsKeptClear(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builds = furnish_time_builds()

    def rooms(self):
        """(label, storey, idx, cells, entries, walk) for every room that is
        neither core nor shaft."""
        for kind, seed, b in self.builds:
            stairs = b.stairs[0] if b.stairs else None
            for level, s in enumerate(b.storeys):
                doors = layout._door_tiles(s)
                for idx, r in enumerate(s.rooms, 1):
                    if r.is_core or r.is_shaft:
                        continue
                    cells = {(x, y) for y, row in enumerate(s.grid)
                             for x, v in enumerate(row) if v == idx}
                    entries = set()
                    for x, y, d in list(s.doors) + sorted(s.open_edge):
                        entries |= {(x, y), (x - 1, y) if d == "W" else (x, y - 1)}
                    if stairs is not None:
                        sx, sy, sd = stairs
                        dx, dy = (0, 1) if sd == "N" else (1, 0)
                        entries |= {(sx - dx, sy - dy),
                                    (sx + dx * layout.STAIR_RUN, sy + dy * layout.STAIR_RUN)}
                    walk = layout._room_walkway(s, idx, doors, stairs)
                    yield ((kind, seed, level, r.kind), s, idx, cells,
                           entries & cells, walk)

    def test_no_blocking_piece_on_a_walkway(self):
        for label, s, idx, _cells, _entries, walk in self.rooms():
            for role, x, y, o in s.furniture:
                if s.grid[y][x] != idx or not layout._blocks(role):
                    continue
                with self.subTest(label, role=role):
                    self.assertFalse(set(layout._tiles_under(role, x, y, o)) & walk)

    def test_walkway_joins_every_way_in(self):
        for label, _s, _idx, _cells, entries, walk in self.rooms():
            with self.subTest(label):
                self.assertLessEqual(entries, walk)
                if entries:
                    self.assertTrue(connected(walk))

    def test_bedrooms_keep_their_beds(self):
        # Before the walkway 293 of 347 bedrooms had a bed at furnish time.
        rooms = beds = 0
        for _kind, _seed, b in self.builds:
            for s in b.storeys:
                for idx, r in enumerate(s.rooms, 1):
                    if r.kind != "bedroom":
                        continue
                    rooms += 1
                    beds += any(role.startswith(("bed", "double_bed"))
                                for role, x, y, _o in s.furniture if s.grid[y][x] == idx)
        self.assertGreaterEqual(beds / rooms, 0.80)


class PriorityWhenTight(unittest.TestCase):
    def setUp(self):
        self._erika = list(layout._ERIKA_ALLOWED)
        layout.use_mod_tiles(False)

    def tearDown(self):
        layout._ERIKA_ALLOWED[:] = self._erika
        layout._ERIKA.clear()

    def test_essentials_go_in_before_decoration(self):
        room = layout.Room(0, 0, 2, 2, kind="kitchen")
        plan = layout.Plan(3, 3, rooms=[room], grid=[[1] * 3 for _ in range(3)],
                           doors=[(0, 1, "W")], kind="house")
        style = {"kitchen": (12, "Kitchen", ["plant"] * 8 + ["fridge"])}
        with mock.patch.dict(layout.ROOM_STYLE, style):
            for seed in range(10):
                p = copy.deepcopy(plan)
                layout._furnish(p, random.Random(seed))
                roles = [f[0] for f in p.furniture]
                with self.subTest(seed=seed):
                    self.assertTrue(any(r.startswith("fridge") for r in roles), roles)
                    self.assertLessEqual(roles.count("plant"), 6, roles)


class FloorStaysInOnePiece(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builds = furnish_time_builds()

    def test_free_floor_hangs_together(self):
        for kind, seed, b in self.builds:
            stairs = b.stairs[0] if b.stairs else None
            for level, s in enumerate(b.storeys):
                doors = layout._door_tiles(s)
                blocked = {t for role, x, y, o in s.furniture if layout._blocks(role)
                           for t in layout._cells_for(role, x, y, o)}
                for idx, r in enumerate(s.rooms, 1):
                    if r.is_core or r.is_shaft:
                        continue
                    cells = {(x, y) for y, row in enumerate(s.grid)
                             for x, v in enumerate(row) if v == idx}
                    walk = layout._room_walkway(s, idx, doors, stairs)
                    with self.subTest(kind=kind, seed=seed, level=level, room=r.kind):
                        self.assertTrue(FR.keeps_floor_open(
                            cells, blocked & cells, walk, set(), layout.POCKET_TILES))

    def test_same_seed_same_furniture(self):
        args = next(a for k, sd, a in SAMPLE if k == "house" and sd == 3)
        with mock.patch.object(layout, "_place_windows", lambda *a, **k: None),                 mock.patch.object(layout, "_clear_the_way", lambda *a, **k: 0):
            one = layout.build_building(**args)
            two = layout.build_building(**args)
        self.assertEqual([s.furniture for s in one.storeys],
                         [s.furniture for s in two.storeys])


class ClearUpByPriority(unittest.TestCase):
    def test_decoration_goes_before_an_essential(self):
        room = layout.Room(0, 0, 5, 4, kind="bathroom")
        furniture = [("plant", 2, 0, "N"), ("plant", 3, 0, "N")]
        furniture += [("toilet", 2, y, "N") for y in range(1, 5)]
        plan = layout.Plan(6, 5, rooms=[room], grid=[[1] * 6 for _ in range(5)],
                           doors=[(0, 2, "W")], furniture=furniture)
        self.assertEqual(layout._open_up(plan, {(0, 2)}), {0, 1})


# route-removal threshold test lands in Task 5, after moved-door and window-path clearing

if __name__ == "__main__":
    unittest.main()
