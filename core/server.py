"""Serveur HTTP local du pont.

Routes principales :

  /                              accueil (catalogue des compteurs)
  /dashboard                     redirige vers le compteur par defaut
  /dashboard/<categorie>/<nom>   un tableau de bord precis
  /settings                      reglages (global / jeu / voiture / compteur)
  /stream                        flux telemetrie SSE a STREAM_HZ
  /api/dash                      dernier etat (contrat commun)
  /api/dashboards                catalogue des compteurs
  /api/schema                    version et description du contrat
  /api/themes                    palettes + etat (GET) / enregistrement (POST)
  /api/themes/active             theme effectif
  /api/themes/stream             SSE : revision du theme
  /api/themes/reset              reinitialise une portee (POST)
  /api/launch                    ouvre un compteur sur le mini ecran (POST)
  /api/ets2/telemetry            format « ETS2 Telemetry Server »
"""
import json
import queue
import socket
import sys
import threading
import time
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from core import (ambient, app_control, app_settings, catalog, ets2_extract, ets2_map, game,
                  health, launcher, media, pump, screens, scs_plugin, simhub,
                  simhub_faithful, startup, studio, themes, updater)
from core.config import (DEFAULT_DASHBOARD, HOME_FILE, PORT, SETTINGS_FILE,
                         STREAM_HZ, STUDIO_DIR, UPDATE_FILE, VERSION,
                         dashboard_asset, dashboard_file, dashboard_manifest,
                         spec_for_path)
from core.nav_snippet import NAV_HTML
from core.schema import schema_info

MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json",
    ".html": "text/html; charset=utf-8",
}

