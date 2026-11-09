"""Capture de la zone GPS du jeu (Windows) pour l'afficher dans idash."""
import io
import logging
import sys
import threading
import time

from core import app_settings

log = logging.getLogger("idash.gps")
_lock = threading.Lock()
_frame = None
_frame_at = 0.0
_error = ""
_thread = None
_stop = threading.Event()
_available = sys.platform == "win32"

try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None


def _loop():
    global _frame, _frame_at, _error
    while not _stop.wait(0.08):
        cfg = app_settings.gps()
        if not cfg["enabled"] or ImageGrab is None:
            with _lock:
                _frame = None
                _frame_at = 0.0
            continue
        try:
            img = ImageGrab.grab(
                bbox=(cfg["x"], cfg["y"],
                      cfg["x"] + cfg["width"],
                      cfg["y"] + cfg["height"]),
                all_screens=True)
            if img.mode != "RGB":
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=82, optimize=True)
            with _lock:
                _frame = buf.getvalue()
                _frame_at = time.monotonic()
                _error = ""
        except Exception as exc:
            with _lock:
                _frame = None
                _frame_at = 0.0
                _error = str(exc)
            log.warning("capture GPS: %s", exc)


def start():
    global _thread
    if not _available or ImageGrab is None:
        return False
    if _thread is not None and _thread.is_alive():
        return True
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="idash-gps", daemon=True)
    _thread.start()
    return True


def stop():
    _stop.set()


def status():
    cfg = app_settings.gps()
    with _lock:
        age = int((time.monotonic() - _frame_at) * 1000) if _frame_at else None
        return {
            "available": _available and ImageGrab is not None,
            "enabled": bool(cfg.get("enabled")),
            "region": {k: cfg[k] for k in ("x", "y", "width", "height")},
            "ok": _frame is not None,
            "age_ms": age,
            "error": _error,
        }


def full():
    if not _available or ImageGrab is None:
        return None
    try:
        img = ImageGrab.grab(all_screens=True)
        if img.mode != "RGB":
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=78, optimize=True)
        return buf.getvalue()
    except Exception as exc:
        log.warning("capture ecran: %s", exc)
        return None


def frame():
    with _lock:
        if _frame is None:
            return None
        if time.monotonic() - _frame_at > 3.0:
            return None
        return _frame
