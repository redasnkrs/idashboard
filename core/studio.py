"""Studio : stockage et validation des compteurs personnalises.

Les layouts et les icones vivent dans ``custom/`` (ignore par git) :

  custom/layouts/<id>.json
  custom/previews/<id>.svg
  custom/icons/<fichier>

Le runtime et l'editeur sont dans ``studio/``. Ce module ne fait que du
stockage, de la validation et de la metadata pour le catalogue.
"""
import base64
import hashlib
import json
import re
import time
from pathlib import Path

from core.config import ROOT
from core.schema import DASH_SCHEMA

CUSTOM_DIR = ROOT / "custom"
LAYOUTS_DIR = CUSTOM_DIR / "layouts"
PREVIEWS_DIR = CUSTOM_DIR / "previews"
ICONS_DIR = CUSTOM_DIR / "icons"
IMPORTS_DIR = CUSTOM_DIR / "imports"

LAYOUT_VERSION = 1
CANVAS_W, CANVAS_H = 1024, 600
MAX_WIDGETS = 800
MAX_PREVIEW = 2 * 1024 * 1024
MAX_ICON = 512 * 1024

WIDGET_TYPES = {
    "value", "text", "gauge", "bar", "icon", "image", "shape",
    "map", "media", "clock", "shiftlights", "gearstrip",
}
FORMATS = {"int", "float1", "float2", "time", "clock", "delta", "gear",
           "text", "percent"}
UNITS = {"auto", "kmh", "mph", "c", "f", "l", "bar", "percent", "none"}
ROLES = {"ink", "ivory", "muted", "rule", "off", "amber", "red", "green",
         "blue", "violet", "dim"}
SHAPES = {"rect", "line", "circle"}
FIELDS = set(DASH_SCHEMA) | {"none"}

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_SAFE_CATEGORY = re.compile(r"^[a-z0-9-]{1,24}$")
_SAFE_GAME_ID = re.compile(r"^[a-z0-9_-]{1,40}$")
_SAFE_ICON = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")
_SAFE_CUSTOM_ICON = re.compile(r"^custom:[A-Za-z0-9._-]{1,120}$")
_SAFE_ICON_FILE = re.compile(r"^[A-Za-z0-9._-]{1,160}$")
_SAFE_IMPORT_TOKEN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def slugify(value):
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "dashboard"


def _color(value, default="ivory"):
    if value in ROLES:
        return value
    if isinstance(value, str) and _HEX.match(value):
        return value
    return default


def _num(value, default, lo, hi):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return max(lo, min(hi, value))


def _text(value, default="", limit=300):
    if not isinstance(value, str):
        return default
    return value[:limit]


def _field(value, default="none"):
    return value if value in FIELDS else default


def _format(value, default="text"):
    return value if value in FORMATS else default


def _unit(value, default="none"):
    return value if value in UNITS else default


def _icon(value, default="circle-dot"):
    if value is None:
        return default
    if isinstance(value, str) and (_SAFE_ICON.match(value)
                                   or _SAFE_CUSTOM_ICON.match(value)):
        return value
    return default


def _src(value):
    if not isinstance(value, str):
        return ""
    if value.startswith("custom:") and _SAFE_CUSTOM_ICON.match(value):
        return value
    if value.startswith("/custom/icons/"):
        name = value.rsplit("/", 1)[-1]
        if _SAFE_ICON_FILE.match(name) and ".." not in name:
            return value
    if value.startswith("/custom/imports/"):
        parts = value[len("/custom/imports/"):].split("/")
        if len(parts) >= 2 and all(_SAFE_ICON_FILE.match(p) and
                                   p not in (".", "..") for p in parts):
            return value
    return ""


def _thresholds(value):
    out = []
    if not isinstance(value, list):
        return out
    for item in value[:20]:
        if not isinstance(item, dict):
            continue
        at = item.get("at")
        if isinstance(at, bool) or not isinstance(at, (int, float)):
            continue
        out.append({
            "at": at,
            "color": _color(item.get("color"), "red"),
            "below": bool(item.get("below")),
        })
    return out


