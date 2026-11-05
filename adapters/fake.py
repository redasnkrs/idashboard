"""Fausse source de donnees.

Sert aux tests et au developpement sans Windows ni Assetto Corsa Evo :

    python main.py --fake

Elle produit un etat plausible et anime, au meme format que la vraie source.
"""
import math
import time

from adapters.base import Source

RATIOS = [0, 7.2, 11.4, 15.8, 20.3, 25, 29.5, 34]  # km/h pour 1000 tr/min


class FakeSource(Source):
    def __init__(self):
        self._dash = None

    def read(self):
        t = time.time()
        rpm_max = 9000.0
        speed = 28 + 240 * (0.5 - 0.5 * math.cos(2 * math.pi * t / 28))
        accel = math.sin(2 * math.pi * t / 28) > 0
        gear = 1
        while gear < 7 and speed / RATIOS[gear] * 1000 > 8900:
            gear += 1
        rpm = max(900.0, speed / RATIOS[gear] * 1000)
        phase = int(t / 6) % 4
        fuel = max(5.0, 42.0 - t * 0.02)
        dash = {
            "c": True, "st": 2, "v": speed, "r": rpm, "rm": rpm_max, "g": gear,
            "gas": 0.92 if accel else 0.0,
            "brk": 0.0 if accel else 0.35 + 0.3 * math.sin(t * 2.2),
            "clu": 0.0, "hb": 0.0,
            "fuel": fuel, "fp": fuel / 60.0, "laps": fuel / 2.4, "fpl": 2.4,
            "low": True, "high": int(t / 9) % 2 == 1,
            "L": phase == 1, "R": phase == 3, "haz": False,
            "pit": False, "pitlane": False,
            "tc": accel and speed < 90,
            "abs": (not accel) and speed > 120 and math.sin(t * 5) > 0.6,
            "esc": False,
            "lim": False, "up": rpm > 8700, "run": True,
            "wt": 88 + 6 * math.sin(t / 9), "ot": 104 + 8 * math.sin(t / 13),
            "op": 4.2, "boost": 0.9 if accel else 0.1,
            "lap": int((t * 1000) % 88500), "last": 89123, "best": 88342,
            "delta": int(math.sin(t / 3) * 420), "valid": True,
            "pos": 3, "nd": 12, "tcl": 3, "absl": 2, "bb": 56.5,
            "car": "FERRARI 296 GT3", "track": "MONZA", "cfg": "GRAND PRIX",
        }
        self._dash = dash
        return dash

    def ets2(self):
        d = self._dash or {}
        if not d:
            return super().ets2()
        gear = d["g"]
        return {
            "game": {"connected": True, "paused": False, "gameName": "ETS2",
                     "version": "1.0", "telemetryPluginVersion": "1"},
            "truck": {
                "id": "fake", "make": "Fake", "model": "Car",
                "speed": d["v"], "cruiseControlOn": False,
                "cruiseControlSpeed": 0.0, "gear": gear,
                "displayedGear": gear, "engineRpm": d["r"],
                "engineRpmMax": d["rm"], "fuel": d["fuel"],
                "fuelCapacity": 60.0, "fuelWarningOn": d["fp"] < 0.1,
                "engineOn": True, "electricOn": True, "parkBrakeOn": False,
                "userThrottle": d["gas"] * 100, "userBrake": d["brk"] * 100,
                "userClutch": 0.0, "lightsBeamLowOn": d["low"],
                "lightsBeamHighOn": d["high"], "lightsParkingOn": False,
                "blinkerLeftOn": d["L"], "blinkerRightOn": d["R"],
                "blinkerLeftActive": d["L"], "blinkerRightActive": d["R"],
                "lightsBrakeOn": d["brk"] > 0.05,
                "lightsReverseOn": gear == -1, "wipersOn": False,
            },
            "navigation": {"speedLimit": 0, "estimatedDistance": 0,
                           "estimatedTime": "0001-01-01T00:00:00Z"},
            "trailer": {"attached": False},
            "job": {},
        }
