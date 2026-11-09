import unittest

from core import ambient, app_settings


class AmbientTest(unittest.TestCase):
    def test_sc_packet(self):
        packet = ambient._sc([(255, 0, 0), (0, 255, 0)])
        self.assertEqual(b"SC", packet[:2])
        self.assertEqual(len(packet), 7 + 5 * 2)
        self.assertEqual(packet[5], ambient.ACTION_SYNC_SCREEN)
        self.assertEqual(packet[-1], sum(packet[:-1]) & 0xFF)

    def test_colors(self):
        self.assertEqual((255, 122, 0), ambient._color("#ff7a00"))
        self.assertEqual((0, 0, 0), ambient._color("bad"))
        self.assertIsNotNone(ambient._flag_color("yellow"))
        self.assertIsNone(ambient._flag_color(""))

    def test_config(self):
        saved = app_settings.save_ambient({
            "enabled": True, "led_count": 60, "split": 0.4,
            "brightness": 0.5, "rpm": False, "flags": True})
        self.assertTrue(saved["enabled"])
        self.assertEqual(60, saved["led_count"])
        self.assertAlmostEqual(0.4, saved["split"])
        self.assertFalse(saved["rpm"])
        self.assertTrue(saved["flags"])
        loaded = app_settings.ambient()
        self.assertTrue(loaded["enabled"])
        self.assertEqual(60, loaded["led_count"])
        self.assertAlmostEqual(0.4, loaded["split"])


if __name__ == "__main__":
    unittest.main()