def _clean_widget(raw, index):
    if not isinstance(raw, dict):
        return None
    kind = raw.get("type")
    if kind not in WIDGET_TYPES:
        return None
    x = _num(raw.get("x"), 0, 0, CANVAS_W)
    y = _num(raw.get("y"), 0, 0, CANVAS_H)
    w = _num(raw.get("w"), 120, 8, CANVAS_W)
    h = _num(raw.get("h"), 60, 8, CANVAS_H)
    if x + w > CANVAS_W:
        w = CANVAS_W - x
    if y + h > CANVAS_H:
        h = CANVAS_H - y
    wid = raw.get("id")
    if not isinstance(wid, str) or not _SAFE_ID.match(wid.lower()):
        wid = "w%d" % (index + 1)
    item = {
        "id": wid,
        "type": kind,
        "x": round(x, 3), "y": round(y, 3),
        "w": round(w, 3), "h": round(h, 3),
        "visible": raw.get("visible") is not False,
        "opacity": _num(raw.get("opacity"), 1, 0, 1),
        "rotation": _num(raw.get("rotation"), 0, -360, 360),
        "scale": _num(raw.get("scale"), 1, -1000, 1000),
        "offset": _num(raw.get("offset"), 0, -100000, 100000),
        "font": _text(raw.get("font"), "", 80),
        "color": _color(raw.get("color")),
        "accent": _color(raw.get("accent"), "amber"),
        "bg": _color(raw.get("bg"), "off"),
        "labelColor": _color(raw.get("labelColor"), "muted"),
        "unitColor": _color(raw.get("unitColor"), "muted"),
        "trackColor": _color(raw.get("trackColor"), "off"),
        "fill": ("none" if raw.get("fill") == "none"
                 else _color(raw.get("fill"), "off")),
        "stroke": ("none" if raw.get("stroke") == "none"
                   else _color(raw.get("stroke"), "rule")),
    }
    if kind in ("value", "text", "gauge", "bar", "clock", "gearstrip"):
        item.update({
            "label": _text(raw.get("label"), "", 80),
            "field": _field(raw.get("field"), "none"),
            "format": _format(raw.get("format"), "text"),
            "unit": _unit(raw.get("unit"), "none"),
            "size": _num(raw.get("size"), 32, 6, 300),
            "labelSize": _num(raw.get("labelSize"), 11, 6, 80),
            "weight": _num(raw.get("weight"), 700, 100, 900),
            "align": raw.get("align") if raw.get("align") in
                ("left", "center", "right") else "left",
            "thresholds": _thresholds(raw.get("thresholds")),
        })
        if kind == "text":
            item["text"] = _text(raw.get("text"), "", 400)
            item["letterSpacing"] = _num(raw.get("letterSpacing"), 0, -5, 20)
        if kind == "clock":
            item["showDate"] = raw.get("showDate") is not False
            item["showTime"] = raw.get("showTime") is not False
            item["locale"] = "fr-FR" if raw.get("locale") == "fr-FR" else "en-US"
    if kind == "bar":
        item.update({
            "min": _num(raw.get("min"), 0, -100000, 100000),
            "max": _num(raw.get("max"), 100, -100000, 100000),
            "maxField": _field(raw.get("maxField"), "none"),
            "orientation": "vertical" if raw.get("orientation") == "vertical" else "horizontal",
            "showValue": raw.get("showValue") is not False,
        })
    if kind == "gauge":
        item.update({
            "min": _num(raw.get("min"), 0, -100000, 100000),
            "max": _num(raw.get("max"), 10000, -100000, 100000),
            "maxField": _field(raw.get("maxField"), "none"),
            "redline": _num(raw.get("redline"), 0.89, 0, 1),
            "needle": raw.get("needle") is True,
            "showValue": raw.get("showValue") is not False,
            "valueSize": _num(raw.get("valueSize"), 0, 0, 300),
        })
    if kind == "icon":
        item.update({
            "icon": _icon(raw.get("icon")),
            "iconOn": _icon(raw.get("iconOn"), ""),
            "iconOff": _icon(raw.get("iconOff"), ""),
            "field": _field(raw.get("field"), "none"),
            "onAt": _num(raw.get("onAt"), 0.5, -100000, 100000),
            "onColor": _color(raw.get("onColor"), "amber"),
            "offColor": _color(raw.get("offColor"), "dim"),
            "showOff": raw.get("showOff") is not False,
        })
    if kind == "image":
        item["src"] = _src(raw.get("src"))
        item["fit"] = raw.get("fit") if raw.get("fit") in ("contain", "cover") else "contain"
    if kind == "shape":
        item.update({
            "shape": raw.get("shape") if raw.get("shape") in SHAPES else "rect",
            "radius": _num(raw.get("radius"), 8, 0, 200),
            "strokeWidth": _num(raw.get("strokeWidth"), 1, 0, 40),
        })
    if kind == "map":
        item.update({
            "field": _field(raw.get("field"), "npos"),
            "roadColor": _color(raw.get("roadColor"), "dim"),
            "dotColor": _color(raw.get("dotColor"), "amber"),
            "showDot": raw.get("showDot") is not False,
        })
    if kind == "media":
        item.update({
            "showControls": raw.get("showControls") is not False,
            "showTimeline": raw.get("showTimeline") is not False,
        })
    if kind == "shiftlights":
        item.update({
            "field": _field(raw.get("field"), "r"),
            "maxField": _field(raw.get("maxField"), "rm"),
            "count": int(_num(raw.get("count"), 27, 3, 60)),
            "low": _num(raw.get("low"), 0.72, 0, 1),
            "high": _num(raw.get("high"), 0.98, 0, 1),
        })
    if kind == "gearstrip":
        item.update({
            "count": int(_num(raw.get("count"), 8, 1, 12)),
            "color": _color(raw.get("color"), "muted"),
            "accent": _color(raw.get("accent"), "amber"),
        })
    return item


