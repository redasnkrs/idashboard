import json
import sys
import tempfile
import unittest
from pathlib import Path

from core import app_settings, game, screens


class AppSettingsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_app = app_settings.APP_FILE
        self.old_legacy = app_settings.LEGACY_GAME_FILE
        app_settings.APP_FILE = Path(self.tmp.name) / "app.json"
        app_settings.LEGACY_GAME_FILE = Path(self.tmp.name) / "game.json"

    def tearDown(self):
        app_settings.APP_FILE = self.old_app
        app_settings.LEGACY_GAME_FILE = self.old_legacy
        self.tmp.cleanup()

    def test_screen_save(self):
        screen = {"x": 10, "y": 20, "width": 1024, "height": 600,
                  "device": "TEST", "primary": False}
        saved = app_settings.save_screen(screen)
        self.assertEqual("TEST", saved["device"])
        self.assertEqual(screen, app_settings.screen())

    def test_games_save(self):
        app_settings.save_game("ac", {"exe": "/tmp/acs.exe"})
        self.assertEqual("/tmp/acs.exe", app_settings.game("ac")["exe"])
        with self.assertRaises(ValueError):
            game.save_game("nope", {"exe": "/tmp/x"})

    def test_default_dashboard(self):
        self.assertEqual("course/acevo-cluster",
                         app_settings.default_dashboard())
        app_settings.save_default_dashboard("course/acevo-minimal")
        self.assertEqual("course/acevo-minimal",
                         app_settings.default_dashboard())

    def test_legacy_migration(self):
        legacy = Path(self.tmp.name) / "game.json"
        legacy.write_text(json.dumps({"exe": "/tmp/acevo.exe",
                                      "app_id": "3058630"}),
                          encoding="utf-8")
        data = app_settings.load()
        self.assertEqual("/tmp/acevo.exe", data["games"]["acevo"]["exe"])

    def test_keep_screen_and_last_dashboard(self):
        self.assertFalse(app_settings.keep_screen())
        self.assertTrue(app_settings.save_keep_screen(True))
        self.assertTrue(app_settings.keep_screen())
        app_settings.save_last_dashboard("custom/audi")
        self.assertEqual("custom/audi", app_settings.last_dashboard())
        app_settings.save_last_dashboard("../bad")
        self.assertEqual("custom/audi", app_settings.last_dashboard())

    def test_pick_7(self):
        monitors = [
            {"width": 2560, "height": 1440, "primary": True, "x": 0, "y": 0},
            {"width": 1024, "height": 600, "primary": False, "x": 2560,
             "y": 834},
        ]
        picked = screens.pick_7(monitors)
        self.assertEqual(1024, picked["width"])
        self.assertEqual(2560, picked["x"])


if __name__ == "__main__":
    unittest.main()
