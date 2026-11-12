"""R6.18 Chromium desktop/mobile FE mesh, equilibrium and foundation HOLD QA."""
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE="http://127.0.0.1:8765/"
DIR=Path("build/r6p18-browser");DIR.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
    for device,viewport,mobile in [
        ("desktop",{"width":1400,"height":920},False),
        ("mobile",{"width":393,"height":852},True)]:
        ctx=browser.new_context(viewport=viewport,is_mobile=mobile,has_touch=mobile)
        page=ctx.new_page()
        errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
        resp=page.goto(BASE+"projects/pokhara-g15/fe-mesh-audit.html",timeout=55000)
        assert resp is not None and resp.status==200
        page.wait_for_function("""() => document.querySelectorAll('.r618-kpi').length===8 &&
             document.querySelectorAll('#r618-supports tr').length===21""",timeout=70000)
        assert "NOT SAFE IN ONE WAY SHEAR" in page.locator(".r618-hold").inner_text()
        assert "103 of 115" in page.locator(".r618-hold").inner_text()
        d=page.evaluate("""async() => (await(await fetch('../../data/r6p18-fe-connection-mesh-foundation-audit.json')).json())""")
        assert d["schema"]=="jp.structural.r6p18.source_bounded_fe_mesh_and_foundation_reaction_gate.v0.1"
        c=d["counts"]
        assert (c["original_frame_members"],c["original_shells"],c["source_graph_connected_shells"],
                c["original_unanchored_shells_excluded"],c["original_base_restraints_declared"],
                c["source_connected_research_support_nodes"])==(165,115,103,12,27,21)
        assert (c["baseline_gravity_cases_at_2x2"],c["additional_independently_solved_4x4_refinement_cases"],
                c["research_signed_base_reaction_records_2x2"],
                c["research_signed_base_reaction_records_4x4"])==(8,2,168,42)
        assert not d["complete_independent_physical_FE_model_accepted"]
        assert not d["original_F3_CF1_source_support_correspondence_verified"]
        assert not d["engineering_approval"] and d["historical_F3_one_way_shear_unsafe"]
        assert d["twelve_unconnected_original_shell_holds"]["source_unanchored_shells_added_to_FE"]==0
        assert len(d["unapproved_original_base_point_to_foundation_reaction_register"])==21
        assert page.locator("#r618-refinement-table tr").count()==21
        assert page.locator("#r618-chart polyline").count()==2
        assert page.locator("#r618-supports tr").count()==21
        assert "NOT MAPPED" in page.locator("#r618-supports").inner_text()
        page.locator("#r618-case").select_option("SLS|Live")
        page.wait_for_function("""() => document.querySelectorAll('#r618-refinement-table tr').length===21""")
        assert "Numerical 5% screen" in page.locator("#r618-refinement").inner_text()
        page.locator("#r618-resolution").select_option("4")
        source=d["shell_frame_boundary_alignment_by_mesh_size"]["4"]
        assert source["source_connected_original_shells_examined"]==103
        assert len(source["geometric_contacts"])>0
        wanted=source["geometric_contacts"][0]["source_frame_key"]
        page.locator("#r618-search").fill(wanted)
        page.wait_for_function("""() => Number(document.querySelector('#r618-contact-count')?.innerText.split(' ')[0])>0""")
        assert page.locator("#r618-contacts tr").count()>=1
        assert wanted in page.locator("#r618-contacts").inner_text()
        page.locator("#r618-search").fill("")
        page.locator("#r618-support-role").select_option("SLS")
        page.locator("#r618-support-pattern").select_option("FLOOR FINISH")
        assert page.locator("#r618-supports tr").count()==21
        assert page.locator("#r618-six-axis .r618-card").count()==5
        assert not errors,errors
        page.locator("#r618-mesh-section").screenshot(path=str(DIR/f"{device}-fe-refinement.png"))
        page.locator("#r618-foundation-section").screenshot(path=str(DIR/f"{device}-foundation-reactions.png"))
        resp=page.goto(BASE+"projects/pokhara-g15/report.html",timeout=45000)
        assert resp is not None and resp.status==200
        for item in ("project-r6p18-fe","project-r6p17-canonical","project-r6p16-reproducibility",
                     "project-r6p15-incomplete","project-r6p14-tributary",
                     "project-r6p13-members","project-r6p12-manual",
                     "project-hand-calculations","project-figures"):
            assert page.locator("#"+item).count()==1,item
        assert page.locator("#project-r6p18-fe a").get_attribute("href")=="projects/pokhara-g15/fe-mesh-audit.html"
        ctx.close()
    browser.close()
print("R6P18_CHROMIUM_DESKTOP_MOBILE_FE_MESH_6_AXIS_FOUNDATION_12_SHELL_F3_HOLD_PASS")
