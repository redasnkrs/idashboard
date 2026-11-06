"""Import de dashboards SimHub (``.simhubdash``, ``.djson``) vers le Studio.

Le format SimHub est un JSON imbrique : un document contient des ecrans, des
items, et des widgets qui referencent d'autres documents ``.djson``. On
aplatit cette arborescence en widgets idash, en copiant les images utiles dans
``custom/imports/<token>/``.
"""
import base64
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

from core import studio
from core.studio import CANVAS_H, CANVAS_W, CUSTOM_DIR

IMPORTS_DIR = CUSTOM_DIR / "imports"
MAX_ARCHIVE = 64 * 1024 * 1024
MAX_FILE = 32 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024
MAX_FILES = 4000
MAX_DEPTH = 8
MAX_WIDGETS = studio.MAX_WIDGETS

_SAFE_TOKEN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_SAFE_FILE = re.compile(r"^[A-Za-z0-9._-]{1,160}$")
_PROP = re.compile(r"\[([^\]]+)\]")
_NUMBER = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)")
_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"}

_PROPERTIES = {
    "speedkmh": ("v", "int", "auto"),
    "speedlocal": ("v", "int", "auto"),
    "filteredspeedlocal": ("v", "int", "auto"),
    "filteredspeed": ("v", "int", "auto"),
    "speedmph": ("v", "int", "none"),
    "rpms": ("r", "int", "none"),
    "rpm": ("r", "int", "none"),
    "filteredrpms": ("r", "int", "none"),
    "maxrpm": ("rm", "int", "none"),
    "carsettings_redlinerpm": ("rm", "int", "none"),
    "gear": ("g", "gear", "none"),
    "throttle": ("gas", "int", "percent"),
    "brake": ("brk", "int", "percent"),
    "clutch": ("clu", "int", "percent"),
    "handbrake": ("hb", "int", "percent"),
    "fuel": ("fuel", "float1", "l"),
    "fuel_litersperlap": ("fpl", "float2", "l"),
    "fuel_lastlapconsumption": ("fpl", "float2", "l"),
    "fuel_remaininglaps": ("laps", "float1", "none"),
    "fuel_percent": ("fp", "float2", "percent"),
    "tclevel": ("tcl", "int", "none"),
    "abslevel": ("absl", "int", "none"),
    "brakebias": ("bb", "float1", "none"),
    "watertemperature": ("wt", "float1", "c"),
    "oiltemperature": ("ot", "float1", "c"),
    "airtemperature": ("at", "float1", "c"),
    "ambienttemperature": ("at", "float1", "c"),
    "oilpressure": ("op", "float2", "bar"),
    "turbolevel": ("boost", "float2", "bar"),
    "turboboost": ("boost", "float2", "bar"),
    "computedturbopercent": ("boost", "float2", "bar"),
    "position": ("pos", "int", "none"),
    "currentlaptime": ("lap", "time", "none"),
    "lastlaptime": ("last", "time", "none"),
    "bestlaptime": ("best", "time", "none"),
    "sessionbest": ("best", "time", "none"),
    "sessionbestlivedeltaseconds": ("delta", "delta", "none"),
    "previouslap_00_deltatobest": ("delta", "delta", "none"),
    "normalizedcarposition": ("npos", "float2", "percent"),
    "is_in_pitlane": ("pitlane", "int", "none"),
    "isinpitlane": ("pitlane", "int", "none"),
    "sessiontypename": ("mode", "text", "none"),
    "carmodel": ("car", "text", "none"),
    "track": ("track", "text", "none"),
}

_BUILTINS = {
    "GearText": {"field": "g", "format": "gear"},
    "SpeedText": {"field": "v", "format": "int", "unit": "auto"},
    "RPMText": {"field": "r", "format": "int"},
    "FuelText": {"field": "fuel", "format": "float1", "unit": "l"},
    "FuelLiterPerLapsText": {"field": "fpl", "format": "float2", "unit": "l"},
    "FuelRemainingLapsText": {"field": "laps", "format": "float1"},
    "RacePositionText": {"field": "pos", "format": "int"},
    "BestLapTime": {"field": "best", "format": "time"},
    "LastLapTime": {"field": "last", "format": "time"},
    "CurrentLapTime": {"field": "lap", "format": "time"},
    "TimeText": {"clock": True},
    "TyreFrontLeftTempText": None,
    "TyreFrontRightTempText": None,
    "TyreBackLeftTempText": None,
    "TyreBackRightTempText": None,
    "RadarItem": None,
    "LeaderboardOpponentPositionText": None,
    "LeaderboardOpponentNameText": None,
    "LeaderboardOpponentBestLap": None,
    "LeaderboardOpponentDelta": None,
    "LeaderboardOpponentGap": None,
    "LeaderboardOpponentCarModelText": None,
    "LeaderboardOpponentCarClassText": None,
    "LapText": None,
}

