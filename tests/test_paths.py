import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core import paths


class PathsTest(unittest.TestCase):
    def test_source_root(self):
        self.assertFalse(paths.is_frozen())
        self.assertEqual(Path(paths.__file__).resolve().parent.parent,
                         paths.APP_DIR)

    def test_frozen_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "idash.exe"
            with mock.patch.object(sys, "frozen", True, create=True), \
                    mock.patch.object(sys, "executable", str(exe)):
                self.assertEqual(Path(tmp).resolve(), paths._app_dir())


if __name__ == "__main__":
    unittest.main()
