"""Mise a jour par ZIP de release GitHub, sans git.

Le ZIP est depose par l'utilisateur (telecharge depuis la page Releases), puis
extrait dans ``.update/``. Un petit script separe attend l'arret du serveur,
copie le code (en conservant les donnees utilisateur) et relance l'application.
"""
import base64
import io
import os
import shutil
import stat
import subprocess
import sys
import threading
import time
import zipfile
from pathlib import Path, PurePosixPath

from core.config import ROOT, VERSION

UPDATE_DIR = ROOT / ".update"
RELEASES_URL = "https://github.com/redasnkrs/idashboard/releases"
MAX_ZIP = 16 * 1024 * 1024
MAX_UNZIP = 80 * 1024 * 1024


def info():
    return {"version": VERSION, "releases_url": RELEASES_URL}


def _decode(data):
    if not isinstance(data, str):
        raise ValueError("fichier manquant")
    if data.startswith("data:"):
        if "," not in data:
            raise ValueError("fichier invalide")
        data = data.split(",", 1)[1]
    try:
        raw = base64.b64decode(data, validate=True)
    except (ValueError, TypeError):
        raise ValueError("base64 invalide")
    if not raw:
        raise ValueError("fichier vide")
    if len(raw) > MAX_ZIP:
        raise ValueError("ZIP trop grand")
    return raw


def _clean_staging():
    if not UPDATE_DIR.is_dir():
        return
    for path in UPDATE_DIR.glob("staging-*"):
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)


def _normalize_root(staging):
    if (staging / "main.py").is_file():
        return staging
    candidates = [p for p in staging.iterdir()
                  if p.is_dir() and (p / "main.py").is_file()]
    if len(candidates) != 1:
        raise ValueError("ZIP invalide : main.py introuvable")
    return candidates[0]


def prepare_zip(data, name="update.zip"):
    raw = _decode(data)
    UPDATE_DIR.mkdir(parents=True, exist_ok=True)
    _clean_staging()
    staging = UPDATE_DIR / ("staging-%d" % int(time.time() * 1000))
    staging.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            total = 0
            for entry in archive.infolist():
                filename = entry.filename.replace("\\", "/")
                if not filename or filename.endswith("/"):
                    continue
                parts = PurePosixPath(filename).parts
                if filename.startswith("/") or ".." in parts:
                    raise ValueError("chemin interdit dans le ZIP")
                if ":" in parts[0]:
                    raise ValueError("chemin absolu interdit dans le ZIP")
                if stat.S_ISLNK(entry.external_attr >> 16):
                    raise ValueError("lien symbolique interdit")
                total += entry.file_size
                if total > MAX_UNZIP:
                    raise ValueError("ZIP decompresse trop grand")
            archive.extractall(staging)
        root = _normalize_root(staging)
        for required in ("core", "studio", "dashboards"):
            if not (root / required).is_dir():
                raise ValueError("ZIP de release incomplet (%s)" % required)
        version = "dev"
        try:
            version = (root / "VERSION").read_text(
                encoding="utf-8").strip() or "dev"
        except OSError:
            pass
        return {"staging": str(root), "version": version, "name": name}
    except (zipfile.BadZipFile, OSError):
        shutil.rmtree(staging, ignore_errors=True)
        raise ValueError("ZIP illisible")


def spawn_apply(staging):
    source = ROOT / "tools" / "apply_update.py"
    if not source.is_file():
        raise OSError("tools/apply_update.py manquant")
    UPDATE_DIR.mkdir(parents=True, exist_ok=True)
    target = UPDATE_DIR / "apply_update.py"
    shutil.copy2(source, target)
    log_path = UPDATE_DIR / "apply.log"
    log = open(log_path, "a", encoding="utf-8")
    log.write("\n--- update %s ---\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
    log.flush()
    cmd = [sys.executable, str(target), "--staging", staging,
           "--root", str(ROOT), "--pid", str(os.getpid())]
    kwargs = {
        "cwd": str(ROOT), "stdin": subprocess.DEVNULL,
        "stdout": log, "stderr": subprocess.STDOUT,
    }
    if sys.platform == "win32":
        flags = getattr(subprocess, "DETACHED_PROCESS", 0)
        flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        kwargs["creationflags"] = flags
    else:
        kwargs["start_new_session"] = True
    try:
        subprocess.Popen(cmd, **kwargs)
    finally:
        log.close()
    return str(log_path)


def schedule_exit(delay=2.0):
    threading.Timer(delay, lambda: os._exit(0)).start()
