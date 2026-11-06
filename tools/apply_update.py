"""Applique un staging de mise a jour apres l'arret du serveur.

Script volontairement autonome (stdlib uniquement) : il est copie dans
``.update/`` avant d'etre lance, pour pouvoir remplacer le dossier ``tools/``.
"""
import argparse
import ctypes
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

CODE_FILES = ["main.py", "acevo_bridge.py", "lancer.bat", "README.md",
              "Mini Deck App Roadmap.md", "VERSION", "requirements.txt"]
CODE_DIRS = ["core", "adapters", "dashboards", "home", "settings", "studio",
             "tools"]


def log(message):
    print(message, flush=True)


def wait_pid(pid):
    if pid <= 0:
        return
    if sys.platform == "win32":
        try:
            kernel = ctypes.windll.kernel32
            handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
            if handle:
                kernel.WaitForSingleObject(handle, 30000)
                kernel.CloseHandle(handle)
        except Exception as exc:
            log("attente pid: %s" % exc)
        time.sleep(0.5)
        return
    for _ in range(300):
        try:
            os.kill(pid, 0)
        except OSError:
            break
        time.sleep(0.2)
    time.sleep(0.3)


def copy_item(src, dst):
    if not src.exists():
        return
    last = None
    for _ in range(6):
        try:
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            return
        except (OSError, PermissionError) as exc:
            last = exc
            time.sleep(0.4)
    raise last


def start_app(root):
    if sys.platform == "win32":
        subprocess.Popen(["cmd", "/c", "start", "", "lancer.bat"],
                         cwd=str(root), shell=False)
    else:
        subprocess.Popen([sys.executable, "main.py"], cwd=str(root),
                         stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         start_new_session=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--staging", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--pid", type=int, default=0)
    args = ap.parse_args()
    staging = Path(args.staging)
    root = Path(args.root)
    log("staging=%s root=%s pid=%s" % (staging, root, args.pid))
    try:
        wait_pid(args.pid)
        for name in CODE_FILES:
            copy_item(staging / name, root / name)
            log("copie %s" % name)
        for name in CODE_DIRS:
            copy_item(staging / name, root / name)
            log("copie %s/" % name)
        themes = staging / "themes"
        if themes.is_dir():
            target = root / "themes"
            target.mkdir(parents=True, exist_ok=True)
            for theme in themes.glob("*.json"):
                if theme.name == "active.json":
                    continue
                copy_item(theme, target / theme.name)
            log("themes mis a jour")
    except Exception as exc:
        log("ERREUR copie: %s" % exc)
    finally:
        try:
            start_app(root)
            log("application relancee")
        except Exception as exc:
            log("ERREUR relance: %s" % exc)


if __name__ == "__main__":
    main()