def validate_layout(payload, existing=None):
    if not isinstance(payload, dict):
        raise ValueError("layout invalide")
    name = _text(payload.get("name"), "", 80).strip()
    if not name:
        raise ValueError("nom obligatoire")
    category = _text(payload.get("category"), "custom", 24).strip().lower()
    if not _SAFE_CATEGORY.match(category):
        category = "custom"
    game_id = _text(payload.get("game_id"), "acevo", 40).strip()
    if not _SAFE_GAME_ID.match(game_id):
        game_id = "acevo"
    canvas = payload.get("canvas") if isinstance(payload.get("canvas"), dict) else {}
    grid = int(_num(canvas.get("grid"), 16, 4, 64))
    background = _color(payload.get("background") or canvas.get("background"),
                        "ink")
    kind = payload.get("kind") if payload.get("kind") in ("widgets", "simhub") \
        else "widgets"
    simhub_data = None
    if kind == "simhub":
        raw_simhub = payload.get("simhub")
        if not isinstance(raw_simhub, dict):
            raise ValueError("donnees SimHub manquantes")
        try:
            size = len(json.dumps(raw_simhub, ensure_ascii=False))
        except (TypeError, ValueError):
            raise ValueError("donnees SimHub invalides")
        if size > 8 * 1024 * 1024:
            raise ValueError("donnees SimHub trop volumineuses")
        simhub_data = raw_simhub
    raw_widgets = payload.get("widgets")
    if not isinstance(raw_widgets, list):
        raw_widgets = []
    if len(raw_widgets) > MAX_WIDGETS:
        raise ValueError("trop de widgets")
    widgets = []
    seen = set()
    for i, raw in enumerate(raw_widgets):
        w = _clean_widget(raw, i)
        if w is None:
            continue
        base = w["id"]
        n = 1
        while w["id"] in seen:
            n += 1
            w["id"] = "%s-%d" % (base, n)
        seen.add(w["id"])
        widgets.append(w)
    now = _now()
    layout_id = existing or _text(payload.get("id"), "", 64).strip().lower()
    if not _SAFE_ID.match(layout_id or ""):
        layout_id = ""
    tags = payload.get("tags") if isinstance(payload.get("tags"), list) else []
    tags = [t[:24] for t in tags if isinstance(t, str)][:12]
    layout = {
        "version": LAYOUT_VERSION,
        "kind": kind,
        "id": layout_id,
        "name": name,
        "description": _text(payload.get("description"), "", 300),
        "category": category,
        "game": _text(payload.get("game"), "Assetto Corsa Evo", 80),
        "game_id": game_id,
        "order": int(_num(payload.get("order"), 10, 0, 999)),
        "tags": tags,
        "canvas": {"width": CANVAS_W, "height": CANVAS_H,
                   "grid": grid, "background": background},
        "background": background,
        "widgets": widgets,
        "created": payload.get("created") or now,
        "updated": now,
    }
    if simhub_data is not None:
        layout["simhub"] = simhub_data
    return layout


