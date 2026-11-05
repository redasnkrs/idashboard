import http.client
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from adapters.fake import FakeSource
from core import pump, themes
from core.schema import validate
from core.server import serve


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.old_state = themes.STATE_FILE
        themes.STATE_FILE = Path(cls.tmp.name) / "active.json"
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

    def test_api_dashboards(self):
        status, _, body = self.get("/api/dashboards")
        self.assertEqual(200, status)
        data = json.loads(body)
        specs = {item["spec"] for item in data["dashboards"]}
        self.assertEqual({"course/acevo-cluster", "course/acevo-minimal"},
                         specs)
        self.assertEqual("course/acevo-cluster", data["default"])
        for item in data["dashboards"]:
            self.assertTrue(item["preview_url"])
            self.assertTrue(item["settings_url"].startswith("/settings"))

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


if __name__ == "__main__":
    unittest.main()
