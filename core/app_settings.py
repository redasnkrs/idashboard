"""Reglages locaux de l'application (ecran, jeux, compteur par defaut).

Le fichier ``app.json`` est ignore par git. Il remplace progressivement
``game.json`` (migration automatique du chemin AC Evo).
"""
import json
import os
import re
import sys
import threading
from pathlib import Path

from core.config import DEFAULT_DASHBOARD, ROOT, SCREEN

APP_FILE = ROOT / "app.json"
LEGACY_GAME_FILE = ROOT / "game.json"
_SAFE_KEY = re.compile(r"^[a-z0-9_-]{1,32}$")
_SAFE_DASH = re.compile(r"^[A-Za-z0-9_/-]{1,120}$")

_lock = threading.Lock()


def _empty():
    return {"screen": {}, "games": {}, "default_dashboard": "",
            "keep_screen": False, "last_dashboard": "",
            "open_on_start": True, "ambient": {}}


def load():
    state = _empty()
    try:
        saved = json.loads(APP_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = None
    if isinstance(saved, dict):
        screen = saved.get("screen")
        if isinstance(screen, dict):
            state["screen"] = screen
        games = saved.get("games")
        if isinstance(games, dict):
            state["games"] = games
        dash = saved.get("default_dashboard")
        if isinstance(dash, str):
            state["default_dashboard"] = dash
        if "keep_screen" in saved:
            state["keep_screen"] = bool(saved.get("keep_screen"))
        if "open_on_start" in saved:
            state["open_on_start"] = bool(saved.get("open_on_start"))
        ambient = saved.get("ambient")
        if isinstance(ambient, dict):
            state["ambient"] = ambient
        last = saved.get("last_dashboard")
        if isinstance(last, str) and _SAFE_DASH.match(last):
            state["last_dashboard"] = last
    if not isinstance(state["games"].get("acevo"), dict) or \
            not state["games"].get("acevo", {}).get("exe"):
        try:
            legacy = json.loads(LEGACY_GAME_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            legacy = None
        if isinstance(legacy, dict):
            exe = legacy.get("exe")
            app_id = legacy.get("app_id")
            if isinstance(exe, str) and exe.strip():
                game = state["games"].setdefault("acevo", {})
                game["exe"] = exe.strip()
                if isinstance(app_id, str) and app_id.isdigit():
                    game["app_id"] = app_id
    return state


def _save(state):
    APP_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = APP_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    tmp.replace(APP_FILE)


def _clean_exe(value):
    if not isinstance(value, str):
        raise ValueError("chemin invalide")
    exe = os.path.expandvars(os.path.expanduser(value.strip().strip('"')))
    if len(exe) > 1024:
        raise ValueError("chemin trop long")
    if any(c in exe for c in ("\x00", "\n", "\r")):
        raise ValueError("chemin invalide")
    return exe


def _valid_screen(screen):
    if not isinstance(screen, dict):
        return None
    try:
        out = {
            "x": int(screen.get("x", 0)),
            "y": int(screen.get("y", 0)),
            "width": int(screen.get("width", 0)),
            "height": int(screen.get("height", 0)),
            "device": str(screen.get("device") or ""),
            "primary": bool(screen.get("primary")),
        }
    except (TypeError, ValueError):
        return None
    if out["width"] < 200 or out["height"] < 200:
        return None
    return out


def screen():
    if any(k in os.environ for k in ("IDASH_SCREEN_X", "IDASH_SCREEN_Y",
                                     "IDASH_SCREEN_W", "IDASH_SCREEN_H")):
        return dict(SCREEN)
    saved = _valid_screen(load().get("screen"))
    if saved is not None:
        if saved.get("device") and sys.platform == "win32":
            try:
                from core.screens import list_screens
                for monitor in list_screens():
                    if monitor.get("device") == saved["device"]:
                        return monitor
            except Exception:
                pass
        return saved
    if sys.platform == "win32":
        try:
            from core.screens import list_screens, pick_7
            found = pick_7(list_screens())
            if found:
                return found
        except Exception:
            pass
    return dict(SCREEN)


def save_screen(screen_dict):
    valid = _valid_screen(screen_dict)
    if valid is None:
        raise ValueError("ecran invalide")
    with _lock:
        state = load()
        state["screen"] = valid
        _save(state)
        return valid


def games():
    return load().get("games") or {}


def game(key):
    if not isinstance(key, str) or not _SAFE_KEY.match(key):
        return {}
    value = games().get(key)
    return value if isinstance(value, dict) else {}


def save_game(key, payload):
    if not isinstance(key, str) or not _SAFE_KEY.match(key):
        raise ValueError("jeu inconnu")
    if not isinstance(payload, dict):
        raise ValueError("payload invalide")
    with _lock:
        state = load()
        entry = state["games"].setdefault(key, {})
        if "exe" in payload:
            entry["exe"] = _clean_exe(payload["exe"])
        if "app_id" in payload:
            app_id = payload["app_id"]
            if not isinstance(app_id, str) or not app_id.isdigit():
                raise ValueError("app id invalide")
            entry["app_id"] = app_id
        _save(state)
        return dict(entry)


def default_dashboard():
    dash = load().get("default_dashboard") or ""
    return dash if _SAFE_DASH.match(dash) else DEFAULT_DASHBOARD


def keep_screen():
    return bool(load().get("keep_screen"))


def save_keep_screen(enabled):
    with _lock:
        state = load()
        state["keep_screen"] = bool(enabled)
        _save(state)
        return state["keep_screen"]


def last_dashboard():
    value = load().get("last_dashboard") or ""
    return value if _SAFE_DASH.match(value) else ""


_AMBIENT_DEFAULTS = {
    "enabled": False,
    "led_count": 0,
    "split": 0.5,
    "swap": False,
    "brightness": 1.0,
    "turn_color": "#ff7a00",
    "idle_color": "#000000",
    "rpm": True,
    "flags": True,
    "brake": False,
    "turns": True,
    "sync": False,
    "sync_mode": "gradient",
    "fps": 20,
}


def _hex_color(value, default):
    if isinstance(value, str):
        value = value.strip()
        if re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            return value.lower()
    return default


def ambient():
    raw = load().get("ambient")
    out = dict(_AMBIENT_DEFAULTS)
    if not isinstance(raw, dict):
        return out
    out["enabled"] = bool(raw.get("enabled"))
    try:
        out["led_count"] = max(0, min(512, int(raw.get("led_count", 0))))
    except (TypeError, ValueError):
        pass
    try:
        out["split"] = max(0.05, min(0.95, float(raw.get("split", 0.5))))
    except (TypeError, ValueError):
        pass
    out["swap"] = bool(raw.get("swap"))
    try:
        out["brightness"] = max(0.05, min(1.0, float(raw.get("brightness", 1.0))))
    except (TypeError, ValueError):
        pass
    out["turn_color"] = _hex_color(raw.get("turn_color"), out["turn_color"])
    out["idle_color"] = _hex_color(raw.get("idle_color"), out["idle_color"])
    for key in ("rpm", "flags", "brake", "turns", "sync"):
        if key in raw:
            out[key] = bool(raw.get(key))
    if raw.get("sync_mode") in ("gradient", "sides"):
        out["sync_mode"] = raw.get("sync_mode")
    try:
        out["fps"] = max(5, min(30, int(raw.get("fps", 20))))
    except (TypeError, ValueError):
        pass
    return out


def save_ambient(payload):
    if not isinstance(payload, dict):
        raise ValueError("configuration ambient invalide")
    with _lock:
        state = load()
        state["ambient"] = ambient_from(payload)
        _save(state)
        return state["ambient"]


def ambient_from(raw):
    out = dict(_AMBIENT_DEFAULTS)
    if not isinstance(raw, dict):
        return out
    out["enabled"] = bool(raw.get("enabled"))
    try:
        out["led_count"] = max(0, min(512, int(raw.get("led_count", 0))))
    except (TypeError, ValueError):
        pass
    try:
        out["split"] = max(0.05, min(0.95, float(raw.get("split", 0.5))))
    except (TypeError, ValueError):
        pass
    out["swap"] = bool(raw.get("swap"))
    try:
        out["brightness"] = max(0.05, min(1.0, float(raw.get("brightness", 1.0))))
    except (TypeError, ValueError):
        pass
    out["turn_color"] = _hex_color(raw.get("turn_color"), out["turn_color"])
    out["idle_color"] = _hex_color(raw.get("idle_color"), out["idle_color"])
    for key in ("rpm", "flags", "brake", "turns", "sync"):
        if key in raw:
            out[key] = bool(raw.get(key))
    if raw.get("sync_mode") in ("gradient", "sides"):
        out["sync_mode"] = raw.get("sync_mode")
    try:
        out["fps"] = max(5, min(30, int(raw.get("fps", 20))))
    except (TypeError, ValueError):
        pass
    return out


def open_on_start():
    return bool(load().get("open_on_start", True))


def save_open_on_start(enabled):
    with _lock:
        state = load()
        state["open_on_start"] = bool(enabled)
        _save(state)
        return state["open_on_start"]


def save_last_dashboard(spec):
    spec = (spec or "").strip().strip("/")
    if spec and not _SAFE_DASH.match(spec):
        return last_dashboard()
    with _lock:
        state = load()
        state["last_dashboard"] = spec
        _save(state)
        return spec


def save_default_dashboard(spec):
    spec = (spec or "").strip().strip("/")
    if spec and not _SAFE_DASH.match(spec):
        raise ValueError("compteur invalide")
    with _lock:
        state = load()
        state["default_dashboard"] = spec
        _save(state)
        return default_dashboard()
