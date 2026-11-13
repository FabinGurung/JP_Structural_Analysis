"""R6.24 real-browser desktop/mobile UI smoke of synthetic Pages viewer.

QA-only harness runs with a local HTTP server (the site is read-only).
No client or source-private data is used. Requires playwright==1.56.0 and
Chromium. Does not certify complete accessibility or engineering results.
"""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright, expect


class QuietFiles(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        return


def verify_page(page, *, mobile: bool, screenshots: Path):
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    response = page.goto(page.context.base_url + "/r6p23.html",
                         wait_until="domcontentloaded")
    assert response is not None and response.status == 200
    expect(page.locator("#load-status")).to_have_text(
        "Synthetic OpenSees calculations verified", timeout=30000)
    assert page.locator("#shell-count").inner_text() == "31"
    assert page.locator("#dead-load").inner_text() == "339 kN"
    assert page.locator("#live-load").inner_text() == "62 kN"
    assert page.locator("#opening-count").inner_text() == "1"
    assert page.locator("#plan rect.shell").count() == 16
    assert page.locator("#support-body tr").count() == 4
    assert page.locator("#convergence-body tr").count() == 4
    page.locator("#plan rect.shell").first.click()
    assert "Shell area" in page.locator("#selected-detail").inner_text()
    # Genuine keyboard activation and inspectable signed member local I/J.
    beam = page.locator("#plan line.beam").first
    beam.focus()
    page.keyboard.press("Enter")
    assert "Local I:" in page.locator("#selected-detail").inner_text()
    assert "Local J:" in page.locator("#selected-detail").inner_text()
    page.locator("#floor").select_option("2")
    assert page.locator("#plan rect.shell").count() == 15
    assert page.locator("#plan rect.opening").count() == 1
    page.locator("#mode").select_option("RIGID_INPLANE_MPC")
    page.locator("#case").select_option("HX")
    assert "kN" in page.locator("#gravity").inner_text()
    assert page.locator("#support-body tr").count() == 4
    assert page.locator("#selected-detail").inner_text().startswith("Select")
    page.locator("#case").select_option("DL")
    assert "339 kN" in page.locator("#gravity").inner_text()
    if mobile:
        width = page.evaluate("document.documentElement.scrollWidth")
        viewport = page.evaluate("window.innerWidth")
        assert width <= viewport + 3, (
            "Unexpected horizontal page overflow", width, viewport)
    screenshots.mkdir(parents=True, exist_ok=True)
    path = screenshots / ("mobile.png" if mobile else "desktop.png")
    page.screenshot(path=str(path), full_page=True)
    assert path.stat().st_size > 20000
    assert not errors, errors


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args=parser.parse_args()
    site=args.site_dir.resolve()
    assert (site/"r6p23.html").is_file()
    assert (site/"data/r6p23-preview.json").is_file()
    server=ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(QuietFiles, directory=str(site)))
    thread=Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        address=f"http://127.0.0.1:{server.server_port}"
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            for mobile in (False, True):
                viewport={"width":390 if mobile else 1440,
                          "height":844 if mobile else 900}
                page=browser.new_page(viewport=viewport, base_url=address)
                verify_page(page,mobile=mobile,screenshots=args.out_dir)
                page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    print("R6P24_DESKTOP_MOBILE_REAL_BROWSER_QA_PASS")


if __name__=="__main__":
    main()
