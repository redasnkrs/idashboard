import unittest
from unittest import mock

from core import scs_plugin


class ScsPluginTest(unittest.TestCase):
    def test_status_no_game(self):
        with mock.patch.object(scs_plugin.game, "load_game",
                               return_value={}), \
                mock.patch.object(scs_plugin.game, "detect_game",
                                  return_value=""):
            info = scs_plugin.status()
            self.assertFalse(info["installed"])
            self.assertIn("available", info)

    def test_install_non_windows(self):
        if scs_plugin.os.name == "nt":
            self.skipTest("Windows")
        with self.assertRaises(ValueError):
            scs_plugin.install()


if __name__ == "__main__":
    unittest.main()
