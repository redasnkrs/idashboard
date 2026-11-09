"""Carte ETS2 locale : tuiles ts-map, sans SimHub en execution."""
import gzip
import json
import logging
import os
import shutil
import tempfile
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

from core.config import RESOURCE_DIR, ROOT

log = logging.getLogger("idash.ets2map")
MAP_DIR = ROOT / "custom" / "maps"
ZIP_NAME = "tsmap-ets2.zip"
PROMODS_NAME = "tsmap-promods.zip"
VECTOR_NAME = "ets2-vector.json.gz"
DOWNLOAD_URL = "https://www.simhubdash.com/TruckMaps/tsmap-ets2.zip"
_lock = threading.Lock()
_zip = None
_zip_path = ""
_info = None
_tile_size = None
_vector_info = None
_vector_path = ""
_download = {"running": False, "progress": 0.0, "error": "",
             "done": False, "started": 0.0}


def _candidates():
    yield MAP_DIR / PROMODS_NAME
    yield MAP_DIR / ZIP_NAME
    if os.environ.get("IDASH_ETS2_MAP"):
        yield Path(os.environ["IDASH_ETS2_MAP"])


def _simhub_candidates():
    if os.name == "nt":
        for env in ("ProgramFiles(x86)", "ProgramFiles"):
            base = os.environ.get(env)
            if base:
                yield Path(base) / "SimHub" / "TruckMaps" / ZIP_NAME


def find_zip():
    for path in _candidates():
        if path.is_file() and path.stat().st_size > 0:
            return path
    return None


def find_vector():
    candidates = [RESOURCE_DIR / "assets" / "maps" / VECTOR_NAME,
                  ROOT / "assets" / "maps" / VECTOR_NAME,
                  MAP_DIR / VECTOR_NAME]
    if os.environ.get("IDASH_ETS2_VECTOR"):
        candidates.append(Path(os.environ["IDASH_ETS2_VECTOR"]))
    for path in candidates:
        if path.is_file() and path.stat().st_size > 0:
            return path
    return None


def vector_info():
    global _vector_info, _vector_path
    path = find_vector()
    if path is None:
        return None
    key = str(path)
    if _vector_info is not None and _vector_path == key:
        return _vector_info
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            data = json.load(handle)
        _vector_info = {
            "name": path.name,
            "bounds": data.get("bounds"),
            "roads": len(data.get("roads") or []),
            "prefabs": len(data.get("prefabs") or []),
            "cities": len(data.get("cities") or []),
        }
        _vector_path = key
    except (OSError, ValueError) as exc:
        log.warning("carte vectorielle ETS2 illisible: %s", exc)
        _vector_info = None
        _vector_path = ""
    return _vector_info


def vector_bytes():
    path = find_vector()
    if path is None:
        return None
    try:
        return path.read_bytes()
    except OSError:
        return None


def reset():
    global _zip, _zip_path, _info, _tile_size, _vector_info, _vector_path
    with _lock:
        try:
            if _zip is not None:
                _zip.close()
        except OSError:
            pass
        _zip = None
        _zip_path = ""
        _info = None
        _tile_size = None
        _vector_info = None
        _vector_path = ""


def _open_zip():
    global _zip, _zip_path
    path = find_zip()
    if path is None:
        return None
    key = str(path)
    with _lock:
        if _zip is not None and _zip_path == key:
            return _zip
        try:
            if _zip is not None:
                _zip.close()
        except OSError:
            pass
        try:
            _zip = zipfile.ZipFile(path)
        except (OSError, zipfile.BadZipFile) as exc:
            log.warning("carte ETS2 illisible: %s", exc)
            _zip = None
            return None
        _zip_path = key
        return _zip


def _root_prefix(archive):
    names = archive.namelist()
    for name in names[:1000]:
        if name.startswith("Tiles/"):
            return ""
        marker = "/Tiles/"
        if marker in name:
            return name.split(marker, 1)[0] + "/"
    return ""


