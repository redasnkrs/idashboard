"""
AC Evo -> tableau de bord + Macro Deck.

Lit la memoire partagee d'Assetto Corsa Evo (Windows) et sert :

  http://localhost:25555/dashboard              tableau de bord (page web 1024x600)
  http://localhost:25555/dashboard?demo         meme page avec des donnees simulees
  http://localhost:25555/stream                 flux temps reel (SSE, 60 Hz)
  http://localhost:25555/api/dash               dernier etat, en JSON
  http://localhost:25555/api/ets2/telemetry     format "ETS2 Telemetry Server"
                                                (pour le plugin Macro Deck)

Installation :  pip install acevo-sdk
Lancement    :  python acevo_bridge.py            (garde dashboard.html a cote)
Debug        :  python acevo_bridge.py --debug    (affiche les valeurs lues)
"""
import argparse
import ctypes
import json
import os
import re
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 25555
POLL_HZ = 60
STREAM_HZ = 60
HERE = os.path.dirname(os.path.abspath(__file__))

c = ctypes


# ---------------------------------------------------------------------------
# Page "graphics" : layout tire de la crate `kerb` (SPageFileGraphicsEvo).
# Les sous-structures a taille fixe sont lues comme des blocs d'octets.
# Verifie en jeu : vitesse, rpm, rapport, carburant, phares. Le reste (tours,
# nom de voiture, TC/ABS...) suit le meme layout mais reste a confirmer.
# ---------------------------------------------------------------------------
class GraphicsEvo(c.Structure):
    _fields_ = [
        ("packet_id", c.c_int32), ("status", c.c_int32),
        ("focused_car_id_a", c.c_uint64), ("focused_car_id_b", c.c_uint64),
        ("player_car_id_a", c.c_uint64), ("player_car_id_b", c.c_uint64),
        ("rpm", c.c_uint16),
        ("is_rpm_limiter_on", c.c_bool), ("is_change_up_rpm", c.c_bool),
        ("is_change_down_rpm", c.c_bool), ("tc_active", c.c_bool),
        ("abs_active", c.c_bool), ("esc_active", c.c_bool),
        ("launch_active", c.c_bool), ("is_ignition_on", c.c_bool),
        ("is_engine_running", c.c_bool), ("kers_is_charging", c.c_bool),
        ("is_wrong_way", c.c_bool), ("is_drs_available", c.c_bool),
        ("battery_is_charging", c.c_bool),
        ("is_max_kj_per_lap_reached", c.c_bool),
        ("is_max_charge_kj_per_lap_reached", c.c_bool),
        ("display_speed_kmh", c.c_int16), ("display_speed_mph", c.c_int16),
        ("display_speed_ms", c.c_int16),
        ("pitspeeding_delta", c.c_float),
        ("gear_int", c.c_int16),
        ("rpm_percent", c.c_float), ("gas_percent", c.c_float),
        ("brake_percent", c.c_float), ("handbrake_percent", c.c_float),
        ("clutch_percent", c.c_float), ("steering_percent", c.c_float),
        ("ffb_strength", c.c_float), ("car_ffb_multiplier", c.c_float),
        ("water_temperature_percent", c.c_float),
        ("water_pressure_bar", c.c_float), ("fuel_pressure_bar", c.c_float),
        ("water_temperature_c", c.c_int8), ("air_temperature_c", c.c_int8),
        ("oil_temperature_c", c.c_float), ("oil_pressure_bar", c.c_float),
        ("exhaust_temperature_c", c.c_float),
        ("g_forces_x", c.c_float), ("g_forces_y", c.c_float),
        ("g_forces_z", c.c_float),
        ("turbo_boost", c.c_float), ("turbo_boost_level", c.c_float),
        ("turbo_boost_perc", c.c_float),
        ("steer_degrees", c.c_int32),
        ("current_km", c.c_float), ("total_km", c.c_uint32),
        ("total_driving_time_s", c.c_uint32),
        ("tod_h", c.c_int32), ("tod_m", c.c_int32), ("tod_s", c.c_int32),
        ("delta_time_ms", c.c_int32), ("current_lap_time_ms", c.c_int32),
        ("predicted_lap_time_ms", c.c_int32),
        ("fuel_liter_current_quantity", c.c_float),
        ("fuel_liter_current_quantity_percent", c.c_float),
        ("fuel_liter_per_km", c.c_float), ("km_per_fuel_liter", c.c_float),
        ("current_torque", c.c_float), ("current_bhp", c.c_int32),
        ("tyre_lf", c.c_uint8 * 256), ("tyre_rf", c.c_uint8 * 256),
        ("tyre_lr", c.c_uint8 * 256), ("tyre_rr", c.c_uint8 * 256),
        ("npos", c.c_float), ("kers_charge_perc", c.c_float),
        ("kers_current_perc", c.c_float), ("control_lock_time", c.c_float),
        ("car_damage", c.c_uint8 * 128),
        ("car_location", c.c_int32),
        ("pit_info", c.c_uint8 * 64),
        ("fuel_liter_used", c.c_float), ("fuel_liter_per_lap", c.c_float),
        ("laps_possible_with_fuel", c.c_float),
        ("battery_temperature", c.c_float), ("battery_voltage", c.c_float),
        ("instant_fuel_liter_per_km", c.c_float),
        ("instant_km_per_fuel_liter", c.c_float),
        ("gear_rpm_window", c.c_float),
        # --- SMEvoInstrumentation (128 octets) ---
        ("main_light_stage", c.c_int8), ("special_light_stage", c.c_int8),
        ("cockpit_light_stage", c.c_int8), ("wiper_level", c.c_int8),
        ("rain_lights", c.c_bool),
        ("direction_light_left", c.c_bool), ("direction_light_right", c.c_bool),
        ("flashing_lights", c.c_bool), ("warning_lights", c.c_bool),
        ("selected_display_index", c.c_int8),
        ("display_page_index", c.c_int8 * 16),
        ("are_headlights_visible", c.c_bool),
        ("_instr_pad", c.c_uint8 * 101),
        # --- blocs de 128 octets : limites + electronique ---
        ("instr_min", c.c_uint8 * 128), ("instr_max", c.c_uint8 * 128),
        ("electronics", c.c_uint8 * 128), ("elec_min", c.c_uint8 * 128),
        ("elec_max", c.c_uint8 * 128), ("elec_mod", c.c_uint8 * 128),
        # --- classement, tours, voiture ---
        ("total_lap_count", c.c_int32), ("current_pos", c.c_uint32),
        ("total_drivers", c.c_uint32),
        ("last_laptime_ms", c.c_int32), ("best_laptime_ms", c.c_int32),
        ("flag", c.c_int32), ("global_flag", c.c_int32),
        ("max_gears", c.c_uint32), ("engine_type", c.c_int32),
        ("has_kers", c.c_bool), ("is_last_lap", c.c_bool),
        ("performance_mode_name", c.c_char * 33),
        ("diff_coast_raw", c.c_float), ("diff_power_raw", c.c_float),
        ("race_cut_gained_time_ms", c.c_int32),
        ("distance_to_deadline", c.c_int32),
        ("race_cut_current_delta", c.c_float),
        ("session_state", c.c_uint8 * 256), ("timing_state", c.c_uint8 * 256),
        ("player_ping", c.c_int32), ("player_latency", c.c_int32),
        ("player_cpu", c.c_int32), ("player_cpu_avg", c.c_int32),
        ("player_qos", c.c_int32), ("player_qos_avg", c.c_int32),
        ("player_fps", c.c_int32), ("player_fps_avg", c.c_int32),
        ("driver_name", c.c_char * 33), ("driver_surname", c.c_char * 33),
        ("car_model_name", c.c_char * 33),
        ("is_in_pit_box", c.c_bool), ("is_in_pit_lane", c.c_bool),
        ("is_valid_lap", c.c_bool),
    ]


