import random
import unittest

from knoxbuild import layout, tower


def cells(rect):
    x0, y0, x1, y1 = rect
    return {(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)}


class Qualifies(unittest.TestCase):
    def test_office_towers_only(self):
        self.assertTrue(tower.qualifies("civic", 12, 14, 14))
        self.assertFalse(tower.qualifies("apartment", 12, 14, 14))
        self.assertFalse(tower.qualifies(None, 12, 14, 14))
        self.assertFalse(tower.qualifies("civic", 11, 14, 14))
        self.assertFalse(tower.qualifies("civic", 12, 13, 30))
        self.assertFalse(tower.qualifies("civic", 12, 30, 13))

    def test_plant_level(self):
        self.assertEqual(tower.plant_level(32), 29)


class PickCore(unittest.TestCase):
    def check(self, core, w, h, mask=None):
        rects = [core.stair] + [r for r, _ in core.lifts] + [r for r, _ in core.service]
        seen = set()
        for r in rects:
            c = cells(r)
            self.assertFalse(seen & c, "overlap")
            seen |= c
            for x, y in c:
                self.assertTrue(0 <= x < w and 0 <= y < h)
                if mask:
                    self.assertTrue(mask[y][x])
        self.assertEqual(layout._stairs_in_core(core.stair)[2] in "NW", True)

    def test_open_footprint(self):
        for seed in range(20):
            core = tower.pick_core(30, 30, None, random.Random(seed))
            self.assertIsNotNone(core)
            self.assertTrue(2 <= len(core.lifts) <= 4)
            self.check(core, 30, 30)
            x0, y0, x1, y1 = core.stair
            self.assertLessEqual(abs((x0 + x1 + 1) / 2 - 15), 4)
            self.assertLessEqual(abs((y0 + y1 + 1) / 2 - 15), 4)
            kinds = sorted(k for _, k in core.service)
            self.assertIn("bathroom", kinds)
            self.assertIn("storage", kinds)

    def test_lifts_face_the_hall(self):
        core = tower.pick_core(30, 30, None, random.Random(2))
        hall = cells(core.stair)
        for (x0, y0, x1, y1), (dx, dy, d) in core.lifts:
            self.assertIn(d, "WN")
            self.assertIn((dx, dy), cells((x0, y0, x1, y1)) | hall)
            self.assertTrue(any((x + ox, y + oy) in hall
                                for x, y in cells((x0, y0, x1, y1))
                                for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1))))

    def test_bigger_floor_more_lifts(self):
        small = tower.pick_core(14, 14, None, random.Random(1))
        big = tower.pick_core(40, 40, None, random.Random(1))
        self.assertLess(len(small.lifts), len(big.lifts))

    def test_deterministic(self):
        a = tower.pick_core(30, 24, None, random.Random(5))
        b = tower.pick_core(30, 24, None, random.Random(5))
        self.assertEqual(a, b)

    def test_masked_footprint(self):
        mask = [[not (x >= 8 and y < 12) for x in range(20)] for y in range(20)]
        core = tower.pick_core(20, 20, mask, random.Random(1))
        self.assertIsNone(core)
        mask = [[not (x >= 14 and y < 14) for x in range(30)] for y in range(30)]
        core = tower.pick_core(30, 30, mask, random.Random(1))
        self.assertIsNotNone(core)
        self.check(core, 30, 30, mask)


if __name__ == "__main__":
    unittest.main()
