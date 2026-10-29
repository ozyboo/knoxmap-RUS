import unittest

from knoxbuild import layout

CORE = (12, 10, 17, 19)
WEST = ((10, 10, 11, 11), (12, 10, "W"))
EAST = ((18, 16, 19, 17), (18, 16, "W"))


class SeveralLifts(unittest.TestCase):
    def plan(self, **kw):
        return layout.build_plan(30, 30, kind="civic", core=CORE, levels=2,
                                 level=0, seed=3, shaft=WEST[0],
                                 shaft_door=WEST[1], **kw)

    def test_two_lifts_are_two_sealed_rooms_with_two_door_pieces(self):
        plan = self.plan(extra_shafts=[EAST])
        self.assertEqual(sum(r.is_shaft for r in plan.rooms), 2)
        self.assertEqual(plan.shafts, [WEST, EAST])
        self.assertEqual(sum(f[0] == "elevator_door" for f in plan.furniture), 2)

    def test_the_first_lift_stays_plan_shaft(self):
        plan = self.plan(extra_shafts=[EAST])
        self.assertEqual((plan.shaft, plan.shaft_door), WEST)

    def test_one_lift_is_as_before(self):
        plan = self.plan()
        self.assertEqual(plan.shafts, [WEST])
        self.assertEqual(sum(f[0] == "elevator_door" for f in plan.furniture), 1)


if __name__ == "__main__":
    unittest.main()
