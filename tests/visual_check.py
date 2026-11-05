"""Captures Playwright des tableaux de bord et des thèmes.

Usage : python -m tests.visual_check
Les images vont dans tests/screenshots/ (ignore par git).
"""
import json
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path

from adapters.fake import FakeSource
from core import pump, themes
from core.server import serve

OUT = Path(__file__).resolve().parent / "screenshots"
THEMES = ("ambre-ivoire", "rouge-sport", "vert")


def _post(url, payload):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.read()


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("Playwright manquant : pip install playwright && "
                 "python -m playwright install chromium")

    tmp = tempfile.TemporaryDirectory()
    old_state = themes.STATE_FILE
    themes.STATE_FILE = Path(tmp.name) / "active.json"
    threading.Thread(target=pump.poll_loop, args=(FakeSource(), False),
                     daemon=True).start()
    server = serve(0)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    OUT.mkdir(exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for theme_id in THEMES:
                _post("http://127.0.0.1:%d/api/themes" % port, {
                    "scope": "global", "active": theme_id, "overrides": {},
                })
                for height in (600, 560):
                    page = browser.new_page(
                        viewport={"width": 1024, "height": height})
                    page.goto(
                        "http://127.0.0.1:%d/dashboard?demo&nogame=1" % port,
                        wait_until="load")
                    page.wait_for_timeout(1200)
                    path = OUT / ("%s-1024x%d.png" % (theme_id, height))
                    page.screenshot(path=str(path))
                    print(path)
                    page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        themes.STATE_FILE = old_state
        tmp.cleanup()


if __name__ == "__main__":
    main()
