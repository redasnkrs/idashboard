"""Source ETS2/ATS via l'API locale de SimHub.

SimHub expose ``/api/getgamedata`` avec les proprietes normalisees et brutes.
Cette source est optionnelle : si SimHub n'est pas lance, elle renvoie None et
les autres sources continuent de fonctionner.
"""
import json
import time
import urllib.request
from datetime import datetime

from adapters.base import DISCONNECTED_ETS2, Source, basic_ets2
from core.config import SIMHUB_API_URL


def _num(value, default=0.0):
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "."))
        except ValueError:
            return default
    return default


def _bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "on")
    return False


def _percent(value):
    n = _num(value)
    if abs(n) <= 1.5:
        return n * 100.0
    return n


def _fraction(value):
    n = _num(value)
    if n > 1.5:
        n /= 100.0
    return max(0.0, min(1.0, n))


def _gear(raw):
    text = str(raw if raw is not None else "N").strip()
    low = text.lower()
    if low in ("n", "neutral", ""):
        return 0, "N"
    if low in ("r", "r1", "reverse"):
        return -1, "R"
    if low in ("d", "drive"):
        return 1, "D"
    digits = "".join(c for c in text if c.isdigit())
    if digits:
        number = int(digits)
        return (-number if low.startswith("r") else number), text
    return 0, text or "N"


