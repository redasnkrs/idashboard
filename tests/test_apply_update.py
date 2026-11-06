import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import apply_update  # noqa: E402


class ApplyUpdateTest(unittest.TestCase):
    def test_copy_exe_preserves_user_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            staging = Path(tmp) / "staging"
            root = Path(tmp) / "root"
            (staging / "_internal").mkdir(parents=True)
            (staging / "custom").mkdir()
            (staging / "custom" / "evil.json").write_text("bad")
            (staging / "app.json").write_text("bad")
            (staging / "idash.exe").write_bytes(b"MZ")
            (staging / "_internal" / "x").write_text("x")
            (staging / "VERSION").write_text("1.0.0")
            (root / "custom").mkdir(parents=True)
            (root / "custom" / "keep.json").write_text("keep")
            (root / "app.json").write_text("user")
            with mock.patch.object(apply_update, "log"):
                apply_update.copy_exe(staging, root)
            self.assertTrue((root / "idash.exe").is_file())
            self.assertTrue((root / "_internal" / "x").is_file())
            self.assertEqual("keep", (root / "custom" / "keep.json").read_text())
            self.assertEqual("user", (root / "app.json").read_text())
            self.assertFalse((root / "custom" / "evil.json").exists())

    def test_copy_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            staging = Path(tmp) / "staging"
            root = Path(tmp) / "root"
            (staging / "core").mkdir(parents=True)
            (staging / "core" / "x.py").write_text("x")
            (staging / "main.py").write_text("main")
            (staging / "VERSION").write_text("1.0.0")
            with mock.patch.object(apply_update, "log"):
                apply_update.copy_source(staging, root)
            self.assertEqual("main", (root / "main.py").read_text())
            self.assertTrue((root / "core" / "x.py").is_file())


if __name__ == "__main__":
    unittest.main()
