"""Installation du plugin SCS SDK dans ETS2/ATS (Windows)."""
import io
import logging
import os
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from core import game

log = logging.getLogger("idash.scsplugin")
DOWNLOAD_URL = ("https://github.com/RenCloud/scs-sdk-plugin/releases/"
                "download/V.1.12.1/release_v_1_12_1.zip")
PLUGIN_NAME = "scs-telemetry.dll"
SOURCE_PATH = "Win64/scs-telemetry.dll"


def _game_exe(key="ets2"):
    state = game.load_game(key)
    exe = state.get("exe") or ""
    if exe and Path(exe).is_file():
        return Path(exe)
    found = game.detect_game(key)
    return Path(found) if found else None


def _plugins_dir(key="ets2"):
    exe = _game_exe(key)
    return (exe.parent / "plugins") if exe else None


def status(key="ets2"):
    exe = _game_exe(key)
    plugins = _plugins_dir(key)
    installed = bool(plugins and (plugins / PLUGIN_NAME).is_file())
    return {
        "ok": installed,
        "available": os.name == "nt",
        "game": key,
        "installed": installed,
        "game_exe": str(exe) if exe else "",
        "plugins_dir": str(plugins) if plugins else "",
        "download_url": DOWNLOAD_URL,
    }


def install(key="ets2"):
    if os.name != "nt":
        raise ValueError("installation du plugin disponible sous Windows")
    plugins = _plugins_dir(key)
    if plugins is None:
        raise ValueError("chemin ETS2 introuvable dans /settings → Jeux")
    if (plugins / PLUGIN_NAME).is_file():
        return status(key)
    plugins.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(DOWNLOAD_URL, headers={
        "User-Agent": "idash/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        data = archive.read(SOURCE_PATH)
    target = plugins / PLUGIN_NAME
    tmp = target.with_suffix(".dll.tmp")
    tmp.write_bytes(data)
    tmp.replace(target)
    log.info("plugin SCS installe: %s", target)
    return status(key)
