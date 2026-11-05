"""Lancement d'Assetto Corsa Evo et chemin du jeu.

Le chemin est stocke dans ``game.json`` (ignore par git). Si aucun chemin
n'est configure, on tente de detecter l'installation Steam, puis on passe par
le protocole ``steam://rungameid/<appid>``.
"""
import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

from core.config import ROOT

GAME_FILE = ROOT / "game.json"
DEFAULT_APP_ID = "3058630"
EXE_NAME = "AssettoCorsaEVO.exe"
INSTALL_DIR = "Assetto Corsa EVO"

_lock = threading.Lock()


def load():
    state = {"exe": "", "app_id": DEFAULT_APP_ID}
    try:
        saved = json.loads(GAME_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return state
    if not isinstance(saved, dict):
        return state
    exe = saved.get("exe")
    if isinstance(exe, str):
        state["exe"] = exe.strip()
    app_id = saved.get("app_id")
    if isinstance(app_id, str) and app_id.isdigit():
        state["app_id"] = app_id
    return state


def _clean_exe(value):
    if not isinstance(value, str):
        raise ValueError("chemin invalide")
    exe = os.path.expandvars(os.path.expanduser(value.strip().strip('"')))
    if len(exe) > 1024:
        raise ValueError("chemin trop long")
    if any(c in exe for c in ("\x00", "\n", "\r")):
        raise ValueError("chemin invalide")
    return exe


def save(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload invalide")
    with _lock:
        state = load()
        if "exe" in payload:
            state["exe"] = _clean_exe(payload["exe"])
        if "app_id" in payload:
            app_id = payload["app_id"]
            if not isinstance(app_id, str) or not app_id.isdigit():
                raise ValueError("app id invalide")
            state["app_id"] = app_id
        tmp = GAME_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False),
                       encoding="utf-8")
        tmp.replace(GAME_FILE)
        return state


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


def detect():
    """Chemin de l'exe si Steam et le jeu sont installes, sinon vide."""
    if sys.platform != "win32":
        return ""
    seen = set()
    for root in _steam_roots():
        for lib in _steam_libraries(root):
            key = os.path.normcase(lib)
            if key in seen:
                continue
            seen.add(key)
            candidate = (Path(lib) / "steamapps" / "common" / INSTALL_DIR
                         / EXE_NAME)
            if candidate.is_file():
                return str(candidate)
    return ""


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


def launch():
    state = load()
    exe = state["exe"]
    if exe and os.path.isfile(exe):
        try:
            _spawn(exe)
            return {"ok": True, "method": "exe", "path": exe}
        except OSError as exc:
            return {"ok": False, "error": str(exc)}
    if not exe:
        found = detect()
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


def status():
    state = load()
    exe = state["exe"]
    exists = bool(exe and os.path.isfile(exe))
    return {
        "platform": sys.platform,
        "app_id": state["app_id"],
        "exe": exe,
        "exe_exists": exists,
        "detected": detect() if not exists else "",
        "steam": sys.platform == "win32",
    }
