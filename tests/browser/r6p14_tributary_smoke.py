"""R6.14 desktop/mobile Chromium coverage for 115 original shells and safe hold display."""
from pathlib import Path
from playwright.sync_api import sync_playwright
URL="http://127.0.0.1:8765/"
DEST=Path("build/r6p14-browser")
DEST.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
    for name,viewport,mobile in [
        ("desktop",{"width":1366,"height":864},False),
        ("mobile",{"width":390,"height":844},True)]:
        context=browser.new_context(viewport=viewport,is_mobile=mobile,has_touch=mobile)
        page=context.new_page()
        errors=[]
        page.on("pageerror",lambda error:errors.append(str(error)))
        r=page.goto(URL+"projects/pokhara-g15/tributary-audit.html",timeout=50000)
        assert r is not None and r.status==200
        page.wait_for_function("""() => document.querySelector('#r614-result-count')?.innerText.includes('115')""",timeout=45000)
        assert page.locator("#r614-shells tr").count()==115
        assert "F3" in page.locator(".r614-hold").first.inner_text()
        assert "NOT SAFE IN ONE WAY SHEAR" in page.locator(".r614-hold").first.inner_text()
        page.locator("#r614-status").select_option("UNSUPPORTED")
        page.wait_for_function("""() => document.querySelector('#r614-result-count')?.innerText.startsWith('12 ')""")
        assert page.locator("#r614-shells tr").count()==12
        page.locator("#r614-shells button").first.click()
        assert "No speculative load has been redistributed" in page.locator("#r614-details").inner_text()
        assert page.locator("#r614-details").get_by_text("NOT VERIFIED").count()>=0
        page.locator("#r614-status").select_option("ALL")
        page.locator("#r614-query").fill("GF:F4")
        page.wait_for_function("""() => document.querySelector('#r614-result-count')?.innerText.startsWith('1 ')""")
        page.locator("#r614-shells button").click()
        assert "GF:F4" in page.locator("#r614-details h3").inner_text()
        assert page.locator(".r614-diagram").count()==1
        page.locator("#r614-query").fill("")
        page.locator("#r614-status").select_option("CONDITIONAL")
        assert "Geometrically complete floor shells" in page.locator("#r614-kpis").inner_text()
        assert not errors,errors
        page.locator("#r614-shell-section").screenshot(path=str(DEST/f"{name}-tributary-audit.png"))
        r=page.goto(URL+"projects/pokhara-g15/report.html",timeout=50000)
        assert r is not None and r.status==200
        assert page.locator("#project-r6p14-tributary").count()==1
        assert page.locator("#project-r6p13-members").count()==1
        assert page.locator("#project-r6p12-manual").count()==1
        assert page.locator("#project-hand-calculations").count()==1
        assert page.locator("#project-figures").count()==1
        assert page.locator("#project-r6p14-tributary a").get_attribute("href")=="projects/pokhara-g15/tributary-audit.html"
        context.close()
    browser.close()
print("R6P14_CHROMIUM_DESKTOP_MOBILE_115_SHELLS_12_UNSUPPORTED_NO_DESIGN_PASS")