SVG_CSP = {
    "Content-Security-Policy":
        "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'",
}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # connexions persistantes

    def _send(self, body, ctype, code=200, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path, ctype, extra=None):
        try:
            with open(path, "rb") as f:
                self._send(f.read(), ctype, extra=extra)
        except OSError:
            self._send(b"Fichier introuvable", "text/plain; charset=utf-8",
                       404)

    def _redirect(self, location, code=302):
        self.send_response(code)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _read_json(self, max_bytes=64 * 1024 * 1024):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0 or length > max_bytes:
            raise ValueError("corps JSON manquant ou trop grand")
        data = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("objet JSON attendu")
        return data

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")
        if path == "/api/ets2/telemetry":
            self._send(json.dumps(pump.STATE["ets2"]).encode(),
                       "application/json")
        elif path in ("", "/home"):
            self._file(HOME_FILE, "text/html; charset=utf-8")
        elif path == "/api/dash":
            self._send(pump.STATE["dash"], "application/json")
        elif path == "/api/game":
            self._send(json.dumps(game.status()).encode(), "application/json")
        elif path == "/api/screens":
            found = screens.list_screens()
            picked = screens.pick_7(found)
            body = {"platform": sys.platform, "screens": found,
                    "current": app_settings.screen(),
                    "detected": picked}
            self._send(json.dumps(body).encode(), "application/json")
        elif path == "/api/games":
            self._send(json.dumps({"games": game.status_all()}).encode(),
                       "application/json")
        elif path == "/api/ambient":
            self._send(json.dumps(ambient.status()).encode(),
                       "application/json")
        elif path == "/api/app":
            body = {"version": VERSION,
                    "default_dashboard": app_settings.default_dashboard(),
                    "keep_screen": app_settings.keep_screen(),
                    "open_on_start": app_settings.open_on_start(),
                    "startup": startup.status(),
                    "frozen": bool(getattr(sys, "frozen", False))}
            self._send(json.dumps(body).encode(), "application/json")
        elif path == "/api/health":
            port = self.server.server_address[1]
            self._send(json.dumps(health.info(port)).encode(),
                       "application/json")
        elif path == "/api/startup":
            self._send(json.dumps(startup.status()).encode(),
                       "application/json")
        elif path == "/api/diagnostics":
            from core.logging_setup import recent_errors
            body = {"health": health.info(), "errors": recent_errors(30)}
            self._send(json.dumps(body).encode(), "application/json")
        elif path == "/api/ets2/map":
            self._send(json.dumps(ets2_map.info()).encode(),
                       "application/json")
        elif path == "/api/ets2/map/generate":
            self._send(json.dumps(ets2_extract.status()).encode(),
                       "application/json")
        elif path == "/api/ets2/vector":
            data = ets2_map.vector_bytes()
            if not data:
                self.send_error(404)
            else:
                self._send(data, "application/json",
                           extra={"Content-Encoding": "gzip"})
        elif path == "/api/ets2/plugin":
            self._send(json.dumps(scs_plugin.status()).encode(),
                       "application/json")
        elif path.startswith("/api/ets2/map/tile/"):
            self._ets2_map_tile(path[len("/api/ets2/map/tile/"):])
        elif path == "/api/media":
            self._send(json.dumps(media.snapshot()).encode(),
                       "application/json")
        elif path == "/update":
            self._file(UPDATE_FILE, "text/html; charset=utf-8")
        elif path == "/api/update/info":
            self._send(json.dumps(updater.info()).encode(),
                       "application/json")
        elif path == "/api/media/art":
            data, ctype = media.art()
            if not data:
                self.send_error(404)
            else:
                self._send(data, ctype or "image/jpeg")
        elif path == "/api/dashboards":
            items = catalog.list_dashboards()
            categories = []
            seen = set()
            for item in items:
                if item["category"] not in seen:
                    seen.add(item["category"])
                    categories.append({"id": item["category"],
                                       "label": item["category_label"]})
            default = catalog.default_dashboard()
            self._send(json.dumps({
                "dashboards": items,
                "categories": categories,
                "default": default["spec"] if default else None,
            }).encode(), "application/json")
        elif path == "/api/schema":
            self._send(json.dumps(schema_info()).encode(), "application/json")
        elif path == "/api/layouts":
            items = []
            for layout in studio.list_layouts():
                item = studio.catalog_entry(layout)
                if item:
                    item["category_label"] = catalog.category_label(
                        item["category"])
                    items.append(item)
            self._send(json.dumps({"layouts": items}).encode(),
                       "application/json")
        elif path.startswith("/api/layouts/"):
            self._get_layout(path[len("/api/layouts/"):])
        elif path == "/api/icons":
            self._send(json.dumps({"icons": studio.list_icons()}).encode(),
                       "application/json")
        elif path == "/studio":
            self._file(STUDIO_DIR / "index.html",
                       "text/html; charset=utf-8")
        elif path.startswith("/studio/"):
            self._studio_asset(path[len("/studio/"):])
        elif path.startswith("/custom/previews/"):
            self._custom_preview(path[len("/custom/previews/"):])
        elif path.startswith("/custom/icons/"):
            self._custom_icon(path[len("/custom/icons/"):])
        elif path.startswith("/custom/imports/"):
            self._custom_import(path[len("/custom/imports/"):])
        elif path == "/api/themes":
            state = themes.load_state()
            info = {
                "active": state.get("active"),
                "revision": themes.revision(),
                "themes": themes.load_themes(),
                "state": state,
            }
            self._send(json.dumps(info).encode(), "application/json")
        elif path == "/api/themes/active":
            query = parse_qs(urlparse(self.path).query)
            get = lambda key: (query.get(key) or [None])[0]
            self._send(json.dumps(themes.resolve(
                dashboard=get("dashboard"), game=get("game"),
                car=get("car"))).encode(), "application/json")
        elif path == "/api/themes/stream":
            self._theme_stream()
        elif path == "/settings":
            self._file(SETTINGS_FILE, "text/html; charset=utf-8")
        elif path == "/dashboard":
            query = self.path.partition("?")[2]
            default = catalog.find(app_settings.default_dashboard())
            spec = default["spec"] if default else DEFAULT_DASHBOARD
            location = "/dashboard/%s" % spec
            if query:
                location += "?" + query
            self._redirect(location)
        elif path.startswith("/dashboard/custom/"):
            self._custom_dashboard(path[len("/dashboard/custom/"):])
        elif path.startswith("/dashboard/"):
            self._dashboard(path)
        elif path == "/stream":
            self._stream()
        else:
            self.send_error(404)

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")
        if path == "/api/themes":
            self._save_theme()
        elif path == "/api/themes/reset":
            self._reset_theme()
        elif path == "/api/launch":
            self._launch()
        elif path == "/api/game":
            self._save_game()
        elif path == "/api/game/detect":
            self._detect_game()
        elif path == "/api/game/launch":
            self._launch_game()
        elif path == "/api/screens":
            self._save_screen()
        elif path == "/api/app":
            self._save_app()
        elif path == "/api/ambient":
            try:
                payload = self._read_json()
                saved = app_settings.save_ambient(payload)
                ambient.restart()
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                self._send(json.dumps({"ok": False, "error": str(exc)}).encode(),
                           "application/json", 400)
                return
            self._send(json.dumps({"ok": True, "ambient": saved}).encode(),
                       "application/json")
        elif path == "/api/ambient/diagnose":
            self._send(json.dumps({"ok": True, "diagnose": ambient.diagnose()}).encode(),
                       "application/json")
        elif path == "/api/ambient/test":
            try:
                payload = self._read_json()
                ambient.test(payload.get("kind", "left"),
                             payload.get("seconds", 3))
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                self._send(json.dumps({"ok": False, "error": str(exc)}).encode(),
                           "application/json", 400)
                return
            self._send(json.dumps({"ok": True}).encode(),
                       "application/json")
        elif path == "/api/startup":
            self._save_startup()
        elif path == "/api/ets2/map/download":
            self._send(json.dumps({"ok": ets2_map.start_download()}).encode(),
                       "application/json")
        elif path == "/api/ets2/map/generate":
            try:
                payload = self._read_json()
                info = ets2_extract.start(
                    payload.get("game_dir"), payload.get("mod"),
                    payload.get("max_zoom", 8))
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                self._send(json.dumps({"ok": False, "error": str(exc)}).encode(),
                           "application/json", 400)
                return
            self._send(json.dumps({"ok": True, "generate": info}).encode(),
                       "application/json")
        elif path == "/api/ets2/plugin/install":
            try:
                info = scs_plugin.install()
            except (ValueError, OSError, KeyError, zipfile.BadZipFile) as exc:
                self._send(json.dumps({"ok": False, "error": str(exc)}).encode(),
                           "application/json", 400)
                return
            self._send(json.dumps({"ok": True, "plugin": info}).encode(),
                       "application/json")
        elif path == "/api/ets2/map/import":
            saved = ets2_map.import_from_simhub()
            self._send(json.dumps({"ok": bool(saved), "path": saved}).encode(),
                       "application/json")
        elif path == "/api/open-logs":
            self._send(json.dumps({"ok": app_control.open_logs()}).encode(),
                       "application/json")
        elif path == "/api/restart":
            self._send(json.dumps({"ok": app_control.restart()}).encode(),
                       "application/json")
        elif path.startswith("/api/games/"):
            self._game_action(path[len("/api/games/"):])
        elif path == "/api/media/control":
            self._media_control()
        elif path == "/api/update/install":
            self._install_update()
        elif path == "/api/layouts":
            self._save_layout()
        elif path == "/api/simhub/import":
            self._import_simhub()
        elif path == "/api/icons":
            self._save_icon()
        else:
            self.send_error(405)

    def do_DELETE(self):
        path = self.path.split("?")[0].rstrip("/")
        if path.startswith("/api/layouts/"):
            self._delete_layout(path[len("/api/layouts/"):])
        elif path.startswith("/api/icons/"):
            self._delete_icon(path[len("/api/icons/"):])
        else:
            self.send_error(405)

    def _dashboard(self, path):
        parts = path[len("/dashboard/"):].split("/")
        if parts and parts[-1] == "manifest.json":
            spec = "/".join(parts[:-1])
            manifest = dashboard_manifest(spec)
            if manifest is None:
                self.send_error(404)
            else:
                self._file(manifest, "application/json")
            return
        if len(parts) >= 3:
            spec = "/".join(parts[:2])
            name = "/".join(parts[2:])
            asset = dashboard_asset(spec, name)
            if asset is None:
                self.send_error(404)
            else:
                self._file(asset, MIME.get(asset.suffix.lower(),
                                           "application/octet-stream"))
            return
        target = dashboard_file("/".join(parts))
        if target is None:
            self.send_error(404)
        else:
            self._serve_dashboard(target)

    def _serve_dashboard(self, target):
        spec = spec_for_path(target)
        item = catalog.find(spec) if spec else None
        try:
            html = target.read_text(encoding="utf-8")
        except OSError:
            self.send_error(404)
            return
        meta = {}
        if item:
            meta = {key: item.get(key) for key in (
                "spec", "id", "name", "category", "category_label", "game",
                "game_id", "schema", "schema_version", "size")}
        snippet = "<script>window.__IDASH__=%s;</script>%s" % (
            json.dumps(meta, ensure_ascii=False).replace("</", "<\\/"),
            NAV_HTML)
        idx = html.find("</head>")
        html = (html[:idx] + snippet + html[idx:]) if idx >= 0 else \
            snippet + html
        self._send(html.encode("utf-8"), "text/html; charset=utf-8")

    def _studio_asset(self, name):
        allowed = {"index.html", "runtime.html", "runtime.js",
                   "simhub-runtime.js", "editor.js", "editor.css", "icons.js"}
        name = unquote(name)
        if name not in allowed:
            self.send_error(404)
            return
        path = STUDIO_DIR / name
        self._file(path, MIME.get(path.suffix.lower(),
                                  "application/octet-stream"))

    def _custom_preview(self, name):
        name = unquote(name)
        if "/" in name or not name.endswith(".svg"):
            self.send_error(404)
            return
        path = studio.preview_path(name[:-4])
        if path is None:
            self.send_error(404)
        else:
            self._file(path, "image/svg+xml", SVG_CSP)

    def _custom_icon(self, name):
        name = unquote(name)
        path = studio.icon_path(name)
        if path is None:
            self.send_error(404)
            return
        ctype = MIME.get(path.suffix.lower(), "application/octet-stream")
        self._file(path, ctype, SVG_CSP if path.suffix.lower() == ".svg"
                   else None)

    def _custom_import(self, name):
        parts = unquote(name).split("/", 1)
        if len(parts) != 2:
            self.send_error(404)
            return
        path = studio.import_asset_path(parts[0], parts[1])
        if path is None:
            self.send_error(404)
            return
        ctype = MIME.get(path.suffix.lower(), "application/octet-stream")
        self._file(path, ctype, SVG_CSP if path.suffix.lower() == ".svg"
                   else None)

    def _ets2_map_tile(self, suffix):
        parts = unquote(suffix).strip("/").split("/")
        if len(parts) != 3:
            self.send_error(404)
            return
        try:
            z = int(parts[0])
            x = int(parts[1])
            y = int(parts[2].removesuffix(".png"))
        except ValueError:
            self.send_error(404)
            return
        if not (0 <= z <= 8 and 0 <= x < 1024 and 0 <= y < 1024):
            self.send_error(404)
            return
        data = ets2_map.tile(z, x, y)
        if data is None:
            self.send_error(404)
            return
        self._send(data, "image/png")

    def _custom_dashboard(self, layout_id):
        layout_id = unquote(layout_id).strip().lower()
        item = catalog.find("custom/" + layout_id)
        if item is None:
            self.send_error(404)
            return
        try:
            html = (STUDIO_DIR / "runtime.html").read_text(encoding="utf-8")
        except OSError:
            self.send_error(404)
            return
        meta = {key: item.get(key) for key in (
            "spec", "id", "name", "category", "category_label", "game",
            "game_id", "schema", "schema_version", "size", "kind")}
        meta["custom"] = True
        snippet = "<script>window.__IDASH__=%s;</script>%s" % (
            json.dumps(meta, ensure_ascii=False).replace("</", "<\\/"),
            NAV_HTML)
        idx = html.find("</head>")
        html = (html[:idx] + snippet + html[idx:]) if idx >= 0 else \
            snippet + html
        self._send(html.encode("utf-8"), "text/html; charset=utf-8")

    def _get_layout(self, layout_id):
        layout = studio.load_layout(unquote(layout_id))
        if layout is None:
            self.send_error(404)
            return
        meta = studio.catalog_entry(layout)
        if meta:
            meta["category_label"] = catalog.category_label(
                meta["category"])
        self._send(json.dumps({"layout": layout, "meta": meta}).encode(),
                   "application/json")

    def _save_layout(self):
        try:
            layout = studio.save_layout(self._read_json())
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            self._send(json.dumps({"ok": False, "error": str(exc)}).encode(),
                       "application/json", 400)
            return
        meta = studio.catalog_entry(layout)
        if meta:
            meta["category_label"] = catalog.category_label(
                meta["category"])
        self._send(json.dumps({"ok": True, "layout": layout,
                               "meta": meta}).encode(), "application/json")

    def _delete_layout(self, layout_id):
        ok = studio.delete_layout(unquote(layout_id))
        self._send(json.dumps({"ok": ok}).encode(), "application/json",
                   200 if ok else 404)

    def _import_simhub(self):
        try:
            payload = self._read_json()
            importer = simhub.import_dashboard
            if payload.get("mode") != "widgets":
                importer = simhub_faithful.import_faithful
            layout, report = importer(
                payload.get("data"), payload.get("name") or "dashboard.simhubdash")
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            self._send(json.dumps({"ok": False, "error": str(exc)}).encode(),
                       "application/json", 400)
            return
        self._send(json.dumps({"ok": True, "layout": layout,
                               "report": report}).encode(),
                   "application/json")

    def _save_icon(self):
        try:
            icon = studio.save_icon(self._read_json())
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            self._send(json.dumps({"ok": False, "error": str(exc)}).encode(),
                       "application/json", 400)
            return
        self._send(json.dumps({"ok": True, "icon": icon}).encode(),
                   "application/json")

    def _delete_icon(self, name):
        ok = studio.delete_icon(unquote(name))
        self._send(json.dumps({"ok": ok}).encode(), "application/json",
                   200 if ok else 404)

    def _save_theme(self):
        try:
            themes.update(self._read_json())
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            body = json.dumps({"ok": False, "error": str(exc)}).encode()
            self._send(body, "application/json", 400)
            return
        body = json.dumps({"ok": True,
                           "revision": themes.revision()}).encode()
        self._send(body, "application/json")

    def _reset_theme(self):
        try:
            payload = self._read_json()
            themes.reset_scope(payload.get("scope") or "global",
                               str(payload.get("key") or "").strip())
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            body = json.dumps({"ok": False, "error": str(exc)}).encode()
            self._send(body, "application/json", 400)
            return
        self._send(json.dumps({"ok": True,
                               "revision": themes.revision()}).encode(),
                   "application/json")

    def _launch(self):
        try:
            payload = self._read_json()
        except (ValueError, KeyError, TypeError) as exc:
            self._send(json.dumps({"ok": False, "error": str(exc)}).encode(),
                       "application/json", 400)
            return
        item = catalog.find(str(payload.get("dashboard") or ""))
        if item is None:
            self._send(json.dumps({"ok": False,
                                   "error": "compteur inconnu"}).encode(),
                       "application/json", 400)
            return
        result = launcher.open_dashboard(item["spec"])
        self._send(json.dumps(result).encode(), "application/json",
                   200 if result.get("ok") else 500)

    def _save_game(self):
        try:
            game.save(self._read_json())
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            body = json.dumps({"ok": False, "error": str(exc)}).encode()
            self._send(body, "application/json", 400)
            return
        body = json.dumps({"ok": True, "game": game.status()}).encode()
        self._send(body, "application/json")

    def _detect_game(self):
        found = game.detect()
        if found:
            try:
                game.save({"exe": found})
            except ValueError:
                pass
        body = json.dumps({"ok": bool(found), "exe": found,
                           "game": game.status()}).encode()
        self._send(body, "application/json")

    def _launch_game(self):
        result = game.launch()
        self._send(json.dumps(result).encode(), "application/json",
                   200 if result.get("ok") else 400)

    def _save_screen(self):
        try:
            payload = self._read_json()
            saved = app_settings.save_screen(payload.get("screen"))
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            self._send(json.dumps({"ok": False, "error": str(exc)}).encode(),
                       "application/json", 400)
            return
        self._send(json.dumps({"ok": True, "screen": saved}).encode(),
                   "application/json")

    def _save_app(self):
        try:
            payload = self._read_json()
            result = {"ok": True,
                      "default_dashboard": app_settings.default_dashboard(),
                      "keep_screen": app_settings.keep_screen(),
                      "open_on_start": app_settings.open_on_start()}
            if "default_dashboard" in payload:
                item = catalog.find(payload.get("default_dashboard") or
                                    DEFAULT_DASHBOARD)
                if item is None:
                    raise ValueError("compteur inconnu")
                result["default_dashboard"] = \
                    app_settings.save_default_dashboard(item["spec"])
            if "keep_screen" in payload:
                result["keep_screen"] = app_settings.save_keep_screen(
                    payload.get("keep_screen"))
            if "open_on_start" in payload:
                result["open_on_start"] = app_settings.save_open_on_start(
                    payload.get("open_on_start"))
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            self._send(json.dumps({"ok": False, "error": str(exc)}).encode(),
                       "application/json", 400)
            return
        self._send(json.dumps(result).encode(), "application/json")

    def _save_startup(self):
        try:
            payload = self._read_json()
            if "enabled" not in payload:
                raise ValueError("enabled manquant")
            startup.set_enabled(bool(payload.get("enabled")))
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            self._send(json.dumps({"ok": False, "error": str(exc)}).encode(),
                       "application/json", 400)
            return
        self._send(json.dumps({"ok": True,
                               "startup": startup.status()}).encode(),
                   "application/json")

    def _game_action(self, suffix):
        parts = suffix.strip("/").split("/")
        key = parts[0] if parts else ""
        action = parts[1] if len(parts) > 1 else ""
        if key not in game.GAMES:
            self._send(json.dumps({"ok": False,
                                   "error": "jeu inconnu"}).encode(),
                       "application/json", 400)
            return
        if action == "detect":
            found = game.detect_game(key)
            if found:
                try:
                    game.save_game(key, {"exe": found})
                except ValueError:
                    pass
            self._send(json.dumps({"ok": bool(found), "exe": found,
                                   "game": game.status_game(key)}).encode(),
                       "application/json")
            return
        if action == "launch":
            result = game.launch_game(key)
            self._send(json.dumps(result).encode(), "application/json",
                       200 if result.get("ok") else 400)
            return
        if action == "":
            try:
                payload = self._read_json()
                game.save_game(key, payload)
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                self._send(json.dumps({"ok": False,
                                       "error": str(exc)}).encode(),
                           "application/json", 400)
                return
            self._send(json.dumps({"ok": True,
                                   "game": game.status_game(key)}).encode(),
                       "application/json")
            return
        self.send_error(404)

    def _install_update(self):
        try:
            payload = self._read_json(240 * 1024 * 1024)
            prepared = updater.prepare_zip(payload.get("data"),
                                           payload.get("name") or "update.zip")
            updater.spawn_apply(prepared["staging"],
                                prepared.get("kind") or "source")
        except (ValueError, OSError, KeyError, TypeError) as exc:
            self._send(json.dumps({"ok": False, "error": str(exc)}).encode(),
                       "application/json", 400)
            return
        body = json.dumps({"ok": True, "version": prepared["version"],
                           "kind": prepared.get("kind"), "restart": True}).encode()
        self._send(body, "application/json")
        updater.schedule_exit(2.0)

    def _media_control(self):
        try:
            payload = self._read_json()
        except (ValueError, KeyError, TypeError) as exc:
            self._send(json.dumps({"ok": False, "error": str(exc)}).encode(),
                       "application/json", 400)
            return
        result = media.control(str(payload.get("action") or ""))
        self._send(json.dumps(result).encode(), "application/json",
                   200 if result.get("ok") else 400)

    def _theme_stream(self):
        """Pousse seulement le numero de revision du theme."""
        q = themes.subscribe()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        try:
            self.wfile.write(
                ("data: {\"v\": %d}\n\n" % themes.revision()).encode())
            self.wfile.flush()
            while True:
                try:
                    rev = q.get(timeout=20)
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    continue
                self.wfile.write(("data: {\"v\": %d}\n\n" % rev).encode())
                self.wfile.flush()
        except OSError:
            pass
        finally:
            themes.unsubscribe(q)

    def _stream(self):
        """Flux SSE : un message toutes les 1/STREAM_HZ s (aussi heartbeat)."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        try:
            while True:
                self.wfile.write(b"data: " + pump.STATE["dash"] + b"\n\n")
                self.wfile.flush()
                time.sleep(1.0 / STREAM_HZ)
        except OSError:
            pass

    def log_message(self, *a):  # silence
        pass


def serve(port=PORT):
    """Ecoute en IPv4 et IPv6 (localhost peut etre resolu en ::1), local only."""
    class V6Server(ThreadingHTTPServer):
        address_family = socket.AF_INET6

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    actual = server.server_address[1]
    try:
        server6 = V6Server(("::1", actual), Handler)
        threading.Thread(target=server6.serve_forever, daemon=True).start()
    except OSError:
        pass  # IPv6 indisponible : IPv4 seul suffit
    return server
