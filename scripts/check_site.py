#!/usr/bin/env python3
"""Fast, zero-network structural Pages QA. Regenerate site/demo before deployment.

Only checks static internal page links, consistent navigation, source privacy,
registry access, common theme, and absence of unnecessary heavy dependencies.
"""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"
PAGES=["index.html","project-lab.html","analysis-studio.html","g15-3d.html","calculation-coverage.html","report.html","more.html"]
class Parse(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.links=[];self.css=[];self.scripts=[];self.mains=0
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=="a" and "href" in d:self.links.append(d["href"])
        if tag=="link" and d.get("rel")=="stylesheet":self.css.append(d.get("href"))
        if tag=="script" and "src" in d:self.scripts.append(d["src"])
        if tag=="main":self.mains+=1


def verify_m09_case(problems):
    import json
    from math import isfinite
    path=SITE/"data/m09-section-capacity.v0.1.json"
    if not path.is_file():
        problems.append("Missing generated M09 numerical JSON")
        return
    try:
        d=json.loads(path.read_text(encoding="utf-8"))
        ref=d["valid_case"]
        unsafe=d["intentionally_unsafe_case"]
        checks=[
            d["schema"]=="jp.structural.m09_column_section.v0.1",
            d["case_id"]=="ASSUMED-M09-SECTION-001",
            d["engineering_approval"] is False,
            d["report_accepted"] is False,
            ref["status"]=="BOUNDED_NUMERICAL_PRECHECK_SP16_CHART_AND_DETAILING_HOLD",
            ref["code_check_complete"] is False,
            ref["legacy_interaction"]["engineering_approval"] is False,
            unsafe["status"]=="FAIL",
            len(ref["face_capacities"])==4,
            all(abs(f["axial_equilibrium_residual_kN"])<0.0001 for f in ref["face_capacities"]),
            all(f["independently_SP16_benchmarked"] is False for f in ref["face_capacities"]),
            isfinite(ref["chosen_conservative_Mux1_kNm"]),
            isfinite(ref["chosen_conservative_Muy1_kNm"]),
            ref["chosen_conservative_Mux1_kNm"]>0,
            ref["chosen_conservative_Muy1_kNm"]>0,
            isfinite(ref["legacy_interaction"]["interaction_utilization"]),
            d["provenance"].startswith("All geometry/bars/forces are synthetic."),
        ]
        if not all(checks):problems.append("Invalid M09 result or acceptance metadata")
        for page in ("calculation-coverage.html","more.html"):
            if 'data-m09-view=' not in (SITE/page).read_text(encoding="utf-8"):
                problems.append(page+": missing M09 evidence section")
    except (ValueError,KeyError,TypeError,IndexError) as exc:
        problems.append("Malformed generated M09 JSON: "+str(exc))


def verify_sp16_and_d2(problems):
    import json
    from math import isfinite
    try:
        s=json.loads((SITE/"data/sp16_1980_primary_source.v0.1.json").read_text())
        d=json.loads((SITE/"data/d2_signed_frame.v0.1.json").read_text())
        assert s["schema"]=="jp.structural.sp16_primary_source.v0.1"
        assert s["sha256"]=="d2a6246a5dc7504568f4e55f310dd4be9d925fb1a8b04b6d7f5132c93f66c76e"
        assert s["pages"]==255 and s["charts_indexed"]==92
        assert len(s["table_a"]["points"])==12
        assert s["chart31"]["physical_page"]==139
        assert s["chart31"]["original_chart_visually_available"] is True
        assert s["chart31"]["curve_points_independently_digitized"] is False
        assert s["chart31"]["engineering_approval"] is False
        assert s["engineering_approval"] is False
        assert d["schema"]=="jp.structural.d2_m08_m09_m10_synthetic_demo.v0.1"
        assert d["engineering_approval"] is False
        assert d["report_accepted"] is False
        checks=d["design_checks"]
        assert checks["engineering_approval"] is False
        assert all(len(checks[k])==1 for k in ("beam_design","column_design","joint_design"))
        assert all(x["global_equilibrium_pass"] for x in d["signed_fe_actions"]["raw_cases"])
        assert isfinite(checks["column_design"][0]["governing_interaction_utilization"])
        for page in ("calculation-coverage.html","more.html"):
            assert "data-d2-view=" in (SITE/page).read_text()
    except (OSError,ValueError,KeyError,TypeError,IndexError,AssertionError) as exc:
        problems.append("SP16/D2 original-source and safety state malformed: "+str(exc))


def verify_original_chart31_source_spots(problems):
    import json
    from math import isfinite
    path=SITE/"data/sp16_chart31_spotcheck.v0.1.json"
    if not path.is_file():
        problems.append("Missing generated original SP16 Chart31 numerical point evidence")
        return
    try:
        d=json.loads(path.read_text(encoding="utf-8"))
        assert d["schema"]=="jp.structural.sp16.chart31.spot_comparison.v0.1"
        assert d["original_sp16_pdf_sha256"]=="d2a6246a5dc7504568f4e55f310dd4be9d925fb1a8b04b6d7f5132c93f66c76e"
        assert d["historical_code_basis"]=="IS456:1978" and d["current_engine_code_basis"]=="IS456:2000"
        assert d["all_sampled_points_agree"] is True
        assert d["full_sp16_chart31_curve_digitization_complete"] is False
        assert d["code_edition_reconciliation"]["full_edition_parity_verified"] is False
        assert d["engineering_approval"] is False and d["report_accepted"] is False
        assert len(d["points"])==2
        assert all(p["spot_agreement"] is True and
                   isfinite(p["engine_mu_over_fck_bD2"]) and
                   p["absolute_normalized_error"]<=p["visual_uncertainty_absolute_normalized_moment"]
                   for p in d["points"])
        for page in ("calculation-coverage.html","more.html"):
            assert "data-sp16-benchmark=" in (SITE/page).read_text(encoding="utf-8")
    except (ValueError,KeyError,IndexError,TypeError,AssertionError) as err:
        problems.append("Original SP16 Chart31 source benchmark incorrect: "+str(err))


def verify_synthetic_nbc105_esm(problems):
    import json
    from math import isclose, isfinite
    path=SITE/"data/nbc105_esm_synthetic.v0.1.json"
    if not path.is_file():
        problems.append("Missing native-generated synthetic NBC105 ESM data")
        return
    try:
        d=json.loads(path.read_text(encoding="utf-8"))
        assert d["schema"]=="jp.structural.synthetic_nbc105_2025_esm.v0.1"
        assert d["synthetic"] is True
        assert d["private_real_project_values_included"] is False
        assert d["engineering_approval"] is False
        assert d["report_accepted"] is False
        assert all(x is False for x in d["safety_gates"].values())
        assert d["cases"]["ULS"]["engineering_approval"] is False
        assert d["guarded_drift_checks"]["ULS"]["engineering_approval"] is False
        for mode in ("ULS","SLS"):
            row=d["cases"][mode]
            assert isfinite(row["base_shear_kN"])
            assert isclose(sum(row["floor_forces_kN"]),row["base_shear_kN"],rel_tol=1e-10)
        for page in ("calculation-coverage.html","more.html"):
            assert 'data-gate05-demo=' in (SITE/page).read_text(encoding="utf-8")
    except (AssertionError,KeyError,ValueError,TypeError) as e:
        problems.append("Invalid synthetic NBC105 ESM case or safety gate: "+str(e))


def verify_gate06_synthetic_source(problems):
    import json
    from math import isfinite
    p=SITE/"data/nbc105_gate06_synthetic.v0.1.json"
    if not p.exists():
        problems.append("Missing generated Gate06 synthetic public evidence")
        return
    try:
        d=json.loads(p.read_text(encoding="utf-8"))
        assert d["schema"]=="jp.structural.public_synthetic_gate06.v0.1"
        assert d["synthetic"] is True
        assert d["private_project_input_values_included"] is False
        assert d["engineering_approval"] is False and d["report_accepted"] is False
        assert len(d["signed_accidental_eccentricity_cases"])==16
        assert set(d["effective_stiffness"])=={"GROSS","ULS","SLS"}
        assert d["effective_stiffness"]["ULS"]["beam_flexural_EI_over_EcIg"]==.35
        assert d["effective_stiffness"]["ULS"]["column_flexural_EI_over_EcIg"]==.70
        assert d["effective_stiffness"]["SLS"]["beam_flexural_EI_over_EcIg"]==.70
        assert d["effective_stiffness"]["SLS"]["column_flexural_EI_over_EcIg"]==.90
        assert d["source_mass_reconciliation_demonstration"]["source_to_trial_mass_closed"] is False
        assert d["source_mass_reconciliation_demonstration"]["missing_components_inferred"] is False
        assert isfinite(d["source_mass_reconciliation_demonstration"]["residual_source_minus_trial_kN"])
        assert d["same_case_member_action_selection"]["do_not_combine_independent_case_peaks"]
        for page in ("calculation-coverage.html","more.html"):
            assert "data-gate06-demo=" in (SITE/page).read_text(encoding="utf-8")
    except (KeyError,ValueError,IndexError,TypeError,AssertionError) as exc:
        problems.append("Gate06 public numeric source or safety HOLD invalid: "+str(exc))


def verify_real_project_calculation_ledger(problems):
    import json
    from math import isclose, isfinite
    p=SITE/"data/g15-project-ledger.v0.2.json"
    if not p.is_file():
        problems.append("Missing generated de-identified real-project calculation ledger")
        return
    try:
        d=json.loads(p.read_text(encoding="utf-8"))
        assert d["schema"]=="jp.structural.deidentified.project_calculation_ledger.public.v0.2"
        assert d["source_visibility"]=="PRIVATE_DRIVE_SOURCE_NOT_PUBLISHED"
        assert d["publication"]=="USER_REQUESTED_DEIDENTIFIED_AGGREGATE_ONLY"
        assert d["derived"]["total_gate05_gate06_gate07_case_solves"]==376
        assert d["derived"]["total_gate05_to_gate08_case_solves"]==1192
        assert d["scope"]["member_count"]==165
        assert len(d["workflow"])==7 and len(d["calculation_families"])>=13
        assert d["gate07"]["case_count"]==204
        assert d["gate08"]["cases"]==816
        assert d["gate08"]["model_real_project_approved"] is False
        assert all(v is False for v in d["safety"].values())
        assert d["member_checks"]["F3_source_status"]=="NOT SAFE IN ONE WAY SHEAR"
        assert d["member_checks"]["F3_repaired"] is False
        assert d["member_checks"]["C24_true_mapping_verified"] is False
        mass=d["gravity_mass"]
        assert mass["mass_reconciled"] is False
        assert isclose(mass["report_W_kN"]-mass["gate07_conditionally_reconstructed_kN"],
                       mass["gate07_remaining_gap_kN"],abs_tol=.001)
        assert mass["gate07_remaining_gap_kN"]>0
        assert len(d["gate06"]["eccentric_scenarios"])==8
        assert len(d["gate07"]["variants"])==4
        assert all(isfinite(row["roof_mm"]) for row in d["gate07"]["variants"])
        assert "data-gate05-demo=" in (SITE/"calculation-coverage.html").read_text(encoding="utf-8")
        page=(SITE/"project-lab.html").read_text(encoding="utf-8")
        assert 'id="lab-response-chart"' in page and 'id="lab-modules"' in page
        assert 'id="lab-mass-graphic"' in page
        assert 'src="project-ledger.js"' in page
        # The projection exposes non-identifying calculated aggregates only.
        text=p.read_text(encoding="utf-8")
        for blocked in ("drive.google.com/file/d/","drive.google.com/drive/folders/",
                        "@gmail.com","Sankalp Singh", "Fabin Gurung", "ETABS License"):
            assert blocked not in text
    except (AssertionError,KeyError,ValueError,TypeError,OSError) as exc:
        problems.append("Real-project public ledger privacy/numerical QA FAILED: "+str(exc))


def verify_deidentified_gate08(problems):
    import json
    from math import isclose,isfinite
    path=SITE/"data/g15-gate08-reconciliation.v0.1.json"
    if not path.is_file():
        problems.append("Missing 16-case Gate08 source-derived projection")
        return
    try:
        d=json.loads(path.read_text(encoding="utf-8"))
        assert d["schema"]=="jp.structural.g15.gate08.public_source_reconciliation.v0.1"
        assert d["gate08_private_summary_sha256"]=="37d3ab85d96953a74a773358fb9d56de1858ed163c896bb99de8e43844ee0a48"
        assert d["cohort"]["variants"]==16
        assert d["cohort"]["solved_cases"]==816
        assert d["cohort"]["signed_member_end_action_records"]==134640
        assert len(d["scenarios"])==16
        assert d["f3_source_failure"]=="NOT SAFE IN ONE WAY SHEAR"
        assert d["engineering_approval"] is False and d["report_accepted"] is False
        assert d["seismic_mass_reconciled"] is False
        assert d["exact_slab_edges_verified"] is False
        assert d["grid_hull_used_as_slab_geometry"] is False
        assert d["original_report_as_built_model_verified"] is False
        m=d["mass_kN"]
        assert isclose(m["source_ETABS_W"]-m["with_wall_hypothesis"],
                       m["remaining_residual"],abs_tol=.00001)
        assert m["remaining_residual"]>0
        assert all(s["design_approved"] is False and
                   isfinite(s["roof_mm"]) and isfinite(s["drift_ratio"]) for s in d["scenarios"])
        page=(SITE/"project-lab.html").read_text(encoding="utf-8")
        assert 'id="lab-gate08"' in page
        assert 'src="gate08.js"' in page
        assert "data/g15-gate08-reconciliation.v0.1.json" in (SITE/"gate08.js").read_text(encoding="utf-8")
        txt=path.read_text(encoding="utf-8")
        for banned in ("drive.google.com/file/d/","@gmail.com","full_grid_geometry_coordinates"):
            assert banned not in txt
    except (AssertionError,ValueError,KeyError,TypeError,OSError) as err:
        problems.append("Gate08 derived source/equilibrium/engineering-HOLD QA failed: "+str(err))

def main():
    problems=[]
    for page in PAGES:
        p=SITE/page
        if not p.is_file():problems.append("Missing "+page);continue
        text=p.read_text(encoding="utf-8")
        parser=Parse();parser.feed(text)
        if parser.css!=(["styles.css","report-book.css","chapter04-model.css","chapter05-results.css","chapter06-design.css"] if page=="report.html" else ["styles.css","more-guide.css"] if page=="more.html" else ["styles.css"]):problems.append(page+": inconsistent stylesheet")
        if parser.scripts!=(["app.js","report-book.js","chapter02-audit.js","chapter02-seismic.js","chapter03-method.js","chapter04-model.js","chapter05-results.js","chapter06-design.js"] if page=="report.html" else ["app.js","d2.js","fem-triad.js"] if page=="more.html" else ["app.js","d2.js"] if page=="calculation-coverage.html" else ["app.js","project-ledger.js","gate08.js","gate09.js","gate10.js","gate11.js","gate12.js","gate13.js","gate14.js","gate15.js","gate16.js","gate17.js","gate18.js","gate19.js","gate20.js","private-force-viewer.js"] if page=="project-lab.html" else ["app.js","analysis-studio.js"] if page=="analysis-studio.html" else ["app.js","g15-3d.js"] if page=="g15-3d.html" else ["app.js"]):problems.append(page+": inconsistent app scripts")
        if parser.mains!=1:problems.append(page+": expected one main")
        nav=text.split('<nav class="navigation" aria-label="Primary navigation">',1)
        if len(nav)!=2 or "</nav>" not in nav[1]:
            problems.append(page+": missing primary navigation")
        else:
            primary=nav[1].split("</nav>",1)[0]
            for target in ("index.html","report.html","more.html"):
                if primary.count('href="'+target+'"')!=1:
                    problems.append(page+": missing or duplicated primary nav target "+target)
            for extra in ("project-lab.html","analysis-studio.html","g15-3d.html","calculation-coverage.html"):
                if 'href="'+extra+'"' in primary:
                    problems.append(page+": tool incorrectly appears at primary navigation level "+extra)
        if page=="more.html":
            for target in ("project-lab.html","analysis-studio.html","g15-3d.html","calculation-coverage.html"):
                if 'href="'+target+'"' not in text:problems.append("More directory missing "+target)
        for url in parser.links+parser.css+parser.scripts:
            u=urlparse(url)
            if u.scheme or url.startswith("//") or url.startswith("#") or url.startswith("mailto:"):continue
            local=(SITE/page).parent/unquote(u.path)
            if not local.is_file() and not (local in {SITE/"demo/SAR.html", SITE/"demo/validation_results.json"} and not (SITE/"demo").exists()):
                problems.append(page+": broken local link "+url)
    for path in ("styles.css","app.js","analysis-studio.js","g15-3d.js","data/g15-working-grid.public.v0.1.json","d2.js","gate08.js","data/sp16_1980_primary_source.v0.1.json","data/report-calculation-coverage.v0.1.json"):
        if not (SITE/path).is_file():problems.append("Missing "+path)
    if (SITE/"styles.css").stat().st_size>28000:problems.append("Shared CSS unexpectedly large")
    if (SITE/"app.js").stat().st_size>12000:problems.append("Shared JS unexpectedly large")
    verify_m09_case(problems)
    verify_sp16_and_d2(problems)
    verify_original_chart31_source_spots(problems)
    verify_synthetic_nbc105_esm(problems)
    verify_gate06_synthetic_source(problems)
    verify_real_project_calculation_ledger(problems)
    verify_deidentified_gate08(problems)
    studio=(SITE/"analysis-studio.html").read_text(encoding="utf-8")
    script=(SITE/"analysis-studio.js").read_text(encoding="utf-8")
    if 'id="studio-form"' not in studio or 'id="studio-queue"' not in studio:
        problems.append("Missing operable analysis-studio controls")
    if "SYNTHETIC_FRAME_ONLY" not in script or "issues/new?" not in script:
        problems.append("No authorized GitHub FE handoff or missing model boundary")
    if "github_pat_" in script or "ghp_" in script or "localStorage" in script:
        problems.append("Studio may not request or store GitHub tokens")
    from math import isfinite
    import json
    m=json.loads((SITE/"data/g15-working-grid.public.v0.1.json").read_text(encoding="utf-8"))
    if len(m["column_positions_mm"])!=23 or len(m["beam_edges"])!=32:
        problems.append("G15 source-derived 3D model count incorrect")
    if m["safety"]["engineering_approval"] is not False or m["safety"]["F3_footing_one_way_shear"]!="NOT SAFE IN ONE WAY SHEAR":
        problems.append("G15 source engineering HOLD/F3 failure lost")
    studio=(SITE/"g15-3d.html").read_text(encoding="utf-8")
    if 'id="g15-scene"' not in studio or 'id="g15-queue"' not in studio or 'src="g15-3d.js"' not in studio:
        problems.append("Missing 3D UI canvas or authenticated run handoff")
    if "JP_G15_3D_RUN_V1" not in (SITE/"g15-3d.js").read_text(encoding="utf-8"):
        problems.append("3D Actions handoff missing")
    p=SITE/"data/g15-open3d-reference.v1.json"
    if not p.is_file():
        problems.append("Missing generated real-source 165-member OpenSees 3D reference")
    else:
        try:
            d=json.loads(p.read_text(encoding="utf-8"))
            assert d["schema"]=="jp.structural.g15.open3d.result.v1"
            assert d["model_counts"]["members"]==165 and len(d["cases"])==5
            assert d["engineering_approval"] is False
            assert d["foundation_F3_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"
            assert all(len(c["member_signed_local_end_forces"])==165 and
                       c["equilibrium_residual_kN"]<.001 and
                       c["equilibrium_moment_residual_kNm"]<.001 and
                       c["roof_displacement_metric"]=="MAX_NODE_HORIZONTAL_EUCLIDEAN_NORM"
                       for c in d["cases"])
            assert "g15-open3d-reference.v1.json" in (SITE/"g15-3d.js").read_text(encoding="utf-8")
            assert 'id="g15-load-result"' in (SITE/"g15-3d.html").read_text(encoding="utf-8")
            assert 'id="g15-restore-reference"' in (SITE/"g15-3d.html").read_text(encoding="utf-8")
            assert "validResult(d)" in (SITE/"g15-3d.js").read_text(encoding="utf-8")
        except (KeyError,ValueError,AssertionError,TypeError) as err:
            problems.append("G15 OpenSees reference evidence malformed: "+str(err))
    from math import isclose
    g09=SITE/"data/g15-gate09-source-audit.v0.1.json"
    if not g09.is_file():
        problems.append("Gate09 source slab/mass audit missing")
    else:
        try:
            d=json.loads(g09.read_text(encoding="utf-8"))
            assert d["schema"]=="jp.structural.g15.gate09.sample_panel_and_mass_audit.v0.1"
            assert isclose(d["panel"]["area_m2"],17.874,abs_tol=.0001)
            assert len(d["panel"]["candidate_beam_line_support"])==4
            assert d["panel"]["whole_building_polygon_coverage"] is False
            assert d["mass_reconciliation"]["source_supported_new_mass_kN"]==0
            assert isclose(d["mass_reconciliation"]["unexplained_W_kN"],772.0329166282687,abs_tol=.001)
            assert d["mass_reconciliation"]["source_mass_reconciled"] is False
            assert d["source_F3_status"]=="NOT SAFE IN ONE WAY SHEAR"
            assert d["engineering_approval"] is False
            assert 'id="lab-gate09"' in (SITE/"project-lab.html").read_text(encoding="utf-8")
        except (AssertionError,KeyError,TypeError,ValueError,OSError) as e:
            problems.append("Gate09 source-audit QA fail: "+str(e))
    g10=SITE/"data/g15-gate10-assumptions.v0.1.json"
    if not g10.exists():
        problems.append("Gate10 mass-assumption evidence missing")
    else:
        try:
            d=json.loads(g10.read_text(encoding="utf-8"))
            assert d["schema"]=="jp.structural.g15.gate10.assumption_sensitivity.v0.1"
            assert d["engineering_approval"] is False
            assert d["seismic_mass_source_reconciled"] is False
            assert d["source_F3_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"
            assert len(d["footprints"]["assumed_per_floor"])==3
            assert len(d["model_cases"])==9
            assert all(x["seismic_mass_accepted"] is False for x in d["model_cases"])
            assert all(len(x["floor_weights_kN"])==3 for x in d["model_cases"])
            assert "G10_INVERSE_FIT" in [x["id"] for x in d["model_cases"]]
            assert 'id="lab-gate10"' in (SITE/"project-lab.html").read_text(encoding="utf-8")
            assert 'id="g15-assumption-note"' in (SITE/"g15-3d.html").read_text(encoding="utf-8")
            assert "g15-gate10-assumptions.v0.1.json" in (SITE/"g15-3d.js").read_text(encoding="utf-8")
        except (AssertionError,KeyError,TypeError,ValueError,OSError) as e:
            problems.append("Gate10 source/mass assumption integrity failure: "+str(e))
    g11=SITE/"data/g15-gate11-diaphragm-proxy.v0.1.json"
    if not g11.exists():problems.append("Missing governed Gate11 torsion response")
    else:
        try:
            d=json.loads(g11.read_text(encoding="utf-8"))
            assert d["schema"]=="jp.structural.g15.gate11.rigid_diaphragm_proxy.v0.1"
            assert len(d["cases"])==8
            assert all(len(c["floors"])==3 for c in d["cases"])
            assert all(f["force_and_moment_equilibrium_verified"] is True for c in d["cases"] for f in c["floors"])
            assert d["mass_source_reconciled"] is False
            assert d["actual_story_drift_accepted"] is False
            assert d["engineering_approval"] is False
            assert d["foundation_F3_source"]=="NOT SAFE IN ONE WAY SHEAR"
            assert 'id="lab-gate11"' in (SITE/"project-lab.html").read_text(encoding="utf-8")
        except (AssertionError,KeyError,ValueError,TypeError,OSError) as e:
            problems.append("Gate11 response provenance failed: "+str(e))
    g12=SITE/"data/g15-gate12-diaphragm-fe.v0.1.json"
    if not g12.exists():
        problems.append("Source-grid 3D diaphragm FE comparison is missing")
    else:
        try:
            d=json.loads(g12.read_text(encoding="utf-8"))
            assert d["schema"]=="jp.structural.g15.gate12.diaphragm_openSees_comparison.v0.1"
            assert len(d["cases"])==18 and len(d["comparisons"])==9
            assert len(d["trial_signed_combinations"])==32
            assert d["trial_factors_need_NBC_SOURCE_COMBINATION_VERIFICATION"] is True
            assert all(x["not_a_confirmed_code_combination"] is True and
                       x["signed_member_action_count"]==165
                       for x in d["trial_signed_combinations"])
            assert 'id="g12-combinations"' in (SITE/"project-lab.html").read_text(encoding="utf-8")
            assert 'id="g12-run-case"' in (SITE/"project-lab.html").read_text(encoding="utf-8")
            assert 'id="g12-run-stiffness"' in (SITE/"project-lab.html").read_text(encoding="utf-8")
            assert 'id="g12-run"' in (SITE/"project-lab.html").read_text(encoding="utf-8")
            assert "JP_G15_GATE12_RUN_V1" in (SITE/"gate12.js").read_text(encoding="utf-8")
            assert d["source_grid_members"]==165 and d["source_columns"]==23
            assert d["engineering_approval"] is False
            assert d["seismic_mass_reconciled"] is False
            assert d["actual_slab_shell_elements"] is False
            assert d["displacement_limit_compliance_verified"] is False
            assert d["source_F3_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"
            assert {c["boundary"] for c in d["cases"]}=={"FLEXIBLE","RIGID_MPC_TRIAL"}
            assert all(c["local_signed_member_action_count"]==165 and
                c["reaction_equilibrium_verified"] is True and
                c["max_force_equilibrium_residual_kN"]<.001 and
                c["max_moment_equilibrium_residual_kNm"]<.001 and
                len(c["governing_signed_local_12_actions"])==12
                for c in d["cases"])
            assert 'id="lab-gate12"' in (SITE/"project-lab.html").read_text(encoding="utf-8")
            assert "g15-gate12-diaphragm-fe.v0.1.json" in (SITE/"gate12.js").read_text(encoding="utf-8")
        except (AssertionError,KeyError,ValueError,TypeError,OSError) as e:
            problems.append("Gate12 finite element source boundary QA failure: "+str(e))
    g13=SITE/"data/g15-gate13-shell-wall.v0.1.json"
    if not g13.exists():
        problems.append("Gate13 shell/beam-wall source-derived FE audit missing")
    else:
        try:
            d=json.loads(g13.read_text(encoding="utf-8"))
            assert d["schema"]=="jp.structural.g15.gate13.bounded_shell_wall_loadpaths.v0.1"
            assert d["source_grid_3d_beam_column_segments"]==165
            assert d["subdivided_3d_frame_segments"]==171
            assert d["shell_elements_on_one_trial_floor"]==4
            assert d["shells_represent_complete_building"] is False
            assert d["real_wall_locations_verified"] is False
            assert d["engineering_approval"] is False
            assert d["seismic_mass_reconciled"] is False
            assert d["source_F3_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"
            assert len(d["cases"])==27 and len(d["comparisons"])==9
            assert {x["mode"] for x in d["cases"]}=={
                "FRAME_POINT_PATCH","SHELLMITC4_PATCH","FULL_RIGID_MPC_REFERENCE"}
            assert all(x["frame_local_signed_action_count"]==171 and
                x["force_and_moment_equilibrium_pass"] is True and
                x["force_equilibrium_error_kN"]<.001 and
                x["moment_equilibrium_error_kNm"]<.001 for x in d["cases"])
            assert 'id="lab-gate13"' in (SITE/"project-lab.html").read_text(encoding="utf-8")
            assert "g15-gate13-shell-wall.v0.1.json" in (SITE/"gate13.js").read_text(encoding="utf-8")
        except (AssertionError,KeyError,ValueError,TypeError,OSError) as e:
            problems.append("Gate13 physical shell source/provenance error: "+str(e))
    g14=SITE/"data/g15-gate14-multilevel-shell.v0.1.json"
    if not g14.exists():
        problems.append("Gate14 multi-level ShellMITC4 result missing")
    else:
        try:
            d=json.loads(g14.read_text(encoding="utf-8"))
            assert d["schema"]=="jp.structural.g15.gate14.multilevel_bay_shell_wall.v0.1"
            assert d["chosen_assumed_panel_levels"]==[1,2]
            assert d["source_grid_3d_beam_column_segments"]==165
            assert d["subdivided_3d_frame_segments"]==177
            assert d["shell_elements_across_assumed_levels"]==8
            assert d["source_bay_geometry_repeated_on_real_floor_verified"] is False
            assert d["shells_represent_complete_building"] is False
            assert d["real_wall_locations_verified"] is False
            assert d["seismic_mass_reconciled"] is False
            assert d["engineering_approval"] is False
            assert d["source_F3_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"
            assert len(d["cases"])==27 and len(d["comparisons"])==9
            assert {x["mode"] for x in d["cases"]}=={
                "FRAME_POINT_PATCH_2F","SHELLMITC4_PATCH_2F",
                "FULL_RIGID_MPC_REFERENCE_2F"}
            assert all(x["frame_local_signed_action_count"]==177 and
                x["force_and_moment_equilibrium_pass"] is True and
                x["force_equilibrium_error_kN"]<.001 and
                x["moment_equilibrium_error_kNm"]<.001 for x in d["cases"])
            assert 'id="lab-gate14"' in (SITE/"project-lab.html").read_text(encoding="utf-8")
            assert "g15-gate14-multilevel-shell.v0.1.json" in (SITE/"gate14.js").read_text(encoding="utf-8")
        except (AssertionError,KeyError,ValueError,TypeError,OSError) as e:
            problems.append("Gate14 shell numerical or public safety QA failed: "+str(e))
    g15=SITE/"data/g15-gate15-mesh-opening.v0.1.json"
    if not g15.exists():
        problems.append("Gate15 shell refinement result missing")
    else:
        try:
            d=json.loads(g15.read_text(encoding="utf-8"))
            assert d["schema"]=="jp.structural.g15.gate15.mesh_opening_source_bay.v0.1"
            assert [m["active_shells"] for m in d["models"]]==[8,32,24]
            assert len(d["cases"])==27 and len(d["comparisons"])==9
            assert {c["mode"] for c in d["cases"]}=={
                "MESH_2X2_FULL","MESH_4X4_FULL","MESH_4X4_CENTER_VOID"}
            assert d["opening_geometry_and_structural_trim_verified"] is False
            assert d["full_floor_slab_geometry_verified"] is False
            assert d["mesh_convergence_verified"] is False
            assert d["mass_source_reconciled"] is False
            assert d["engineering_approval"] is False
            assert d["source_F3_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"
            assert all(c["force_and_moment_equilibrium_pass"] and
                       c["force_equilibrium_error_kN"]<.001 and
                       c["moment_equilibrium_error_kNm"]<.001 for c in d["cases"])
            assert 'id="lab-gate15"' in (SITE/"project-lab.html").read_text(encoding="utf-8")
            assert "g15-gate15-mesh-opening.v0.1.json" in (SITE/"gate15.js").read_text(encoding="utf-8")
        except (AssertionError,KeyError,TypeError,ValueError,OSError) as e:
            problems.append("Gate15 FEM mesh, source boundary or HOLD violated: "+str(e))
    g16=SITE/"data/g15-gate16-source-mesh.v0.1.json"
    if not g16.exists():
        problems.append("Gate16 source audited FE numerical artifact missing")
    else:
        try:
            d=json.loads(g16.read_text(encoding="utf-8"))
            assert d["schema"]=="jp.structural.g15.gate16.third_resolution_source_mass_review.v0.1"
            assert len(d["cases"])==36 and len(d["comparisons"])==9
            assert [m["element_count_two_levels"] for m in d["models"]]==[8,32,128,24]
            assert d["mass_source_reconciled"] is False
            assert d["mesh_convergence_accepted"] is False
            assert d["source_concrete_unit_weight_conflict_unresolved"] is True
            assert d["source_full_slab_and_terrace_boundaries_verified"] is False
            assert d["F3_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"
            assert d["engineering_approval"] is False
            assert all(c["force_and_moment_equilibrium_pass"] is True and
                       c["force_equilibrium_error_kN"]<.001 and
                       c["moment_equilibrium_error_kNm"]<.001 for c in d["cases"])
            assert 'id="lab-gate16"' in (SITE/"project-lab.html").read_text()
            assert "g15-gate16-source-mesh.v0.1.json" in (SITE/"gate16.js").read_text()
        except (KeyError,AssertionError,TypeError,ValueError,OSError) as e:
            problems.append("Gate16 FEM/source check/HOLD error: "+str(e))
    g17=SITE/"data/g15-gate17-source-audit.v0.1.json"
    if not g17.exists():
        problems.append("Gate17 source-traced mass discrepancy ledger missing")
    else:
        try:
            d=json.loads(g17.read_text(encoding="utf-8"))
            assert d["schema"]=="jp.structural.g15.gate17.source_mass_conflict_ledger.v0.1"
            assert d["audit_fact_count"]==11
            assert abs(d["report_seismic_weight_kN"]-6831.9109)<.0001
            assert len(d["gap_scenarios"])==2
            assert all(g["unexplained_kN"]>0 and
                       g["source_verified_reconciliation"] is False for g in d["gap_scenarios"])
            assert d["slab_125mm_25kN_m3_implied_selfweight_kPa"]==3.125
            assert d["whole_building_concrete_density_reconciled"] is False
            assert d["original_ETABS_e2k_for_this_building_found"] is False
            assert d["engineering_approval"] is False
            assert d["source_mass_reconciled"] is False
            assert d["F3_status"]=="NOT SAFE IN ONE WAY SHEAR"
            assert len(d["decision_gates"])==5 and not any(g["ready"] for g in d["decision_gates"])
            assert 'id="lab-gate17"' in (SITE/"project-lab.html").read_text(encoding="utf-8")
            assert "g15-gate17-source-audit.v0.1.json" in (SITE/"gate17.js").read_text(encoding="utf-8")
        except (AssertionError,KeyError,TypeError,ValueError,OSError) as e:
            problems.append("Gate17 report fidelity or structural safety HOLD failed: "+str(e))
    g18=SITE/"data/g15-gate18-source-mass-f3.v0.1.json"
    if not g18.exists():
        problems.append("Gate18 source storey-mass and F3 safety reconciliation missing")
    else:
        try:
            d=json.loads(g18.read_text(encoding="utf-8"))
            assert d["schema"]=="jp.structural.g15.gate18.story_mass_and_f3_safety.v0.1"
            assert d["reported_mass_table_units_printed"] is False
            assert d["kilograms_inferred_not_native_ETABS_verified"] is True
            assert d["ETABS_source_mass_settings_observed"] is False
            assert d["mass_source_reconciled"] is False
            assert d["f3_source_explicit_verdict"]=="NOT SAFE IN ONE WAY SHEAR"
            assert d["f3_current_design_accepted"] is False
            assert d["engineering_approval"] is False
            assert abs(d["reported_minus_story_table_W_kN"])<=d["max_rounding_bound_kN"]
            assert len(d["source_floor_conditional_weights"])==3
            assert len(d["f3_hypothetical_depth_trials"])==4
            assert all(c["redesign_accepted"] is False for c in d["f3_hypothetical_depth_trials"])
            assert 'id="lab-gate18"' in (SITE/"project-lab.html").read_text(encoding="utf-8")
            assert "g15-gate18-source-mass-f3.v0.1.json" in (SITE/"gate18.js").read_text(encoding="utf-8")
        except (AssertionError,KeyError,TypeError,ValueError,OSError) as ex:
            problems.append("Gate18 mass-source or F3 safety QA failed: "+str(ex))
    g19=SITE/"data/g15-gate19-e2k-readiness.v0.1.json"
    if not g19.is_file():
        problems.append("Missing Gate19 original-model intake readiness JSON")
    else:
        try:
            d=json.loads(g19.read_text(encoding="utf-8"))
            assert d["schema"]=="jp.structural.g15.gate19.e2k_source_intake.v0.1"
            assert d["status"]=="BLOCKED_ORIGINAL_ETABS_MODEL_NOT_FOUND"
            assert d["source_candidate_sha256"] is None
            assert d["raw_model_uploaded"] is False
            assert d["raw_model_published"] is False
            assert d["source_model_admitted"] is False
            assert d["physical_mass_reconciled"] is False
            assert d["f3_source_status"]=="NOT SAFE IN ONE WAY SHEAR"
            assert d["engineering_approval"] is False
            assert 'id="lab-gate19"' in (SITE/"project-lab.html").read_text()
        except (KeyError,AssertionError,ValueError,TypeError,OSError) as exc:
            problems.append("Gate19 ETABS source/structural safety failed: "+str(exc))
    g20=SITE/"data/g15-gate20-crosswalk.v0.1.json"
    if not g20.is_file():
        problems.append("Gate20 P0/P1 evidence crosswalk is missing")
    else:
        try:
            d=json.loads(g20.read_text(encoding="utf-8"))
            assert d["schema"]=="jp.structural.g15.gate20.crosswalk_F3_reconciliation.v0.1"
            assert d["gate_count"]==15 and d["accepted_gate_count"]==0
            assert d["upstream_native_ETABS_model_found"] is False
            assert d["native_ETABS_mass_unit_and_source_definition_verified"] is False
            assert d["component_mass_reconciliation_complete"] is False
            assert d["f3"]["source_verdict"]=="NOT SAFE IN ONE WAY SHEAR"
            assert d["f3"]["F3_redesign_verified"] is False
            assert d["engineering_approval"] is False
            assert not any(x["accepted"] for x in d["gates"])
            assert 'id="lab-gate20"' in (SITE/"project-lab.html").read_text()
            assert "g15-gate20-crosswalk.v0.1.json" in (SITE/"gate20.js").read_text()
        except (KeyError,AssertionError,ValueError,TypeError,OSError) as ex:
            problems.append("Gate20 engineering evidence safety violation: "+str(ex))
    g21=SITE/"reports/g15-gate21-report.v0.1.json"
    if not g21.is_file():
        problems.append("Gate21 actual OpenSees numerical report missing")
    else:
        try:
            import json,hashlib
            d=json.loads(g21.read_text())
            m=json.loads((SITE/"reports/g15-gate21-manifest.json").read_text())
            assert d["schema"]=="jp.structural.g15.gate21.open_reproducible_sar.v0.1"
            assert d["case_count"]==5 and d["signed_end_action_count"]==825
            assert d["counts"]["members"]==165
            assert d["F3_verdict"]=="NOT SAFE IN ONE WAY SHEAR" and d["engineering_approval"] is False
            assert not d["model_ETABS_source_verified"] and not d["p_delta_performed"]
            assert all(x["force_residual_kN"]<.001 and x["moment_residual_kNm"]<.001 for x in d["cases"])
            for name,item in m["files"].items():
                assert hashlib.sha256((SITE/"reports"/name).read_bytes()).hexdigest()==item["sha256"]
            assert 'id="gate21-report-engine"' in (SITE/"more.html").read_text()
            assert 'id="lab-gate21"' in (SITE/"project-lab.html").read_text()
        except (KeyError,AssertionError,ValueError,TypeError,OSError) as ex:
            problems.append("Gate21 real source-cited report validation failed: "+str(ex))
    book=(SITE/"report.html").read_text(encoding="utf-8")
    for i in range(1,8):
        if f'id="chapter-{i:02d}"' not in book:
            problems.append("Report book chapter missing: "+str(i))
    if 'id="report-contents"' not in book or 'id="rb-print"' not in book:
        problems.append("Continuous report contents and PDF-print interaction missing")
    if book.count('class="rb-chapter"')!=7:
        problems.append("Continuous report expected exactly seven chapters")
    if 'report-book.js' not in book or not (SITE/"report-book.js").is_file():
        problems.append("Report book live OpenSees data reader absent")
    if not (SITE/"report-book.css").is_file():
        problems.append("Report book responsive and print styles missing")
    if any('id="'+mid+'"' in book for mid in ("m09-report-case","d2-trace","gate05-report","gate06-report","gate21-report-engine")):
        problems.append("Out-of-sequence R&D panels remain in the original report")
    shelf=(SITE/"more.html").read_text(encoding="utf-8")
    for mid in ("m09-report-case","d2-trace","gate05-report","gate06-report","gate21-report-engine"):
        if shelf.count('id="'+mid+'"')!=1:
            problems.append("R&D panel missing or duplicated in More shelf: "+mid)
    if 'id="chapter-01-input-check"' not in book:
        problems.append("Chapter 1 sequential source review missing")
    guide=(SITE/"more.html").read_text(encoding="utf-8")
    for marker in ("guide-map","guide-3d","guide-run","guide-lab","guide-skills","guide-machines","guide-selftest"):
        if f'id="{marker}"' not in guide:
            problems.append("Missing integrated More learning chapter "+marker)
    if guide.count('<details class="guide-check">')<10:
        problems.append("More teach-back content lost")
    if 'NOT SAFE IN ONE WAY SHEAR' not in guide or "825" not in guide:
        problems.append("More guide engineering limitations changed unexpectedly")
    if not (SITE/"more-guide.css").is_file():
        problems.append("More guide stylesheet not shipped")
    try:
        from check_g15_chapter01_source import check as check_ch1
        check_ch1()
    except (AssertionError,KeyError,ValueError,TypeError,OSError) as ex:
        problems.append("Chapter01 source-evidence and safety gate failed: "+str(ex))
    fem=(SITE/"more.html").read_text()
    for key in ("guide-fem-triad","fem-three","fem-svg","fem-numbers","fem-manual-compare"):
        if fem.count('id="'+key+'"')!=1:
            problems.append("Missing synchronized FEM teaching view: "+key)
    for file in ("fem-triad.js","more-guide.css"):
        if not (SITE/file).is_file():problems.append("Missing FEM learning asset "+file)
    for file in ("opensees-cantilever-learning.v0.1.json","fem-workflow-map.v0.1.json",
                 "nbc105-verified-rule-inventory.v0.1.json"):
        if not (SITE/"data"/file).is_file():problems.append("Missing real FEM/code projection "+file)
    if 'id="chapter-02-input-provenance"' not in book:
        problems.append("Source-first supports and loads input review not linked in Chapter2")
    ch2=SITE/"data/g15-chapter02-source-audit.v0.1.json"
    if not ch2.is_file():
        problems.append("Chapter02 source-checked material arithmetic output absent")
    else:
        try:
            d=json.loads(ch2.read_text(encoding="utf-8"))
            assert d["schema"]=="jp.structural.g15.chapter02.source_audit.v0.1"
            assert d["source_record_count"]==21
            assert d["gate_open_count"]==8 and d["gate_accepted_count"]==0
            assert not d["engineering_approval"] and not d["actual_model_materials_verified"]
            assert not d["actual_member_load_assignments_verified"]
            assert d["original_F3_verdict"]=="NOT SAFE IN ONE WAY SHEAR"
            assert len(d["illustrative_square_member_alternatives"])==6
            assert "chapter02-audit.js" in book
            assert all('id="c02-'+s+'"' in book for s in ("concrete","steel","cover","code","source-scenarios"))
        except (KeyError,AssertionError,ValueError,TypeError,OSError) as ex:
            problems.append("Chapter02 material code/density discrepancy QA failed: "+str(ex))
    ch2loads=SITE/"data/g15-chapter02-load-review.v0.1.json"
    if not ch2loads.is_file():
        problems.append("Chapter02 documented load rate audit missing")
    else:
        try:
            d=json.loads(ch2loads.read_text(encoding="utf-8"))
            assert d["schema"]=="jp.structural.g15.chapter02.load_review.v0.1"
            assert d["numeric_screen_discrepancies_count"]==2
            assert d["member_load_assignments_accepted"]==0
            assert not d["engineering_approval"] and not d["source_geometry_verified"]
            assert not d["private_ETABS_load_assignment_verified"]
            assert d["original_F3_verdict"]=="NOT SAFE IN ONE WAY SHEAR"
            assert len(d["wall_load_arithmetic"])==5
            assert 'id="c02-wall-audit"' in book
        except (KeyError,AssertionError,ValueError,TypeError,OSError) as e:
            problems.append("Chapter02 source load unresolved scope QA failed: "+str(e))
    ch2seis=SITE/"data/g15-chapter02-seismic-audit.v0.1.json"
    if not ch2seis.is_file():
        problems.append("Chapter02 original seismic/wind/combination audit missing")
    else:
        try:
            d=json.loads(ch2seis.read_text(encoding="utf-8"))
            assert d["schema"]=="jp.structural.g15.chapter02.seismic_wind_combinations_audit.v0.1"
            assert d["physical_evidence_accepted"] is False and d["engineering_approval"] is False
            assert d["source_mass_reconciled"] is False
            assert d["source_f3_verdict"]=="NOT SAFE IN ONE WAY SHEAR"
            assert d["source_summary"]["source_ULS_coefficient_printed"]==.131
            assert d["source_summary"]["formula_ULS_coefficient_unrounded"]==.13125
            assert d["wind_screen"]["wind_dominance_proven"] is False
            assert d["soft_storey_screen"]["actual_story_stiffnesses_verified"] is False
            assert len(d["source_conditional_floor_weights_and_forces"])==3
            assert 'id="c02-seismic-source"' in book
            assert 'id="c02-wind-evidence"' in book
            assert 'id="c02-soft-evidence"' in book
            assert 'id="c02-combo-evidence"' in book
            assert "chapter02-seismic.js" in book
        except (KeyError,AssertionError,ValueError,TypeError,OSError) as e:
            problems.append("Chapter02 seismic source/engineering hold QA failed: "+str(e))
    ch3=SITE/"data/g15-chapter03-method.v0.1.json"
    if not ch3.is_file():
        problems.append("Chapter03 real-OpenSees/source-method projection missing")
    else:
        try:
            d=json.loads(ch3.read_text(encoding="utf-8"))
            n=d["real_OpenSees_numerical_snapshot"]
            assert d["schema"]=="jp.structural.g15.chapter03.method_execution.v0.1"
            assert d["engineering_approval"] is False and d["original_native_ETABS_model_authenticated"] is False
            assert d["source_gates_open"]==15 and d["accepted_engineering_method_stages"]==0
            assert d["original_F3_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"
            assert n["case_count"]==5 and n["signed_member_end_action_records"]==825
            assert n["max_equilibrium_force_residual_kN"]<.001
            assert n["max_equilibrium_moment_residual_kNm"]<.001
            assert len(d["stages"])==12
            assert 'id="chapter-03-stages"' in book and "chapter03-method.js" in book
        except (KeyError,AssertionError,ValueError,TypeError,OSError) as exc:
            problems.append("Chapter03 original method / OpenSees numerical QA failed: "+str(exc))
    if problems:raise SystemExit("\n".join(problems))
    print("STRUCTURAL_SITE_QA_PASS: seven pages including open real-source 3D frame analysis, source-linked de-identified project journal, SP16, M09/D2, privacy checks and shared theme")
if __name__=="__main__":main()
