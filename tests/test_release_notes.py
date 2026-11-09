import unittest

from tools.release_notes import extract


TEXT = """# Changelog

## [0.8.0] - 2026-12-01
### Ajouté
- Futur.

## [0.7.2] - 2026-11-09
### Ajouté
- ETS2.

## [0.7.1] - 2026-11-09
### Ajouté
- Ancien.
"""


class ReleaseNotesTest(unittest.TestCase):
    def test_extract(self):
        notes = extract(TEXT, "0.7.2")
        self.assertIn("ETS2", notes)
        self.assertNotIn("Ancien", notes)

    def test_missing(self):
        self.assertEqual("", extract(TEXT, "9.9.9"))


if __name__ == "__main__":
    unittest.main()
