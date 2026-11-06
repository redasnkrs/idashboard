import unittest
from unittest import mock

from core import startup


class Key:
    def __init__(self, store):
        self.store = store

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeWinreg:
    HKEY_CURRENT_USER = object()
    KEY_READ = 1
    KEY_SET_VALUE = 2
    REG_SZ = 1

    def __init__(self):
        self.values = {}

    def OpenKey(self, root, path, reserved=0, access=0):
        if not self.values and access == self.KEY_READ:
            raise OSError("absent")
        return Key(self.values)

    def CreateKey(self, root, path):
        return Key(self.values)

    def QueryValueEx(self, key, name):
        if name not in self.values:
            raise OSError("absent")
        return self.values[name], self.REG_SZ

    def SetValueEx(self, key, name, reserved, kind, value):
        self.values[name] = value

    def DeleteValue(self, key, name):
        self.values.pop(name, None)


class StartupTest(unittest.TestCase):
    def test_status_non_windows(self):
        with mock.patch.object(startup.sys, "platform", "darwin"):
            self.assertFalse(startup.available())
            self.assertFalse(startup.enabled())
            self.assertFalse(startup.set_enabled(True))

    def test_windows_toggle(self):
        fake = FakeWinreg()
        with mock.patch.object(startup.sys, "platform", "win32"), \
                mock.patch.object(startup, "winreg", fake):
            self.assertTrue(startup.available())
            self.assertFalse(startup.enabled())
            self.assertTrue(startup.set_enabled(True))
            self.assertTrue(startup.enabled())
            self.assertIn("main.py", startup.command())
            self.assertFalse(startup.set_enabled(False))
            self.assertFalse(startup.enabled())


if __name__ == "__main__":
    unittest.main()