class StaticEvo(c.Structure):
    _fields_ = [
        ("sm_version", c.c_char * 15), ("ac_evo_version", c.c_char * 15),
        ("session", c.c_int32), ("session_name", c.c_char * 33),
        ("event_id", c.c_uint8), ("session_id", c.c_uint8),
        ("starting_grip", c.c_int32),
        ("ambient_c", c.c_float), ("ground_c", c.c_float),
        ("is_static_weather", c.c_bool), ("is_timed_race", c.c_bool),
        ("is_online", c.c_bool), ("number_of_sessions", c.c_int32),
        ("nation", c.c_char * 33),
        ("longitude", c.c_float), ("latitude", c.c_float),
        ("track", c.c_char * 33), ("track_configuration", c.c_char * 33),
        ("track_length_m", c.c_float),
    ]


# ---------------------------------------------------------------------------
# Lecture de la memoire partagee (via le lecteur de acevo-sdk, Windows only)
# ---------------------------------------------------------------------------
class Source:
    def __init__(self):
        from acevo import (RegionReader, PHYSICS_SHM_SIZE, GRAPHICS_SHM_SIZE,
                           STATIC_SHM_SIZE)
        self.phys = RegionReader("acevo_pmf_physics", PHYSICS_SHM_SIZE)
        self.gfx = RegionReader("acevo_pmf_graphics", GRAPHICS_SHM_SIZE)
        self.stat = RegionReader("acevo_pmf_static", STATIC_SHM_SIZE)
        self.phys_ok = self.gfx_ok = self.stat_ok = False
        self.static = None
        self.static_at = 0.0
        self.next_try = 0.0

    def read(self):
        """Retourne (physics_dict, GraphicsEvo, StaticEvo|None) ou None."""
        from acevo import decode_physics
        now = time.time()
        if not (self.phys_ok and self.gfx_ok):
            if now < self.next_try:
                return None
            self.next_try = now + 0.5
            if not self.phys_ok:
                self.phys_ok = self.phys.open()
            if not self.gfx_ok:
                self.gfx_ok = self.gfx.open()
            if not (self.phys_ok and self.gfx_ok):
                return None
        if now - self.static_at > 2.0:  # la page statique change rarement
            self.static_at = now
            if not self.stat_ok:
                self.stat_ok = self.stat.open()
            if self.stat_ok:
                try:
                    self.static = StaticEvo.from_buffer_copy(
                        self.stat.read_raw()[: c.sizeof(StaticEvo)])
                except Exception:
                    pass
        phys = decode_physics(self.phys.read_raw())
        gfx = GraphicsEvo.from_buffer_copy(
            self.gfx.read_raw()[: c.sizeof(GraphicsEvo)])
        return phys, gfx, self.static


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------
def convert_gear(raw):
    """Convention AC : 0 = marche arriere, 1 = point mort, 2 = 1ere..."""
    if raw == 0:
        return -1
    if raw == 1:
        return 0
    return raw - 1


