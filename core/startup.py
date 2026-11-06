"""Demarrage automatique avec Windows (HKCU Run)."""
import os
import subprocess
import sys
from pathlib import Path

from core.config import ROOT

try:
    import winreg
except ImportError:
    winreg = None

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "idash"


def available():
    return sys.platform == "win32" and winreg is not None


def _pythonw():
    exe = Path(sys.executable)
    candidate = exe.with_name("pythonw.exe")
    return str(candidate if candidate.is_file() else exe)


def command():
    if getattr(sys, "frozen", False):
        return subprocess.list2cmdline([str(Path(sys.executable).resolve())])
    return subprocess.list2cmdline([_pythonw(), str(ROOT / "main.py")])


def enabled():
    if not available():
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
    except OSError:
        return False
    return bool(value)


def set_enabled(value):
    if not available():
        return False
    if value:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command())
        return True
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, VALUE_NAME)
    except OSError:
        pass
    return False


def status():
    return {"available": available(), "enabled": enabled(),
            "command": command() if available() else ""}