_FONT_WEIGHT = {
    "thin": 200, "light": 300, "normal": 400, "regular": 400,
    "medium": 500, "semibold": 600, "semi bold": 600,
    "bold": 700, "extrabold": 800, "extra bold": 800,
    "heavy": 900, "black": 900,
}


def _values(value):
    if isinstance(value, dict):
        value = value.get("$values")
    return value if isinstance(value, list) else []


def _num(value, default=0.0):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return float(value)


def _text(value, limit=400):
    return value[:limit] if isinstance(value, str) else ""


def _typename(item):
    raw = _text(item.get("$type"), 300)
    return raw.split(",", 1)[0].rsplit(".", 1)[-1]


def _decode_base64(value):
    if not isinstance(value, str):
        raise ValueError("image sans donnees")
    raw = "".join(value.split())
    if "," in raw and raw.lower().startswith("data:"):
        raw = raw.split(",", 1)[1]
    raw += "=" * (-len(raw) % 4)
    return base64.b64decode(raw, validate=False)


def _image_meta(name, ext, data):
    ext = (ext or "").lower()
    if not ext.startswith("."):
        ext = "." + ext if ext else ".png"
    if ext not in _IMAGE_EXT:
        ext = ".png"
    return name or "image", ext, data


def _color(value):
    """Convertit #AARRGGBB SimHub en (hex #RRGGBB, alpha)."""
    if not isinstance(value, str):
        return None, 0
    raw = value.strip().lstrip("#")
    if len(raw) == 8:
        alpha = int(raw[:2], 16)
        rgb = raw[2:]
    elif len(raw) == 6:
        alpha = 255
        rgb = raw
    else:
        return None, 0
    try:
        int(rgb, 16)
    except ValueError:
        return None, 0
    return "#" + rgb.lower(), alpha


def _paint(value):
    color, alpha = _color(value)
    return color if color and alpha > 0 else None


def _alpha(value):
    return _color(value)[1] / 255.0


def _border(item):
    style = item.get("BorderStyle")
    if not isinstance(style, dict):
        style = {}
    color = _paint(style.get("BorderColor"))
    widths = [_num(style.get(k), 0) for k in (
        "AllBorders", "BorderTop", "BorderBottom", "BorderLeft", "BorderRight")]
    width = max(widths) if widths else 0
    if color is None or width <= 0:
        color = _paint(item.get("BorderColor"))
        width = max(_num(item.get(k), 0) for k in (
            "BorderTop", "BorderBottom", "BorderLeft", "BorderRight"))
    if color is None or width <= 0:
        return None, 0
    return color, max(1, min(40, round(width)))


def _radius(item):
    style = item.get("BorderStyle")
    if not isinstance(style, dict):
        style = {}
    value = style.get("AllCornerRadius")
    if isinstance(value, (int, float)):
        return max(0, min(200, int(value)))
    raw = _text(style.get("CornerRadius"), 80)
    match = _NUMBER.search(raw)
    return max(0, min(200, int(float(match.group(0))))) if match else 0


def _font_size(value, default=20):
    return max(6, min(300, round(_num(value, default))))


def _weight(value):
    return _FONT_WEIGHT.get(_text(value, 30).strip().lower(), 400)


def _align(value):
    return {0: "left", 1: "center", 2: "right", 3: "center"}.get(
        int(_num(value, 0)), "left")


def _formula(item, target):
    bindings = item.get("Bindings")
    if not isinstance(bindings, dict):
        return ""
    entry = bindings.get(target)
    if not isinstance(entry, dict):
        return ""
    formula = entry.get("Formula")
    if not isinstance(formula, dict):
        return ""
    return _text(formula.get("Expression"), 4000).strip()


