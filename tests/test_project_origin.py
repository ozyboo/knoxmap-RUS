import os
import tempfile
import unittest

from knoxbuild.buildheader import ORIGIN_X, cell_tables
from tools.terrain_source import project_origin


def project(d, origin):
    proj = os.path.join(d, "m")
    os.makedirs(proj)
    line = f'<worldOrigin origin="{origin}"/>\n' if origin else ""
    with open(os.path.join(proj, "m.pzw"), "w", encoding="utf-8") as f:
        f.write(f'<?xml version="1.0"?>\n<world version="1.0" width="2" height="2">\n{line}</world>\n')
    return proj


class ProjectOrigin(unittest.TestCase):
    def test_read_from_the_project_file_in_tiles(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(project_origin(project(d, "0,0")), (0, 0))
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(project_origin(project(d, "3,2")), (900, 600))

    def test_no_file_or_no_line_is_the_vanilla_corner(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(project_origin(project(d, "")), (ORIGIN_X, 0))
            self.assertEqual(project_origin(os.path.join(d, "nothing")), (ORIGIN_X, 0))

    def test_room_tables_follow_the_origin(self):
        placed = [(10, 10, [{"name": "kitchen", "z": 0, "rects": [(10, 10, 5, 5)]}])]
        rooms, _ = cell_tables(0, 0, placed, origin=(0, 0))
        self.assertTrue(rooms)
        # the same building is not in that cell when the world starts 300 tiles east
        self.assertEqual(cell_tables(0, 0, placed, origin=(300, 0)), ([], []))


if __name__ == "__main__":
    unittest.main()
