import base64
import json
import tempfile
import unittest
from pathlib import Path

from core import studio


class StudioTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name) / "custom"
        self.old = (studio.LAYOUTS_DIR, studio.PREVIEWS_DIR, studio.ICONS_DIR)
        studio.LAYOUTS_DIR = base / "layouts"
        studio.PREVIEWS_DIR = base / "previews"
        studio.ICONS_DIR = base / "icons"

    def tearDown(self):
        studio.LAYOUTS_DIR, studio.PREVIEWS_DIR, studio.ICONS_DIR = self.old
        self.tmp.cleanup()

    def payload(self):
        return {
            "name": "My Dashboard",
            "description": "test",
            "category": "custom",
            "game": "Assetto Corsa Evo",
            "game_id": "acevo",
            "order": 12,
            "tags": ["test", "gt"],
            "canvas": {"grid": 16},
            "background": "ink",
            "widgets": [
                {"type": "value", "x": 40, "y": 40, "w": 220, "h": 90,
                 "label": "SPEED", "field": "v", "format": "int",
                 "unit": "auto", "size": 64},
                {"type": "icon", "x": 700, "y": 40, "w": 44, "h": 44,
                 "icon": "low-beam", "field": "low"},
                {"type": "nope"},
                {"type": "shape", "x": -10, "y": 500, "w": 2000, "h": 200},
            ],
        }

    def test_save_load_list_delete(self):
        data = self.payload()
        data["preview_svg"] = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>'
        layout = studio.save_layout(data)
        self.assertEqual("my-dashboard", layout["id"])
        self.assertEqual(3, len(layout["widgets"]))
        shape = layout["widgets"][2]
        self.assertEqual(0, shape["x"])
        self.assertEqual(1024, shape["w"])
        self.assertEqual(100, shape["h"])
        self.assertIsNotNone(studio.load_layout("my-dashboard"))
        self.assertIsNotNone(studio.preview_path("my-dashboard"))
        items = studio.list_layouts()
        self.assertEqual(1, len(items))
        meta = studio.catalog_entry(items[0])
        self.assertEqual("custom/my-dashboard", meta["spec"])
        self.assertEqual("/dashboard/custom/my-dashboard", meta["url"])
        self.assertTrue(meta["preview_url"].endswith(".svg"))
        self.assertTrue(studio.delete_layout("my-dashboard"))
        self.assertIsNone(studio.load_layout("my-dashboard"))
        self.assertIsNone(studio.preview_path("my-dashboard"))

    def test_name_required(self):
        with self.assertRaises(ValueError):
            studio.save_layout({"category": "custom", "widgets": []})

    def test_unique_ids(self):
        a = studio.save_layout({"name": "Same", "widgets": []})
        b = studio.save_layout({"name": "Same", "widgets": []})
        self.assertNotEqual(a["id"], b["id"])

    def test_icon_upload_list_delete(self):
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><circle cx="5" cy="5" r="4"/></svg>'
        data = "data:image/svg+xml;base64," + base64.b64encode(svg).decode()
        icon = studio.save_icon({"name": "Dot", "data": data})
        self.assertTrue(icon["id"].endswith(".svg"))
        self.assertIsNotNone(studio.icon_path(icon["id"]))
        self.assertEqual(1, len(studio.list_icons()))
        self.assertTrue(studio.delete_icon(icon["id"]))
        self.assertIsNone(studio.icon_path(icon["id"]))

    def test_icon_rejects_script(self):
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        data = "data:image/svg+xml;base64," + base64.b64encode(svg).decode()
        with self.assertRaises(ValueError):
            studio.save_icon({"name": "Bad", "data": data})

    def test_preview_strips_foreign_object(self):
        data = self.payload()
        data["preview_svg"] = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<foreignObject x="0" y="0" width="10" height="10">'
            '<div xmlns="http://www.w3.org/1999/xhtml">map</div>'
            '</foreignObject><rect width="10" height="10"/></svg>')
        layout = studio.save_layout(data)
        preview = studio.preview_path(layout["id"]).read_text()
        self.assertNotIn("foreignObject", preview)
        self.assertIn("<rect", preview)

    def test_preview_rejects_script(self):
        data = self.payload()
        data["preview_svg"] = ('<svg xmlns="http://www.w3.org/2000/svg">'
                               '<script>alert(1)</script></svg>')
        with self.assertRaises(ValueError):
            studio.save_layout(data)


if __name__ == "__main__":
    unittest.main()
