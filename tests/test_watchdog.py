import time
import unittest
from unittest import mock

from core import watchdog


class WatchdogTest(unittest.TestCase):
    def tearDown(self):
        watchdog.stop()

    def test_start_status_stop(self):
        with mock.patch.object(watchdog.app_settings, "keep_screen",
                               return_value=False):
            self.assertTrue(watchdog.start())
            time.sleep(0.05)
            self.assertTrue(watchdog.status()["running"])
            self.assertIn("relaunches", watchdog.status())
            watchdog.stop()


if __name__ == "__main__":
    unittest.main()
