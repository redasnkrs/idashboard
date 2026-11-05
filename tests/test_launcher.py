import sys
import unittest

from core import launcher
from core.config import SCREEN


class LauncherTest(unittest.TestCase):
    def test_dashboard_url(self):
        self.assertEqual(
            "http://127.0.0.1:25555/dashboard/course/acevo-minimal",
            launcher.dashboard_url("course/acevo-minimal"))

    def test_command_flags_when_chromium_available(self):
        cmd = launcher._command(launcher.dashboard_url("course/acevo-cluster"))
        if cmd is None:
            self.skipTest("aucun Chromium installe sur cette machine")
        joined = " ".join(cmd)
        self.assertIn("--app=", joined)
        self.assertIn("--user-data-dir=", joined)
        self.assertIn("--start-fullscreen", joined)
        self.assertIn("course/acevo-cluster", joined)
        if sys.platform == "win32":
            self.assertIn("--window-position=%d,%d" % (SCREEN["x"],
                                                       SCREEN["y"]), joined)
            self.assertIn("--window-size=%d,%d" % (SCREEN["width"],
                                                   SCREEN["height"]), joined)


if __name__ == "__main__":
    unittest.main()
