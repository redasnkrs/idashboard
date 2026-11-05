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
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from core import catalog, launcher, pump, themes
from core.config import (DEFAULT_DASHBOARD, HOME_FILE, PORT, SETTINGS_FILE,
                         STREAM_HZ, dashboard_asset, dashboard_file,
                         dashboard_manifest, spec_for_path)
from core.schema import schema_info

MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json",
    ".html": "text/html; charset=utf-8",
}


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

    def _file(self, path, ctype):
        try:
            with open(path, "rb") as f:
                self._send(f.read(), ctype)
        except OSError:
            self._send(b"Fichier introuvable", "text/plain; charset=utf-8", 404)

    def _redirect(self, location, code=302):
        self.send_response(code)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0 or length > 65536:
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
            location = "/dashboard/%s" % DEFAULT_DASHBOARD
            if query:
                location += "?" + query
            self._redirect(location)
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
        snippet = "<script>window.__IDASH__=%s;</script>" % json.dumps(
            meta, ensure_ascii=False).replace("</", "<\\/")
        idx = html.find("</head>")
        html = (html[:idx] + snippet + html[idx:]) if idx >= 0 else \
            snippet + html
        self._send(html.encode("utf-8"), "text/html; charset=utf-8")

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
