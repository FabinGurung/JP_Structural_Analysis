"""R6.11 desktop/mobile Chromium DOM, navigation, filter and SVG marker QA."""
from pathlib import Path
from playwright.sync_api import sync_playwright

URL="http://127.0.0.1:8765/r6p10-shell-diaphragm-studio.html"
OUT=Path("build/r6p11-browser")
OUT.mkdir(parents=True,exist_ok=True)

def inspect(browser,name,viewport,is_mobile):
    context=browser.new_context(viewport=viewport,is_mobile=is_mobile,
      device_scale_factor=2 if is_mobile else 1,
      has_touch=is_mobile)
    page=context.new_page()
    errors=[]
    page.on("pageerror",lambda err:errors.append(str(err)))
    response=page.goto(URL,wait_until="domcontentloaded",timeout=45000)
    assert response is not None and response.status==200
    page.wait_for_function("""() => document.querySelector('#r611-contact-detail')?.innerText.includes('4 of 4')""",timeout=45000)
    assert page.locator("#r611-plan circle[fill='#ffd369']").count()==4
    assert page.locator("#r611-3d circle[fill='#ffd369']").count()==4
    assert "ENGINEERING HOLD" in page.locator("#r611-contact-detail").inner_text()

    page.locator("#r611-group").select_option("FF_B27")
    page.wait_for_function("""() => document.querySelector('#r611-contact-detail')?.innerText.includes('2 of 2')""")
    assert page.locator("#r611-plan circle[fill='#ffd369']").count()==2
    assert page.locator("#r611-3d circle[fill='#ffd369']").count()==2
    assert page.locator("#r610-floor").input_value()=="FF"
    assert "FF:W3" in page.locator("#r611-contact-detail").inner_text()

    page.locator("#r611-view-filter").select_option("SUPPORTED")
    assert page.locator("#r610-filter").input_value()=="SUPPORTED"
    assert page.locator("#r611-plan circle[fill='#ffd369']").count()==2
    assert page.locator("#r611-plan polygon").count()>0

    page.locator("#r611-group").select_option("GF_F56")
    assert page.locator("#r610-floor").input_value()=="GF"
    assert page.locator("#r611-plan circle[fill='#ffd369']").count()==4
    assert page.locator("#r611-view-filter").input_value()=="ALL"
    page.locator("#r610-rot-right").click()
    assert page.locator("#r611-3d circle[fill='#ffd369']").count()==4
    assert "12 unsupported" in page.locator("#r611-contact-detail").inner_text()
    assert not errors, errors
    page.locator("#r611-support").screenshot(path=str(OUT/f"{name}-contact.png"))
    context.close()

with sync_playwright() as playwright:
    browser=playwright.chromium.launch(headless=True,args=["--no-sandbox"])
    inspect(browser,"desktop",{"width":1440,"height":900},False)
    inspect(browser,"mobile",{"width":390,"height":844},True)
    browser.close()
print("R6P11_CHROMIUM_DESKTOP_MOBILE_2D_3D_MARKERS_FILTER_QA_PASS")
