"""Captures Playwright du tableau de bord a 1024x600 et 1024x560.

Usage : python -m tests.visual_check
Les images vont dans tests/screenshots/ (ignore par git).
"""
import sys
import threading
from pathlib import Path

from adapters.fake import FakeSource
from core import pump
from core.server import serve

OUT = Path(__file__).resolve().parent / "screenshots"


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("Playwright manquant : pip install playwright && "
                 "python -m playwright install chromium")

    threading.Thread(target=pump.poll_loop, args=(FakeSource(), False),
                     daemon=True).start()
    server = serve(0)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    OUT.mkdir(exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for height in (600, 560):
                page = browser.new_page(
                    viewport={"width": 1024, "height": height})
                page.goto("http://127.0.0.1:%d/dashboard?demo" % port,
                          wait_until="load")
                page.wait_for_timeout(1200)
                path = OUT / ("dashboard-1024x%d.png" % height)
                page.screenshot(path=str(path))
                print(path)
                page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
