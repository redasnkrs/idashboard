import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from core import ets2_map


class Ets2MapTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_dir = ets2_map.MAP_DIR
        self.old_zip = ets2_map._zip
        self.old_path = ets2_map._zip_path
        self.old_info = ets2_map._info
        ets2_map.MAP_DIR = Path(self.tmp.name)
        ets2_map._zip = None
        ets2_map._zip_path = ""
        ets2_map._info = None
        path = ets2_map.MAP_DIR / ets2_map.ZIP_NAME
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("tsmap-ets2/TileMapInfo.json", json.dumps({
                "x1": -100, "x2": 100, "y1": -100, "y2": 100,
                "minZoom": 0, "maxZoom": 8}))
            archive.writestr("tsmap-ets2/Tiles/0/0/0.png", b"PNG")
        self.path = path

    def tearDown(self):
        ets2_map.MAP_DIR = self.old_dir
        ets2_map._zip = self.old_zip
        ets2_map._zip_path = self.old_path
        ets2_map._info = self.old_info
        self.tmp.cleanup()

    def test_info_and_tile(self):
        info = ets2_map.info()
        self.assertTrue(info["ok"])
        self.assertEqual(8, info["max_zoom"])
        self.assertEqual(b"PNG", ets2_map.tile(0, 0, 0))
        self.assertIsNone(ets2_map.tile(8, 255, 255))

    def test_missing_tile(self):
        self.assertIsNone(ets2_map.tile(1, 0, 0))


if __name__ == "__main__":
    unittest.main()