def frac(x):
    """Pourcentage 0..1 ou 0..100 -> 0..1."""
    x = float(x)
    if x > 1.5:
        x /= 100.0
    return max(0.0, min(1.0, x))


def clean(raw):
    """Texte ASCII imprimable, sinon chaine vide (layout non confirme)."""
    try:
        s = raw.decode("latin-1").strip()
    except Exception:
        return ""
    return s if re.fullmatch(r"[\w .\-+/()&']{1,40}", s) else ""


def pretty(s):
    s = re.sub(r"^(ks|ace|acevo)_", "", s, flags=re.I)
    return s.replace("_", " ").strip().upper()


def level(b):
    """Octet signe -> niveau d'aide (TC, ABS) ou None si incoherent."""
    v = b if b < 128 else b - 256
    return v if 0 <= v <= 20 else None


def plausible(x, lo, hi):
    return x if lo <= x <= hi else None


# ---------------------------------------------------------------------------
# Format du serveur ETS2 (plugin Macro Deck)
# ---------------------------------------------------------------------------
def build_payload(phys, gfx):
    gear = convert_gear(int(phys.get("gear", 1)))
    speed = float(gfx.display_speed_kmh)
    max_rpm = float(phys.get("current_max_rpm") or 8000)
    fuel_pct = float(gfx.fuel_liter_current_quantity_percent)
    fuel_l = float(gfx.fuel_liter_current_quantity)
    low = gfx.main_light_stage >= 1
    high = gfx.main_light_stage >= 2
    left = bool(gfx.direction_light_left)
    right = bool(gfx.direction_light_right)
    handbrake = gfx.handbrake_percent > 0.5
    fuel_ratio = fuel_pct / 100.0 if fuel_pct > 1.0 else fuel_pct
    capacity = fuel_l / fuel_ratio if fuel_ratio > 0.001 else 0.0

    return {
        "game": {
            "connected": True, "paused": gfx.status == 3,
            "gameName": "ETS2", "version": "1.0", "telemetryPluginVersion": "1",
        },
        "truck": {
            "id": "acevo", "make": "AC Evo", "model": "Car",
            "speed": speed,
            "cruiseControlOn": False, "cruiseControlSpeed": 0.0,
            "gear": gear, "displayedGear": gear,
            "engineRpm": float(gfx.rpm), "engineRpmMax": max_rpm,
            "fuel": fuel_l, "fuelCapacity": capacity,
            "fuelWarningOn": fuel_ratio < 0.1,
            "engineOn": bool(gfx.is_engine_running),
            "electricOn": bool(gfx.is_ignition_on),
            "parkBrakeOn": handbrake,
            "userThrottle": float(gfx.gas_percent),
            "userBrake": float(gfx.brake_percent),
            "userClutch": float(gfx.clutch_percent),
            "lightsBeamLowOn": low, "lightsBeamHighOn": high,
            "lightsParkingOn": False,
            "blinkerLeftOn": left, "blinkerRightOn": right,
            "blinkerLeftActive": left, "blinkerRightActive": right,
            "lightsBrakeOn": gfx.brake_percent > 0.05,
            "lightsReverseOn": gear == -1,
            "wipersOn": gfx.wiper_level > 0,
        },
        "navigation": {"speedLimit": 0, "estimatedDistance": 0,
                       "estimatedTime": "0001-01-01T00:00:00Z"},
        "trailer": {"attached": False},
        "job": {},
    }


