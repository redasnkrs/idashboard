"""Lancement des jeux (AC Evo, AC 2014, AMS2) et chemins configurables.

Les chemins sont dans ``app.json`` (via ``core.app_settings``). La detection
Steam est commune aux trois jeux ; en dernier recours on ouvre le protocole
``steam://rungameid/<appid>``.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from core import app_settings

GAMES = {
    "acevo": {
        "name": "Assetto Corsa Evo", "app_id": "3058630",
        "install": "Assetto Corsa EVO", "exe": "AssettoCorsaEVO.exe",
    },
    "ac": {
        "name": "Assetto Corsa", "app_id": "244210",
        "install": "assettocorsa", "exe": "acs.exe",
    },
    "ams2": {
        "name": "Automobilista 2", "app_id": "1066890",
        "install": "Automobilista 2", "exe": "AMS2.exe",
    },
    "ets2": {
        "name": "Euro Truck Simulator 2", "app_id": "227300",
        "install": "Euro Truck Simulator 2", "exe": "eurotrucks2.exe",
    },
}
DEFAULT_GAME = "acevo"
DEFAULT_APP_ID = GAMES[DEFAULT_GAME]["app_id"]
GAME_FILE = app_settings.LEGACY_GAME_FILE  # compatibilite


def _meta(key):
    return GAMES.get(key) or GAMES[DEFAULT_GAME]


def load_game(key):
    meta = _meta(key)
    saved = app_settings.game(key)
    return {
        "key": key,
        "name": meta["name"],
        "app_id": str(saved.get("app_id") or meta["app_id"]),
        "exe": str(saved.get("exe") or ""),
        "install": meta["install"],
        "exe_name": meta["exe"],
    }


def load():
    return load_game(DEFAULT_GAME)


def save_game(key, payload):
    if key not in GAMES:
        raise ValueError("jeu inconnu")
    app_settings.save_game(key, payload)
    return load_game(key)


def save(payload):
    return save_game(DEFAULT_GAME, payload)


def _steam_roots():
    roots = []
    if sys.platform != "win32":
        return roots
    try:
        import winreg
        locations = [
            (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
        ]
        for hive, sub, name in locations:
            try:
                with winreg.OpenKey(hive, sub) as key:
                    roots.append(winreg.QueryValueEx(key, name)[0])
            except OSError:
                pass
    except ImportError:
        pass
    for env in ("ProgramFiles(x86)", "ProgramFiles"):
        base = os.environ.get(env)
        if base:
            roots.append(os.path.join(base, "Steam"))
    return roots


def _steam_libraries(root):
    libs = [root]
    vdf = Path(root) / "steamapps" / "libraryfolders.vdf"
    try:
        text = vdf.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return libs
    for match in re.finditer(r'"path"\s+"([^"]+)"', text):
        libs.append(match.group(1).replace("\\\\", "\\"))
    return libs


def detect_game(key):
    if key not in GAMES or sys.platform != "win32":
        return ""
    meta = GAMES[key]
    seen = set()
    for root in _steam_roots():
        for lib in _steam_libraries(root):
            norm = os.path.normcase(lib)
            if norm in seen:
                continue
            seen.add(norm)
            candidate = (Path(lib) / "steamapps" / "common" /
                         meta["install"] / meta["exe"])
            if candidate.is_file():
                return str(candidate)
    return ""


def detect():
    return detect_game(DEFAULT_GAME)


def _spawn(exe):
    kwargs = {
        "cwd": os.path.dirname(exe) or None,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        flags = getattr(subprocess, "DETACHED_PROCESS", 0)
        flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        kwargs["creationflags"] = flags
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen([exe], **kwargs)


def launch_game(key):
    if key not in GAMES:
        return {"ok": False, "error": "jeu inconnu"}
    state = load_game(key)
    exe = state["exe"]
    if exe and os.path.isfile(exe):
        try:
            _spawn(exe)
            return {"ok": True, "method": "exe", "path": exe}
        except OSError as exc:
            return {"ok": False, "error": str(exc)}
    if not exe:
        found = detect_game(key)
        if found:
            try:
                _spawn(found)
                return {"ok": True, "method": "detected", "path": found}
            except OSError:
                pass
    if sys.platform == "win32":
        try:
            os.startfile("steam://rungameid/%s" % state["app_id"])
            return {"ok": True, "method": "steam",
                    "app_id": state["app_id"]}
        except OSError as exc:
            return {"ok": False, "error": "Steam introuvable: %s" % exc}
    return {"ok": False,
            "error": "Renseigne le chemin du jeu dans les reglages."}


def launch():
    return launch_game(DEFAULT_GAME)


def status_game(key):
    state = load_game(key)
    exe = state["exe"]
    exists = bool(exe and os.path.isfile(exe))
    return {
        "key": key,
        "name": state["name"],
        "platform": sys.platform,
        "app_id": state["app_id"],
        "exe": exe,
        "exe_exists": exists,
        "detected": detect_game(key) if not exists else "",
        "steam": sys.platform == "win32",
    }


def status():
    return status_game(DEFAULT_GAME)


def status_all():
    return [status_game(key) for key in GAMES]