def _png_size(data):
    if not data or len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return 256
    try:
        return max(64, int.from_bytes(data[16:20], "big"))
    except ValueError:
        return 256


def info():
    global _info, _tile_size
    archive = _open_zip()
    path = find_zip()
    vector = vector_info()
    status = {"ok": archive is not None or vector is not None,
              "path": str(path) if path else "",
              "name": path.name if path else "",
              "promods": bool(path and path.name == PROMODS_NAME),
              "tile_size": _tile_size or 256,
              "downloading": _download["running"],
              "progress": _download["progress"],
              "error": _download["error"]}
    if vector:
        status["vector"] = vector
    if archive is None:
        return status
    if _info is None or _tile_size is None:
        try:
            with _lock:
                prefix = _root_prefix(archive)
                raw = archive.read(prefix + "TileMapInfo.json")
                try:
                    _tile_size = _png_size(archive.read(
                        prefix + "Tiles/0/0/0.png"))
                except (OSError, KeyError, ValueError):
                    _tile_size = 256
            _info = json.loads(raw.decode("utf-8-sig"))
        except (OSError, KeyError, ValueError):
            _info = None
    if _info:
        status["tile"] = _info
        status["tile_size"] = _tile_size or 256
        status["min_zoom"] = _info.get("minZoom", 0)
        status["max_zoom"] = _info.get("maxZoom", 8)
    return status


def tile(z, x, y):
    archive = _open_zip()
    if archive is None:
        return None
    try:
        with _lock:
            prefix = _root_prefix(archive)
            return archive.read("%sTiles/%d/%d/%d.png" % (prefix, z, x, y))
    except (KeyError, OSError, ValueError):
        return None


def _download_worker():
    global _info
    MAP_DIR.mkdir(parents=True, exist_ok=True)
    target = MAP_DIR / ZIP_NAME
    tmp = None
    try:
        _download.update({"running": True, "progress": 0.0, "error": "",
                          "done": False, "started": time.time()})
        req = urllib.request.Request(DOWNLOAD_URL, headers={
            "User-Agent": "idash/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            fd, name = tempfile.mkstemp(prefix="ets2-map-", suffix=".zip",
                                        dir=str(MAP_DIR))
            tmp = Path(name)
            done = 0
            with os.fdopen(fd, "wb") as out:
                while True:
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    out.write(chunk)
                    done += len(chunk)
                    if total:
                        _download["progress"] = min(1.0, done / total)
                    else:
                        _download["progress"] = min(0.99, done / (90 * 1024 * 1024))
            tmp.replace(target)
        with _lock:
            global _zip, _zip_path, _info, _tile_size
            try:
                if _zip is not None:
                    _zip.close()
            except OSError:
                pass
            _zip = None
            _zip_path = ""
            _info = None
            _tile_size = None
        _download.update({"running": False, "progress": 1.0, "done": True})
        log.info("carte ETS2 installee: %s", target)
    except Exception as exc:
        _download.update({"running": False, "error": str(exc)})
        log.warning("telechargement carte ETS2: %s", exc)
        if tmp is not None:
            try:
                tmp.unlink()
            except OSError:
                pass


def start_download():
    if _download["running"]:
        return False
    if find_zip() is not None:
        _download.update({"running": False, "progress": 1.0, "done": True})
        return False
    threading.Thread(target=_download_worker, name="ets2-map-download",
                     daemon=True).start()
    return True


def import_from_simhub():
    """Copie la carte de SimHub vers custom/maps si elle existe."""
    target = MAP_DIR / ZIP_NAME
    if target.is_file():
        return str(target)
    for path in _simhub_candidates():
        if path == target or not path.is_file():
            continue
        MAP_DIR.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(path, target)
            global _zip, _zip_path, _info, _tile_size
            with _lock:
                if _zip is not None:
                    _zip.close()
                _zip = None
                _zip_path = ""
                _info = None
                _tile_size = None
            return str(target)
        except OSError as exc:
            return str(exc)
    return ""
