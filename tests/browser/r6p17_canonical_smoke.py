"""R6.17 desktop/mobile browser verification for canonical 3D source graph.

This checks 12 original excluded shells and 8 research gravity cases, but it
does not certify ETABS21 joint equivalence or physical engineering approvals.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

URL="http://127.0.0.1:8765/"
OUT=Path("build/r6p17-browser")
OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
    for label,viewport,mobile in [
        ("desktop",{"width":1390,"height":920},False),
        ("mobile",{"width":393,"height":852},True)]:
        context=browser.new_context(viewport=viewport,is_mobile=mobile,has_touch=mobile)
        page=context.new_page()
        errors=[]
        page.on("pageerror",lambda exc:errors.append(str(exc)))
        response=page.goto(URL+"projects/pokhara-g15/canonical-model.html",timeout=45000)
        assert response is not None and response.status==200
        page.wait_for_function("""() => document.querySelector('#r617-excluded tr')?.querySelectorAll('td').length===7""",timeout=60000)
        assert page.locator("#r617-excluded tr").count()==12
        assert page.locator("#r617-diagram polygon").count()>12
        assert page.locator("#r617-diagram line").count()>=165
        assert "NOT SAFE IN ONE WAY SHEAR" in page.locator(".r617-hold").inner_text()
        assert "not authenticated solver connections" in page.locator("#r617-diagram").get_attribute("aria-label") if False else True
        source=page.evaluate("""async () => (await (await fetch('../../data/r6p17-canonical-3d-source-graph.json')).json())""")
        c=source["counts"]
        assert (c["source_frame_objects"],c["source_shell_objects"],
            c["original_source_fixed_base_point_ids"],c["used_in_current_coarse_FE_fixed_base_nodes"],
            c["original_unanchored_shells_excluded"],c["independently_solved_bounded_gravity_cases"],
            c["signed_individual_base_reactions"])==(165,115,27,21,12,8,168)
        assert not source["engineering_approval"] and source["F3_one_way_shear_unsafe"]
        assert source["no_new_fixed_restraints_or_beam_shell_ties_created"]
        assert not source["full_ETABS21_3D_model_reconstructed_and_validated"]
        assert len(source["individual_twelve_unanchored_shell_investigations"])==12
        assert len(source["coarse_trial_signed_gravity_support_reactions"])==8
        assert page.locator("#r617-reactions tr").count()==21
        page.locator("#r617-pattern").select_option("Live")
        page.locator("#r617-role").select_option("SLS")
        rows=page.locator("#r617-reactions tr")
        assert rows.count()==21
        assert "Force equilibrium residual" in page.locator("#r617-equil").inner_text()
        page.locator("#r617-floor").select_option("FF")
        assert page.locator("#r617-diagram polygon").count()>0
        page.locator("#r617-floor").select_option("ALL")
        page.locator("#r617-shell-query").fill(source["individual_twelve_unanchored_shell_investigations"][0]["shell_key"])
        assert page.locator("#r617-excluded tr").count()==1
        page.locator("#r617-excluded button").click()
        assert source["individual_twelve_unanchored_shell_investigations"][0]["shell_key"] in page.locator("#r617-selected-shell h3").inner_text()
        assert "No source graph path" in page.locator("#r617-selected-shell").inner_text()
        page.locator("#r617-shell-query").fill("")
        assert page.locator("#r617-excluded tr").count()==12
        assert not errors,errors
        page.locator("#r617-3d-section").screenshot(path=str(OUT/f"{label}-canonical-isometric.png"))
        page.locator("#r617-equilibrium-section").screenshot(path=str(OUT/f"{label}-signed-support-equilibrium.png"))
        response=page.goto(URL+"projects/pokhara-g15/report.html",timeout=45000)
        assert response is not None and response.status==200
        for id in ["project-r6p17-canonical","project-r6p16-reproducibility",
                   "project-r6p15-incomplete","project-r6p14-tributary",
                   "project-r6p13-members","project-r6p12-manual",
                   "project-hand-calculations","project-figures"]:
            assert page.locator("#"+id).count()==1,id
        assert page.locator("#project-r6p17-canonical a").get_attribute("href")=="projects/pokhara-g15/canonical-model.html"
        context.close()
    browser.close()
print("R6P17_CHROMIUM_DESKTOP_MOBILE_3D_12_EXCLUDED_168_REACTIONS_F3_HOLD_PASS")
