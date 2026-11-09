import unittest

from core import gps_capture


class GpsCaptureTest(unittest.TestCase):
    def test_status(self):
        info = gps_capture.status()
        self.assertIn("available", info)
        self.assertIn("enabled", info)
        self.assertIn("region", info)
        self.assertIsNone(gps_capture.frame())


if __name__ == "__main__":
    unittest.main()
