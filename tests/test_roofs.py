import unittest

from knoxbuild import layout, tbx


class RoofLayouts(unittest.TestCase):
    def test_roof_rectangles_cover_an_irregular_footprint_once(self):
        grid = [[1] * 8 + [0] * 4 for _ in range(4)]
        grid.extend([[1] * 12 for _ in range(8)])
        rects = layout.roof_rects(grid)

        for peaked, roof30 in ((False, False), (True, False), (True, True)):
            with self.subTest(peaked=peaked, roof30=roof30):
                covered = [[0] * 12 for _ in range(12)]
                for _kind, _depth, _caps, (x0, y0, width, height) in tbx._roof_pieces(
                        rects, peaked, roof30):
                    for y in range(y0, y0 + height):
                        for x in range(x0, x0 + width):
                            covered[y][x] += 1
                self.assertEqual(covered, grid)

    def test_flat_roof_equipment_varies_by_building_without_overlapping(self):
        grid = [[1] * 10 for _ in range(10)]
        first = tbx._rooftop(grid, 10, 10, "house-a")
        second = tbx._rooftop(grid, 10, 10, "house-b")

        self.assertNotEqual(first, second)
        for placement in (first, second):
            for index, (_role, x, y, _orientation) in enumerate(placement):
                for _other, other_x, other_y, _other_orientation in placement[index + 1:]:
                    self.assertTrue(abs(x - other_x) > 1 or abs(y - other_y) > 1)

    def test_a_wide_block_among_many_wings_is_not_given_the_steep_roof(self):
        # An 11-wide block with two narrow wings: three pieces, so the block takes the
        # 45-degree roof (three levels at most), not a 30-degree one six levels high.
        grid = [[1] * 11 for _ in range(12)]
        for y in range(2, 5):
            grid[y] += [1] * 3
        for y in range(8, 11):
            grid[y] += [1] * 3
        grid = [row + [0] * (14 - len(row)) for row in grid]
        kinds = [k for k, _d, _c, box in tbx._roof_pieces(layout.roof_rects(grid), True, True)
                 if box[2] * box[3] >= 100]
        self.assertTrue(kinds and all(not k.startswith("Peak30") for k in kinds), kinds)
        # Alone, the same block keeps it.
        alone = tbx._roof_pieces(layout.roof_rects([[1] * 11 for _ in range(12)]), True, True)
        self.assertTrue(any(k.startswith("Peak30") for k, *_ in alone), alone)


if __name__ == "__main__":
    unittest.main()