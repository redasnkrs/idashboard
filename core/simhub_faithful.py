"""Import SimHub fidele : conserve le design d'origine et branche la telemetrie."""
import base64
import json
from pathlib import Path

from core import studio
from core.config import SIMHUB_MAP_URL
from core.simhub import (_BUILTINS, _Importer, _formula, _formula_field,
                         _main_doc, _num, _read_zip, _text, _typename,
                         _values, _weight, _align)


MAX_ITEMS = 3000
MAX_SIMHUB_JSON = 8 * 1024 * 1024


def _corners(item):
    style = item.get("BorderStyle")
    if not isinstance(style, dict):
        style = {}
    out = []
    for key in ("RadiusTopLeft", "RadiusTopRight", "RadiusBottomRight",
                "RadiusBottomLeft"):
        out.append(max(0, min(300, int(_num(style.get(key), 0)))))
    if not any(out):
        value = style.get("AllCornerRadius")
        if isinstance(value, (int, float)):
            out = [max(0, min(300, int(value)))] * 4
    return out


def _brush(value):
    if isinstance(value, str) and value.startswith("#"):
        return {"kind": "solid", "color": value}
    if not isinstance(value, dict):
        return None
    solid = value.get("SolidColorBrush")
    if isinstance(solid, dict):
        color = solid.get("#text")
        if isinstance(color, str):
            return {"kind": "solid", "color": color}
    gradient = value.get("LinearGradientBrush")
    if not isinstance(gradient, dict):
        return None

    def point(raw):
        parts = str(raw or "").split(",")
        try:
            return float(parts[0]), float(parts[1])
        except (IndexError, ValueError):
            return 0.0, 0.0

    x1, y1 = point(gradient.get("@StartPoint"))
    x2, y2 = point(gradient.get("@EndPoint"))
    stops = gradient.get("LinearGradientBrush.GradientStops") or \
        gradient.get("GradientStops")
    if isinstance(stops, dict):
        stops = stops.get("GradientStop")
    if not isinstance(stops, list):
        stops = [stops] if isinstance(stops, dict) else []
    out = []
    for stop in stops:
        if not isinstance(stop, dict):
            continue
        out.append({"offset": _num(stop.get("@Offset"), 0),
                    "color": _text(stop.get("@Color"), 20)})
    out.sort(key=lambda s: s["offset"])
    return {"kind": "linear", "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "stops": out}


def _format_from_item(item):
    if item.get("TimeFormat"):
        return "time"
    raw = _text(item.get("Format"), 40)
    if raw:
        if "." in raw:
            decimals = len(raw.split(".", 1)[1].replace("0", ""))
            return "float2" if decimals >= 2 else "float1"
        return "int"
    return "int"


class _FaithfulImporter(_Importer):
    def __init__(self, blob, filename, files):
        super().__init__(blob, filename, files)
        self.items_count = 0

    def _base_item(self, item, ctx, kind):
        self.items_count += 1
        if self.items_count > MAX_ITEMS:
            raise ValueError("trop d'elements SimHub (max %d)" % MAX_ITEMS)
        out = {
            "type": kind,
            "name": _text(item.get("Name"), 80),
            "left": _num(item.get("Left"), 0),
            "top": _num(item.get("Top"), 0),
            "width": max(0.0, _num(item.get("Width"), 0)),
            "height": max(0.0, _num(item.get("Height"), 0)),
            "opacity": max(0.0, min(1.0, _num(item.get("Opacity"), 100) / 100)),
            "visible": self._visible(item, ctx[0], ctx[1]),
        }
        if item.get("UseRotation") is not False and _num(item.get("Rotation")):
            out["rotation"] = _num(item.get("Rotation"))
        return out

    def _border(self, item):
        style = item.get("BorderStyle")
        if not isinstance(style, dict):
            style = {}
        color = _text(style.get("BorderColor"), 20)
        widths = [_num(style.get(k), 0) for k in (
            "AllBorders", "BorderTop", "BorderBottom", "BorderLeft",
            "BorderRight")]
        width = max(widths) if widths else 0
        if not color or not color.startswith("#") or width <= 0:
            color = _text(item.get("BorderColor"), 20)
            width = max(_num(item.get(k), 0) for k in (
                "BorderTop", "BorderBottom", "BorderLeft", "BorderRight"))
        if not color or not color.startswith("#") or width <= 0:
            return None
        return {"color": color, "width": max(0, min(40, width)),
                "corners": _corners(item)}

    def _bind(self, expression):
        if not expression:
            return None
        mapped = _formula_field(expression)
        if not mapped:
            return None
        field, fmt, unit, scale, offset = mapped
        return {"field": field, "format": fmt, "unit": unit,
                "scale": scale, "offset": offset}

    def _route_bind(self, item):
        name = _text(item.get("Name"), 80).strip().lower()
        expression = _formula(item, "Text").lower()
        if name == "speedlabel":
            return {"field": "v", "format": "int", "unit": "none",
                    "scale": 1, "offset": 0, "suffixField": "speed_unit",
                    "suffixSpace": True}
        if name == "gearlabel":
            return {"field": "gear_text", "format": "text", "unit": "none",
                    "scale": 1, "offset": 0}
        if name == "clock":
            return {"field": "game_time", "format": "text", "unit": "none",
                    "scale": 1, "offset": 0}
        if name == "limit":
            return {"field": "speed_limit", "format": "int", "unit": "none",
                    "scale": 1, "offset": 0}
        if "wearchassis" in expression:
            return {"field": "wear_truck", "format": "int", "unit": "none",
                    "scale": 1, "offset": 0, "suffix": "%"}
        if "trailervalues01" in expression:
            return {"field": "wear_cargo", "format": "int", "unit": "none",
                    "scale": 1, "offset": 0, "suffix": "%"}
        if "weartrailer" in expression:
            return {"field": "wear_trailer", "format": "int", "unit": "none",
                    "scale": 1, "offset": 0, "suffix": "%"}
        if name == "destination":
            if "navigationtime" in expression:
                return {"field": "eta_text", "format": "text",
                        "unit": "none", "scale": 1, "offset": 0}
            return {"field": "destination", "format": "text",
                    "unit": "none", "scale": 1, "offset": 0}
        return None

    def _text_bind(self, item, kind):
        route = self._route_bind(item)
        if route:
            return route
        bind = self._bind(_formula(item, "Text"))
        if bind:
            return bind
        spec = _BUILTINS.get(kind)
        if spec and spec.get("field"):
            return {"field": spec["field"],
                    "format": spec.get("format", "int"),
                    "unit": spec.get("unit", "none"), "scale": 1,
                    "offset": 0}
        return None

    def _text_style(self, item, color_key="TextColor"):
        return {
            "font": _text(item.get("Font"), 80),
            "size": max(6, min(300, _num(item.get("FontSize"), 20))),
            "weight": _weight(item.get("FontWeight")),
            "italic": _text(item.get("FontStyle"), 20).lower() == "italic",
            "color": _text(item.get(color_key), 20) or "#FFFFFFFF",
            "hAlign": int(_num(item.get("HorizontalAlignment"), 0)),
            "vAlign": int(_num(item.get("VerticalAlignment"), 0)),
        }

    def _text_item(self, item, ctx, kind):
        out = self._base_item(item, ctx, "Text")
        out["text"] = _text(item.get("Text"), 400)
        out["style"] = self._text_style(item)
        bind = self._text_bind(item, kind)
        if bind:
            out["bind"] = bind
        return out

    def _gauge(self, item, ctx):
        out = self._base_item(item, ctx, "DialGauge")
        value = self._bind(_formula(item, "Value"))
        if value and value["field"] == "boost" and \
                "computedturbopercent" in _formula(item, "Value").lower():
            value["scale"] = 100
        out["value"] = value
        out["minimum"] = _num(item.get("Minimum"), 0)
        out["maximum"] = _num(item.get("Maximum"), 100)
        out["start"] = _num(item.get("StartAngle"), 135)
        out["sweep"] = _num(item.get("SweepAngle"), 270)
        out["outerRadius"] = _num(item.get("OuterRadius"), 0)
        out["innerRadius"] = _num(item.get("InnerRadius"), 0)
        out["outerStroke"] = _num(item.get("OuterStrokeThickness"), 0)
        out["innerStroke"] = _num(item.get("InnerStrokeThickness"), 0)
        out["dialBg"] = _brush(item.get("DialBackgroundColor"))
        out["dialStroke"] = _brush(item.get("DialStrokeColor"))
        out["showRadial"] = bool(item.get("ShowRadialGauge"))
        out["radialRadius"] = _num(item.get("RadialGaugeRadius"), 0)
        out["radialThickness"] = _num(item.get("RadialGaugeThickness"), 0)
        out["radialColor"] = _text(item.get("RadialGaugeColor"), 20)
        out["rangeStart"] = _num(item.get("RangeOptimalStartValue"), 0)
        out["rangeEnd"] = _num(item.get("RangeOptimalEndValue"), 0)
        out["above"] = item.get("AboveOptimalStyle") or {}
        out["below"] = item.get("BelowOptimalStyle") or {}
        out["optimal"] = item.get("OptimalStyle") or {}
        out["showNeedle"] = bool(item.get("ShowNeedle"))
        out["needleLength"] = _num(item.get("NeedleLength"), 0)
        out["needleOffset"] = _num(item.get("NeedleOffset"), 0)
        out["needleThickness"] = _num(item.get("NeedleThickness"), 4)
        out["needleSrc"] = self.resolve_image(item.get("NeedleImage"))
        out["capRadius"] = _num(item.get("CapRadius"), 0)
        out["majorRadius"] = _num(item.get("MajorTickRadius"), 0)
        out["majorDivisions"] = _num(item.get("MajorDivisionsCount"), 0)
        out["majorColor"] = _text(item.get("MajorTickColor"), 20)
        out["majorSize"] = _text(item.get("MajorTickSize"), 40)
        out["minorRadius"] = _num(item.get("MinorTickRadius"), 0)
        out["minorDivisions"] = _num(item.get("MinorDivisionsCount"), 0)
        out["minorColor"] = _text(item.get("MinorTickColor"), 20)
        out["minorSize"] = _text(item.get("MinorTickSize"), 40)
        out["labelStyle"] = item.get("ScaleLabelStyle") or {}
        out["altLabelStyle"] = item.get("AlternateScaleLabelStyle") or {}
        out["customLabels"] = _text(item.get("CustomScaleLabels"), 200)
        out["ticksPerLabel"] = _num(item.get("TicksPerLabel"), 0)
        return out

    def _item(self, item, path, base_w, base_h, depth=0):
        if not isinstance(item, dict):
            return None
        kind = _typename(item)
        ctx = (base_w, base_h)
        name = _text(item.get("Name"), 80)
        if name.startswith("_"):
            return None
        if not self._visible(item, base_w, base_h):
            return None
        if kind == "Layer":
            out = self._base_item(item, ctx, "Layer")
            children = self._items(_values(item.get("Childrens")), path,
                                   base_w, base_h, depth)
            out["children"] = children
            return out
        if kind == "WidgetItem":
            filename = _text(item.get("FileName"), 300)
            if not filename or depth >= 8:
                return None
            child_path = self._resolve_child(path, filename)
            if child_path is None:
                self.missing += 1
                self.warn("composant introuvable: %s" % filename)
                return None
            child = self._load_doc(child_path)
            if child is None:
                self.missing += 1
                return None
            screen = self._pick_screen(child)
            if screen is None:
                return None
            cw = max(1.0, _num(child.get("BaseWidth"), 800))
            ch = max(1.0, _num(child.get("BaseHeight"), 480))
            out = self._base_item(item, ctx, "Widget")
            out["child"] = {
                "base": [cw, ch],
                "items": self._items(_values(screen.get("Items")),
                                     child_path, cw, ch, depth + 1),
            }
            return out
        if kind == "RectangleItem":
            out = self._base_item(item, ctx, "Rectangle")
            out["fill"] = _brush(item.get("BackgroundColor"))
            out["border"] = self._border(item)
            return out
        if kind == "EllipseItem":
            out = self._base_item(item, ctx, "Ellipse")
            out["fill"] = _brush(item.get("FillColor"))
            out["stroke"] = _text(item.get("EllipseColor"), 20)
            out["strokeWidth"] = _num(item.get("EllipseThickness"), 1)
            return out
        if kind == "GradientItem":
            out = self._base_item(item, ctx, "Gradient")
            out["fill"] = _brush(item.get("Color"))
            out["border"] = self._border(item)
            return out
        if kind == "TextItem" or kind in _BUILTINS:
            return self._text_item(item, ctx, kind)
        if kind == "ImageItem":
            out = self._base_item(item, ctx, "Image")
            out["src"] = self.resolve_image(item.get("Image"))
            if not out["src"]:
                self.skipped += 1
                return None
            name_low = _text(item.get("Name"), 80).lower()
            if "blinker" in name_low:
                out["visible_bind"] = {"any": ["L", "R"]}
            return out
        if kind == "ToggleImageItem":
            out = self._base_item(item, ctx, "Image")
            out["src"] = self.resolve_image(item.get("OffImage") or
                                            item.get("OnImage"))
            return out if out["src"] else None
        if kind in ("DialGaugeItem", "CircularGaugeItem"):
            return self._gauge(item, ctx)
        if kind == "ETSMap":
            return self._base_item(item, ctx, "ETSMap")
        if kind == "LinearGaugeItem":
            out = self._base_item(item, ctx, "LinearGauge")
            out["value"] = self._bind(_formula(item, "Value"))
            if _text(item.get("Name"), 80).lower() == "fuelgauge" and \
                    out["value"] and out["value"].get("field") == "fp":
                out["value"]["scale"] = 100.0
            out["minimum"] = _num(item.get("Minimum"), 0)
            out["maximum"] = _num(item.get("Maximum"), 100)
            out["orientation"] = int(_num(item.get("GaugeOrientation"), 1))
            out["color"] = _text(item.get("GaugeColor"), 20) or "#FFFFFFFF"
            out["trackColor"] = _text(item.get("BackgroundColor"), 20)
            out["backgroundSrc"] = self.resolve_image(
                item.get("BackgroundImage"))
            out["gaugeSrc"] = self.resolve_image(item.get("GaugeImage"))
            return out
        if kind in ("GeneratedMapItem", "GeneratedStaticMapItem", "MapItem"):
            return None
        self.warn("type SimHub non supporte: %s" % kind)
        self.skipped += 1
        return None

    def _items(self, items, path, base_w, base_h, depth=0):
        out = []
        for item in items:
            try:
                value = self._item(item, path, base_w, base_h, depth)
            except (TypeError, ValueError, KeyError) as exc:
                self.warn("item ignore: %s" % exc)
                self.skipped += 1
                continue
            if value is not None:
                out.append(value)
        return out

    def run_faithful(self, doc_path):
        doc = self._load_doc(doc_path)
        if doc is None:
            raise ValueError("dashboard SimHub illisible")
        screen = self._pick_screen(doc)
        if screen is None:
            raise ValueError("aucun ecran SimHub")
        self.screen = _text(screen.get("Name"), 80)
        self._index_assets()
        base_w = max(1.0, _num(doc.get("BaseWidth"), 1280))
        base_h = max(1.0, _num(doc.get("BaseHeight"), 720))
        self.meta = doc.get("Metadata") if isinstance(
            doc.get("Metadata"), dict) else {}
        items = self._items(_values(screen.get("Items")), doc_path,
                            base_w, base_h)
        background = _text(doc.get("BackgroundColor"), 20) or "#FF000000"
        name = _text(self.meta.get("Title"), 80).strip() or \
            Path(self.filename).stem or Path(doc_path).parent.name
        description = _text(self.meta.get("Description"), 300).strip()
        tags = ["simhub", "faithful"]
        author = _text(self.meta.get("Author"), 40).strip()
        if author:
            tags.append(author)
        simhub = {"base": [base_w, base_h], "background": background,
                  "items": items, "map_url": SIMHUB_MAP_URL}
        encoded = json.dumps(simhub)
        if len(encoded) > MAX_SIMHUB_JSON:
            raise ValueError("dashboard SimHub trop complexe")
        has_ets_map = False

        def find_map(items):
            nonlocal has_ets_map
            for item in items:
                if item.get("type") == "ETSMap":
                    has_ets_map = True
                find_map(item.get("children") or [])
                find_map((item.get("child") or {}).get("items") or [])

        find_map(items)
        payload = {
            "kind": "simhub",
            "name": name,
            "description": description,
            "category": "custom",
            "game": "Euro Truck Simulator 2" if has_ets_map
            else "Assetto Corsa Evo",
            "game_id": "ets2" if has_ets_map else "acevo",
            "order": 10,
            "tags": tags,
            "background": "#000000",
            "canvas": {"width": 1024, "height": 600, "grid": 16,
                       "background": "#000000"},
            "widgets": [],
            "simhub": simhub,
        }
        layout = studio.validate_layout(payload)
        report = self.report(doc_path, doc)
        report["widgets"] = self.items_count
        report["faithful"] = True
        return layout, report


def import_faithful(data, filename="dashboard.simhubdash"):
    if not isinstance(data, str) or not data.strip():
        raise ValueError("fichier SimHub manquant")
    if "," in data and data.lstrip().lower().startswith("data:"):
        data = data.split(",", 1)[1]
    try:
        blob = base64.b64decode(data, validate=False)
    except (ValueError, TypeError):
        raise ValueError("base64 invalide")
    if not blob or len(blob) > 64 * 1024 * 1024:
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
    importer = _FaithfulImporter(blob, name, files)
    return importer.run_faithful(doc_path)
