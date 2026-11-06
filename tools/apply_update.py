"""Applique un staging de mise a jour apres l'arret du serveur.

Ce script est volontairement autonome (stdlib uniquement). En mode source, il
est lance par Python ; en mode exe, il est compile en ``idash-update.exe`` et
copie dans ``.update/`` avant execution.
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
              "Mini Deck App Roadmap.md", "VERSION", "requirements.txt",
              "requirements-windows.txt", "requirements-build.txt"]
CODE_DIRS = ["core", "adapters", "assets", "dashboards", "home", "settings",
             "studio", "tools"]
PROTECTED = {"custom", "logs", ".update", ".profile-7", "app.json",
             "game.json", ".idash.lock", "themes", "simhub_samples"}
_LOG_PATH = None


def log(message):
    line = str(message)
    try:
        if sys.stdout is not None:
            print(line, flush=True)
    except Exception:
        pass
    try:
        if _LOG_PATH is not None:
            _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with _LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception:
        pass


def wait_pid(pid):
    if pid <= 0:
        return
    if sys.platform == "win32":
        try:
            kernel = ctypes.windll.kernel32
            handle = kernel.OpenProcess(0x00100000, False, pid)
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


def backup_user_data(root):
    target = root / ".update" / ("backup-" + time.strftime("%Y%m%d-%H%M%S"))
    for name in ("app.json", "game.json", "themes/active.json"):
        source = root / name
        if source.is_file():
            copy_item(source, target / name)
    return target


def copy_source(staging, root):
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


def copy_exe(staging, root):
    for item in staging.iterdir():
        if item.name in PROTECTED:
            continue
        copy_item(item, root / item.name)
        log("copie %s" % item.name)
    themes = staging / "themes"
    if themes.is_dir():
        target = root / "themes"
        target.mkdir(parents=True, exist_ok=True)
        for theme in themes.glob("*.json"):
            if theme.name == "active.json":
                continue
            copy_item(theme, target / theme.name)


def start_app(root, exe=""):
    if exe and Path(exe).is_file():
        cmd = [exe]
    elif (root / "idash.exe").is_file():
        cmd = [str(root / "idash.exe")]
    elif sys.platform == "win32":
        cmd = ["cmd", "/c", "start", "", "lancer.bat"]
    else:
        cmd = [sys.executable, "main.py"]
    kwargs = {"cwd": str(root), "stdin": subprocess.DEVNULL,
              "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if sys.platform == "win32":
        kwargs["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0) | \
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(cmd, **kwargs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--staging", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--pid", type=int, default=0)
    ap.add_argument("--kind", default="source")
    ap.add_argument("--exe", default="")
    args = ap.parse_args()
    staging = Path(args.staging)
    root = Path(args.root)
    global _LOG_PATH
    _LOG_PATH = root / ".update" / "apply-detail.log"
    log("staging=%s root=%s pid=%s kind=%s" % (staging, root, args.pid,
                                               args.kind))
    try:
        wait_pid(args.pid)
        backup_user_data(root)
        if args.kind == "exe":
            copy_exe(staging, root)
        else:
            copy_source(staging, root)
    except Exception as exc:
        log("ERREUR copie: %s" % exc)
    finally:
        try:
            start_app(root, args.exe)
            log("application relancee")
        except Exception as exc:
            log("ERREUR relance: %s" % exc)


if __name__ == "__main__":
    main()
