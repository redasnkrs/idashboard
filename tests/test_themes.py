import tempfile
import unittest
from pathlib import Path

from core import themes


class ThemesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_state = themes.STATE_FILE
        themes.STATE_FILE = Path(self.tmp.name) / "active.json"

    def tearDown(self):
        themes.STATE_FILE = self.old_state
        self.tmp.cleanup()

    def test_presets_exist(self):
        presets = themes.load_themes()
        self.assertEqual({"ambre-ivoire", "rouge-sport", "vert"}, set(presets))
        for theme in presets.values():
            self.assertTrue(themes.COLOR_KEYS <= set(theme["colors"]))
            self.assertTrue(set(theme["blocks"]) >= themes.BLOCK_KEYS)
            self.assertIn(theme["units"]["speed"], ("kmh", "mph"))

    def test_default_resolution(self):
        theme = themes.resolve()
        self.assertEqual("ambre-ivoire", theme["id"])
        self.assertIn("colors", theme)

    def test_global_override(self):
        themes.update({
            "scope": "global",
            "active": "vert",
            "overrides": {"colors": {"amber": "#00ff00"},
                          "units": {"speed": "mph"},
                          "blocks": {"fuel": False}},
        })
        theme = themes.resolve()
        self.assertEqual("vert", theme["id"])
        self.assertEqual("#00ff00", theme["colors"]["amber"])
        self.assertEqual("mph", theme["units"]["speed"])
        self.assertFalse(theme["blocks"]["fuel"])

    def test_scope_resolution_order(self):
        themes.update({"scope": "global", "active": "ambre-ivoire",
                       "overrides": {"colors": {"ink": "#000001"}}})
        themes.update({"scope": "game", "key": "acevo", "active": "vert",
                       "overrides": {"colors": {"ivory": "#ffffff"}}})
        themes.update({"scope": "car", "key": "FERRARI 296 GT3",
                       "active": "rouge-sport",
                       "overrides": {"colors": {"amber": "#123456"}}})
        themes.update({"scope": "dashboard", "key": "course/acevo-cluster",
                       "active": "vert",
                       "overrides": {"colors": {"amber": "#abcdef"}}})
        theme = themes.resolve(dashboard="course/acevo-cluster",
                               game="acevo", car="FERRARI 296 GT3")
        self.assertEqual("vert", theme["id"])
        self.assertEqual("#000001", theme["colors"]["ink"])
        self.assertEqual("#ffffff", theme["colors"]["ivory"])
        self.assertEqual("#abcdef", theme["colors"]["amber"])

    def test_dashboard_scope_reset(self):
        themes.update({"scope": "car", "key": "FERRARI 296 GT3",
                       "active": "rouge-sport"})
        themes.update({"scope": "dashboard", "key": "course/acevo-cluster",
                       "active": "vert"})
        self.assertEqual("vert", themes.resolve(
            dashboard="course/acevo-cluster", car="FERRARI 296 GT3")["id"])
        themes.reset_scope("dashboard", "course/acevo-cluster")
        self.assertEqual("rouge-sport", themes.resolve(
            dashboard="course/acevo-cluster", car="FERRARI 296 GT3")["id"])

    def test_sanitize(self):
        clean = themes.sanitize_overrides({
            "colors": {"amber": "#aabbcc", "nope": "#ffffff", "ink": "red"},
            "units": {"speed": "warp", "temp": "f"},
            "blocks": {"fuel": False, "nope": True},
            "font": "x" * 5,
        })
        self.assertEqual({"amber": "#aabbcc"}, clean["colors"])
        self.assertEqual({"temp": "f"}, clean["units"])
        self.assertEqual({"fuel": False}, clean["blocks"])
        self.assertEqual("xxxxx", clean["font"])

    def test_unknown_theme_rejected(self):
        with self.assertRaises(ValueError):
            themes.update({"scope": "global", "active": "nope"})


if __name__ == "__main__":
    unittest.main()
