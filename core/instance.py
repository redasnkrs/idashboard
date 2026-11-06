"""Verrou d'instance unique (mutex Windows, fichier ailleurs)."""
import os
import sys
from pathlib import Path

from core.config import ROOT

LOCK_FILE = ROOT / ".idash.lock"
_lock = None
_handle = None
MUTEX_NAME = "Local\\idash-bridge"


def _win_acquire():
    global _handle
    import ctypes
    kernel = ctypes.windll.kernel32
    kernel.CreateMutexW.restype = ctypes.c_void_p
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                    ctypes.c_wchar_p]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.CreateMutexW(None, False, MUTEX_NAME)
    if not handle:
        return False
    if kernel.GetLastError() == 183:
        kernel.CloseHandle(handle)
        return False
    _handle = handle
    return True


def _file_acquire():
    global _lock
    try:
        import fcntl
    except ImportError:
        return True
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    lock = LOCK_FILE.open("a+")
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock.close()
        return False
    lock.seek(0)
    lock.truncate()
    lock.write(str(os.getpid()))
    lock.flush()
    _lock = lock
    return True


def acquire():
    if sys.platform == "win32":
        return _win_acquire()
    return _file_acquire()


def release():
    global _lock, _handle
    if _handle is not None:
        try:
            import ctypes
            ctypes.windll.kernel32.CloseHandle(_handle)
        except Exception:
            pass
        _handle = None
    if _lock is not None:
        try:
            import fcntl
            fcntl.flock(_lock.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            _lock.close()
        except OSError:
            pass
        _lock = None
    try:
        LOCK_FILE.unlink()
    except OSError:
        pass
