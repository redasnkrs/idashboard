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

SWIPE_JS = """(dx) => {
  const mk = x => new Touch({identifier: 1, target: document.body,
    clientX: x, clientY: 300, pageX: x, pageY: 300});
  const ev = (type, touches, changed) => document.dispatchEvent(
    new TouchEvent(type, {touches, changedTouches: changed,
                          bubbles: true, cancelable: true}));
  ev('touchstart', [mk(800)], [mk(800)]);
  ev('touchend', [], [mk(800 + dx)]);
}"""


def _post(url, payload):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.read()


def _delete(url):
    req = urllib.request.Request(url, method="DELETE")
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
                    for height in (600, 560):
                        page = new_page(1024, height)
                        page.goto(
                            "%s%s?demo&nogame=1" % (base, item["url"]),
                            wait_until="load")
                        page.wait_for_timeout(1200)
                        path = OUT / ("%s-%s-1024x%d.png" % (
                            item["id"], theme_id, height))
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

            sample = {
                "name": "Studio sample", "category": "custom",
                "description": "Generated by visual_check",
                "background": "ink", "canvas": {"grid": 16},
                "widgets": [
                    {"type": "value", "x": 40, "y": 40, "w": 260, "h": 100,
                     "label": "SPEED", "field": "v", "format": "int",
                     "unit": "auto", "size": 72, "color": "ivory",
                     "labelColor": "muted", "unitColor": "muted"},
                    {"type": "gauge", "x": 360, "y": 40, "w": 260, "h": 260,
                     "field": "r", "maxField": "rm", "max": 10000,
                     "label": "RPM", "format": "int", "unit": "none",
                     "size": 46, "labelSize": 10, "color": "ivory",
                     "accent": "amber", "bg": "off", "redline": .89},
                    {"type": "icon", "x": 700, "y": 40, "w": 44, "h": 44,
                     "icon": "low-beam", "field": "low",
                     "onColor": "green", "offColor": "dim"},
                    {"type": "media", "x": 40, "y": 320, "w": 280, "h": 260},
                    {"type": "map", "x": 360, "y": 320, "w": 260, "h": 260,
                     "field": "npos", "color": "amber", "roadColor": "dim",
                     "dotColor": "amber"},
                    {"type": "clock", "x": 700, "y": 320, "w": 240, "h": 80,
                     "showDate": True, "showTime": True, "locale": "en-US",
                     "size": 26, "color": "ivory"},
                ],
            }
            sample_id = None
            try:
                created = json.loads(_post(base + "/api/layouts", sample))
                if created.get("ok"):
                    sample_id = created["layout"]["id"]
                    page = new_page()
                    page.goto("%s/dashboard/custom/%s?demo" %
                              (base, sample_id), wait_until="load")
                    page.wait_for_timeout(1200)
                    path = OUT / "custom-sample-1024x600.png"
                    page.screenshot(path=str(path))
                    print(path)
                    page.close()
                    page = new_page(1440, 900)
                    page.goto("%s/studio?id=%s" % (base, sample_id),
                              wait_until="networkidle")
                    page.wait_for_timeout(1500)
                    path = OUT / "studio-1440x900.png"
                    page.screenshot(path=str(path))
                    print(path)
                    page.close()
                else:
                    errors.append("sample layout not created")
            except Exception as exc:
                errors.append("sample layout: %s" % exc)
            finally:
                if sample_id:
                    _delete(base + "/api/layouts/" + sample_id)

            ctx = browser.new_context(viewport={"width": 1024, "height": 600},
                                      has_touch=True)
            page = ctx.new_page()
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(base + "/dashboard/course/acevo-cluster?demo",
                      wait_until="load")
            page.wait_for_timeout(800)
            page.evaluate(SWIPE_JS, -150)
            page.wait_for_timeout(1400)
            expected = base + "/dashboard/course/acevo-minimal?demo"
            if page.url != expected:
                errors.append("swipe gauche: %s" % page.url)
            else:
                page.evaluate(SWIPE_JS, 150)
                page.wait_for_timeout(1400)
                expected = base + "/dashboard/course/acevo-cluster?demo"
                if page.url != expected:
                    errors.append("swipe droite: %s" % page.url)
            print("swipe:", page.url)
            ctx.close()

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
