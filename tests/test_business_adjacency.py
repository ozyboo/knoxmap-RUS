import unittest

from knoxbuild import layout


class BusinessAdjacency(unittest.TestCase):
    def plan(self):
        rooms = [layout.Room(i * 4, 0, i * 4 + 3, 3, kind=kind)
                 for i, kind in enumerate(("kitchen", "office", "storage", "diningroom"))]
        plan = layout.Plan(16, 4, rooms=rooms)
        layout._paint(plan)
        return plan

    def test_school_canteen_and_kitchen_are_adjacent(self):
        plan = self.plan()
        layout._arrange_business_rooms(plan, "school")
        adj = layout._neighbours(plan)
        kitchen = next(i for i, r in enumerate(plan.rooms, 1) if r.kind == "kitchen")
        dining = next(i for i, r in enumerate(plan.rooms, 1) if r.kind == "diningroom")
        self.assertIn(dining, adj[kitchen])
        self.assertCountEqual([r.kind for r in plan.rooms],
                              ["kitchen", "office", "storage", "diningroom"])

    def test_fixed_rooms_are_not_moved(self):
        plan = self.plan()
        for room in plan.rooms:
            room.fixed = True
        layout._arrange_business_rooms(plan, "school")
        self.assertEqual([r.kind for r in plan.rooms],
                         ["kitchen", "office", "storage", "diningroom"])

    def test_circulation_is_never_moved(self):
        plan = self.plan()
        plan.rooms[0].kind = "lockerroom"
        plan.rooms[1].kind = "office"
        plan.rooms[2].kind = "sportstorage"
        plan.rooms[3].kind = "hall"
        layout._arrange_business_rooms(plan, "stadium")
        self.assertEqual(plan.rooms[3].kind, "hall")

    def test_large_size_mismatch_does_not_move_rooms(self):
        plan = self.plan()
        plan.rooms[3].x1 += 20
        before = [r.kind for r in plan.rooms]
        layout._arrange_business_rooms(plan, "school")
        self.assertEqual([r.kind for r in plan.rooms], before)

    def test_generated_medical_floor_keeps_clinic_next_to_medical(self):
        plan = layout.build_plan(32, 28, commercial=True, kind="medical", seed=0)
        adj = layout._neighbours(plan)
        self.assertTrue(any(room.kind == "clinic" and
                            any(plan.rooms[j - 1].kind == "medical" for j in adj[i])
                            for i, room in enumerate(plan.rooms, 1)))


if __name__ == "__main__":
    unittest.main()
