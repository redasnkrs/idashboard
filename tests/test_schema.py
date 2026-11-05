import unittest

from adapters.fake import FakeSource
from core.schema import (DASH_SCHEMA, SCHEMA_VERSION, schema_info, validate)


class SchemaTest(unittest.TestCase):
    def test_version(self):
        self.assertIsInstance(SCHEMA_VERSION, int)
        self.assertGreaterEqual(SCHEMA_VERSION, 1)
        self.assertEqual(schema_info()["version"], SCHEMA_VERSION)

    def test_fake_source_respects_contract(self):
        dash = FakeSource().read()
        self.assertEqual([], validate(dash))
        self.assertIsInstance(dash["ign"], bool)
        self.assertIsInstance(dash["run"], bool)

    def test_disconnected_state(self):
        self.assertEqual([], validate({"c": False}))

    def test_disconnected_rejects_extra_keys(self):
        self.assertTrue(validate({"c": False, "v": 0}))

    def test_unknown_key_is_rejected(self):
        self.assertTrue(validate({"c": False, "nope": 1}))

    def test_bool_is_not_a_number(self):
        bad = FakeSource().read()
        bad["v"] = True
        self.assertTrue(validate(bad))

    def test_nullable_values(self):
        dash = FakeSource().read()
        for key in ("wt", "ot", "op", "boost", "at", "tcl", "absl", "bb",
                    "npos"):
            dash[key] = None
        self.assertEqual([], validate(dash))

    def test_contract_has_expected_keys(self):
        for key in ("c", "v", "r", "rm", "g", "fuel", "lap", "car",
                    "ign", "run", "npos", "mode", "at"):
            self.assertIn(key, DASH_SCHEMA)


if __name__ == "__main__":
    unittest.main()
