"""Etat de sante de l'application pour /api/health et le diagnostic."""
import json
import os
import sys
import time

from core import app_settings, launcher, pump
from core.config import PORT, ROOT, VERSION
from core.logging_setup import log_path
from core.paths import FROZEN

_START = time.monotonic()


def _dash():
    try:
        data = json.loads(pump.STATE["dash"].decode("utf-8"))
    except (ValueError, AttributeError):
        return {}
    return data if isinstance(data, dict) else {}


def info(port=None):
    dash = _dash()
    age = None
    if pump.LAST_UPDATE:
        age = max(0, int((time.monotonic() - pump.LAST_UPDATE) * 1000))
    try:
        from core import watchdog
        watch = watchdog.status()
    except Exception:
        watch = {}
    return {
        "ok": True,
        "version": VERSION,
        "uptime_s": int(time.monotonic() - _START),
        "pid": os.getpid(),
        "frozen": FROZEN,
        "platform": sys.platform,
        "port": int(port or PORT),
        "root": str(ROOT),
        "log_file": str(log_path()),
        "telemetry_age_ms": age,
        "connected": bool(dash.get("c")),
        "game_id": dash.get("game_id") or "",
        "game": dash.get("game") or "",
        "car": dash.get("car") or "",
        "last_error": pump.LAST_ERROR,
        "launcher_running": launcher.is_running(),
        "default_dashboard": app_settings.default_dashboard(),
        "keep_screen": app_settings.keep_screen(),
        "startup": _startup_enabled(),
        "watchdog": watch,
    }


def _startup_enabled():
    try:
        from core import startup
        return startup.enabled()
    except Exception:
        return False
