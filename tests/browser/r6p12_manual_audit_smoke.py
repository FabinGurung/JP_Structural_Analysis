"""R6.12 desktop/mobile Chromium smoke, requires locally built Pages site."""
from pathlib import Path
from playwright.sync_api import sync_playwright
URL="http://127.0.0.1:8765/"
DEST=Path("build/r6p12-browser")
DEST.mkdir(parents=True,exist_ok=True)

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
    for name,viewport,mobile in [
        ("desktop",{"width":1440,"height":900},False),
        ("mobile",{"width":390,"height":844},True)]:
        ctx=browser.new_context(viewport=viewport,is_mobile=mobile,has_touch=mobile)
        page=ctx.new_page()
        errors=[]
        page.on("pageerror",lambda exc: errors.append(str(exc)))
        resp=page.goto(URL+"projects/pokhara-g15/manual-verification.html",timeout=45000)
        assert resp is not None and resp.status==200
        assert "Manual verification of the archived structural report" in page.locator("h1").inner_text()
        assert page.locator("article.item").count()>=40
        assert "F3 remains NOT SAFE IN ONE WAY SHEAR" in page.locator(".hold").inner_text()
        assert "ULS coefficient" in page.locator("body").inner_text()
        assert "First mode achieving 90%" in page.locator("body").inner_text()
        page.locator("article.item").first.screenshot(path=str(DEST/f"{name}-first-arithmetic.png"))
        back=page.goto(URL+"projects/pokhara-g15/report.html",timeout=45000)
        assert back is not None and back.status==200
        assert page.locator("#project-r6p12-manual").count()==1
        assert page.locator("#project-hand-calculations").count()==1
        assert page.locator("#project-figures").count()==1
        href=page.locator("#project-r6p12-manual a").get_attribute("href")
        assert href=="projects/pokhara-g15/manual-verification.html"
        assert not errors, errors
        ctx.close()
    browser.close()
print("R6P12_CHROMIUM_DESKTOP_MOBILE_ARITHMETIC_REPORT_LINKS_PASS")
