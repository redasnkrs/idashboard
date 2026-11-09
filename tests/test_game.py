import sys
import tempfile
import unittest
from pathlib import Path

from core import app_settings, game


class GameTest(unittest.TestCase):
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

    def test_defaults(self):
        state = game.load()
        self.assertEqual(game.DEFAULT_APP_ID, state["app_id"])
        self.assertEqual("", state["exe"])
        info = game.status()
        self.assertEqual(game.DEFAULT_APP_ID, info["app_id"])
        self.assertFalse(info["exe_exists"])

    def test_save_roundtrip(self):
        target = Path(self.tmp.name) / "AssettoCorsaEVO.exe"
        target.write_text("", encoding="utf-8")
        state = game.save({"exe": '"%s"' % target})
        self.assertEqual(str(target), state["exe"])
        self.assertEqual(str(target), game.load()["exe"])
        self.assertTrue(game.status()["exe_exists"])

    def test_rejects_bad_paths(self):
        for value in (123, "a\nb", "a\x00b", "x" * 2000):
            with self.assertRaises(ValueError):
                game.save({"exe": value})

    def test_rejects_bad_app_id(self):
        with self.assertRaises(ValueError):
            game.save({"app_id": "abc"})

    @unittest.skipIf(sys.platform == "win32",
                     "script de test non execute sous Windows")
    def test_launch_with_executable(self):
        script = Path(self.tmp.name) / "fake-game.sh"
        script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        script.chmod(0o755)
        game.save({"exe": str(script)})
        result = game.launch()
        self.assertTrue(result["ok"])
        self.assertEqual("exe", result["method"])

    @unittest.skipIf(sys.platform == "win32",
                     "Windows lance Steam par defaut")
    def test_launch_without_path(self):
        result = game.launch()
        self.assertFalse(result["ok"])
        self.assertIn("chemin", result["error"])

    def test_detect_on_non_windows(self):
        if sys.platform != "win32":
            self.assertEqual("", game.detect())
            self.assertEqual("", game.detect_game("ac"))
            self.assertEqual("", game.detect_game("ams2"))

    def test_all_games_status(self):
        keys = {item["key"] for item in game.status_all()}
        self.assertEqual({"acevo", "ac", "ams2", "ets2"}, keys)


if __name__ == "__main__":
    unittest.main()
