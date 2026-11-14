"""Desktop/mobile real-browser QA of independent R6.26 report book."""
from __future__ import annotations
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright

class Files(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--site-dir",type=Path,required=True)
    p.add_argument("--screenshots",type=Path,required=True)
    a=p.parse_args()
    a.screenshots.mkdir(parents=True,exist_ok=True)
    server=ThreadingHTTPServer(("127.0.0.1",0),partial(Files,directory=str(a.site_dir.resolve())))
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    url=f"http://127.0.0.1:{server.server_port}/r6p26-report.html"
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(headless=True)
            for name,width,height in (("mobile",390,844),("desktop",1440,900)):
                page=browser.new_page(viewport={"width":width,"height":height})
                errors=[]
                page.on("pageerror",lambda e: errors.append(str(e)))
                response=page.goto(url,wait_until="networkidle")
                assert response is not None and response.status==200
                page.wait_for_function("document.querySelector('[data-field=\"eq\"]').textContent==='PASS'")
                assert not errors,errors
                assert page.locator('[data-field="columns"]').inner_text()=="23"
                assert page.locator('[data-field="cases"]').inner_text()=="4"
                assert page.locator("#member-results tr").count()==17
                assert page.locator("#base-results tr").count()==23
                assert page.locator("#displacement-results tr").count()==3
                assert page.locator("#source-digest").inner_text().strip()
                assert "NOT SAFE IN ONE WAY SHEAR" in page.locator("#design").inner_text()
                page.locator("#case-select").select_option("PX10")
                assert page.locator("#current-case").inner_text().startswith("PX10")
                assert page.locator("#case-equilibrium").inner_text()!=""
                page.locator("#case-select").select_option("LL")
                assert "kN" in page.locator("#case-load").inner_text()
                page.locator("#floor-select").select_option("FF")
                assert page.locator("#frame-visual").get_attribute("aria-label").endswith("FF level")
                page.locator("#floor-select").select_option("ALL")
                first=page.locator("#frame-visual line.member-hit").first
                first.focus()
                page.keyboard.press("Enter")
                assert "Geometry:" in page.locator("#member-detail").inner_text()
                assert "CURRENT CASE" in page.locator("#member-detail").inner_text()
                sizes=page.evaluate("""({viewport:innerWidth,doc:document.documentElement.scrollWidth,body:document.body.scrollWidth})""")
                assert sizes["doc"]<=sizes["viewport"]+1,sizes
                assert sizes["body"]<=sizes["viewport"]+1,sizes
                target=a.screenshots/(name+".png")
                page.screenshot(path=str(target),full_page=True)
                assert target.stat().st_size>20000
                print("R6P26_"+name.upper()+"_REPORT_QA_PASS",sizes)
                page.close()
            browser.close()
    finally:
        server.shutdown();server.server_close()

if __name__=="__main__":
    main()
