"""Actions systeme : ouvrir les logs, redemarrer, quitter."""
import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

from core.config import PORT, ROOT
from core.paths import LOG_DIR


def open_home():
    return webbrowser.open("http://127.0.0.1:%d/" % PORT)


def open_settings():
    return webbrowser.open("http://127.0.0.1:%d/settings" % PORT)


def open_logs():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if sys.platform == "win32":
            os.startfile(str(LOG_DIR))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(LOG_DIR)])
        else:
            subprocess.Popen(["xdg-open", str(LOG_DIR)])
        return True
    except OSError:
        return False


def _command():
    if getattr(sys, "frozen", False):
        return [str(Path(sys.executable).resolve())]
    return [sys.executable, str(ROOT / "main.py")]


def restart(delay=1.0):
    def run():
        env = os.environ.copy()
        env["IDASH_RESTART"] = "1"
        kwargs = {"cwd": str(ROOT), "env": env, "stdin": subprocess.DEVNULL,
                  "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if sys.platform == "win32":
            kwargs["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0)
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen(_command(), **kwargs)
        os._exit(0)
    threading.Timer(delay, run).start()
    return True


def quit_app():
    threading.Timer(0.2, lambda: os._exit(0)).start()
    return True
