import tempfile
import unittest
from pathlib import Path

from core import instance


class InstanceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = instance.LOCK_FILE
        instance.LOCK_FILE = Path(self.tmp.name) / ".idash.lock"
        instance.release()

    def tearDown(self):
        instance.release()
        instance.LOCK_FILE = self.old
        self.tmp.cleanup()

    def test_acquire_release(self):
        self.assertTrue(instance.acquire())
        self.assertTrue(instance.LOCK_FILE.is_file())
        instance.release()
        self.assertFalse(instance.LOCK_FILE.exists())
        self.assertTrue(instance.acquire())

    def test_release_is_idempotent(self):
        instance.release()
        instance.release()
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
