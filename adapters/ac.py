"""Source Assetto Corsa 2014 (shared memory classique, Windows).

Lit `acpmf_physics`, `acpmf_graphics` et `acpmf_static` et convertit vers le
contrat commun. AC n'expose pas les feux, clignotants ni la temperature moteur
dans cette API : ces champs restent a zero / null.
"""
import ctypes
import mmap
import re
import sys
import time

from adapters.ac_defs import (SPageFileGraphic, SPageFilePhysics,
                              SPageFileStatic)
from adapters.base import Source, basic_ets2

SIZES = (ctypes.sizeof(SPageFilePhysics),
         ctypes.sizeof(SPageFileGraphic),
         ctypes.sizeof(SPageFileStatic))
NAMES = ("acpmf_physics", "acpmf_graphics", "acpmf_static")
FUEL_DENSITY = 0.75  # AC expose le carburant en kg ; les compteurs affichent des litres


def _clean(value):
    try:
        text = str(value).strip()
    except Exception:
        return ""
    text = re.sub(r"[^\w .\-+/()&']", "", text)
    return text[:40]


def _plausible(value, lo, hi):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if lo <= value <= hi else None


def _mapping_exists(name):
    if sys.platform != "win32":
        return False
    try:
        kernel = ctypes.windll.kernel32
        handle = kernel.OpenFileMappingW(0x0004, False, name)  # FILE_MAP_READ
        if not handle:
            return False
        kernel.CloseHandle(handle)
        return True
    except Exception:
        return False


def _gear(raw):
    if raw == 0:
        return -1
    if raw == 1:
        return 0
    return int(raw) - 1


class AcSource(Source):
    def __init__(self):
        self._maps = []
        self._structs = None
        self._next_try = 0.0
        self._last = None

    def _open_map(self, name, size):
        if sys.platform != "win32":
            return None
        for tag in (name, "Local\\" + name):
            if not _mapping_exists(tag):
                continue
            try:
                return mmap.mmap(0, size, tagname=tag,
                                 access=mmap.ACCESS_READ)
            except (OSError, ValueError):
                continue
        return None

    def _close(self):
        for mapping in self._maps:
            try:
                mapping.close()
            except Exception:
                pass
        self._maps = []
        self._structs = None

    def _open(self):
        if sys.platform != "win32":
            return False
        if time.time() < self._next_try:
            return False
        self._close()
        maps = []
        try:
            for name, size in zip(NAMES, SIZES):
                mapping = self._open_map(name, size)
                if mapping is None:
                    raise OSError("shared memory absente")
                maps.append(mapping)
            static = SPageFileStatic.from_buffer(maps[2])
            if not str(static._smVersion).strip():
                raise OSError("shared memory non initialisee")
            self._maps = maps
            self._structs = (
                SPageFilePhysics.from_buffer(maps[0]),
                SPageFileGraphic.from_buffer(maps[1]),
                static,
            )
            return True
        except (OSError, ValueError):
            for mapping in maps:
                try:
                    mapping.close()
                except Exception:
                    pass
            self._next_try = time.time() + 0.5
            return False

    def read(self):
        if self._structs is None and not self._open():
            return None
        phys, gfx, static = self._structs
        try:
            speed = float(phys.speedKmh)
            rpm = float(phys.rpms)
            max_rpm = float(static.maxRpm or 0) or 8000.0
            gear = _gear(int(phys.gear))
            fuel = float(phys.fuel) / FUEL_DENSITY
            max_fuel = float(static.maxFuel or 0)
            status = int(gfx.status)
            brake_bias = float(phys.brakeBias)
            if 0 < brake_bias < 1.5:
                brake_bias *= 100.0
            air = _plausible(static.airTemp, -30, 60)
            if air is None:
                air = _plausible(phys.airTemp, -30, 60)
            dash = {
                "c": True,
                "st": status,
                "v": speed,
                "r": rpm,
                "rm": max_rpm,
                "g": gear,
                "gas": float(phys.gas),
                "brk": float(phys.brake),
                "clu": float(phys.clutch),
                "hb": 0.0,
                "fuel": fuel,
                "fp": (fuel / max_fuel) if max_fuel > 0 else 0.0,
                "fpl": 0.0,
                "laps": 0.0,
                "low": False,
                "high": False,
                "L": False,
                "R": False,
                "haz": False,
                "pit": bool(phys.pitLimiterOn),
                "pitlane": bool(gfx.isInPitLine or gfx.isInPit),
                "tc": float(phys.tc) > .5,
                "abs": float(phys.abs) > .5,
                "esc": False,
                "lim": False,
                "up": False,
                "run": True,
                "ign": True,
                "wt": None,
                "ot": None,
                "op": None,
                "boost": _plausible(phys.turboBoost, -2, 10),
                "at": air,
                "lap": max(0, int(gfx.iCurrentTime)),
                "last": max(0, int(gfx.iLastTime)),
                "best": max(0, int(gfx.iBestTime)),
                "delta": 0,
                "valid": True,
                "pos": int(gfx.position),
                "nd": int(static.numCars),
                "npos": max(0.0, min(1.0, float(gfx.normalizedCarPosition))),
                "tcl": None,
                "absl": None,
                "bb": _plausible(brake_bias, 20, 90),
                "car": _clean(static.carModel),
                "track": _clean(static.track),
                "cfg": _clean(getattr(static, "trackConfiguration", "")),
                "mode": "",
                "game": "Assetto Corsa",
                "game_id": "ac",
            }
        except Exception:
            self._close()
            return None
        self._last = dash
        return dash

    def ets2(self):
        return basic_ets2(self._last)