def _prop_field(prop):
    prop = prop.strip().lower()
    if prop in _PROPERTIES:
        return _PROPERTIES[prop]
    last = prop.rsplit(".", 1)[-1]
    return _PROPERTIES.get(last)


def _formula_field(expression):
    expression = re.sub(r"\s+", "", expression or "")
    if not expression:
        return None
    while len(expression) > 2 and expression[0] == "(" and \
            expression[-1] == ")":
        expression = expression[1:-1]
    matches = list(_PROP.finditer(expression))
    if len(matches) != 1:
        found = []
        seen = set()
        for candidate in matches:
            info = _prop_field(candidate.group(1))
            if info is None or info[0] in seen:
                continue
            seen.add(info[0])
            found.append(info)
        if len(found) == 1:
            field, fmt, unit = found[0]
            return field, fmt, unit, 1.0, 0.0
        return None
    match = matches[0]
    info = _prop_field(match.group(1))
    if info is None:
        return None
    field, fmt, unit = info
    before = expression[:match.start()]
    after = expression[match.end():]
    scale, offset = 1.0, 0.0

    def number(raw):
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    if before and after:
        found = []
        seen = set()
        for candidate in _PROP.finditer(expression):
            item = _prop_field(candidate.group(1))
            if item is None or item[0] in seen:
                continue
            seen.add(item[0])
            found.append(item)
        if len(found) == 1:
            field, fmt, unit = found[0]
            return field, fmt, unit, 1.0, 0.0
        return None
    if not before and not after:
        pass
    elif not before and after.startswith("/"):
        value = number(after[1:])
        if value in (None, 0):
            return None
        scale = 1.0 / value
    elif not before and after.startswith("*"):
        value = number(after[1:])
        if value is None:
            return None
        scale = value
    elif not before and after[:1] in ("+", "-"):
        value = number(after[1:])
        if value is None:
            return None
        offset = value if after[0] == "+" else -value
    elif not after and before.endswith("-"):
        value = number(before[:-1])
        if value is None:
            return None
        scale, offset = -1.0, value
    elif not after and before.endswith("+"):
        value = number(before[:-1])
        if value is None:
            return None
        offset = value
    else:
        found = []
        seen = set()
        for candidate in _PROP.finditer(expression):
            info = _prop_field(candidate.group(1))
            if info is None or info[0] in seen:
                continue
            seen.add(info[0])
            found.append(info)
        if len(found) == 1:
            field, fmt, unit = found[0]
            return field, fmt, unit, 1.0, 0.0
        return None
    if field == "boost" and (abs(scale - 1.0) > 1e-9 or
                             abs(offset) > 1e-9):
        scale, offset = 1.0, 0.0
    return field, fmt, unit, scale, offset


def _iracing_visible(expression):
    compact = re.sub(r"\s+", "", expression or "").lower()
    if "currentgame" not in compact:
        return None
    match = re.match(
        r"if\(\[datacoreplugin\.currentgame\](<>|!=|=)'iracing',([^,]+),",
        compact)
    if match:
        is_not_iracing = match.group(1) in ("<>", "!=")
        branch = match.group(2)
        if branch in ("1", "true"):
            return is_not_iracing
        if branch in ("0", "false"):
            return not is_not_iracing
        return None
    if "if(" in compact:
        return None
    if re.search(r"\[datacoreplugin\.currentgame\](<>|!=)'iracing'", compact):
        return True
    if re.search(r"\[datacoreplugin\.currentgame\]='iracing'", compact):
        return False
    return None


def _area(item, base_w, base_h):
    return max(0.0, _num(item.get("Width"))) * \
        max(0.0, _num(item.get("Height"))) / \
        max(1.0, base_w * base_h)


