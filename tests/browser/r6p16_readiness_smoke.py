"""Browser QA: R6.16 first-party report reproduction readiness must not imply safety."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE="http://127.0.0.1:8765/"
SHOTS=Path("build/r6p16-browser")
SHOTS.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
    for name,viewport,mobile in [
        ("desktop",{"width":1365,"height":850},False),
        ("mobile",{"width":390,"height":844},True)]:
        ctx=browser.new_context(viewport=viewport,is_mobile=mobile,has_touch=mobile)
        page=ctx.new_page()
        errors=[]
        page.on("pageerror",lambda err:errors.append(str(err)))
        response=page.goto(BASE+"projects/pokhara-g15/reproducibility.html",timeout=50000)
        assert response is not None and response.status==200
        page.wait_for_function("""() => document.querySelector('#r616-filter-count')?.innerText.startsWith('18 of 18')""",timeout=40000)
        assert page.locator("#r616-modules tr").count()==18
        assert page.locator(".r616-stage").count()==7
        assert page.locator(".r616-blocker").count()==6
        assert "NOT SAFE IN ONE WAY SHEAR" in page.locator(".r616-warning").inner_text()
        assert "cannot yet prove complete equivalence" in page.locator(".r616-hero").inner_text()
        data=page.evaluate("""async () => (await (await fetch('../../data/r6p16-report-reproducibility-readiness.json')).json())""")
        assert data["module_count"]==18
        assert data["module_coverage_status_counts"]=={
            "DRAFT_UNVALIDATED":1,"IMPLEMENTED_BOUNDED":2,"MISSING":4,"PARTIAL":11}
        assert not data["reproduction"]["full_governing_ETABS21_model_equivalent"]
        assert not data["reproduction"]["all_historical_report_results_recomputed"]
        assert not data["source_scope"]["source_drift_detection_against_drive_at_each_build"]
        assert not data["engineering_approval"]
        page.locator("#r616-module-status").select_option("MISSING")
        page.wait_for_function("""() => document.querySelector('#r616-filter-count')?.innerText.startsWith('4 of')""")
        assert page.locator("#r616-modules tr").count()==4
        page.locator("#r616-module-status").select_option("PARTIAL")
        page.wait_for_function("""() => document.querySelector('#r616-filter-count')?.innerText.startsWith('11 of')""")
        assert page.locator("#r616-modules tr").count()==11
        page.locator("#r616-module-status").select_option("ALL")
        page.locator("#r616-module-query").fill("M04")
        page.wait_for_function("""() => document.querySelector('#r616-filter-count')?.innerText.startsWith('1 of')""")
        assert "3D elastic FE" in page.locator("#r616-modules").inner_text()
        page.locator("#r616-module-query").fill("")
        assert page.locator("#r616-modules tr").count()==18
        assert not errors,errors
        page.locator(".r616-main").screenshot(path=str(SHOTS/f"{name}-report-readiness.png"))
        report=page.goto(BASE+"projects/pokhara-g15/report.html",timeout=50000)
        assert report is not None and report.status==200
        for item in ("project-r6p12-manual","project-r6p13-members",
                     "project-r6p14-tributary","project-r6p15-incomplete",
                     "project-r6p16-reproducibility","project-figures","project-hand-calculations"):
            assert page.locator("#"+item).count()==1,item
        assert page.locator("#project-r6p16-reproducibility a").get_attribute("href")=="projects/pokhara-g15/reproducibility.html"
        assert not errors,errors
        ctx.close()
    browser.close()
print("R6P16_CHROMIUM_DESKTOP_MOBILE_MODULE_STATUS_SOURCE_AND_ENGINEERING_HOLD_PASS")
