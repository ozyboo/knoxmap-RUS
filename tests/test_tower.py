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
        for (x0, y0, x1, y1), _kind in core.service:
            # Thinner than a room, _mend_fragments folds it away as a sliver.
            self.assertGreaterEqual(min(x1 - x0, y1 - y0) + 1, layout.MIN_ROOM)

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


FOOTPRINTS = ((14, 14), (15, 37), (30, 30))


def tower_floor(w, h, seed, **kw):
    t = tower.pick_core(w, h, None, random.Random(seed))
    return layout.build_plan(
        w, h, seed=seed, kind="civic", core=t.stair,
        stairs=layout._stairs_in_core(t.stair), shaft=t.lifts[0][0],
        shaft_door=t.lifts[0][1], extra_shafts=t.lifts[1:], levels=20,
        tower=t, **kw)


def door_links(plan):
    links = {}
    for x, y, d in plan.doors:
        a = layout._room_at(plan, x, y)
        b = layout._room_at(plan, x - 1, y) if d == "W" else layout._room_at(plan, x, y - 1)
        links.setdefault(a, set()).add(b)
        links.setdefault(b, set()).add(a)
    return links


def lift_lobby(plan, links):
    """Circulation rooms reached from the stair hall through doors."""
    core = next(i for i, r in enumerate(plan.rooms, 1) if r.is_core)
    seen, stack = {core}, [core]
    while stack:
        for n in links.get(stack.pop(), ()):
            if n and n not in seen and plan.rooms[n - 1].kind in ("hall", "lobby"):
                seen.add(n)
                stack.append(n)
    return seen


class TowerFloor(unittest.TestCase):
    def test_every_office_area_has_a_door_to_the_lift_lobby(self):
        for w, h in FOOTPRINTS:
            for seed in range(4):
                with self.subTest(w=w, h=h, seed=seed):
                    plan = tower_floor(w, h, seed, ground=False, level=5)
                    links = door_links(plan)
                    lobby = lift_lobby(plan, links)
                    offices = [i for i, r in enumerate(plan.rooms, 1) if r.kind == "office"]
                    self.assertTrue(offices)
                    t = tower.pick_core(w, h, None, random.Random(seed))
                    self.assertEqual(
                        sum(r.kind == "bathroom" for r in plan.rooms),
                        sum(k == "bathroom" for _, k in t.service))
                    for i, r in enumerate(plan.rooms, 1):
                        if r.kind in ("office", "bathroom", "storage"):
                            self.assertTrue(links.get(i, set()) & lobby, (i, r))
                    self.assertEqual(len(plan.shafts), len(
                        tower.pick_core(w, h, None, random.Random(seed)).lifts))

    def test_ground_floor_has_a_lobby_with_an_entrance(self):
        for w, h in FOOTPRINTS:
            for seed in range(4):
                with self.subTest(w=w, h=h, seed=seed):
                    plan = tower_floor(w, h, seed, ground=True, street="S")
                    links = door_links(plan)
                    lobbies = [i for i, r in enumerate(plan.rooms, 1) if r.kind == "lobby"]
                    self.assertEqual(len(lobbies), 1)
                    self.assertIn(0, links.get(lobbies[0], set()))
                    self.assertIn(lobbies[0], lift_lobby(plan, links))

    def test_plant_floor_has_no_offices(self):
        for w, h in FOOTPRINTS:
            plan = tower_floor(w, h, 1, ground=False, level=18, plant=True)
            kinds = {r.kind for r in plan.rooms}
            self.assertNotIn("office", kinds)
            self.assertIn("storage", kinds)

    def test_ground_floor_with_uses_and_mapped_rooms_still_builds(self):
        mapped = [([(0, 0), (5, 0), (5, 5), (0, 5)], "kitchen")]
        for w, h in FOOTPRINTS:
            plan = tower_floor(w, h, 2, ground=True, uses=[("shop", "office")],
                               mapped=mapped)
            links = door_links(plan)
            lobbies = [i for i, r in enumerate(plan.rooms, 1) if r.kind == "lobby"]
            self.assertTrue(lobbies)
            self.assertIn(lobbies[0], lift_lobby(plan, links))

if __name__ == "__main__":
    unittest.main()