class _Importer:
    def __init__(self, blob, filename, files):
        self.blob = blob
        self.filename = filename
        self.files = files
        self.token = self._token()
        self.widgets = []
        self.ids = set()
        self.docs = {}
        self.embedded = {}
        self.external = {}
        self.assets = {}
        self.warnings = []
        self._warned = set()
        self.skipped = 0
        self.hidden = 0
        self.missing = 0
        self.depth = 0
        self.screen = ""
        self.meta = {}
        self.fonts = set()

    def _token(self):
        digest = hashlib.sha1(self.blob).hexdigest()[:10]
        base = studio.slugify(Path(self.filename).stem)[:40] or "simhub"
        return "%s-%s" % (base, digest)

    def warn(self, message):
        if message not in self._warned:
            self._warned.add(message)
            self.warnings.append(message)

    def asset(self, name, ext, data):
        if not data:
            return ""
        key = (name.lower(), ext.lower(), hashlib.sha1(data).hexdigest())
        if key in self.assets:
            return self.assets[key]
        stem = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("._-")[:80]
        stem = stem or "image"
        ext = ext if ext.startswith(".") else "." + ext
        if ext.lower() not in _IMAGE_EXT:
            ext = ".png"
        filename = stem + ext.lower()
        digest = hashlib.sha1(data).hexdigest()[:8]
        path = IMPORTS_DIR / self.token / filename
        if path.exists() and path.read_bytes() != data:
            filename = "%s-%s%s" % (stem, digest, ext.lower())
            path = IMPORTS_DIR / self.token / filename
        if not _SAFE_FILE.match(filename):
            return ""
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_bytes(data)
            tmp.replace(path)
        url = "/custom/imports/%s/%s" % (self.token, filename)
        self.assets[key] = url
        return url

    def resolve_image(self, name):
        key = _text(name, 200).strip()
        if not key:
            return ""
        lower = key.lower()
        for candidate in (lower, lower.rsplit("/", 1)[-1]):
            if candidate in self.embedded:
                return self.embedded[candidate]
        stem = lower.rsplit(".", 1)[0]
        for candidate in (lower, stem, lower.rsplit("/", 1)[-1]):
            if candidate not in self.external:
                continue
            data = self.external[candidate]
            if isinstance(data, (bytes, bytearray)):
                shown = candidate if "." in candidate else candidate + ".png"
                ext = Path(shown).suffix or ".png"
                data = self.asset(Path(shown).stem, ext, bytes(data))
                self.external[candidate] = data
            return data
        self.warn("image introuvable: %s" % key)
        return ""

    def _index_assets(self):
        for name, data in self.files.items():
            ext = Path(name).suffix.lower()
            if ext not in _IMAGE_EXT:
                continue
            self.external.setdefault(name, data)
            self.external.setdefault(Path(name).stem.lower(), data)
            if name.endswith(".djson.png"):
                self.external.setdefault(name[:-len(".djson.png")], data)
        for path, data in list(self.files.items()):
            if not path.endswith(".ressources"):
                continue
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    for info in z.infolist()[:500]:
                        ext = Path(info.filename).suffix.lower()
                        if info.is_dir() or ext not in _IMAGE_EXT:
                            continue
                        if info.file_size > MAX_FILE:
                            continue
                        raw = z.read(info)
                        self.external.setdefault(
                            info.filename.replace("\\", "/").lower(), raw)
                        self.external.setdefault(
                            Path(info.filename).stem.lower(), raw)
            except (OSError, zipfile.BadZipFile):
                self.warn("ressources SimHub illisibles")

    def _index_embedded(self, doc):
        for image in _values(doc.get("Images")):
            if not isinstance(image, dict):
                continue
            name = _text(image.get("Name"), 200)
            if not name:
                continue
            try:
                raw = _decode_base64(image.get("Data"))
            except (ValueError, TypeError):
                continue
            name, ext, raw = _image_meta(name, image.get("Extension"), raw)
            url = self.asset(name, ext, raw)
            self.embedded[name.lower()] = url
            self.embedded[Path(name).stem.lower()] = url

    def _load_doc(self, path):
        key = path.lower()
        if key in self.docs:
            return self.docs[key]
        data = self.files.get(key)
        if data is None:
            return None
        try:
            doc = json.loads(data.decode("utf-8-sig"))
        except (UnicodeDecodeError, ValueError):
            return None
        if not isinstance(doc, dict):
            return None
        self.docs[key] = doc
        self._index_embedded(doc)
        return doc

    def _pick_screen(self, doc):
        screens = [s for s in _values(doc.get("Screens"))
                   if isinstance(s, dict)]
        if not screens:
            return None
        ref = doc.get("SelectedScreen")
        ref_id = ref.get("$ref") if isinstance(ref, dict) else None
        if ref_id is not None:
            for screen in screens:
                if str(screen.get("$id")) == str(ref_id):
                    return screen
        meta = doc.get("Metadata") or {}
        index = meta.get("MainPreviewIndex")
        if isinstance(index, int) and 0 <= index < len(screens):
            picked = screens[index]
            if not picked.get("IdleScreen"):
                return picked
        for screen in screens:
            if screen.get("InGameScreen") and not screen.get("IdleScreen"):
                return screen
        for screen in screens:
            if not screen.get("IdleScreen"):
                return screen
        return screens[0]

    def _visible(self, item, base_w, base_h):
        visible = item.get("Visible") is not False
        expression = _formula(item, "Visible")
        if not expression:
            return visible
        decided = _iracing_visible(expression)
        if decided is not None:
            return decided
        compact = re.sub(r"\s+", "", expression).lower()
        unit = re.search(r"speedlocalunit\]?[^=]*=[\"']?(kmh|mph)", compact)
        if unit:
            return unit.group(1) == "kmh"
        fill = _paint(item.get("BackgroundColor") or item.get("FillColor"))
        if fill and _area(item, base_w, base_h) >= .35:
            self.warn("calque plein ecran conditionnel ignore: %s"
                      % _text(item.get("Name"), 80))
            return False
        return visible

    def _add(self, kind, item, ctx, **extra):
        if len(self.widgets) >= MAX_WIDGETS:
            raise ValueError("trop de widgets (max %d)" % MAX_WIDGETS)
        name = _text(item.get("Name"), 80) or kind
        base = studio.slugify(name)[:48] or "widget"
        wid = base
        n = 2
        while wid in self.ids:
            wid = "%s-%d" % (base, n)
            n += 1
        self.ids.add(wid)
        x = ctx["x"] + _num(item.get("Left")) * ctx["sx"]
        y = ctx["y"] + _num(item.get("Top")) * ctx["sy"]
        w = max(8.0, _num(item.get("Width"), 8) * ctx["sx"])
        h = max(8.0, _num(item.get("Height"), 8) * ctx["sy"])
        rotation = _num(item.get("Rotation"))
        if item.get("UseRotation") is False:
            rotation = 0
        opacity = ctx["opacity"] * max(0.0, min(1.0, _num(
            item.get("Opacity"), 100) / 100.0))
        widget = {
            "id": wid, "type": kind,
            "x": round(x, 3), "y": round(y, 3),
            "w": round(w, 3), "h": round(h, 3),
            "visible": ctx["visible"], "opacity": round(opacity, 3),
            "rotation": round((ctx["rotation"] + rotation) % 360, 2),
        }
        widget.update(extra)
        self.widgets.append(widget)
        return widget

    def _shape(self, item, ctx, kind="rect"):
        fill = _paint(item.get("BackgroundColor"))
        stroke = None
        width = 1
        if kind == "circle":
            fill = _paint(item.get("FillColor"))
            stroke = _paint(item.get("EllipseColor"))
            width = max(1, min(40, round(_num(item.get("EllipseThickness"), 1))))
        else:
            stroke, width = _border(item)
        if fill is None and stroke is None:
            self.skipped += 1
            return None
        if kind == "circle" and fill and not stroke:
            stroke = None
        return self._add(
            "shape", item, ctx, shape=kind,
            fill=fill or "none", stroke=stroke or "none",
            strokeWidth=width, radius=_radius(item))

    def _text_style(self, item, ctx, color=None):
        font = _text(item.get("Font"), 80)
        if font:
            self.fonts.add(font)
        return {
            "font": font,
            "size": _font_size(item.get("FontSize")),
            "weight": _weight(item.get("FontWeight")),
            "align": _align(item.get("HorizontalAlignment")),
            "color": color or _paint(item.get("TextColor")) or "ivory",
        }

    def _static_text(self, item, ctx, text):
        style = self._text_style(item, ctx)
        return self._add("text", item, ctx, text=_text(text, 400), **style)

    def _value(self, item, ctx, field, fmt="int", unit="none", **extra):
        style = self._text_style(item, ctx,
                                 color=extra.pop("color", None))
        return self._add("value", item, ctx, field=field, format=fmt,
                         unit=unit, **style, **extra)

    def _builtin(self, item, ctx, kind, spec):
        if spec is None:
            self.warn("type SimHub non supporte: %s" % kind)
            self.skipped += 1
            return
        if spec.get("clock"):
            self._add("clock", item, ctx, size=_font_size(
                item.get("FontSize")), color=_paint(item.get("TextColor"))
                or "ivory", showDate=False, showTime=True, locale="en-US")
            return
        field = spec["field"]
        fmt = spec.get("format", "int")
        unit = spec.get("unit", "none")
        color = _paint(item.get("GearTextColor")) if kind == "GearText" else None
        self._value(item, ctx, field, fmt, unit,
                    color=color or _paint(item.get("TextColor")))

    def _text_item(self, item, ctx):
        expression = _formula(item, "Text")
        if expression:
            mapped = _formula_field(expression)
            if mapped:
                field, fmt, unit, scale, offset = mapped
                self._value(item, ctx, field, fmt, unit,
                            scale=scale, offset=offset)
                return
            self.warn("formule texte ignoree: %s" % _text(expression, 90))
        text = item.get("Text")
        if isinstance(text, str) and text.strip():
            if text.strip().lower() in ("mph", "km/h", "kmh"):
                self.skipped += 1
                return
            self._static_text(item, ctx, text)
        else:
            self.skipped += 1

    def _dial(self, item, ctx):
        expression = _formula(item, "Value")
        mapped = _formula_field(expression)
        if not mapped:
            self.warn("jauge sans propriete connue: %s"
                      % _text(item.get("Name"), 80))
            self.skipped += 1
            return
        field, fmt, _unit, scale, offset = mapped
        if abs(scale - 1.0) > 1e-9 and fmt == "int":
            fmt = "float1"
        maximum = _num(item.get("Maximum", item.get("MaxValue")), 100)
        minimum = _num(item.get("Minimum", item.get("MinValue")), 0)
        if field == "r":
            maximum = max(maximum, 10000)
            extra = {"maxField": "rm"}
        else:
            extra = {"maxField": "none"}
        self._add("gauge", item, ctx, field=field, min=minimum, max=maximum,
                  redline=.89, needle=True, showValue=True,
                  size=_font_size(item.get("FontSize"), 24),
                  valueSize=0, label="", format=fmt, scale=scale,
                  offset=offset, **extra)

    def _linear_gauge(self, item, ctx):
        expression = _formula(item, "Value")
        mapped = _formula_field(expression)
        if not mapped:
            self.skipped += 1
            self.warn("jauge lineaire ignoree: %s"
                      % _text(item.get("Name"), 80))
            return
        field, fmt, unit, scale, offset = mapped
        color = _paint(item.get("GaugeColor"))
        if color is None:
            name = _text(item.get("GaugeImage"), 80).lower()
            color = ("red" if "red" in name else "amber" if "yellow" in name
                     else "blue" if "blue" in name else "green")
        self._add("bar", item, ctx, field=field, min=0,
                  max=1 if field in ("tcl", "absl", "pitlane") else 100,
                  maxField="none", orientation="horizontal",
                  label="", showValue=False, format=fmt, unit=unit,
                  color=color or "amber", trackColor="off",
                  size=_font_size(item.get("FontSize"), 14),
                  labelSize=8, scale=scale, offset=offset)

    def _image(self, item, ctx, image_key="Image"):
        src = self.resolve_image(item.get(image_key))
        if not src:
            self.skipped += 1
            return
        self._add("image", item, ctx, src=src, fit="contain")

    def _widget(self, item, ctx, path):
        filename = _text(item.get("FileName"), 300)
        if not filename:
            self.skipped += 1
            return
        child_path = self._resolve_child(path, filename)
        if child_path is None:
            self.missing += 1
            self.warn("composant introuvable: %s" % filename)
            return
        if self.depth >= MAX_DEPTH:
            self.warn("profondeur maximale atteinte: %s" % filename)
            self.skipped += 1
            return
        child = self._load_doc(child_path)
        if child is None:
            self.missing += 1
            self.warn("composant illisible: %s" % filename)
            return
        screen = self._pick_screen(child)
        if screen is None:
            self.skipped += 1
            return
        base_w = max(1.0, _num(child.get("BaseWidth"), CANVAS_W))
        base_h = max(1.0, _num(child.get("BaseHeight"), CANVAS_H))
        width = max(1.0, _num(item.get("Width"), base_w))
        height = max(1.0, _num(item.get("Height"), base_h))
        child_ctx = {
            "x": ctx["x"] + _num(item.get("Left")) * ctx["sx"],
            "y": ctx["y"] + _num(item.get("Top")) * ctx["sy"],
            "sx": ctx["sx"] * width / base_w,
            "sy": ctx["sy"] * height / base_h,
            "rotation": ctx["rotation"] + (_num(item.get("Rotation"))
                                           if item.get("UseRotation") is not False
                                           else 0),
            "opacity": ctx["opacity"] * max(0.0, min(1.0, _num(
                item.get("Opacity"), 100) / 100.0)),
            "visible": ctx["visible"] and self._visible(
                item, base_w, base_h),
        }
        self.depth += 1
        try:
            self._items(_values(screen.get("Items")), child_ctx,
                        child_path, base_w, base_h)
        finally:
            self.depth -= 1

    def _resolve_child(self, path, filename):
        name = filename.replace("\\", "/").lstrip("/")
        parent = path.rsplit("/", 1)[0] if "/" in path else ""
        candidates = []
        if parent:
            candidates.append(parent + "/" + name)
        candidates.append(name)
        for candidate in candidates:
            key = candidate.lower()
            if key in self.files:
                return key
        return None

    def _items(self, items, ctx, path, base_w, base_h):
        for item in items:
            if not isinstance(item, dict):
                continue
            name = _text(item.get("Name"), 80)
            if name.startswith("_"):
                continue
            if not self._visible(item, base_w, base_h):
                self.hidden += 1
                continue
            kind = _typename(item)
            try:
                if kind == "Layer":
                    fill = _paint(item.get("BackgroundColor"))
                    if fill:
                        self._add("shape", item, ctx, shape="rect",
                                  fill=fill, stroke="none", strokeWidth=0,
                                  radius=_radius(item))
                    self._items(_values(item.get("Childrens")), ctx,
                                path, base_w, base_h)
                elif kind == "RectangleItem":
                    self._shape(item, ctx, "rect")
                elif kind == "EllipseItem":
                    self._shape(item, ctx, "circle")
                elif kind in ("ImageItem", "ToggleImageItem"):
                    key = "OnImage" if kind == "ToggleImageItem" else "Image"
                    self._image(item, ctx, key)
                elif kind == "TextItem":
                    self._text_item(item, ctx)
                elif kind == "WidgetItem":
                    self._widget(item, ctx, path)
                elif kind in ("DialGaugeItem", "CircularGaugeItem"):
                    self._dial(item, ctx)
                elif kind == "LinearGaugeItem":
                    self._linear_gauge(item, ctx)
                elif kind in ("GeneratedMapItem", "GeneratedStaticMapItem",
                              "MapItem"):
                    self._add("map", item, ctx, field="npos",
                              roadColor=_paint(item.get("TrackColor"))
                              or "dim", dotColor=_paint(item.get("CursorColor"))
                              or "amber", showDot=True)
                elif kind in _BUILTINS:
                    self._builtin(item, ctx, kind, _BUILTINS[kind])
                else:
                    self.warn("type SimHub non supporte: %s" % kind)
                    self.skipped += 1
            except (TypeError, ValueError, KeyError) as exc:
                self.warn("item ignore (%s): %s" % (name or kind, exc))
                self.skipped += 1

    def run(self, doc_path):
        doc = self._load_doc(doc_path)
        if doc is None:
            raise ValueError("dashboard SimHub illisible")
        screen = self._pick_screen(doc)
        if screen is None:
            raise ValueError("aucun ecran SimHub")
        self.screen = _text(screen.get("Name"), 80)
        self._index_assets()
        base_w = max(1.0, _num(doc.get("BaseWidth"), CANVAS_W))
        base_h = max(1.0, _num(doc.get("BaseHeight"), CANVAS_H))
        bg = _paint(doc.get("BackgroundColor")) or \
            _paint(screen.get("BackgroundColor")) or "ink"
        self.meta = doc.get("Metadata") if isinstance(
            doc.get("Metadata"), dict) else {}
        self._items(_values(screen.get("Items")), {
            "x": 0.0, "y": 0.0,
            "sx": CANVAS_W / base_w, "sy": CANVAS_H / base_h,
            "rotation": 0.0, "opacity": 1.0, "visible": True,
        }, doc_path, base_w, base_h)
        name = _text(self.meta.get("Title"), 80).strip() or \
            Path(doc_path).parent.name or Path(self.filename).stem
        description = _text(self.meta.get("Description"), 300).strip()
        tags = ["simhub"]
        author = _text(self.meta.get("Author"), 40).strip()
        if author:
            tags.append(author)
        payload = {
            "name": name,
            "description": description,
            "category": "custom",
            "game": "Assetto Corsa Evo",
            "game_id": "acevo",
            "order": 10,
            "tags": tags,
            "background": bg,
            "canvas": {"width": CANVAS_W, "height": CANVAS_H,
                       "grid": 16, "background": bg},
            "widgets": self.widgets,
        }
        layout = studio.validate_layout(payload)
        return layout, self.report(doc_path, doc)

    def report(self, doc_path, doc):
        screens = [_text(s.get("Name"), 80) for s in _values(
            doc.get("Screens")) if isinstance(s, dict)]
        return {
            "source": self.filename,
            "file": doc_path,
            "screen": self.screen,
            "screens": screens,
            "widgets": len(self.widgets),
            "assets": len(self.assets),
            "skipped": self.skipped,
            "hidden": self.hidden,
            "missing": self.missing,
            "fonts": sorted(self.fonts),
            "warnings": self.warnings[:40],
        }


