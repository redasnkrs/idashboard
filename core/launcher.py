"""Ouverture du tableau de bord dans la fenetre Chrome du mini ecran.

Sous Windows, utilise Chrome (ou Edge en secours) en mode ``--app`` avec un
profil dedie et la position du 7" (voir ``config.SCREEN``). Ailleurs, ouvre
Chrome si present, sinon le navigateur par defaut.

Ce module ne fait rien d'autre : il ne touche pas au jeu et n'ecrit que dans
le profil Chrome du projet (ignore par git).
"""
import os
import shutil
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

from core.config import PORT, ROOT, SCREEN

PROFILE_DIR = ROOT / ".profile-7"

_lock = threading.Lock()
_process = None
_last_spec = None


def _first_existing(paths):
    for path in paths:
        if path and Path(path).is_file():
            return str(path)
    return None


def _chrome():
    """Chemin d'un navigateur Chromium, ou None."""
    if sys.platform == "win32":
        roots = [os.environ.get("ProgramFiles"),
                 os.environ.get("ProgramFiles(x86)"),
                 os.environ.get("LocalAppData")]
        rels = ("Google/Chrome/Application/chrome.exe",
                "Chromium/Application/chrome.exe",
                "Microsoft/Edge/Application/msedge.exe")
        found = _first_existing(
            str(Path(root) / rel) for root in roots if root for rel in rels)
        if found:
            return found
        for name in ("chrome", "chrome.exe", "msedge", "msedge.exe"):
            path = shutil.which(name)
            if path:
                return path
        return None
    if sys.platform == "darwin":
        return _first_existing([
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ])
    for name in ("google-chrome", "chromium", "chromium-browser",
                 "microsoft-edge"):
        path = shutil.which(name)
        if path:
            return path
    return None


def dashboard_url(spec):
    return "http://127.0.0.1:%d/dashboard/%s" % (PORT, spec)


def _command(url):
    browser = _chrome()
    if browser is None:
        return None
    args = [
        browser,
        "--app=%s" % url,
        "--user-data-dir=%s" % PROFILE_DIR,
        "--new-window", "--no-first-run", "--no-default-browser-check",
    ]
    # Les coordonnees par defaut sont celles du PC de jeu (Windows). Ailleurs,
    # on ne les applique que si l'utilisateur les a fournies explicitement.
    place = sys.platform == "win32" or "IDASH_SCREEN_X" in os.environ
    if place:
        args.insert(3, "--window-position=%d,%d" % (SCREEN["x"], SCREEN["y"]))
        args.insert(4, "--window-size=%d,%d" % (SCREEN["width"],
                                                SCREEN["height"]))
    return args


def is_running():
    with _lock:
        return _process is not None and _process.poll() is None


def close():
    global _process, _last_spec
    with _lock:
        if _process is not None and _process.poll() is None:
            try:
                _process.terminate()
            except OSError:
                pass
        _process = None
        _last_spec = None


def open_dashboard(spec):
    """Ouvre ``spec`` sur le mini ecran. Retourne un petit rapport."""
    global _process, _last_spec
    url = dashboard_url(spec)
    with _lock:
        if _process is not None and _process.poll() is None:
            if _last_spec == spec:
                return {"ok": True, "url": url, "method": "already-open"}
            try:
                _process.terminate()
                _process.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                pass
            _process = None
        cmd = _command(url)
        if cmd is None:
            opened = webbrowser.open(url)
            _last_spec = spec
            return {"ok": bool(opened), "url": url,
                    "method": "default-browser"}
        try:
            _process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True)
        except OSError as exc:
            return {"ok": False, "url": url, "method": "error",
                    "error": str(exc)}
        _last_spec = spec
        return {"ok": True, "url": url, "method": "chrome-app"}
