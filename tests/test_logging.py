import logging
import tempfile
import unittest
from pathlib import Path

from core import logging_setup


class LoggingTest(unittest.TestCase):
    def test_recent_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = logging_setup.LOG_FILE
            logging_setup.LOG_FILE = Path(tmp) / "idash.log"
            logging_setup.LOG_FILE.write_text(
                "2026 INFO ok\n2026 ERROR boom\n2026 CRITICAL bad\n",
                encoding="utf-8")
            try:
                errors = logging_setup.recent_errors()
                self.assertEqual(2, len(errors))
                self.assertIn("ERROR boom", errors[0])
            finally:
                logging_setup.LOG_FILE = old


if __name__ == "__main__":
    unittest.main()
