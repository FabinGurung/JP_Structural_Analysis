"""R6.15 real Chromium desktop/mobile evidence navigator QA; zero design approval."""
from pathlib import Path
from playwright.sync_api import sync_playwright
URL="http://127.0.0.1:8765/"
SHOTS=Path("build/r6p15-browser")
SHOTS.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
    for name,viewport,mobile in (
        ("desktop",{"width":1365,"height":860},False),
        ("mobile",{"width":390,"height":844},True)):
        ctx=browser.new_context(viewport=viewport,is_mobile=mobile,has_touch=mobile)
        page=ctx.new_page()
        errors=[]
        page.on("pageerror",lambda err:errors.append(str(err)))
        resp=page.goto(URL+"projects/pokhara-g15/incomplete-edges.html",timeout=50000)
        assert resp is not None and resp.status==200
        page.wait_for_function("""() => document.querySelector('#r615-count')?.innerText.includes('77 of 77')""",timeout=45000)
        assert page.locator("#r615-rows tr").count()==77
        assert page.locator("#r615-detail h3").count()==1
        assert page.locator(".r615-diagram").count()==1
        assert "NOT SAFE IN ONE WAY SHEAR" in page.locator(".r615-warning").inner_text()
        assert "No original or approved design load has changed" in page.locator(".r615-warning").inner_text()
        data=page.evaluate("""async () => (await (await fetch('../../data/r6p15-incomplete-slab-edge-audit.json')).json())""")
        assert data["coverage"]["slabs_examined"]==77
        assert data["coverage"]["source_edges_examined"]==308
        assert data["F3_one_way_shear_unsafe"] and not data["engineering_approval"]
        assert data["baseline"]["r614_complete_four_edge_shells"]==25
        assert data["baseline"]["source_graph_unanchored"]==12
        # Verify group filter matches the actual generated source classification.
        group,count=next(iter(data["coverage"]["review_group_counts"].items()))
        page.locator("#r615-group").select_option(group)
        page.wait_for_function("""count => Number(document.querySelector('#r615-count').innerText.split(' ')[0])===count""",count)
        assert page.locator("#r615-rows tr").count()==count
        page.locator("#r615-group").select_option("ALL")
        # A full source ID must return one row, not prefix matches.
        wanted=data["cases"][0]["shell_key"]
        page.locator("#r615-query").fill(wanted)
        page.wait_for_function("""() => document.querySelector('#r615-count')?.innerText.startsWith('1 of')""")
        assert page.locator("#r615-rows tr").count()==1
        page.locator("#r615-rows button").click()
        assert wanted in page.locator("#r615-detail h3").inner_text()
        assert page.locator(".r615-edge").count()==4
        assert page.locator(".r615-diagram").count()==1
        link=page.locator("#r615-detail a").get_attribute("href")
        assert link=="tributary-audit.html?shell="+wanted.replace(":","%3A")
        page.locator("#r615-query").fill("")
        # Hypothesis filter uses scenario evidence, not an assumed fixed count.
        for scenario,match in (("ONE_WAY","ONE_WAY"),("CANTILEVER","CANTILEVER")):
            page.locator("#r615-scenario").select_option(scenario)
            actual=sum(any(match in s["scenario"] for s in row["provisional_scenarios"]) for row in data["cases"])
            if actual:
                page.wait_for_function("""count => Number(document.querySelector('#r615-count').innerText.split(' ')[0])===count""",actual)
                assert page.locator("#r615-rows tr").count()==actual
        page.locator("#r615-scenario").select_option("ALL")
        assert page.locator("#r615-rows tr").count()==77
        assert not errors,errors
        page.locator("#r615-casework").screenshot(path=str(SHOTS/f"{name}-77-case-explorer.png"))
        response=page.goto(URL+"projects/pokhara-g15/report.html",timeout=50000)
        assert response is not None and response.status==200
        assert page.locator("#project-r6p15-incomplete").count()==1
        assert page.locator("#project-r6p14-tributary").count()==1
        assert page.locator("#project-r6p13-members").count()==1
        assert page.locator("#project-r6p12-manual").count()==1
        assert page.locator("#project-hand-calculations").count()==1
        assert page.locator("#project-figures").count()==1
        assert page.locator("#project-r6p15-incomplete a").get_attribute("href")=="projects/pokhara-g15/incomplete-edges.html"
        response=page.goto(URL+"projects/pokhara-g15/tributary-audit.html",timeout=50000)
        assert response is not None and response.status==200
        assert page.locator('a[href="incomplete-edges.html"]').count()==1
        ctx.close()
    browser.close()
print("R6P15_CHROMIUM_DESKTOP_MOBILE_77_CASES_308_EDGES_REPORT_LINKS_F3_HOLD_PASS")
