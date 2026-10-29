import random
import unittest
from collections import Counter

from knoxbuild import layout
from knoxbuild.profile import BuildingProfile


class RoomFurnitureLayouts(unittest.TestCase):
    def setUp(self):
        # The game's own art only, whatever is installed on the machine running
        # the tests: with Erika's Tiles present a bathroom mirror is swapped for
        # one of the mod's prints, so these pass on a bare PC and fail on a
        # player's.
        self._erika = list(layout._ERIKA_ALLOWED)
        layout.use_mod_tiles(False)

    def tearDown(self):
        layout._ERIKA_ALLOWED[:] = self._erika
        layout._ERIKA.clear()

    def test_bathroom_fixture_plan_does_not_mix_bath_and_shower(self):
        # A bathroom the size this generator cuts gets a bath; one smaller than
        # it ever cuts for a house - a flat's or a motel's - gets the shower.
        # Either way, never both: the room is 6.5 m2.
        cramped = layout._bathroom_wishlist(layout.BATHROOM_TILES - 1, public=False)
        self.assertIn("shower", cramped)
        self.assertNotIn("bath", cramped)
        for area in (layout.BATHROOM_TILES, 18):
            with self.subTest(area=area):
                fitted = layout._bathroom_wishlist(area, public=False)
                self.assertIn("bath", fitted)
                self.assertIn("bath_mat", fitted)
                self.assertNotIn("shower", fitted)
                # Two tiles of tub, placed before the one-tile fixtures take
                # the wall it needs.
                self.assertEqual(fitted[0], "bath")
                self.assertLess(fitted.index("sink"), fitted.index("bath_mat"))

    def test_public_bathroom_fixtures_scale_with_room_area(self):
        small = layout._bathroom_wishlist(9, public=True)
        large = layout._bathroom_wishlist(36, public=True)
        self.assertEqual(Counter(small), Counter(toilet=1, sink_public=1, mirror=1))
        self.assertEqual(Counter(large), Counter(toilet=3, sink_public=3, mirror=1))

    def test_multitile_furniture_anchors_inside_east_and_south_walls(self):
        for facing, x, y in (("E", 5, 4), ("S", 4, 5)):
            with self.subTest(facing=facing):
                ax, ay = layout._wall_anchor("shower", x, y, facing, facing)
                cells = layout._cells_for("shower", ax, ay, facing)
                if facing == "E":
                    self.assertEqual(max(cx for cx, _cy in cells), x)
                else:
                    self.assertEqual(max(cy for _cx, cy in cells), y)

    def test_bathroom_fixtures_use_shared_plumbing_wall(self):
        bathroom = layout.Room(0, 2, 2, 5, kind="bathroom")
        kitchen = layout.Room(0, 0, 2, 1, kind="kitchen")
        grid = [[2] * 3 for _ in range(2)] + [[1] * 3 for _ in range(4)]
        plan = layout.Plan(3, 6, rooms=[bathroom, kitchen], grid=grid,
                           doors=[(0, 4, "W")], kind="house")

        layout._furnish(plan, random.Random(9))

        fixtures = [("sink" if layout._is_sink(role) else role, orient)
                for role, _x, _y, orient in plan.furniture
                    if layout._room_at(plan, _x, _y) == 1
                    and (role in {"toilet", "bath"} or layout._is_sink(role))]
        self.assertEqual({role for role, _orient in fixtures},
                         {"toilet", "sink", "bath"})
        fixture_orient = dict(fixtures)
        self.assertEqual(fixture_orient["toilet"], "N")
        self.assertEqual(fixture_orient["sink"], "N")
        basin = next(item for item in plan.furniture if layout._is_sink(item[0]))
        mirror = next(item for item in plan.furniture if item[0] == "mirror")
        self.assertEqual(mirror[3], basin[3])
        self.assertLessEqual(abs(mirror[1] - basin[1]), 1)
        self.assertLessEqual(abs(mirror[2] - basin[2]), 1)

    def test_bath_mat_is_next_to_the_tub(self):
        bathroom = layout.Room(0, 0, 5, 4, kind="bathroom")
        plan = layout.Plan(6, 5, rooms=[bathroom], grid=[[1] * 6 for _ in range(5)],
                           doors=[(0, 2, "W")], kind="house")

        layout._furnish(plan, random.Random(17))

        tub = next((item for item in plan.furniture if item[0] == "bath"), None)
        mat = next((item for item in plan.furniture if item[0] == "bath_mat"), None)
        self.assertIsNotNone(tub)
        self.assertIsNotNone(mat)
        tub_cells = layout._cells_for(tub[0], tub[1], tub[2], tub[3])
        mat_cells = layout._cells_for(mat[0], mat[1], mat[2], mat[3])
        self.assertTrue(any(abs(tx - mx) + abs(ty - my) == 1
                            for tx, ty in tub_cells for mx, my in mat_cells))

    def test_open_plan_merges_only_full_aligned_living_and_kitchen_rooms(self):
        rooms = [layout.Room(0, 0, 3, 5, kind="livingroom"),
                 layout.Room(4, 0, 7, 5, kind="kitchen"),
                 layout.Room(0, 6, 7, 8, kind="bedroom")]
        grid = [[1] * 4 + [2] * 4 for _ in range(6)] + [[3] * 8 for _ in range(3)]
        plan = layout.Plan(8, 9, rooms=rooms, grid=grid)

        self.assertTrue(layout._merge_house_open_plan(plan, 1, 2))

        self.assertEqual(len(plan.rooms), 2)
        self.assertEqual(plan.rooms[0].kind, "openplan")
        self.assertEqual(plan.grid[:6], [[1] * 8 for _ in range(6)])
        self.assertEqual(plan.grid[6:], [[2] * 8 for _ in range(3)])

    def test_home_profile_varies_open_plan_dining_and_study_chances(self):
        older = BuildingProfile.infer(
            {"start_date": "1920", "class": "working_class"},
            "house", 0.16, 168, 1, 42)
        modern = BuildingProfile.infer(
            {"start_date": "1988", "class": "luxury"},
            "house", 0.2, 168, 1, 41)

        self.assertGreater(layout._house_open_plan_share(modern),
                           layout._house_open_plan_share(older))
        self.assertGreater(layout._house_dining_share(older),
                           layout._house_dining_share(modern))
        self.assertGreater(layout._house_study_share(modern),
                           layout._house_study_share(older))

    def test_modern_home_can_be_open_plan_without_making_old_homes_uniform(self):
        older = BuildingProfile.infer(
            {"start_date": "1920", "class": "working_class"},
            "house", 0.16, 168, 1, 42)
        modern = BuildingProfile.infer(
            {"start_date": "1988", "class": "luxury"},
            "house", 0.2, 168, 1, 41)
        # Counted over seeds: which one house comes out open plan is the
        # rng's business, how often is the profile's.
        def open_plan(profile):
            return sum("openplan" in {room.kind for room in layout.build_building(
                14, 12, seed=seed, kind="house", profile=profile).rooms}
                for seed in range(10))

        self.assertEqual(open_plan(older), 0)
        self.assertGreaterEqual(open_plan(modern), 2)

    def test_extra_hall_bridges_unserved_room_clusters(self):
        rooms = [layout.Room(0, 3, 2, 5), layout.Room(3, 3, 5, 5),
                 layout.Room(6, 3, 8, 5), layout.Room(3, 0, 5, 2),
                 layout.Room(3, 6, 5, 8)]
        plan = layout.Plan(9, 9, rooms=rooms,
                           grid=[[0] * 9 for _ in range(9)])
        for index, room in enumerate(rooms, start=1):
            for y in range(room.y0, room.y1 + 1):
                for x in range(room.x0, room.x1 + 1):
                    plan.grid[y][x] = index
        adj = layout._neighbours(plan)
        free = [2, 3, 4, 5]
        kinds = {}

        made = layout._more_halls(plan, adj, free, kinds, [1], 1)

        self.assertEqual(made, 1)
        self.assertEqual(kinds, {2: "hall"})

    def test_tied_hall_candidates_extend_existing_circulation(self):
        plan = layout.Plan(6, 3, rooms=[layout.Room(0, 0, 2, 2) for _ in range(6)])
        adj = {1: {2}, 2: {1, 3, 4}, 3: {2, 5},
               4: {2}, 5: {3, 6}, 6: {5}}
        kinds = {}

        made = layout._more_halls(plan, adj, [5, 2, 3, 4, 6], kinds, [1], 1)

        self.assertEqual(made, 1)
        self.assertEqual(kinds, {2: "hall"})

    def test_corridor_does_not_replace_a_stations_only_police_office(self):
        rooms = [layout.Room(x, 0, x, 0,
                             kind="policeoffice" if x == 1 else
                             "policelocker" if x == 8 else "storage")
                 for x in range(10)]
        plan = layout.Plan(10, 1, rooms=rooms, grid=[list(range(1, 11))],
                           kind="police")

        layout._circulation(plan, rooms)

        self.assertIn("policeoffice", [room.kind for room in rooms])
        self.assertIn("policelocker", [room.kind for room in rooms])


if __name__ == "__main__":
    unittest.main()