def _atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _unique_id(base):
    candidate = base
    n = 2
    while (LAYOUTS_DIR / (candidate + ".json")).exists():
        candidate = "%s-%d" % (base, n)
        n += 1
    return candidate


def save_layout(payload):
    if not isinstance(payload, dict):
        raise ValueError("layout invalide")
    preview = payload.pop("preview_svg", None) if isinstance(payload, dict) else None
    preview_text = None
    if isinstance(preview, str) and preview.strip():
        if len(preview) > MAX_PREVIEW:
            raise ValueError("apercu trop grand")
        preview_text = _sanitize_svg_text(preview)
    raw_id = _text(payload.get("id"), "", 64).strip().lower()
    existing = raw_id if _SAFE_ID.match(raw_id or "") and \
        (LAYOUTS_DIR / (raw_id + ".json")).exists() else None
    layout = validate_layout(payload, existing)
    if not layout["id"]:
        layout["id"] = _unique_id(slugify(layout["name"]))
    if not _SAFE_ID.match(layout["id"]):
        layout["id"] = _unique_id("dashboard")
    _atomic_write(LAYOUTS_DIR / (layout["id"] + ".json"),
                  json.dumps(layout, indent=2, ensure_ascii=False))
    if preview_text is not None:
        _atomic_write(PREVIEWS_DIR / (layout["id"] + ".svg"), preview_text)
    return layout


