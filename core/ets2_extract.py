"""Generation d'une carte ETS2/ProMods complete avec ts-map.

Le binaire ts-map lit base.scs, les DLC et le mod ProMods, puis dessine les
routes, prefabs, villes, icones et overlays dans un pack de tuiles compatible
avec core.ets2_map.
"""
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from pathlib import Path

from core import app_settings, ets2_map
from core.config import RESOURCE_DIR

log = logging.getLogger("idash.ets2extract")
EXE = RESOURCE_DIR / "assets" / "tsmap" / "TsMap.Cli.exe"
TARGET = ets2_map.MAP_DIR / "tsmap-promods.zip"
_lock = threading.Lock()
_state = {"running": False, "progress": 0.0, "error": "", "message": "",
          "done": False, "started": 0.0, "max_zoom": 7}


def _game_candidates():
    exe = app_settings.game("ets2").get("exe")
    if exe:
        yield Path(exe).parent
    yield Path(r"D:\SteamLibrary\steamapps\common\Euro Truck Simulator 2")
    yield Path(r"C:\Program Files (x86)\Steam\steamapps\common\Euro Truck Simulator 2")
    yield Path(r"C:\Program Files\Steam\steamapps\common\Euro Truck Simulator 2")


def find_game_dir():
    for path in _game_candidates():
        if (path / "base.scs").is_file():
            return path
    return None


def _mod_dirs(game_dir):
    yield Path.home() / "Documents" / "Euro Truck Simulator 2" / "mod"
    yield Path.home() / "OneDrive" / "Documents" / "Euro Truck Simulator 2" / "mod"
    if game_dir:
        yield game_dir / "mod"
        yield game_dir


def find_mods(game_dir=None):
    found = []
    seen = set()
    for directory in _mod_dirs(game_dir):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.scs")):
            name = path.name.lower()
            if name.startswith(("base", "dlc_", "def")):
                continue
            key = str(path).lower()
            if key in seen:
                continue
            seen.add(key)
            found.append(path)
    promods = [p for p in found if "promods" in p.name.lower()]
    return promods or found


def status():
    game = find_game_dir()
    mods = find_mods(game)
    return {
        "available": sys.platform == "win32" and EXE.is_file(),
        "exe": str(EXE),
        "game_dir": str(game) if game else "",
        "mods": [str(p) for p in mods],
        "output": str(TARGET),
        "target_exists": TARGET.is_file(),
        "running": _state["running"],
        "progress": _state["progress"],
        "message": _state["message"],
        "error": _state["error"],
        "done": _state["done"],
        "started": _state["started"],
        "max_zoom": _state["max_zoom"],
    }


def _zip_tree(source, target):
    tmp = target.with_suffix(".tmp")
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED) as archive:
            for path in source.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(source).as_posix())
        tmp.replace(target)
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


def _worker(game_dir, mod_path, max_zoom):
    temp = Path(tempfile.mkdtemp(prefix="idash-tsmap-", dir=str(ets2_map.MAP_DIR)))
    try:
        _state.update({"running": True, "progress": 0.0, "error": "",
                       "message": "Lecture des fichiers du jeu…",
                       "done": False, "started": time.time(),
                       "max_zoom": max_zoom})
        cmd = [str(EXE), "--game", str(game_dir), "--mod", str(mod_path),
               "--out", str(temp), "--min", "0", "--max", str(max_zoom),
               "--tile", "512"]
        log.info("ts-map: %s", " ".join(cmd))
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        proc = subprocess.Popen(
            cmd, cwd=str(EXE.parent), stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            errors="replace", creationflags=flags)
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            log.info("ts-map: %s", line)
            if line.startswith("Progress "):
                _state["message"] = "Génération des tuiles…"
                try:
                    parts = line.split()
                    done, total = int(parts[1]), int(parts[2])
                    _state["progress"] = min(0.99, done / max(1, total))
                except (ValueError, IndexError):
                    pass
            else:
                _state["message"] = line[-180:]
                if line.startswith("Zoom ") and "termin" in line:
                    try:
                        zoom = int(line.split()[1])
                        _state["progress"] = min(0.99, (zoom + 1) / (max_zoom + 1))
                    except (ValueError, IndexError):
                        pass
        code = proc.wait()
        if code != 0:
            raise RuntimeError("ts-map a échoué (code %s)" % code)
        if not (temp / "TileMapInfo.json").is_file() or not (temp / "Tiles").is_dir():
            raise RuntimeError("ts-map n'a produit aucune tuile")
        _state.update({"message": "Compression de la carte…", "progress": 0.99})
        _zip_tree(temp, TARGET)
        ets2_map.reset()
        _state.update({"running": False, "progress": 1.0, "done": True,
                       "message": "Carte ProMods prête"})
        log.info("carte ProMods generee: %s", TARGET)
    except Exception as exc:
        _state.update({"running": False, "error": str(exc),
                       "message": "Échec de la génération"})
        log.warning("generation carte ProMods: %s", exc)
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def start(game_dir=None, mod_path=None, max_zoom=7):
    if _state["running"]:
        raise ValueError("génération déjà en cours")
    game = Path(game_dir) if game_dir else find_game_dir()
    if game is None or not (game / "base.scs").is_file():
        raise ValueError("dossier ETS2 invalide (base.scs introuvable)")
    if not EXE.is_file() or sys.platform != "win32":
        raise ValueError("générateur ts-map indisponible sur cette plateforme")
    mods = find_mods(game)
    mod = Path(mod_path) if mod_path else (mods[0] if mods else None)
    if mod is None or not mod.is_file():
        raise ValueError("fichier ProMods .scs introuvable")
    try:
        max_zoom = max(0, min(8, int(max_zoom)))
    except (TypeError, ValueError):
        max_zoom = 8
    ets2_map.MAP_DIR.mkdir(parents=True, exist_ok=True)
    threading.Thread(target=_worker, args=(game, mod, max_zoom),
                     name="ets2-tsmap", daemon=True).start()
    return status()