def _clock(raw):
    if isinstance(raw, str) and raw.strip():
        text = raw.strip()
        if "T" in text:
            text = text.split("T", 1)[1]
        parts = text.split(":")
        if len(parts) >= 2:
            return "%s:%s" % (parts[0][-2:].zfill(2), parts[1][:2])
        return text[:5]
    n = _num(raw)
    if n > 10_000_000:
        try:
            return datetime.fromtimestamp(n).strftime("%H:%M")
        except (OSError, ValueError, OverflowError):
            pass
    if n >= 0:
        n = int(n) % 86400
        return "%02d:%02d" % (n // 3600, (n % 3600) // 60)
    return time.strftime("%H:%M")


def _eta(raw):
    if isinstance(raw, str) and raw.strip():
        text = raw.strip()
        if "T" in text:
            text = text.split("T", 1)[1]
        parts = text.split(":")
        if len(parts) >= 2:
            return "ETA : %s:%s" % (parts[0][-2:].zfill(2), parts[1][:2])
        return "ETA : " + text[:5]
    n = _num(raw)
    if n > 0:
        minutes = int(n / 60 if n > 5000 else n)
        return "ETA : %02d:%02d" % ((minutes // 60) % 24, minutes % 60)
    return ""


def _index(data):
    out = {}

    def walk(value, path):
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, path + (str(key),))
        elif isinstance(value, list):
            return
        else:
            full = ".".join(path).lower()
            if full:
                out.setdefault(full, value)
            if path:
                out.setdefault(path[-1].lower(), value)

    walk(data, ())
    return out


def _get(index, *names):
    for name in names:
        key = name.strip(".").lower()
        for prefix in ("", "datacoreplugin.", "gamedata.", "gamerawdata.",
                       "gamedata.newdata.",
                       "datacoreplugin.gamedata.newdata."):
            if prefix + key in index:
                return index[prefix + key]
    return None


class SimHubSource(Source):
    def __init__(self, url=SIMHUB_API_URL, interval=0.5, timeout=0.35):
        self.url = url
        self.interval = interval
        self.timeout = timeout
        self._next = 0.0
        self._dash = None
        self._raw = None

    def _fetch(self):
        with urllib.request.urlopen(self.url, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def read(self):
        now = time.monotonic()
        if now < self._next:
            return self._dash
        self._next = now + self.interval
        try:
            data = self._fetch()
        except Exception:
            self._dash = None
            self._raw = None
            return None
        if not isinstance(data, dict):
            self._dash = None
            return None
        self._raw = data
        self._dash = self._map(data)
        return self._dash

    def _map(self, data):
        idx = _index(data)
        running = _bool(_get(idx, "GameRunning", "DataCorePlugin.GameRunning"))
        if not running and _get(idx, "GameName", "CurrentGame") is None:
            return None
        game_raw = str(_get(idx, "GameName", "CurrentGame", "Game") or "")
        low = game_raw.lower()
        if "ats" in low or "american" in low:
            game_id, game = "ats", "American Truck Simulator"
        elif "ets" in low or "euro" in low:
            game_id, game = "ets2", "Euro Truck Simulator 2"
        else:
            game_id, game = "simhub", game_raw or "SimHub"
        gear_raw = _get(idx, "Gear", "NewData.Gear", "GameData.NewData.Gear")
        gear, gear_text = _gear(gear_raw)
        fuel_raw = _num(_get(idx, "Fuel", "NewData.Fuel",
                             "GameData.NewData.Fuel"))
        fuel_pct = _fraction(_get(idx, "FuelPercent", "Fuel_Percent",
                                   "Computed.Fuel_Percent"))
        fuel_cap = _num(_get(idx, "FuelCapacity", "FuelCapacityLiters"))
        if fuel_raw <= 0 and fuel_cap > 0:
            fuel_raw = fuel_cap * fuel_pct
        speed = _num(_get(idx, "SpeedKmh", "SpeedLocal",
                          "FilteredSpeedLocal", "NewData.SpeedKmh"))
        speed_unit = str(_get(idx, "SpeedLocalUnit", "SpeedUnit") or "km/h")
        rpm = _num(_get(idx, "Rpms", "RPM", "FilteredRpms", "EngineRpm"))
        rpm_max = _num(_get(idx, "MaxRpm", "MaxRPM", "CarSettings_MaxRPM",
                            "EngineRpmMax"), 9000)
        wear_truck = _percent(_get(idx, "WearChassis", "Damage.WearChassis"))
        wear_trailer = _percent(_get(
            idx, "WearTrailer", "Damage.WearTrailer"))
        wear_cargo = _percent(_get(
            idx, "TrailerValues01.DamageValues.Chassis",
            "DamageValues.Chassis"))
        city = str(_get(idx, "CityDestination", "Job.CityDestination") or "")
        company = str(_get(idx, "CompanyDestination",
                           "Job.CompanyDestination") or "")
        destination = " ".join(x for x in (city, company) if x).strip()
        speed_limit = _get(idx, "SpeedLimitKmh", "Job.SpeedLimitKmh",
                           "NavigationValues.SpeedLimit.Kph",
                           "SpeedLimit")
        eta = _eta(_get(idx, "NavigationTime", "Job.NavigationTime"))
        truck_brand = str(_get(idx, "TruckBrand", "Make") or "")
        truck_name = str(_get(idx, "TruckName", "Model") or "")
        car = " ".join(x for x in (truck_brand, truck_name) if x).strip()
        dash = {
            "c": True, "st": 3 if _bool(_get(idx, "GamePaused")) else 2,
            "v": speed, "r": rpm, "rm": rpm_max or 9000,
            "g": gear, "gear_text": gear_text,
            "gas": _fraction(_get(idx, "Throttle", "NewData.Throttle")),
            "brk": _fraction(_get(idx, "Brake", "NewData.Brake")),
            "clu": _fraction(_get(idx, "Clutch", "NewData.Clutch")),
            "hb": _fraction(_get(idx, "Handbrake", "NewData.Handbrake")),
            "fuel": max(0.0, fuel_raw), "fp": fuel_pct,
            "fpl": _num(_get(idx, "Fuel_LitersPerLap",
                             "FuelLiterPerLap")),
            "laps": _num(_get(idx, "Fuel_RemainingLaps",
                              "FuelRemainingLaps")),
            "low": _bool(_get(idx, "LowFuel", "FuelWarning")),
            "high": _bool(_get(idx, "HighBeam", "LightsBeamHigh")),
            "L": _bool(_get(idx, "TurnIndicatorLeft", "BlinkerLeftActive")),
            "R": _bool(_get(idx, "TurnIndicatorRight",
                            "BlinkerRightActive")),
            "haz": _bool(_get(idx, "LightsHazard", "HazardLights")),
            "pit": False, "pitlane": False,
            "tc": False, "abs": False, "esc": False, "lim": False,
            "up": False,
            "run": running,
            "ign": _bool(_get(idx, "EngineEnabled", "ElectricEnabled",
                              "EngineOn")) or running,
            "wt": _num(_get(idx, "WaterTemperature")),
            "ot": _num(_get(idx, "OilTemperature")),
            "op": _num(_get(idx, "OilPressure")),
            "boost": _num(_get(idx, "TurboBoost")),
            "at": _num(_get(idx, "AirTemperature", "AmbientTemperature")),
            "lap": 0, "last": 0, "best": 0, "delta": 0, "valid": True,
            "pos": int(_num(_get(idx, "Position"))),
            "nd": int(_num(_get(idx, "TotalDrivers", "NumCars"))),
            "npos": None, "tcl": None, "absl": None, "bb": None,
            "car": car, "track": str(_get(idx, "City") or ""),
            "cfg": "",
            "mode": str(_get(idx, "Job.Market") or ""),
            "game_time": _clock(_get(idx, "TimeAbsolute",
                                      "GameRawData.TimeAbsolute")),
            "speed_unit": speed_unit.lower(),
            "destination": destination,
            "eta_text": eta,
            "wear_truck": wear_truck, "wear_trailer": wear_trailer,
            "wear_cargo": wear_cargo,
            "speed_limit": _num(speed_limit) if speed_limit is not None
            else None,
            "game": game, "game_id": game_id,
        }
        if dash["wt"] <= 0:
            dash["wt"] = None
        if dash["ot"] <= 0:
            dash["ot"] = None
        if dash["op"] <= 0:
            dash["op"] = None
        return dash

    def ets2(self):
        if not self._dash:
            return DISCONNECTED_ETS2
        base = basic_ets2(self._dash)
        base["truck"]["speed"] = self._dash["v"]
        base["job"] = {
            "cityDestination": self._dash.get("destination", ""),
            "companyDestination": "",
        }
        base["navigation"]["speedLimit"] = self._dash.get("speed_limit") or 0
        return base