def _main_doc(files, wanted=""):
    wanted = (wanted or "").strip().lower()
    candidates = []
    for path, data in files.items():
        if not path.endswith(".djson") or "_backups" in path:
            continue
        try:
            doc = json.loads(data.decode("utf-8-sig"))
        except (UnicodeDecodeError, ValueError):
            continue
        if not isinstance(doc, dict) or not _values(doc.get("Screens")):
            continue
        parts = path.split("/")
        stem = Path(path).stem.lower()
        parent = parts[-2].lower() if len(parts) > 1 else ""
        score = 0
        if wanted and (stem == wanted or parent == wanted):
            score += 100
        elif parent and stem == parent:
            score += 80
        if "main display" in stem:
            score += 35
        if "dashboard" in stem:
            score += 25
        if stem in ("new dashboard", "subscreen", "instructions",
                    "settings", "idle"):
            score -= 60
        meta = doc.get("Metadata") if isinstance(
            doc.get("Metadata"), dict) else {}
        if meta.get("Title"):
            score += 5
        total = sum(len(_values((s or {}).get("Items")))
                    for s in _values(doc.get("Screens"))
                    if isinstance(s, dict))
        score += min(total, 40)
        candidates.append((score, total, path))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1], -len(x[2])), reverse=True)
    return candidates[0][2]


