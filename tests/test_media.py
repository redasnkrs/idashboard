import base64
import sys
import unittest

from core import media


PNG = b"\x89PNG\r\n\x1a\n" + b"idash" * 4


class MediaTest(unittest.TestCase):
    def tearDown(self):
        media._apply({"ok": False})

    def test_snapshot_has_platform(self):
        info = media.snapshot()
        self.assertIn("platform", info)
        self.assertIn("has_art", info)
        if sys.platform != "win32":
            self.assertFalse(info["ok"])

    def test_apply_metadata_and_art(self):
        media._apply({
            "ok": True, "key": "T|A|B",
            "title": "T", "artist": "A", "album": "B",
            "source": "Cider", "playing": True,
            "position": 1.5, "duration": 3.0,
            "art": base64.b64encode(PNG).decode(),
        })
        info = media.snapshot()
        self.assertTrue(info["ok"])
        self.assertEqual("T", info["title"])
        self.assertEqual("A", info["artist"])
        self.assertEqual("Cider", info["source"])
        self.assertTrue(info["playing"])
        self.assertTrue(info["has_art"])
        raw, ctype = media.art()
        self.assertEqual(PNG, raw)
        self.assertEqual("image/png", ctype)

    def test_new_track_clears_old_art(self):
        media._apply({
            "ok": True, "key": "T1|A|B", "title": "T1",
            "art": base64.b64encode(PNG).decode(),
        })
        self.assertIsNotNone(media.art()[0])
        media._apply({"ok": True, "key": "T2|A|B", "title": "T2"})
        self.assertIsNone(media.art()[0])

    def test_control_rejects_unknown_action(self):
        result = media.control("nope")
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
