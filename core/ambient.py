"""Pilotage des bandeaux Robobloq / DX Light en USB HID.

Le bandeau expose deux protocoles :
- RB : commandes courtes (brightness, effet, section) ;
- SC : couleur LED par LED pour les effets dynamiques.

Le module est independant du jeu : il lit l'etat commun de core.pump et
calcule les couleurs (clignotants gauche/droite, regime moteur, drapeaux).
"""
import json
import logging
import threading
import time

from core import app_settings

log = logging.getLogger("idash.ambient")
try:
    import hid
    HID_AVAILABLE = True
except Exception:  # pragma: no cover - depend de la machine
    hid = None
    HID_AVAILABLE = False
try:
    import serial
    from serial.tools import list_ports
    SERIAL_AVAILABLE = True
except Exception:  # pragma: no cover - depend de la machine
    serial = None
    list_ports = None
    SERIAL_AVAILABLE = False

VID = 0x1A86
PID = 0xFE07
ACTION_SYNC_SCREEN = 0x80
ACTION_READ_INFO = 0x82
ACTION_SECTION = 0x86
ACTION_BRIGHTNESS = 0x87
ACTION_OFF = 0x97

_lock = threading.Lock()
_thread = None
_stop = threading.Event()
_device = None
_serial = None
_transport = ""
_port = ""
_count = 0
_error = ""
_test = None
_test_until = 0.0
_last_dash = {}


def _checksum(data):
    return sum(data) & 0xFF


def _rb(action, payload=b""):
    sid = int(time.monotonic() * 1000) & 0xFF or 1
    packet = bytearray(b"RB")
    packet.append(2 + 1 + 1 + 1 + len(payload) + 1)
    packet.append(sid)
    packet.append(action)
    packet.extend(payload)
    packet.append(_checksum(packet))
    return bytes(packet)


def _sc(colors):
    sid = int(time.monotonic() * 1000) & 0xFF or 1
    data = bytearray()
    for index, (r, g, b) in enumerate(colors):
        data.extend((index & 0xFF, r & 0xFF, g & 0xFF, b & 0xFF,
                     index & 0xFF))
    total = 7 + len(data)
    packet = bytearray(b"SC")
    packet.append((total >> 8) & 0xFF)
    packet.append(total & 0xFF)
    packet.append(sid)
    packet.append(ACTION_SYNC_SCREEN)
    packet.extend(data)
    packet.append(_checksum(packet))
    return bytes(packet)


def _chunks(packet):
    return [packet[i:i + 64] for i in range(0, len(packet), 64)]


def _write(packet):
    if _device is None and _serial is None:
        return False
    for i, chunk in enumerate(_chunks(packet)):
        if i:
            time.sleep(0.003)
        try:
            if _serial is not None:
                _serial.write(chunk)
                _serial.flush()
            else:
                _device.write([0x00] + list(chunk))
        except Exception as exc:
            global _error
            _error = str(exc)
            _close()
            return False
    return True


def _close():
    global _device, _serial, _transport, _port
    if _device is not None:
        try:
            _device.close()
        except Exception:
            pass
    if _serial is not None:
        try:
            _serial.close()
        except Exception:
            pass
    _device = None
    _serial = None
    _transport = ""
    _port = ""


def _read_info():
    global _count, _error
    if _device is None and _serial is None:
        return
    if not _write(_rb(ACTION_READ_INFO)):
        return
    time.sleep(0.2)
    for attempt in range(3):
        try:
            if _serial is not None:
                data = list(_serial.read(256))
            else:
                data = _device.read(256, 500)
        except Exception:
            data = []
        if data and len(data) > 20 and data[20] > 0:
            _count = min(254, int(data[20]))
            log.info("bandeau ambient: %s LED", _count)
            break
        time.sleep(0.1)
    _error = ""


def _hid_candidates():
    try:
        found = hid.enumerate(VID, PID)
    except Exception as exc:
        global _error
        _error = "HID: " + str(exc)
        found = []
    if not found:
        try:
            found = [d for d in (hid.enumerate() or [])
                     if d.get("vendor_id") == VID]
        except Exception:
            found = []
    return found or []


