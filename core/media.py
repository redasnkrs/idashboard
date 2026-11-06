"""Now Playing Windows (SMTC) pour le panneau media.

Un poller lance ``media_smtc.ps1`` (PowerShell/WinRT), qui lit la session
media Windows : Cider en priorite, sinon la session courante. L'etat est
partage avec le serveur ; la pochette est mise en cache et servie a part.
"""
import base64
import atexit
import json
import subprocess
import sys
import threading
from pathlib import Path

from core.config import RESOURCE_DIR

SCRIPT = RESOURCE_DIR / "core" / "media_smtc.ps1"
_IS_WIN = sys.platform == "win32"
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_ACTIONS = {"playpause", "next", "prev"}

_lock = threading.Lock()
_started = False
_stop = threading.Event()
_proc = None
_art = None
_art_type = "image/jpeg"
_key = ""
_rev = 0

_state = {
    "ok": False,
    "platform": sys.platform,
    "reason": "starting" if _IS_WIN else "windows",
    "has_art": False,
    "art_rev": 0,
}


def _apply(data):
    global _state, _art, _art_type, _key, _rev
    with _lock:
        ok = bool(data.get("ok"))
        key = str(data.get("key") or "")
        if key != _key:
            _key = key
            if _art is not None or key:
                _art = None
                _rev += 1
        art = data.get("art")
        if isinstance(art, str) and art:
            try:
                raw = base64.b64decode(art)
            except (ValueError, TypeError):
                raw = None
            if raw:
                _art = raw
                _art_type = ("image/png" if raw.startswith(b"\x89PNG")
                             else "image/jpeg")
                _rev += 1
        if not ok and (_art is not None or _key):
            _art = None
            _key = ""
            _rev += 1
        _state = {
            "ok": ok,
            "platform": sys.platform,
            "source": str(data.get("source") or ""),
            "title": str(data.get("title") or ""),
            "artist": str(data.get("artist") or ""),
            "album": str(data.get("album") or ""),
            "playing": bool(data.get("playing")),
            "status": str(data.get("status") or ""),
            "position": float(data.get("position") or 0),
            "duration": float(data.get("duration") or 0),
            "has_art": _art is not None,
            "art_rev": _rev,
        }


def _cmd(action):
    return [
        "powershell.exe", "-NoProfile", "-NonInteractive",
        "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT),
        "-Action", action,
    ]


def _poller():
    global _proc
    while not _stop.is_set():
        try:
            _proc = subprocess.Popen(
                _cmd("loop"), stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
                creationflags=_NO_WINDOW)
            for line in _proc.stdout:
                if _stop.is_set():
                    break
                line = line.strip().lstrip("\ufeff")
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except (ValueError, TypeError):
                    continue
                if isinstance(data, dict):
                    _apply(data)
            try:
                _proc.terminate()
            except OSError:
                pass
            _proc = None
        except OSError:
            pass
        if _stop.wait(2):
            break


def start():
    global _started
    if not _IS_WIN or _started:
        return
    with _lock:
        if _started:
            return
        _started = True
    atexit.register(stop)
    threading.Thread(target=_poller, name="media-smtc",
                     daemon=True).start()


def stop():
    global _proc
    _stop.set()
    with _lock:
        proc = _proc
    if proc is not None and proc.poll() is None:
        try:
            proc.terminate()
        except OSError:
            pass


def snapshot():
    with _lock:
        return dict(_state)


def art():
    with _lock:
        return _art, _art_type


def control(action):
    if action not in _ACTIONS:
        return {"ok": False, "error": "action inconnue"}
    if not _IS_WIN:
        return {"ok": False, "error": "Windows uniquement"}
    try:
        proc = subprocess.run(
            _cmd(action), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=15,
            creationflags=_NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)}
    for line in reversed((proc.stdout or "").splitlines()):
        line = line.strip().lstrip("\ufeff")
        if not line:
            continue
        try:
            data = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(data, dict):
            return data
    return {"ok": False, "error": "reponse invalide"}
