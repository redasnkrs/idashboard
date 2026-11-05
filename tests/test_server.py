import http.client
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from adapters.fake import FakeSource
from core import game, media, pump, studio, themes
from core.schema import validate
from core.server import serve


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.old_state = themes.STATE_FILE
        themes.STATE_FILE = Path(cls.tmp.name) / "active.json"
        cls.old_game = game.GAME_FILE
        game.GAME_FILE = Path(cls.tmp.name) / "game.json"
        cls.old_studio = (studio.LAYOUTS_DIR, studio.PREVIEWS_DIR,
                          studio.ICONS_DIR)
        base = Path(cls.tmp.name) / "custom"
        studio.LAYOUTS_DIR = base / "layouts"
        studio.PREVIEWS_DIR = base / "previews"
        studio.ICONS_DIR = base / "icons"
        threading.Thread(target=pump.poll_loop, args=(FakeSource(), False),
                         daemon=True).start()
        cls.server = serve(0)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        themes.STATE_FILE = cls.old_state
        game.GAME_FILE = cls.old_game
        (studio.LAYOUTS_DIR, studio.PREVIEWS_DIR,
         studio.ICONS_DIR) = cls.old_studio
        cls.tmp.cleanup()

    def get(self, path, timeout=5):
        conn = http.client.HTTPConnection("127.0.0.1", self.port,
                                          timeout=timeout)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read()
        conn.close()
        return resp.status, resp.getheader("Content-Type") or "", body

    def post(self, path, payload, timeout=5):
        body = json.dumps(payload).encode()
        conn = http.client.HTTPConnection("127.0.0.1", self.port,
                                          timeout=timeout)
        conn.request("POST", path, body=body,
                     headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        return resp.status, data

    def delete(self, path, timeout=5):
        conn = http.client.HTTPConnection("127.0.0.1", self.port,
                                          timeout=timeout)
        conn.request("DELETE", path)
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        return resp.status, data

    def wait_for_game(self):
        deadline = time.time() + 3
        while time.time() < deadline:
            _, _, body = self.get("/api/dash")
            dash = json.loads(body)
            if dash.get("c"):
                return dash
            time.sleep(0.05)
        self.fail("la fausse source n'a rien produit")

    def test_api_dash(self):
        dash = self.wait_for_game()
        self.assertEqual([], validate(dash))

    def test_api_schema(self):
        status, _, body = self.get("/api/schema")
        self.assertEqual(200, status)
        info = json.loads(body)
        self.assertEqual("course", info["name"])
        self.assertIn("v", info["keys"])

    def test_dashboard_default(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", "/dashboard?demo")
        resp = conn.getresponse()
        resp.read()
        self.assertEqual(302, resp.status)
        location = resp.getheader("Location")
        self.assertEqual("/dashboard/course/acevo-cluster?demo", location)
        conn.close()
        status, ctype, body = self.get(location)
        self.assertEqual(200, status)
        self.assertIn("text/html", ctype)
        self.assertIn(b'viewBox="0 0 1024 600"', body)

    def test_home_page(self):
        status, ctype, body = self.get("/")
        self.assertEqual(200, status)
        self.assertIn("text/html", ctype)
        self.assertIn("Choisis ton compteur".encode(), body)
        self.assertIn("Lancer AC Evo".encode(), body)

    def test_api_dashboards(self):
        status, _, body = self.get("/api/dashboards")
        self.assertEqual(200, status)
        data = json.loads(body)
        specs = {item["spec"] for item in data["dashboards"]}
        self.assertEqual({"course/acevo-cluster", "course/acevo-minimal",
                          "course/acevo-cockpit"}, specs)
        self.assertEqual("course/acevo-cluster", data["default"])
        for item in data["dashboards"]:
            self.assertTrue(item["preview_url"])
            self.assertTrue(item["settings_url"].startswith("/settings"))

    def test_game_api(self):
        status, _, body = self.get("/api/game")
        self.assertEqual(200, status)
        info = json.loads(body)
        self.assertEqual(game.DEFAULT_APP_ID, info["app_id"])
        self.assertIn("exe_exists", info)
        self.assertIn("detected", info)

    def test_game_settings_roundtrip(self):
        status, body = self.post("/api/game", {"exe": "/tmp/assetto-test.exe"})
        self.assertEqual(200, status)
        self.assertTrue(json.loads(body)["ok"])
        _, _, raw = self.get("/api/game")
        info = json.loads(raw)
        self.assertEqual("/tmp/assetto-test.exe", info["exe"])
        self.assertFalse(info["exe_exists"])

    def test_game_settings_reject_bad_payload(self):
        status, body = self.post("/api/game", {"exe": 42})
        self.assertEqual(400, status)
        self.assertFalse(json.loads(body)["ok"])

    def test_game_launch_route(self):
        old = game.launch
        game.launch = lambda: {"ok": True, "method": "test"}
        try:
            status, body = self.post("/api/game/launch", {})
        finally:
            game.launch = old
        self.assertEqual(200, status)
        self.assertTrue(json.loads(body)["ok"])

    def test_game_detect_route(self):
        old = game.detect
        game.detect = lambda: "/tmp/assetto-test.exe"
        try:
            status, body = self.post("/api/game/detect", {})
        finally:
            game.detect = old
        self.assertEqual(200, status)
        data = json.loads(body)
        self.assertTrue(data["ok"])
        self.assertEqual("/tmp/assetto-test.exe", data["exe"])

    def test_media_api(self):
        status, _, body = self.get("/api/media")
        self.assertEqual(200, status)
        info = json.loads(body)
        self.assertIn("platform", info)
        self.assertIn("has_art", info)

    def test_media_control_rejects_bad_action(self):
        status, body = self.post("/api/media/control", {"action": "nope"})
        self.assertEqual(400, status)
        self.assertFalse(json.loads(body)["ok"])

    def test_media_control_route(self):
        old = media.control
        media.control = lambda action: {"ok": True, "action": action}
        try:
            status, body = self.post("/api/media/control",
                                     {"action": "playpause"})
        finally:
            media.control = old
        self.assertEqual(200, status)
        self.assertEqual("playpause", json.loads(body)["action"])

    def test_media_art_route(self):
        png = b"\x89PNG\r\n\x1a\nidash"
        old = media.art
        media.art = lambda: (png, "image/png")
        try:
            status, ctype, body = self.get("/api/media/art")
        finally:
            media.art = old
        self.assertEqual(200, status)
        self.assertIn("image/png", ctype)
        self.assertEqual(png, body)

    def test_media_art_missing(self):
        old = media.art
        media.art = lambda: (None, "image/jpeg")
        try:
            status, _, _ = self.get("/api/media/art")
        finally:
            media.art = old
        self.assertEqual(404, status)

    def test_studio_page(self):
        status, ctype, body = self.get("/studio")
        self.assertEqual(200, status)
        self.assertIn("text/html", ctype)
        self.assertIn(b"idash", body)
        self.assertIn(b"Studio", body)

    def test_studio_assets(self):
        status, ctype, body = self.get("/studio/runtime.js")
        self.assertEqual(200, status)
        self.assertIn("javascript", ctype)
        self.assertIn(b"IDashStudio", body)

    def test_studio_layout_flow(self):
        payload = {
            "name": "Server Studio", "category": "custom",
            "background": "ink", "canvas": {"grid": 16},
            "widgets": [
                {"type": "value", "x": 40, "y": 40, "w": 220, "h": 90,
                 "label": "SPEED", "field": "v", "format": "int",
                 "unit": "auto", "size": 64},
            ],
            "preview_svg": ('<svg xmlns="http://www.w3.org/2000/svg">'
                            '<rect width="10" height="10"/></svg>'),
        }
        status, body = self.post("/api/layouts", payload)
        self.assertEqual(200, status)
        data = json.loads(body)
        self.assertTrue(data["ok"])
        layout_id = data["layout"]["id"]
        self.assertEqual("server-studio", layout_id)
        status, _, raw = self.get("/api/layouts/" + layout_id)
        self.assertEqual(200, status)
        self.assertEqual("Server Studio", json.loads(raw)["layout"]["name"])
        status, _, raw = self.get("/api/dashboards")
        specs = [d["spec"] for d in json.loads(raw)["dashboards"]]
        self.assertIn("custom/server-studio", specs)
        status, _, page = self.get("/dashboard/custom/" + layout_id)
        self.assertEqual(200, status)
        self.assertIn(b"window.__IDASH__", page)
        self.assertIn(("custom/" + layout_id).encode(), page)
        status, ctype, preview = self.get(
            "/custom/previews/" + layout_id + ".svg")
        self.assertEqual(200, status)
        self.assertIn("image/svg+xml", ctype)
        self.assertEqual(b"<svg", preview[:4])
        status, _ = self.delete("/api/layouts/" + layout_id)
        self.assertEqual(200, status)
        status, _, _ = self.get("/dashboard/custom/" + layout_id)
        self.assertEqual(404, status)

    def test_studio_layout_rejects_bad_payload(self):
        status, body = self.post("/api/layouts", {"name": ""})
        self.assertEqual(400, status)
        self.assertFalse(json.loads(body)["ok"])

    def test_studio_icons_flow(self):
        import base64
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><circle cx="6" cy="6" r="5"/></svg>'
        data = "data:image/svg+xml;base64," + base64.b64encode(svg).decode()
        status, body = self.post("/api/icons", {"name": "Dot", "data": data})
        self.assertEqual(200, status)
        icon = json.loads(body)["icon"]
        status, _, raw = self.get("/api/icons")
        self.assertEqual(200, status)
        self.assertIn(icon["id"], [i["id"] for i in json.loads(raw)["icons"]])
        status, ctype, body = self.get("/custom/icons/" + icon["id"])
        self.assertEqual(200, status)
        self.assertIn("image/svg+xml", ctype)
        self.assertIn(b"circle", body)
        status, _ = self.delete("/api/icons/" + icon["id"])
        self.assertEqual(200, status)

    def test_dashboard_injects_meta(self):
        status, _, body = self.get("/dashboard/course/acevo-minimal")
        self.assertEqual(200, status)
        self.assertIn(b"window.__IDASH__", body)
        self.assertIn(b'"spec": "course/acevo-minimal"', body)
        self.assertIn(b'"game_id": "acevo"', body)
        self.assertIn(b"idash-swipe", body)
        self.assertIn(b"/api/dashboards", body)

    def test_dashboard_asset(self):
        status, ctype, body = self.get(
            "/dashboard/course/acevo-cluster/preview.png")
        self.assertEqual(200, status)
        self.assertIn("image/png", ctype)
        self.assertTrue(body.startswith(b"\x89PNG"))

    def test_launch_rejects_unknown_dashboard(self):
        status, body = self.post("/api/launch", {"dashboard": "nope"})
        self.assertEqual(400, status)
        self.assertFalse(json.loads(body)["ok"])

    def test_theme_reset(self):
        self.post("/api/themes", {"scope": "game", "key": "acevo",
                                  "overrides": {"colors": {"ink": "#0a0b0c"}}})
        _, _, raw = self.get("/api/themes/active?game=acevo")
        self.assertEqual("#0a0b0c", json.loads(raw)["colors"]["ink"])
        status, body = self.post("/api/themes/reset",
                                 {"scope": "game", "key": "acevo"})
        self.assertEqual(200, status)
        self.assertTrue(json.loads(body)["ok"])
        _, _, raw = self.get("/api/themes/active?game=acevo")
        self.assertNotEqual("#0a0b0c", json.loads(raw)["colors"]["ink"])

    def test_dashboard_named_and_shortcut(self):
        for path in ("/dashboard/course/acevo-cluster",
                     "/dashboard/acevo-cluster"):
            status, _, body = self.get(path)
            self.assertEqual(200, status, path)
            self.assertIn(b"Tableau de bord", body)

    def test_dashboard_manifest(self):
        status, ctype, body = self.get(
            "/dashboard/course/acevo-cluster/manifest.json")
        self.assertEqual(200, status)
        self.assertIn("application/json", ctype)
        manifest = json.loads(body)
        self.assertEqual("acevo-cluster", manifest["id"])
        self.assertEqual("course", manifest["schema"])

    def test_unknown_dashboard(self):
        status, _, body = self.get("/dashboard/does-not-exist")
        self.assertEqual(404, status)
        status, _, body = self.get("/dashboard/../config.py")
        self.assertEqual(404, status)
        status, _, body = self.get(
            "/dashboard/course/acevo-cluster/../acevo-minimal/index.html")
        self.assertEqual(404, status)

    def test_stream(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", "/stream")
        resp = conn.getresponse()
        self.assertEqual(200, resp.status)
        self.assertIn("text/event-stream", resp.getheader("Content-Type"))
        messages = []
        while len(messages) < 3:
            line = resp.fp.readline()
            if not line:
                break
            if line.startswith(b"data: "):
                messages.append(json.loads(line[len(b"data: "):]))
        conn.close()
        self.assertGreaterEqual(len(messages), 3)
        self.assertEqual([], validate(messages[-1]))

    def test_ets2_telemetry(self):
        self.wait_for_game()
        status, _, body = self.get("/api/ets2/telemetry")
        self.assertEqual(200, status)
        payload = json.loads(body)
        self.assertTrue(payload["game"]["connected"])
        self.assertIn("truck", payload)

    def test_themes_list(self):
        status, _, body = self.get("/api/themes")
        self.assertEqual(200, status)
        info = json.loads(body)
        self.assertIn("ambre-ivoire", info["themes"])
        self.assertIn("state", info)

    def test_theme_active(self):
        status, _, body = self.get("/api/themes/active?game=acevo")
        self.assertEqual(200, status)
        theme = json.loads(body)
        self.assertIn("colors", theme)
        self.assertIn("blocks", theme)

    def test_save_theme(self):
        status, body = self.post("/api/themes", {
            "scope": "global",
            "active": "vert",
            "overrides": {
                "colors": {"amber": "#00ff00"},
                "units": {"speed": "mph"},
                "blocks": {"fuel": False},
            },
        })
        self.assertEqual(200, status)
        self.assertTrue(json.loads(body)["ok"])
        _, _, raw = self.get("/api/themes/active")
        theme = json.loads(raw)
        self.assertEqual("vert", theme["id"])
        self.assertEqual("#00ff00", theme["colors"]["amber"])
        self.assertEqual("mph", theme["units"]["speed"])

    def test_save_theme_rejects_bad_payload(self):
        status, _ = self.post("/api/themes", {"active": "nope"})
        self.assertEqual(400, status)

    def test_settings_page(self):
        status, ctype, body = self.get("/settings")
        self.assertEqual(200, status)
        self.assertIn("text/html", ctype)
        self.assertIn(b"R\xc3\xa9glages", body)
        self.assertIn(b"Chemin d'Assetto Corsa Evo", body)


if __name__ == "__main__":
    unittest.main()