def _serial_candidates():
    if not SERIAL_AVAILABLE:
        return []
    try:
        ports = list(list_ports.comports())
    except Exception:
        return []
    found = []
    for port in ports:
        vid = getattr(port, "vid", None)
        desc = ((getattr(port, "description", "") or "") + " " +
                (getattr(port, "product", "") or ""))
        if vid == VID or "robobloq" in desc.lower() or "dx light" in desc.lower():
            found.append(port.device)
    return found


def _connect():
    global _device, _serial, _transport, _port, _error, _count
    _error = ""
    last = ""
    if HID_AVAILABLE:
        candidates = _hid_candidates()
        preferred = [d for d in candidates
                     if (d.get("usage_page") or 0) >= 0xFF00 or
                     d.get("interface_number") == 0 or
                     d.get("product_id") == PID]
        ordered = preferred + [d for d in candidates if d not in preferred]
        for info in ordered:
            try:
                device = hid.device()
                try:
                    device.open_path(info["path"])
                except Exception:
                    device.open(VID, PID)
                device.set_nonblocking(1)
                _device = device
                _transport = "hid"
                _port = str(info.get("path", ""))
                _count = 0
                _read_info()
                if _device is not None:
                    return True
            except Exception as exc:
                last = "HID: " + str(exc)
                _close()
    if SERIAL_AVAILABLE:
        for port in _serial_candidates():
            try:
                ser = serial.Serial(port, 115200, timeout=0.2,
                                    write_timeout=0.5)
                _serial = ser
                _transport = "serial"
                _port = port
                _count = 0
                _read_info()
                if _serial is not None:
                    return True
            except Exception as exc:
                last = "Série " + port + ": " + str(exc)
                _close()
    if last:
        _error = last
    elif HID_AVAILABLE and _hid_candidates():
        _error = "Bandeau HID trouvé mais ouverture impossible"
    elif _serial_candidates():
        _error = "Port série trouvé mais ouverture impossible"
    else:
        _error = "Bandeau introuvable (USB HID ou port série)"
    return False


def _color(value, default=(0, 0, 0)):
    if not isinstance(value, str):
        return default
    value = value.strip().lstrip("#")
    if len(value) != 6:
        return default
    try:
        return (int(value[0:2], 16), int(value[2:4], 16),
                int(value[4:6], 16))
    except ValueError:
        return default


def _scale(color, brightness):
    return tuple(max(0, min(255, int(c * brightness))) for c in color)


def _flag_color(flag):
    flag = (flag or "").lower()
    if "double" in flag or "yellow" in flag:
        return (255, 190, 0)
    if "red" in flag:
        return (255, 0, 0)
    if "blue" in flag:
        return (0, 80, 255)
    if "white" in flag:
        return (255, 255, 255)
    if "green" in flag:
        return (0, 255, 60)
    if "check" in flag:
        return (255, 255, 255)
    if "black" in flag:
        return (255, 120, 0)
    return None


def _render(dash, cfg, count):
    idle = _scale(_color(cfg.get("idle_color")), cfg["brightness"])
    leds = [idle] * count
    if not dash or not dash.get("c"):
        return leds

    rpm = float(dash.get("r") or 0)
    max_rpm = float(dash.get("rm") or 0)
    if cfg.get("rpm") and max_rpm > 0:
        frac = max(0.0, min(1.0, rpm / max_rpm))
        for i in range(count):
            pos = (i + 1) / count
            if pos <= frac:
                if pos < 0.6:
                    color = (0, 220, 70)
                elif pos < 0.85:
                    color = (255, 190, 0)
                else:
                    color = (255, 30, 20)
                leds[i] = _scale(color, cfg["brightness"])

    now = time.monotonic()
    flash = (now * 2.5) % 1.0 < 0.5
    left = bool(dash.get("L")) or bool(dash.get("haz"))
    right = bool(dash.get("R")) or bool(dash.get("haz"))
    if cfg.get("swap"):
        left, right = right, left
    if cfg.get("turns", True) and flash and (left or right):
        split = int(round(count * cfg.get("split", 0.5)))
        amber = _scale(_color(cfg.get("turn_color"), (255, 122, 0)),
                       cfg["brightness"])
        for i in range(count):
            if i < split and left:
                leds[i] = amber
            elif i >= split and right:
                leds[i] = amber

    if cfg.get("flags"):
        color = _flag_color(dash.get("flag"))
        if color and flash:
            leds = [_scale(color, cfg["brightness"])] * count

    if cfg.get("brake") and float(dash.get("brk") or 0) > 0.5:
        red = _scale((255, 0, 0), cfg["brightness"])
        leds = [red] * count

    return leds


