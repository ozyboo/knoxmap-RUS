import unittest

from generator.osm import OSMFeature
from generator.rendering.sea import sea_polygons


class _Proj:
    """Pixels are (lon, lat) x 100 on a 100 x 100 map."""
    width = height = 100

    def to_px(self, lat, lon):
        return lon, lat


def coast(ident, pts):
    return OSMFeature(ident, "way", {"natural": "coastline"}, [(y, x) for x, y in pts])


class Sea(unittest.TestCase):
    def test_a_shore_across_the_map_makes_one_sea(self):
        # land on the left of a line running west to east: the north half is water.
        faces = sea_polygons([coast(1, [(-5, 50), (105, 50)])], _Proj())
        self.assertEqual(len(faces), 1)
        self.assertAlmostEqual(faces[0].area, 5000, delta=300)

    def test_a_loose_end_inside_the_map_is_carried_on(self):
        faces = sea_polygons([coast(1, [(-5, 50), (60, 50)])], _Proj())
        self.assertEqual(len(faces), 1)
        self.assertGreater(faces[0].area, 4000)

    def test_a_junction_is_not_a_loose_end(self):
        # Two shores crossing at (50, 50): every end of the pieces they are cut
        # into at the crossing used to fire a ray across the whole map.
        shores = [coast(1, [(-5, 50), (105, 50)]), coast(2, [(50, -5), (50, 105)])]
        faces = sea_polygons(shores, _Proj())
        total = sum(f.area for f in faces)
        # at most the map itself, split along lines that stay on the grid
        self.assertLessEqual(total, 10000 + 1)
        for f in faces:
            minx, miny, maxx, maxy = f.bounds
            self.assertGreaterEqual(minx, -0.001)
            self.assertLessEqual(maxx, 100.001)


if __name__ == "__main__":
    unittest.main()