DISCONNECTED = {
    "game": {"connected": False, "paused": False, "gameName": None},
    "truck": {}, "trailer": {}, "navigation": {}, "job": {},
}


# ---------------------------------------------------------------------------
# Format du tableau de bord
# ---------------------------------------------------------------------------
def build_dash(phys, gfx, st):
    gear = convert_gear(int(phys.get("gear", 1)))
    max_rpm = float(phys.get("current_max_rpm") or 0) or 8000.0
    fuel_l = float(gfx.fuel_liter_current_quantity)
    fuel_pct = frac(gfx.fuel_liter_current_quantity_percent)
    elec = bytes(gfx.electronics[:4])
    bb = float(phys.get("brake_bias") or 0)
    if 0 < bb < 1.5:
        bb *= 100.0
    car = pretty(clean(gfx.car_model_name))
    track = cfg = ""
    if st is not None:
        track = pretty(clean(st.track))
        cfg = pretty(clean(st.track_configuration))
    laps_left = float(gfx.laps_possible_with_fuel)
    return {
        "c": True, "st": int(gfx.status),
        "v": float(gfx.display_speed_kmh), "r": float(gfx.rpm),
        "rm": max_rpm, "g": gear,
        "gas": frac(gfx.gas_percent), "brk": frac(gfx.brake_percent),
        "clu": frac(gfx.clutch_percent), "hb": frac(gfx.handbrake_percent),
        "fuel": fuel_l, "fp": fuel_pct,
        "fpl": float(gfx.fuel_liter_per_lap),
        "laps": laps_left if 0 < laps_left < 999 else 0.0,
        "low": gfx.main_light_stage >= 1, "high": gfx.main_light_stage >= 2,
        "L": bool(gfx.direction_light_left),
        "R": bool(gfx.direction_light_right),
        "haz": bool(gfx.warning_lights),
        "pit": bool(phys.get("pit_limiter_on")),
        "pitlane": bool(gfx.is_in_pit_lane),
        "tc": bool(gfx.tc_active), "abs": bool(gfx.abs_active),
        "esc": bool(gfx.esc_active),
        "lim": bool(gfx.is_rpm_limiter_on), "up": bool(gfx.is_change_up_rpm),
        "run": bool(gfx.is_engine_running),
        "wt": plausible(float(gfx.water_temperature_c), -20, 200),
        "ot": plausible(float(gfx.oil_temperature_c), -20, 250),
        "op": plausible(float(gfx.oil_pressure_bar), 0, 20),
        "boost": plausible(float(gfx.turbo_boost), -2, 10),
        "lap": int(gfx.current_lap_time_ms), "last": int(gfx.last_laptime_ms),
        "best": int(gfx.best_laptime_ms), "delta": int(gfx.delta_time_ms),
        "valid": bool(gfx.is_valid_lap),
        "pos": int(gfx.current_pos), "nd": int(gfx.total_drivers),
        "tcl": level(elec[0]), "absl": level(elec[2]),
        "bb": plausible(bb, 20, 90),
        "car": car, "track": track, "cfg": cfg,
    }


