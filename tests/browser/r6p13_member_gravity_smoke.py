"""R6.13 Chrome desktop/mobile QA for source members, shell holds and navigation."""
from pathlib import Path
from playwright.sync_api import sync_playwright

URL="http://127.0.0.1:8765/"
SHOT=Path("build/r6p13-browser")
SHOT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
    for label,viewport,mobile in [
        ("desktop",{"width":1365,"height":850},False),
        ("mobile",{"width":390,"height":844},True)]:
        ctx=browser.new_context(viewport=viewport,is_mobile=mobile,has_touch=mobile)
        page=ctx.new_page()
        errors=[]
        page.on("pageerror",lambda err:errors.append(str(err)))
        response=page.goto(URL+"projects/pokhara-g15/member-gravity.html",timeout=50000)
        assert response is not None and response.status==200
        page.wait_for_function("""() => document.querySelector('#r613-count')?.innerText.includes('165')""",timeout=45000)
        assert page.locator("#r613-members tr").count()==165
        assert page.locator("#r613-shells tr").count()==115
        assert page.get_by_text("Excluded — support unverified").count()==12
        assert "GF:B46" in page.locator("#r613-detail h3").inner_text()
        assert "NOT SAFE IN ONE WAY SHEAR" in page.locator(".r613-hold").inner_text()
        assert "NOT DETERMINED" in page.locator("#r613-detail").inner_text().upper() or (
            "strength/capacity is NOT DETERMINED" in page.locator("#r613-detail").inner_text())
        assert page.locator("#r613-detail a").get_attribute("href").endswith("member=GF%3AB46")
        page.locator("#r613-role").select_option("SLS")
        page.locator("#r613-case").select_option("WALL LOAD")
        assert "SLS stiffness, WALL LOAD loading" in page.locator("#r613-detail").inner_text()
        page.locator("#r613-storey").select_option("TF")
        page.locator("#r613-type").select_option("COLUMN")
        page.locator("#r613-search").fill("C24")
        assert page.locator("#r613-members tr").count()==1
        assert "TF:C24" in page.locator("#r613-members").inner_text()
        page.locator("#r613-members button").click()
        assert "TF:C24" in page.locator("#r613-detail h3").inner_text()
        page.locator("#r613-search").fill("")
        page.locator("#r613-type").select_option("ALL")
        page.locator("#r613-storey").select_option("ALL")
        assert page.locator("#r613-members tr").count()==165
        assert not errors,errors
        page.locator("#r613-member-section").screenshot(path=str(SHOT/f"{label}-member-research.png"))
        report=page.goto(URL+"projects/pokhara-g15/report.html",timeout=50000)
        assert report is not None and report.status==200
        assert page.locator("#project-r6p13-members a").get_attribute("href")=="projects/pokhara-g15/member-gravity.html"
        assert page.locator("#project-hand-calculations").count()==1
        assert page.locator("#project-figures").count()==1
        assert page.locator("#project-r6p12-manual").count()==1
        ctx.close()
    browser.close()
print("R6P13_CHROMIUM_DESKTOP_MOBILE_165_FRAMES_115_SHELLS_F3_HOLD_PASS")
