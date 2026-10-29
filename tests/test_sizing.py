import random
import unittest

from knoxbuild import sizing as S


class Sizes(unittest.TestCase):
    def test_order(self):
        z = S.SIZES
        self.assertLess(z["bathroom"].target, z["bedroom"].target)
        self.assertLess(z["bedroom"].target, z["livingroom"].target)

    def test_ranges(self):
        for kind in ("bathroom bedroom kidsbedroom kitchen livingroom openplan dining "
                     "hall closet laundry storage office").split():
            s = S.SIZES[kind]
            self.assertTrue(0 < s.lo <= s.target <= s.hi, kind)
            self.assertGreaterEqual(s.aspect, 1)


class Programmes(unittest.TestCase):
    def test_studio(self):
        p = S.programme_for_flat(S.min_area(["livingroom", "bathroom"]), random.Random(1))
        self.assertEqual(sum(k in ("livingroom", "openplan") for k in p), 1)
        self.assertEqual(p.count("bathroom"), 1)

    def test_two_bed(self):
        for open_plan in (False, True):
            p = S.programme_for_flat(70, random.Random(2), open_plan)
            self.assertGreaterEqual(sum(k in ("bedroom", "kidsbedroom") for k in p), 2)
            self.assertLessEqual(p.count("bathroom"), 2)
            self.assertEqual("openplan" in p, open_plan)

    def test_bathrooms_never_exceed_bedrooms(self):
        for area in range(18, 160, 3):
            for seed in range(5):
                p = S.programme_for_flat(area, random.Random(seed))
                if p is None:
                    continue
                beds = sum(k in ("bedroom", "kidsbedroom") for k in p)
                self.assertLessEqual(p.count("bathroom"), max(1, beds))

    def test_area_at_least_lo_sum(self):
        for open_plan in (False, True):
            for area in range(1, 200):
                for seed in range(6):
                    p = S.programme_for_flat(area, random.Random(seed), open_plan)
                    if p:
                        self.assertLessEqual(S.min_area(p), area)
        for levels, level in ((1, 0), (2, 0), (2, 1), (3, 2)):
            for area in range(1, 200):
                for seed in range(6):
                    p = S.programme_for_house_floor(area, level, levels, random.Random(seed))
                    if p:
                        self.assertLessEqual(S.min_area(p), area)

    def test_none_just_below_smallest(self):
        studio = S.min_area(["livingroom", "bathroom"])
        self.assertIsNone(S.programme_for_flat(studio - 1, random.Random(0)))
        self.assertIsNotNone(S.programme_for_flat(studio, random.Random(0)))
        open_min = S.min_area(["openplan", "bathroom"])
        self.assertIsNone(S.programme_for_flat(open_min - 1, random.Random(0), True))

    def test_step_down_both_outcomes(self):
        one_bed = S.min_area(["livingroom", "kitchen", "bedroom", "bathroom"])
        got = {len(S.programme_for_flat(one_bed, random.Random(s)))
               for s in range(40)}
        self.assertEqual(got, {2, 4})   # studio (stepped down) and 1-bed

    def test_too_small(self):
        self.assertIsNone(S.programme_for_flat(8, random.Random(0)))
        self.assertIsNone(S.programme_for_house_floor(8, 0, 2, random.Random(0)))

    def test_deterministic(self):
        a = S.programme_for_flat(55, random.Random(7))
        self.assertEqual(a, S.programme_for_flat(55, random.Random(7)))

    def test_house_floors(self):
        g = S.programme_for_house_floor(80, 0, 2, random.Random(3))
        self.assertIn("kitchen", g)
        self.assertIn("livingroom", g)
        u = S.programme_for_house_floor(60, 1, 2, random.Random(3))
        self.assertIn("bedroom", u)
        self.assertIn("bathroom", u)
        one = S.programme_for_house_floor(80, 0, 1, random.Random(3))
        self.assertTrue({"kitchen", "bedroom", "bathroom"} <= set(one))


FLAT = ["livingroom", "kitchen", "bedroom", "bathroom"]


def _tiles(r):
    return {(x, y) for x in range(r.x0, r.x1 + 1) for y in range(r.y0, r.y1 + 1)}


class Split(unittest.TestCase):
    def assertTiles(self, rooms, want):
        got = [t for r in rooms for t in _tiles(r)]
        self.assertEqual(len(got), len(set(got)))       # no overlap
        self.assertEqual(set(got), want)                # full coverage

    def test_tiles_box(self):
        box = {(x, y) for x in range(12) for y in range(10)}
        ordered = 0
        for seed in range(50):
            rooms = S.split_by_targets((0, 0, 11, 9), FLAT, random.Random(seed))
            self.assertIsNotNone(rooms, seed)
            self.assertEqual([r.kind for r in rooms], FLAT)
            self.assertTrue(all(r.fixed for r in rooms))
            self.assertTrue(all(min(r.w, r.h) >= 3 for r in rooms))
            self.assertTiles(rooms, box)
            a = {r.kind: r.area for r in rooms}
            ordered += a["bathroom"] < a["bedroom"] < a["livingroom"]
        self.assertGreaterEqual(ordered, 45)

    def test_too_small(self):
        self.assertIsNone(S.split_by_targets((0, 0, 4, 3), FLAT, random.Random(0)))

    def test_deterministic(self):
        a = S.split_by_targets((2, 3, 15, 12), FLAT, random.Random(9))
        self.assertEqual(a, S.split_by_targets((2, 3, 15, 12), FLAT, random.Random(9)))

    def test_first_edge(self):
        x0, y0, x1, y1 = box = (1, 2, 13, 11)
        on = {"N": lambda r: r.y0 == y0, "S": lambda r: r.y1 == y1,
              "W": lambda r: r.x0 == x0, "E": lambda r: r.x1 == x1}
        for edge, touches in on.items():
            for seed in range(20):
                rooms = S.split_by_targets(box, FLAT, random.Random(seed), first_edge=edge)
                self.assertIsNotNone(rooms, (edge, seed))
                self.assertEqual(rooms[0].kind, "livingroom")
                self.assertTrue(touches(rooms[0]), (edge, seed, rooms[0]))

    def test_masked_l(self):
        # 12x10 box with the north-east 5x4 corner outside the building.
        mask = [[not (x >= 7 and y < 4) for x in range(12)] for y in range(10)]
        inside = {(x, y) for y in range(10) for x in range(12) if mask[y][x]}
        for seed in range(20):
            rooms = S.split_by_targets((0, 0, 11, 9), FLAT, random.Random(seed), mask)
            self.assertIsNotNone(rooms, seed)
            self.assertTiles(rooms, inside)
            self.assertTrue(all(min(r.w, r.h) >= 3 for r in rooms))

    def test_mask_hole_none(self):
        # One tile missing mid-floor: no room may hold it, nothing can cut it out.
        mask = [[(x, y) != (5, 5) for x in range(12)] for y in range(10)]
        self.assertIsNone(S.split_by_targets((0, 0, 11, 9), FLAT, random.Random(0), mask))


if __name__ == "__main__":
    unittest.main()
