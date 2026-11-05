import http.client
import json
import threading
import time
import unittest

from adapters.fake import FakeSource
from core import pump
from core.schema import validate
from core.server import serve


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        threading.Thread(target=pump.poll_loop, args=(FakeSource(), False),
                         daemon=True).start()
        cls.server = serve(0)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def get(self, path, timeout=5):
        conn = http.client.HTTPConnection("127.0.0.1", self.port,
                                          timeout=timeout)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read()
        conn.close()
        return resp.status, resp.getheader("Content-Type") or "", body

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
        status, ctype, body = self.get("/dashboard")
        self.assertEqual(200, status)
        self.assertIn("text/html", ctype)
        self.assertIn(b'viewBox="0 0 1024 600"', body)

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


if __name__ == "__main__":
    unittest.main()
