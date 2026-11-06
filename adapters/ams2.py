"""Source Automobilista 2 (shared memory Project CARS 2 `$pcars2$`).

AMS2 doit etre configure en mode Shared Memory « Project CARS 2 » dans les
options du jeu. La structure v9 est lue via ctypes ; les champs utilises par le
contrat commun sont convertis (m/s -> km/h, secondes -> ms, kPa -> bar...).
"""
import ctypes
import mmap
import re
import sys
import time

from adapters.ams2_defs import (CAR_ENGINE_ACTIVE, CAR_HEADLIGHT,
                                CAR_SPEED_LIMITER, GAME_INGAME_PAUSED,
                                GAME_INGAME_PLAYING, GAME_INGAME_REPLAY,
                                GAME_FRONT_END_REPLAY, GameInstance)
from adapters.base import Source, basic_ets2

SHARED_NAME = "$pcars2$"
SIZE = ctypes.sizeof(GameInstance)


def _clean(value):
    try:
        if isinstance(value, bytes):
            text = value.decode("utf-8", "replace")
        else:
            text = str(value)
    except Exception:
        return ""
    text = re.sub(r"[^\w .\-+/()&']", "", text).strip()
    return text[:40]


def _num(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _plausible(value, lo, hi):
    value = _num(value)
    return value if value is not None and lo <= value <= hi else None


def _mapping_exists(name):
    if sys.platform != "win32":
        return False
    try:
        kernel = ctypes.windll.kernel32
        handle = kernel.OpenFileMappingW(0x0004, False, name)
        if not handle:
            return False
        kernel.CloseHandle(handle)
        return True
    except Exception:
        return False


def _ms(seconds):
    value = _num(seconds, 0.0) or 0.0
    if value <= 0 or value > 3600:
        return 0
    return int(value * 1000)


class Ams2Source(Source):
    def __init__(self):
        self._map = None
        self._view = None
        self._next_try = 0.0
        self._last = None

    def _open_map(self):
        if sys.platform != "win32":
            return None
        for tag in (SHARED_NAME, "Local\\" + SHARED_NAME):
            if not _mapping_exists(tag):
                continue
            try:
                return mmap.mmap(0, SIZE, tagname=tag,
                                 access=mmap.ACCESS_READ)
            except (OSError, ValueError):
                continue
        return None

    def _close(self):
        if self._map is not None:
            try:
                self._map.close()
            except Exception:
                pass
        self._map = None
        self._view = None

    def _open(self):
        if sys.platform != "win32":
            return False
        if time.time() < self._next_try:
            return False
        self._close()
        mapping = self._open_map()
        if mapping is None:
            self._next_try = time.time() + 0.5
            return False
        try:
            view = GameInstance.from_buffer(mapping)
            if int(view.mVersion) < 9:
                self._close()
                self._next_try = time.time() + 0.5
                return False
        except (OSError, ValueError):
            self._close()
            self._next_try = time.time() + 0.5
            return False
        self._map = mapping
        self._view = view
        return True

    def read(self):
        if self._view is None and not self._open():
            return None
        view = self._view
        try:
            version = int(view.mVersion)
            if version < 9:
                return None
            idx = int(view.mViewedParticipantIndex)
            count = int(view.mNumParticipants)
            player = None
            if 0 <= idx < min(64, max(0, count)):
                player = view.mParticipantInfo[idx]
            flags = int(view.mCarFlags)
            run = bool(flags & CAR_ENGINE_ACTIVE)
            lap_distance = _num(player.mCurrentLapDistance, 0.0) if player else 0.0
            track_len = _num(view.mTrackLength, 0.0) or 0.0
            npos = (max(0.0, min(1.0, lap_distance / track_len))
                    if player and track_len > 1 else None)
            water = _plausible(view.mWaterTempCelsius, -30, 250)
            oil = _plausible(view.mOilTempCelsius, -30, 250)
            pressure = _plausible(view.mOilPressureKPa, 0, 20000)
            if pressure is not None:
                pressure /= 100.0
            boost = _plausible(view.mTurboBoostPressure, -2, 10)
            brake_bias = _num(view.mBrakeBias, 0.0) or 0.0
            if 0 < brake_bias < 1.5:
                brake_bias *= 100.0
            state = int(view.mGameState)
            if state == GAME_INGAME_PLAYING:
                status = 2
            elif state == GAME_INGAME_PAUSED:
                status = 3
            elif state in (GAME_INGAME_REPLAY, GAME_FRONT_END_REPLAY):
                status = 1
            else:
                status = 0
            track = _clean(view.mTranslatedTrackLocation) or \
                _clean(view.mTrackLocation)
            cfg = _clean(view.mTranslatedTrackVariation) or \
                _clean(view.mTrackVariation)
            dash = {
                "c": True,
                "st": status,
                "v": max(0.0, (_num(view.mSpeed, 0.0) or 0.0) * 3.6),
                "r": max(0.0, _num(view.mRpm, 0.0) or 0.0),
                "rm": max(0.0, _num(view.mMaxRPM, 0.0) or 0.0),
                "g": int(view.mGear),
                "gas": float(view.mThrottle),
                "brk": float(view.mBrake),
                "clu": float(view.mClutch),
                "hb": float(view.mHandBrake),
                "fuel": max(0.0, float(view.mFuelLevel) *
                            float(view.mFuelCapacity)),
                "fp": max(0.0, min(1.0, float(view.mFuelLevel))),
                "fpl": 0.0,
                "laps": 0.0,
                "low": bool(flags & CAR_HEADLIGHT),
                "high": False,
                "L": False,
                "R": False,
                "haz": False,
                "pit": bool(flags & CAR_SPEED_LIMITER),
                "pitlane": int(view.mPitMode) > 0,
                "tc": False,
                "abs": bool(view.mAntiLockActive),
                "esc": False,
                "lim": False,
                "up": False,
                "run": run,
                "ign": run,
                "wt": water,
                "ot": oil,
                "op": pressure,
                "boost": boost,
                "at": _plausible(view.mAmbientTemperature, -30, 60),
                "lap": _ms(view.mCurrentTime),
                "last": _ms(view.mLastLapTime),
                "best": _ms(view.mBestLapTime),
                "delta": 0,
                "valid": not bool(view.mLapInvalidated),
                "pos": int(player.mRacePosition) if player else 0,
                "nd": max(0, count),
                "npos": npos,
                "tcl": None,
                "absl": None,
                "bb": _plausible(brake_bias, 20, 90),
                "car": _clean(view.mCarName),
                "track": track,
                "cfg": cfg,
                "mode": "",
                "game": "Automobilista 2",
                "game_id": "ams2",
            }
        except Exception:
            self._close()
            return None
        self._last = dash
        return dash

    def ets2(self):
        return basic_ets2(self._last)
