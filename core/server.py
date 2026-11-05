"""Serveur HTTP local du pont.

Routes (identiques a la version d'origine, plus ``/api/schema``) :

  /dashboard                    tableau de bord par defaut
  /dashboard/<categorie>/<nom>  un tableau de bord precis (dossier)
  /dashboard/<nom>              raccourci si le nom est unique
  /stream                       flux SSE a STREAM_HZ
  /api/dash                     dernier etat (contrat commun)
  /api/schema                   version et description du contrat
  /api/ets2/telemetry           format « ETS2 Telemetry Server »
"""
import json
import socket
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from core import pump
from core.config import (DEFAULT_DASHBOARD, PORT, STREAM_HZ, dashboard_file,
                         dashboard_manifest)
from core.schema import schema_info


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

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")
        if path in ("/api/ets2/telemetry", ""):
            self._send(json.dumps(pump.STATE["ets2"]).encode(),
                       "application/json")
        elif path == "/api/dash":
            self._send(pump.STATE["dash"], "application/json")
        elif path == "/api/schema":
            self._send(json.dumps(schema_info()).encode(), "application/json")
        elif path == "/dashboard" or path.startswith("/dashboard/"):
            self._dashboard(path)
        elif path == "/stream":
            self._stream()
        else:
            self.send_error(404)

    do_POST = do_GET

    def _dashboard(self, path):
        spec = path[len("/dashboard/"):] if path.startswith("/dashboard/") \
            else DEFAULT_DASHBOARD
        if spec.endswith("/manifest.json"):
            manifest = dashboard_manifest(spec[:-len("/manifest.json")])
            if manifest is None:
                self.send_error(404)
            else:
                self._file(manifest, "application/json")
            return
        target = dashboard_file(spec)
        if target is None:
            self.send_error(404)
        else:
            self._file(target, "text/html; charset=utf-8")

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
        import threading
        threading.Thread(target=server6.serve_forever, daemon=True).start()
    except OSError:
        pass  # IPv6 indisponible : IPv4 seul suffit
    return server