def _read_zip(blob):
    files = {}
    try:
        archive = zipfile.ZipFile(io.BytesIO(blob))
    except zipfile.BadZipFile:
        raise ValueError("archive SimHub invalide")
    infos = [i for i in archive.infolist() if not i.is_dir()]
    if len(infos) > MAX_FILES:
        raise ValueError("trop de fichiers dans l'archive")
    total = 0
    for info in infos:
        if info.flag_bits & 0x1:
            raise ValueError("archive chiffree non supportee")
        name = info.filename.replace("\\", "/")
        parts = [p for p in name.split("/") if p not in ("", ".")]
        if not parts or any(p == ".." for p in parts):
            continue
        if info.file_size > MAX_FILE:
            continue
        total += info.file_size
        if total > MAX_TOTAL:
            raise ValueError("archive trop volumineuse")
        data = archive.read(info)
        files["/".join(parts).lower()] = data
    return files


def import_dashboard(data, filename="dashboard.simhubdash"):
    """Convertit un fichier SimHub en layout Studio (non sauvegarde)."""
    if not isinstance(data, str) or not data.strip():
        raise ValueError("fichier SimHub manquant")
    if "," in data and data.lstrip().lower().startswith("data:"):
        data = data.split(",", 1)[1]
    try:
        blob = base64.b64decode(data, validate=False)
    except (ValueError, TypeError):
        raise ValueError("base64 invalide")
    if not blob or len(blob) > MAX_ARCHIVE:
        raise ValueError("fichier SimHub trop grand")
    name = Path(filename or "dashboard.simhubdash").name
    if name.lower().endswith(".djson"):
        files = {name.lower(): blob}
        doc_path = name.lower()
    else:
        files = _read_zip(blob)
        doc_path = _main_doc(files, Path(name).stem)
        if doc_path is None:
            raise ValueError("aucun dashboard .djson dans l'archive")
    importer = _Importer(blob, name, files)
    return importer.run(doc_path)
