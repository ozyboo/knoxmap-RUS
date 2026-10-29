import unittest

from knoxbuild import catalog, layout
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


if __name__ == "__main__":
    unittest.main()
