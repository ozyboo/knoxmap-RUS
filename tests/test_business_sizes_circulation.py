import unittest
from knoxbuild import layout


class BusinessSizesAndCirculation(unittest.TestCase):
    def test_public_buildings_have_compact_bathrooms(self):
        for kind in ("school", "church", "industrial", "military", "castle",
                     "stadium", "medical", "civic", "police", "library", "fire", "offices"):
            with self.subTest(kind=kind):
                plan = layout.build_building(32, 28, kind=kind, commercial=True,
                                             seed=0, levels=1).storeys[0]
                toilets = [room for room in plan.rooms if room.kind == "bathroom"]
                self.assertTrue(toilets)
                self.assertLessEqual(min(room.area for room in toilets), 20)

    def test_school_has_circulation_reaching_classrooms(self):
        plan = layout.build_building(32, 28, kind="school", commercial=True,
                                     seed=0, levels=1).storeys[0]
        adj = layout._neighbours(plan)
        halls = {i for i, r in enumerate(plan.rooms, 1) if r.kind in layout.CIRCULATION}
        classrooms = [i for i, r in enumerate(plan.rooms, 1) if r.kind == "classroom"]
        self.assertTrue(classrooms)
        self.assertGreaterEqual(sum(bool(set(adj[i]) & halls) for i in classrooms) * 2,
                                len(classrooms))

    def test_shop_floors_keep_a_compact_bathroom(self):
        for kind in ("shop", "restaurant", "retail"):
            with self.subTest(kind=kind):
                plan = layout.build_building(32, 28, kind=kind, commercial=True,
                                             seed=0, street="S").storeys[0]
                self.assertLessEqual(min(r.area for r in plan.rooms if r.kind == "bathroom"), 20)

    def test_special_purpose_floors_keep_their_primary_space(self):
        for kind, primary in (("barn", "warehouse"), ("shed", "shed"),
                              ("garage", "garage"), ("mall", "concourse")):
            with self.subTest(kind=kind):
                plan = layout.build_building(32, 28, kind=kind, commercial=True,
                                             seed=0, street="S").storeys[0]
                self.assertIn(primary, {r.kind for r in plan.rooms})
                if kind == "garage":
                    self.assertEqual(len(plan.rooms), 1)


if __name__ == "__main__":
    unittest.main()
