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


if __name__ == "__main__":
    unittest.main()
