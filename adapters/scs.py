"""Source ETS2/ATS directe via le plugin SCS SDK (shared memory)."""
import math
import time

from adapters.base import DISCONNECTED_ETS2, Source, basic_ets2


def _num(value, default=0.0):
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bool(value):
    return bool(value)


def _clock(minutes):
    try:
        minutes = int(minutes) % 1440
    except (TypeError, ValueError):
        return ""
    return "%02d:%02d" % (minutes // 60, minutes % 60)


def _eta(minutes):
    try:
        minutes = int(minutes)
    except (TypeError, ValueError):
        return ""
    if minutes < 0:
        minutes += 1440
    return "ETA : %02d:%02d" % ((minutes // 60) % 24, minutes % 60)


def _gear(value):
    try:
        gear = int(value)
    except (TypeError, ValueError):
        return 0, "N"
    if gear < 0:
        return -1, "R"
    if gear == 0:
        return 0, "N"
    return gear, str(gear)


def map_data(data):
    """Transforme le dict de truck-telemetry au contrat idash."""
    if not isinstance(data, dict) or not _bool(data.get("sdkActive")):
        return None
    game_no = int(_num(data.get("game"), 1))
    if game_no == 2:
        game_id, game = "ats", "American Truck Simulator"
    else:
        game_id, game = "ets2", "Euro Truck Simulator 2"
    speed = _num(data.get("speed"))
    fuel = _num(data.get("fuel"))
    capacity = _num(data.get("fuelCapacity"))
    fuel_pct = fuel / capacity if capacity > 0 else 0.0
    speed_limit = _num(data.get("speedLimit"))
    if 0 < speed_limit <= 60:
        speed_limit *= 3.6
    gear, gear_text = _gear(data.get("gear"))
    trailers = data.get("trailer") or []
    trailer = trailers[0] if trailers and isinstance(trailers[0], dict) else {}
    wear_trailer = _num(trailer.get("wearChassis")) * 100
    wear_cargo = _num(trailer.get("cargoDamage")) * 100
    time_abs = _num(data.get("time_abs"))
    delivery = _num(data.get("time_abs_delivery"))
    remaining = data.get("routeTime")
    if remaining is None:
        remaining = delivery - time_abs if delivery > 0 else 0
    remaining = _num(remaining)
    if remaining > 1440:
        remaining /= 60
    destination = " ".join(x for x in (
        str(data.get("cityDst") or ""), str(data.get("compDst") or "")
    ) if x).strip()
    rotation = _num(data.get("rotationY"))
    heading = math.degrees(rotation) % 360 if rotation else 0.0
    dash = {
        "c": True,
        "st": 3 if _bool(data.get("paused")) else 2,
        "v": speed * 3.6,
        "r": _num(data.get("engineRpm")),
        "rm": _num(data.get("engineRpmMax"), 9000) or 9000,
        "g": gear, "gear_text": gear_text,
        "gas": _num(data.get("userThrottle")),
        "brk": _num(data.get("userBrake")),
        "clu": _num(data.get("userClutch")),
        "hb": 1.0 if _bool(data.get("parkBrake")) else 0.0,
        "fuel": max(0.0, fuel), "fp": max(0.0, min(1.0, fuel_pct)),
        "fpl": 0.0, "laps": 0.0,
        "low": _bool(data.get("lightsBeamLow")),
        "high": _bool(data.get("lightsBeamHigh")),
        "L": _bool(data.get("blinkerLeftActive")),
        "R": _bool(data.get("blinkerRightActive")),
        "haz": _bool(data.get("lightsHazards")),
        "pit": False, "pitlane": False,
        "tc": False, "abs": False, "esc": False, "lim": False,
        "up": False,
        "run": not _bool(data.get("paused")),
        "ign": _bool(data.get("engineEnabled") or
                    data.get("electricEnabled")),
        "wt": _num(data.get("waterTemperature")),
        "ot": _num(data.get("oilTemperature")),
        "op": _num(data.get("oilPressure")),
        "boost": None,
        "at": None,
        "lap": 0, "last": 0, "best": 0, "delta": 0, "valid": True,
        "pos": 0, "nd": 0, "npos": None,
        "tcl": None, "absl": None, "bb": None,
        "car": " ".join(x for x in (
            str(data.get("truckBrand") or ""),
            str(data.get("truckName") or "")) if x).strip(),
        "track": str(data.get("citySrc") or data.get("cityDst") or ""),
        "cfg": "", "mode": str(data.get("jobMarket") or ""),
        "game_time": _clock(time_abs),
        "speed_unit": "km/h",
        "destination": destination,
        "eta_text": _eta(remaining),
        "wear_truck": _num(data.get("wearChassis")) * 100,
        "wear_trailer": wear_trailer,
        "wear_cargo": wear_cargo,
        "speed_limit": speed_limit if speed_limit > 0 else None,
        "map_x": _num(data.get("coordinateX")),
        "map_y": _num(data.get("coordinateY")),
        "map_heading": heading,
        "game": game, "game_id": game_id,
    }
    if dash["wt"] <= 0:
        dash["wt"] = None
    if dash["ot"] <= 0:
        dash["ot"] = None
    if dash["op"] <= 0:
        dash["op"] = None
    return dash


class ScsSource(Source):
    def __init__(self, interval=0.1):
        self.interval = interval
        self._next = 0.0
        self._mod = None
        self._last_try = 0.0
        self._dash = None

    def _load(self):
        if self._mod is not None:
            return self._mod
        if time.monotonic() - self._last_try < 2.0:
            return None
        self._last_try = time.monotonic()
        try:
            import truck_telemetry
            truck_telemetry.init()
            self._mod = truck_telemetry
        except Exception:
            self._mod = None
        return self._mod

    def read(self):
        now = time.monotonic()
        if now < self._next:
            return self._dash
        self._next = now + self.interval
        mod = self._load()
        if mod is None:
            self._dash = None
            return None
        try:
            data = mod.get_data()
        except Exception:
            self._mod = None
            self._dash = None
            return None
        self._dash = map_data(data)
        return self._dash

    def ets2(self):
        if not self._dash:
            return DISCONNECTED_ETS2
        base = basic_ets2(self._dash)
        base["job"] = {"cityDestination": self._dash.get("destination", "")}
        base["navigation"]["speedLimit"] = self._dash.get("speed_limit") or 0
        return base
