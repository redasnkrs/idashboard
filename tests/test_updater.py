import base64
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from core import updater


def make_zip(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return "data:application/zip;base64," + base64.b64encode(
        buffer.getvalue()).decode()


class UpdaterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = updater.UPDATE_DIR
        updater.UPDATE_DIR = Path(self.tmp.name) / ".update"

    def tearDown(self):
        updater.UPDATE_DIR = self.old
        self.tmp.cleanup()

    def test_prepare_valid_zip(self):
        data = make_zip({
            "main.py": "# app",
            "core/__init__.py": "",
            "studio/runtime.js": "",
            "dashboards/x.html": "",
            "VERSION": "9.9.9\n",
        })
        result = updater.prepare_zip(data, "release.zip")
        self.assertEqual("9.9.9", result["version"])
        staging = Path(result["staging"])
        self.assertTrue((staging / "main.py").is_file())
        self.assertTrue((staging / "core").is_dir())

    def test_prepare_single_wrapper_folder(self):
        data = make_zip({
            "idash/main.py": "# app",
            "idash/core/__init__.py": "",
            "idash/studio/x": "",
            "idash/dashboards/x": "",
            "idash/VERSION": "1.2.3",
        })
        result = updater.prepare_zip(data)
        self.assertEqual("1.2.3", result["version"])
        self.assertTrue(Path(result["staging"]).name in ("idash", "root"))

    def test_rejects_path_traversal(self):
        data = make_zip({
            "main.py": "",
            "core/__init__.py": "",
            "studio/x": "",
            "dashboards/x": "",
            "../evil.txt": "nope",
        })
        with self.assertRaises(ValueError):
            updater.prepare_zip(data)

    def test_rejects_missing_main(self):
        data = make_zip({"VERSION": "1.0.0"})
        with self.assertRaises(ValueError):
            updater.prepare_zip(data)

    def test_info(self):
        info = updater.info()
        self.assertIn("version", info)
        self.assertTrue(info["releases_url"].startswith("https://github.com/"))


if __name__ == "__main__":
    unittest.main()