def _dash():
    try:
        from core import pump
        raw = pump.STATE.get("dash") or b"{}"
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


def _loop():
    global _error, _last_dash, _test
    while not _stop.is_set():
        cfg = app_settings.ambient()
        if not cfg["enabled"]:
            if _device is not None:
                _write(_rb(ACTION_OFF))
                _close()
            _stop.wait(0.25)
            continue
        if _device is None and not _connect():
            _stop.wait(1.0)
            continue
        count = cfg.get("led_count") or _count or 60
        count = max(1, min(512, int(count)))
        dash = _dash()
        _last_dash = dash
        test = _test
        if test and time.monotonic() < _test_until:
            dash = dict(dash)
            if test == "left":
                dash.update({"c": True, "L": True, "R": False, "haz": False,
                             "r": 0, "rm": 0, "flag": ""})
            elif test == "right":
                dash.update({"c": True, "L": False, "R": True, "haz": False,
                             "r": 0, "rm": 0, "flag": ""})
            elif test == "rpm":
                dash.update({"c": True, "L": False, "R": False, "haz": False,
                             "r": 0.8 * 7000, "rm": 7000, "flag": ""})
            elif test == "flag":
                dash.update({"c": True, "L": False, "R": False, "haz": False,
                             "r": 0, "rm": 0, "flag": "yellow"})
        elif test:
            _test = None
        leds = _render(dash, cfg, count)
        _write(_sc(leds))
        _stop.wait(1.0 / max(5, cfg.get("fps", 20)))


def start():
    global _thread
    with _lock:
        if _thread is not None and _thread.is_alive():
            return
        _stop.clear()
        _thread = threading.Thread(target=_loop, name="ambient", daemon=True)
        _thread.start()


def stop():
    _stop.set()
    _close()


def restart():
    stop()
    time.sleep(0.05)
    start()


def test(kind="left", seconds=3.0):
    global _test, _test_until
    _test = kind if kind in ("left", "right", "rpm", "flag") else None
    _test_until = time.monotonic() + max(1.0, min(10.0, seconds))
    start()


def diagnose():
    """Ouvre chaque interface HID et rapporte l'erreur exacte."""
    result = {"hid": [], "serial": []}
    if HID_AVAILABLE:
        try:
            devices = hid.enumerate(VID, PID) or []
        except Exception as exc:
            result["hid_error"] = str(exc)
            devices = []
        for info in devices:
            item = {
                "path": str(info.get("path", "")),
                "interface": info.get("interface_number"),
                "usage_page": info.get("usage_page"),
                "usage": info.get("usage"),
                "product": info.get("product_string"),
            }
            try:
                dev = hid.device()
                try:
                    dev.open_path(info["path"])
                except Exception:
                    dev.open(VID, PID)
                dev.set_nonblocking(1)
                item["opened"] = True
                try:
                    dev.close()
                except Exception:
                    pass
            except Exception as exc:
                item["opened"] = False
                item["open_error"] = str(exc)
            result["hid"].append(item)
    if SERIAL_AVAILABLE:
        for port in _serial_candidates():
            item = {"port": port}
            try:
                ser = serial.Serial(port, 115200, timeout=0.2,
                                    write_timeout=0.5)
                item["opened"] = True
                ser.close()
            except Exception as exc:
                item["opened"] = False
                item["open_error"] = str(exc)
            result["serial"].append(item)
    return result


def status():
    hid_list = []
    if HID_AVAILABLE:
        try:
            for d in (hid.enumerate() or []):
                if d.get("vendor_id") == VID:
                    hid_list.append({
                        "vendor_id": d.get("vendor_id"),
                        "product_id": d.get("product_id"),
                        "interface": d.get("interface_number"),
                        "product": d.get("product_string"),
                    })
        except Exception:
            pass
    return {
        "available": HID_AVAILABLE or SERIAL_AVAILABLE,
        "hid": HID_AVAILABLE,
        "serial": SERIAL_AVAILABLE,
        "connected": _device is not None or _serial is not None,
        "transport": _transport,
        "port": _port,
        "led_count": _count,
        "error": _error,
        "hid_devices": hid_list,
        "serial_ports": _serial_candidates(),
        "config": app_settings.ambient(),
        "dash": _last_dash,
    }
