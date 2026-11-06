"""Watchdog leger : relance Chrome si l'ecran du 7" a ete ferme."""
import logging
import threading
import time

from core import app_settings, launcher

log = logging.getLogger("idash.watchdog")
_thread = None
_stop = threading.Event()
_state = {"relaunches": 0, "last_error": "", "last_at": 0.0}


def _loop():
    last_seen = None
    while not _stop.wait(3.0):
        try:
            if not app_settings.keep_screen():
                last_seen = None
                continue
            running = launcher.is_running()
            if running:
                last_seen = None
                continue
            now = time.monotonic()
            if last_seen is None:
                last_seen = now
                continue
            if now - last_seen < 2.0:
                continue
            spec = app_settings.last_dashboard() or \
                app_settings.default_dashboard()
            result = launcher.open_dashboard(spec)
            _state["last_at"] = time.time()
            if result.get("ok"):
                _state["relaunches"] += 1
                _state["last_error"] = ""
                log.info("watchdog: 7\" relance sur %s", spec)
            else:
                _state["last_error"] = str(result.get("error") or "echec")
                log.warning("watchdog: relance impossible: %s",
                            _state["last_error"])
            last_seen = time.monotonic()
        except Exception as exc:
            _state["last_error"] = str(exc)
            log.exception("watchdog")


def start():
    global _thread
    if _thread is not None and _thread.is_alive():
        return False
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="idash-watchdog",
                               daemon=True)
    _thread.start()
    return True


def stop():
    _stop.set()


def status():
    return {
        "running": bool(_thread and _thread.is_alive()),
        "keep_screen": app_settings.keep_screen(),
        "last_dashboard": app_settings.last_dashboard(),
        "relaunches": _state["relaunches"],
        "last_error": _state["last_error"],
        "last_at": _state["last_at"],
    }
