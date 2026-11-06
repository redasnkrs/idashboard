"""Chemins de l'application, en source ou dans l'exe PyInstaller."""
import sys
from pathlib import Path


def _app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


APP_DIR = _app_dir()
ROOT = APP_DIR
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
FROZEN = bool(getattr(sys, "frozen", False))
LOG_DIR = APP_DIR / "logs"


def is_frozen():
    return FROZEN
