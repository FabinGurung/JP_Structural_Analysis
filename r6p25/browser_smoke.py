"""Real Chromium desktop/mobile interactivity and scroll QA for R6.25."""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading

from playwright.sync_api import sync_playwright


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*a):pass


def check(site:Path,screenshots:Path)->None:
    screenshots.mkdir(exist_ok=True,parents=True)
    handler=partial(QuietHandler,directory=str(site.resolve()))
    server=ThreadingHTTPServer(("127.0.0.1",0),handler)
    t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
    url=f"http://127.0.0.1:{server.server_port}/r6p25.html"
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            for name,width,height in [("mobile",390,844),("desktop",1440,1000)]:
                page=browser.new_page(viewport={"width":width,"height":height},device_scale_factor=1)
                errors=[]
                page.on("pageerror",lambda error: errors.append(str(error)))
                page.goto(url,wait_until="networkidle")
                page.wait_for_function("document.getElementById('load-state').textContent.includes('Pinned CAD source')")
                assert not errors,errors
                assert page.locator("#ncols").inner_text()=="23"
                assert page.locator("#nfoot").inner_text()=="21"
                assert page.locator("#nbeams").inner_text()=="32 · 17 · 17"
                assert page.locator("#level-beams").inner_text().startswith("32 / 32")
                assert page.locator("#plan circle.column-mark").count()==23
                page.locator("#plan circle.column-mark").first.click()
                assert "SOURCE: original ground-floor DXF column marker" in page.locator("#selection").inner_text()
                page.select_option("#floor","FF")
                assert "17 / 17" in page.locator("#level-beams").inner_text()
                assert page.locator("#plan line.beam").count()==17
                page.locator("#plan line.beam").first.click()
                assert "End I candidate" in page.locator("#selection").inner_text()
                page.select_option("#scope","gap")
                assert page.locator("#plan line.beam").count()>0
                page.select_option("#scope","all")
                page.select_option("#floor","SF")
                assert "17 / 17" in page.locator("#level-beams").inner_text()
                page.select_option("#floor","GF")
                assert page.locator("#plan rect.found").count()==21
                page.locator("#show-footings").uncheck()
                assert page.locator("#plan rect.found").count()==0
                page.locator("#show-ties").uncheck()
                assert page.locator("#plan line.joint-tie").count()==0
                dims=page.evaluate("""({width:innerWidth,scroll:document.documentElement.scrollWidth,
                    body:document.body.scrollWidth,main:document.querySelector('main').getBoundingClientRect().width})""")
                assert dims["scroll"]<=dims["width"]+1,dims
                assert dims["body"]<=dims["width"]+1,dims
                page.screenshot(path=str(screenshots/f"{name}.png"),full_page=True)
                print("R6P25_"+name.upper()+"_QA_PASS",dims)
                page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--site-dir",type=Path,required=True)
    p.add_argument("--screenshots",type=Path,required=True)
    a=p.parse_args()
    check(a.site_dir,a.screenshots)
