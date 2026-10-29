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
        p = S.programme_for_flat(S.min_area(["openplan", "bathroom"]), random.Random(1))
        self.assertEqual(p, ["openplan", "bathroom"])   # a studio has its kitchen
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
        studio = S.min_area(["openplan", "bathroom"])
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


LIVING = ("livingroom", "openplan")
BEDS = ("bedroom", "kidsbedroom")


def _flat_floors(n=100):
    """Every storey of n flat blocks of varied footprint."""
    from knoxbuild import layout as L
    rng = random.Random(11)
    for i in range(n):
        w, h = rng.randint(9, 22), rng.randint(8, 18)
        b = L.build_building(w, h, levels=rng.randint(2, 4), kind="apartment", seed=i)
        yield from b.storeys


def _touches_corridor(plan, idx):
    for y in range(plan.height):
        for x in range(plan.width):
            if plan.grid[y][x] != idx:
                continue
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (0 <= nx < plan.width and 0 <= ny < plan.height
                        and plan.grid[ny][nx]
                        and plan.rooms[plan.grid[ny][nx] - 1].unit == 0):
                    return True
    return False


class Flats(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.floors = list(_flat_floors())

    def test_medians(self):
        import statistics as st
        area = {"bath": [], "bed": [], "living": []}
        for plan in self.floors:
            for r in plan.rooms:
                key = ("bath" if r.kind == "bathroom" else "bed" if r.kind == "bedroom"
                       else "living" if r.kind in LIVING else None)
                if key and not r.is_core:
                    area[key].append(r.area)
        m = {k: st.median(v) for k, v in area.items()}
        self.assertLess(m["bath"], m["bed"], m)
        self.assertLess(m["bed"], m["living"], m)

    def test_bathrooms_vs_bedrooms(self):
        baths = beds = flats = 0
        for plan in self.floors:
            baths += sum(r.kind == "bathroom" for r in plan.rooms)
            beds += sum(r.kind in BEDS for r in plan.rooms)
            flats += len({r.unit for r in plan.rooms if r.unit})
        self.assertLessEqual(baths, beds + flats)

    def test_living_at_corridor(self):
        bad = []
        for n, plan in enumerate(self.floors):
            if not plan.corridor:
                continue
            units = {r.unit for r in plan.rooms if r.unit}
            for u in units:
                if not any(r.unit == u and r.kind in LIVING and _touches_corridor(plan, i)
                           for i, r in enumerate(plan.rooms, 1)):
                    bad.append((n, u))
        self.assertEqual(bad, [])

    def test_small_flat_falls_back(self):
        from knoxbuild import layout as L
        self.assertIsNone(L._flat_by_kind((0, 0, 4, 3), random.Random(0), False, None, "N"))
        L._flat_by_kind((0, 0, 5, 4), random.Random(0), False, None, "N")
        for seed in range(10):
            b = L.build_building(6, 5, levels=2, kind="apartment", seed=seed)
            self.assertTrue(all(s.rooms for s in b.storeys))

    def test_masked_flats_keep_bathroom(self):
        # Irregular and turned footprints, as tools/audit_layouts.py builds them.
        import os
        import sys
        from knoxbuild import layout as L
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "tools"))
        from audit_layouts import irregular_mask, rotated_mask
        rng, bad = random.Random(4242), []
        for i in range(140):
            w, h = rng.randint(9, 40), rng.randint(9, 40)
            if i % 2:
                mask = irregular_mask(w, h, rng)
            else:
                fp = rotated_mask(rng)
                if fp is None:
                    continue
                w, h, mask = fp.width, fp.height, fp.mask_list()
            b = L.build_building(w, h, levels=rng.choice((2, 3, 4, 5)), seed=i,
                                 kind="apartment", mask=mask)
            for n, plan in enumerate(b.storeys):
                for u in {r.unit for r in plan.rooms if r.unit}:
                    rooms = [r for r in plan.rooms if r.unit == u]
                    if (len(rooms) >= 2 and any(r.fixed for r in rooms)
                            and not any(r.kind == "bathroom" for r in rooms)):
                        bad.append((i, n, u))
        self.assertEqual(bad, [])

    def test_hotel_unchanged(self):
        import hashlib
        from knoxbuild import layout as L
        out = []
        for seed, (w, h) in enumerate([(24, 16), (32, 24), (18, 30)]):
            b = L.build_building(w, h, levels=3, kind="apartment", hotel=True, seed=seed)
            out.append(tuple((r.x0, r.y0, r.x1, r.y1, r.kind, r.unit)
                             for s in b.storeys for r in s.rooms))
        self.assertEqual(hashlib.sha256(repr(out).encode()).hexdigest(),
                         "645f44026bd40753b1a9617d47707c825d032fcad4d5dcd8e5c06d35c518e3c9")



def _houses(n=100):
    """n houses of one to three storeys, as tools' measure.py builds them."""
    from knoxbuild import layout as L
    rng = random.Random(7)
    for i in range(n):
        w, h = rng.randint(9, 20), rng.randint(8, 16)
        yield L.build_building(w, h, levels=rng.randint(1, 3), kind="house", seed=i)


def _has_kitchen(kinds):
    return "kitchen" in kinds or "openplan" in kinds


class Houses(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.houses = list(_houses())

    def test_medians(self):
        import statistics as st
        area: dict[str, list[int]] = {}
        for b in self.houses:
            for s in b.storeys:
                for r in s.rooms:
                    if not r.is_core and not r.is_shaft:
                        area.setdefault(r.kind, []).append(r.area)
        m = {k: st.median(v) for k, v in area.items()}
        self.assertLessEqual(m["hall"], m["bedroom"], m)
        self.assertLess(m["laundry"], m["bedroom"], m)
        self.assertLess(m["storage"], m["bedroom"], m)
        self.assertLess(m["bathroom"], m["bedroom"], m)
        self.assertLess(m["bedroom"], m["livingroom"], m)

    def test_every_house_has_the_basics(self):
        for n, b in enumerate(self.houses):
            kinds = {r.kind for s in b.storeys for r in s.rooms}
            self.assertTrue(_has_kitchen(kinds), (n, kinds))
            self.assertIn("bathroom", kinds, n)
            self.assertTrue(kinds & set(BEDS), (n, kinds))

    def test_small_house(self):
        from knoxbuild import layout as L
        for seed in range(10):
            b = L.build_building(8, 10, levels=1, kind="house", seed=seed)
            kinds = {r.kind for r in b.storeys[0].rooms}
            self.assertTrue(_has_kitchen(kinds), (seed, kinds))
            self.assertIn("bathroom", kinds, seed)
            self.assertTrue(kinds & set(BEDS), (seed, kinds))

    def test_bathroom_on_every_bedroom_floor(self):
        from knoxbuild import layout as L
        rng = random.Random(3)
        for seed in range(20):
            w, h = rng.randint(9, 20), rng.randint(8, 16)
            b = L.build_building(w, h, levels=3, kind="house", seed=seed)
            self.assertEqual(len(b.storeys), 3)
            for lvl, s in enumerate(b.storeys):
                kinds = {r.kind for r in s.rooms}
                if kinds & set(BEDS):
                    self.assertIn("bathroom", kinds, (seed, w, h, lvl, kinds))

if __name__ == "__main__":
    unittest.main()