def load_layout(layout_id):
    layout_id = (layout_id or "").strip().lower()
    if not _SAFE_ID.match(layout_id):
        return None
    path = LAYOUTS_DIR / (layout_id + ".json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def list_layouts():
    out = []
    if not LAYOUTS_DIR.is_dir():
        return out
    for path in sorted(LAYOUTS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get("id") == path.stem:
            out.append(data)
    out.sort(key=lambda x: (int(x.get("order") or 10),
                            str(x.get("name") or "").lower()))
    return out


def delete_layout(layout_id):
    layout_id = (layout_id or "").strip().lower()
    if not _SAFE_ID.match(layout_id):
        return False
    removed = False
    for path in (LAYOUTS_DIR / (layout_id + ".json"),
                 PREVIEWS_DIR / (layout_id + ".svg")):
        try:
            path.unlink()
            removed = True
        except OSError:
            pass
    return removed


def preview_path(layout_id):
    layout_id = (layout_id or "").strip().lower()
    if not _SAFE_ID.match(layout_id):
        return None
    path = PREVIEWS_DIR / (layout_id + ".svg")
    return path if path.is_file() else None


def catalog_entry(layout):
    layout_id = layout.get("id")
    if not layout_id:
        return None
    preview = preview_path(layout_id)
    category = layout.get("category") or "custom"
    return {
        "spec": "custom/" + layout_id,
        "id": layout_id,
        "name": layout.get("name") or layout_id,
        "description": layout.get("description") or "",
        "category": category,
        "category_label": None,
        "game": layout.get("game") or "Assetto Corsa Evo",
        "game_id": layout.get("game_id") or "acevo",
        "size": [CANVAS_W, CANVAS_H],
        "schema": "course",
        "schema_version": 1,
        "preview_url": ("/custom/previews/%s.svg" % layout_id
                        if preview else None),
        "url": "/dashboard/custom/%s" % layout_id,
        "settings_url": "/settings?dashboard=custom/%s" % layout_id,
        "order": int(layout.get("order") or 10),
        "tags": layout.get("tags") or [],
        "custom": True,
        "kind": layout.get("kind") or "widgets",
    }


def _sanitize_svg_text(text):
    if "<svg" not in text[:500].lower():
        raise ValueError("SVG invalide")
    lowered = text.lower()
    for bad in ("<script", "<foreignobject", "<iframe", "<object", "<embed",
                "javascript:"):
        if bad in lowered:
            raise ValueError("SVG non autorise")
    if re.search(r"<[^>]*\bon\w+\s*=", text, re.I):
        raise ValueError("SVG non autorise")
    if re.search(r"(?:href|xlink:href)\s*=\s*[\"']https?://", text, re.I):
        raise ValueError("ressource externe non autorisee")
    return text


def _safe_icon_filename(name):
    return _SAFE_ICON_FILE.match(name or "") and ".." not in name


def icon_path(filename):
    if not _safe_icon_filename(filename):
        return None
    path = ICONS_DIR / filename
    return path if path.is_file() else None


def import_asset_path(token, filename):
    token = (token or "").strip().lower()
    if not _SAFE_IMPORT_TOKEN.match(token) or not _safe_icon_filename(filename):
        return None
    path = IMPORTS_DIR / token / filename
    return path if path.is_file() else None


def list_icons():
    out = []
    if not ICONS_DIR.is_dir():
        return out
    for path in sorted(ICONS_DIR.iterdir()):
        if not path.is_file() or not _safe_icon_filename(path.name):
            continue
        ext = path.suffix.lower()
        if ext not in (".svg", ".png", ".jpg", ".jpeg", ".webp"):
            continue
        stem = re.sub(r"-[0-9a-f]{8}$", "", path.stem)
        name = stem.replace("-", " ").strip().title() or path.stem
        out.append({
            "id": path.name,
            "name": name,
            "url": "/custom/icons/%s" % path.name,
            "mime": {
                ".svg": "image/svg+xml", ".png": "image/png",
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".webp": "image/webp",
            }.get(ext, "application/octet-stream"),
        })
    return out


def save_icon(payload):
    if not isinstance(payload, dict):
        raise ValueError("icone invalide")
    name = _text(payload.get("name"), "icon", 60).strip() or "icon"
    data = payload.get("data")
    if not isinstance(data, str) or "," not in data:
        raise ValueError("fichier invalide")
    head, b64 = data.split(",", 1)
    mime = "image/svg+xml"
    if ";" in head:
        mime = head[5:].split(";", 1)[0] or mime
    ext = {"image/svg+xml": ".svg", "image/png": ".png",
           "image/jpeg": ".jpg", "image/webp": ".webp"}.get(mime)
    if ext is None:
        raise ValueError("format non supporte")
    try:
        raw = base64.b64decode(b64, validate=True)
    except (ValueError, TypeError):
        raise ValueError("base64 invalide")
    if not raw or len(raw) > MAX_ICON:
        raise ValueError("fichier trop grand")
    if ext == ".svg":
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("SVG invalide")
        if "<svg" not in text.lower():
            raise ValueError("SVG invalide")
        _sanitize_svg_text(text)
        raw = text.encode("utf-8")
    digest = hashlib.sha1(raw).hexdigest()[:8]
    filename = "%s-%s%s" % (slugify(name)[:60], digest, ext)
    path = ICONS_DIR / filename
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(raw)
        tmp.replace(path)
    return {
        "id": filename, "name": name,
        "url": "/custom/icons/%s" % filename, "mime": mime,
    }


def delete_icon(filename):
    path = icon_path(filename)
    if path is None:
        return False
    try:
        path.unlink()
        return True
    except OSError:
        return False
