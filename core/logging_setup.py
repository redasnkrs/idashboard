"""Logs fichier + capture des exceptions pour l'app Windows."""
import logging
import logging.handlers
import sys
import threading

from core.paths import LOG_DIR

LOG_FILE = LOG_DIR / "idash.log"
_configured = False


def _hook(exc_type, exc, tb):
    logging.getLogger("idash").critical(
        "exception non geree", exc_info=(exc_type, exc, tb))


def _thread_hook(args):
    if args.exc_type is SystemExit:
        return
    logging.getLogger("idash").critical(
        "exception thread %s" % (args.thread.name if args.thread else "?"),
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback))


def setup(debug=False):
    global _configured
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if _configured:
        return LOG_FILE
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
    handler.setFormatter(formatter)
    root.addHandler(handler)
    if not getattr(sys, "frozen", False) and sys.stderr is not None:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        root.addHandler(console)
    logger = logging.getLogger("idash")
    logger.info("logs: %s", LOG_FILE)
    sys.excepthook = _hook
    threading.excepthook = _thread_hook
    _configured = True
    return LOG_FILE


def log_path():
    return LOG_FILE


def recent_errors(limit=20):
    entries = []
    try:
        with LOG_FILE.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return entries
    for line in reversed(lines):
        if " ERROR " in line or " CRITICAL " in line:
            entries.append(line.rstrip())
            if len(entries) >= limit:
                break
    return list(reversed(entries))
