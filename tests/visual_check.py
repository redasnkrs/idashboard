"""Captures Playwright des tableaux de bord, de l'accueil et des reglages.

Usage : python -m tests.visual_check
Les captures de travail vont dans tests/screenshots/ (ignore par git).
Les apercus des compteurs (preview.png) sont ecrits dans leur dossier.
"""
import json
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path

from adapters.fake import FakeSource
from core import catalog, pump, themes
from core.config import DASHBOARDS_DIR
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
    base = "http://127.0.0.1:%d" % port
    threading.Thread(target=server.serve_forever, daemon=True).start()

    OUT.mkdir(exist_ok=True)
    errors = []
    dashboards = catalog.list_dashboards()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()

            def new_page(width=1024, height=600):
                page = browser.new_page(
                    viewport={"width": width, "height": height})
                page.on("pageerror", lambda e: errors.append(str(e)))
                return page

            for item in dashboards:
                for theme_id in THEMES:
                    _post(base + "/api/themes", {
                        "scope": "global", "active": theme_id,
                        "overrides": {},
                    })
                    page = new_page()
                    page.goto("%s%s?demo&nogame=1" % (base, item["url"]),
                              wait_until="load")
                    page.wait_for_timeout(1200)
                    path = OUT / ("%s-%s.png" % (item["id"], theme_id))
                    page.screenshot(path=str(path))
                    print(path)
                    page.close()

            _post(base + "/api/themes", {
                "scope": "global", "active": "ambre-ivoire",
                "overrides": {},
            })
            for item in dashboards:
                page = new_page()
                page.goto("%s%s?demo&nogame=1" % (base, item["url"]),
                          wait_until="load")
                page.wait_for_timeout(1200)
                target = DASHBOARDS_DIR / item["spec"] / "preview.png"
                page.screenshot(path=str(target))
                print(target)
                page.close()

            for item in dashboards:
                page = new_page()
                page.goto("%s%s?demo&ign=off&nogame=1" % (base, item["url"]),
                          wait_until="load")
                page.wait_for_timeout(1200)
                if not page.eval_on_selector(
                        "#d", "el => el.classList.contains('sleep')"):
                    errors.append("%s: veille absente" % item["id"])
                if page.eval_on_selector(
                        "#spd", "el => el.textContent") != "0":
                    errors.append("%s: vitesse non remise a zero" % item["id"])
                path = OUT / ("%s-off.png" % item["id"])
                page.screenshot(path=str(path))
                print(path)
                page.close()

                page = new_page()
                page.goto("%s%s?demo&ign=wake&nogame=1" % (base, item["url"]),
                          wait_until="load")
                page.wait_for_timeout(2900)
                if page.eval_on_selector(
                        "#d", "el => el.classList.contains('sleep')"):
                    errors.append("%s: reveil absent" % item["id"])
                path = OUT / ("%s-wake.png" % item["id"])
                page.screenshot(path=str(path))
                print(path)
                page.close()

            page = new_page(1400, 980)
            page.goto(base + "/", wait_until="networkidle")
            page.wait_for_timeout(500)
            path = OUT / "home-1400x980.png"
            page.screenshot(path=str(path))
            print(path)
            page.close()

            page = new_page(1400, 980)
            page.goto(base + "/settings?dashboard=" + dashboards[0]["spec"],
                      wait_until="load")
            page.wait_for_timeout(1500)
            path = OUT / "settings-1400x980.png"
            page.screenshot(path=str(path))
            print(path)
            page.close()

            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        themes.STATE_FILE = old_state
        tmp.cleanup()

    if errors:
        print("ERREURS JS :", *errors, sep="\n  ")
        sys.exit(1)
    print("OK : aucune erreur JS")


if __name__ == "__main__":
    main()