DASH_OFF = json.dumps({"c": False}).encode()
state = {"payload": DISCONNECTED, "dash": DASH_OFF}


def poll_loop(source, debug):
    period = 1.0 / POLL_HZ
    nxt = time.perf_counter()
    last_log = 0.0
    while True:
        try:
            res = source.read()
            if res is None:
                state["payload"] = DISCONNECTED
                state["dash"] = DASH_OFF
            else:
                phys, gfx, st = res
                state["payload"] = build_payload(phys, gfx)
                dash = build_dash(phys, gfx, st)
                state["dash"] = json.dumps(dash).encode()
                if debug and time.time() - last_log > 0.5:
                    last_log = time.time()
                    t = state["payload"]["truck"]
                    print(f"kmh={t['speed']:.0f} rpm={t['engineRpm']:.0f}/"
                          f"{t['engineRpmMax']:.0f} gear={t['gear']} "
                          f"fuel={dash['fuel']:.1f}L "
                          f"low={dash['low']} high={dash['high']} "
                          f"L={dash['L']} R={dash['R']} haz={dash['haz']} "
                          f"hb={dash['hb']:.2f} | car='{dash['car']}' "
                          f"track='{dash['track']}' lap={dash['lap']} "
                          f"best={dash['best']} tc={dash['tcl']} "
                          f"abs={dash['absl']} wt={dash['wt']} ot={dash['ot']}")
        except Exception as exc:  # le jeu se ferme, memoire invalide...
            state["payload"] = DISCONNECTED
            state["dash"] = DASH_OFF
            if debug:
                print("erreur lecture:", exc)
        nxt += period
        delay = nxt - time.perf_counter()
        if delay > 0:
            time.sleep(delay)
        else:
            nxt = time.perf_counter()


# ---------------------------------------------------------------------------
# Serveur HTTP
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # connexions persistantes

    def _send(self, body, ctype, code=200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")
        if path in ("/api/ets2/telemetry", ""):
            self._send(json.dumps(state["payload"]).encode(),
                       "application/json")
        elif path == "/api/dash":
            self._send(state["dash"], "application/json")
        elif path == "/dashboard":
            try:
                with open(os.path.join(HERE, "dashboard.html"), "rb") as f:
                    self._send(f.read(), "text/html; charset=utf-8")
            except OSError:
                self._send("dashboard.html introuvable : mets-le dans le "
                           "meme dossier que acevo_bridge.py".encode(),
                           "text/plain; charset=utf-8", 404)
        elif path == "/stream":
            self._stream()
        else:
            self.send_error(404)

    do_POST = do_GET

    def _stream(self):
        """Flux SSE : un message toutes les 1/60 s (sert aussi de heartbeat)."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        try:
            while True:
                self.wfile.write(b"data: " + state["dash"] + b"\n\n")
                self.wfile.flush()
                time.sleep(1.0 / STREAM_HZ)
        except OSError:
            pass

    def log_message(self, *a):  # silence
        pass


def serve():
    """Ecoute en IPv4 et IPv6 (localhost peut etre resolu en ::1), local only."""
    class V6Server(ThreadingHTTPServer):
        address_family = socket.AF_INET6

    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    try:
        server6 = V6Server(("::1", PORT), Handler)
        threading.Thread(target=server6.serve_forever, daemon=True).start()
    except OSError:
        pass  # IPv6 indisponible : IPv4 seul suffit
    return server


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    if sys.platform != "win32":
        sys.exit("Ce script doit tourner sur Windows (memoire partagee AC Evo).")

    threading.Thread(target=poll_loop, args=(Source(), args.debug),
                     daemon=True).start()
    server = serve()
    print(f"Tableau de bord : http://localhost:{PORT}/dashboard")
    print(f"Apercu sans jeu : http://localhost:{PORT}/dashboard?demo")
    print(f"Plugin Macro Deck : http://localhost:{PORT}/api/ets2/telemetry")
    print("Lance AC Evo (en session). Ctrl+C pour quitter.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
