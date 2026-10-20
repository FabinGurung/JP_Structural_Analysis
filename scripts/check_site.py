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
PAGES=["index.html","project-lab.html","calculation-coverage.html","report.html","more.html"]
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
        for page in ("calculation-coverage.html","report.html"):
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
        for page in ("calculation-coverage.html","report.html"):
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
        for page in ("calculation-coverage.html","report.html"):
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
        for page in ("calculation-coverage.html","report.html"):
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
        for page in ("calculation-coverage.html","report.html"):
            assert "data-gate06-demo=" in (SITE/page).read_text(encoding="utf-8")
    except (KeyError,ValueError,IndexError,TypeError,AssertionError) as exc:
        problems.append("Gate06 public numeric source or safety HOLD invalid: "+str(exc))


def verify_real_project_calculation_ledger(problems):
    import json
    from math import isclose, isfinite
    p=SITE/"data/g15-project-ledger.v0.1.json"
    if not p.is_file():
        problems.append("Missing generated de-identified real-project calculation ledger")
        return
    try:
        d=json.loads(p.read_text(encoding="utf-8"))
        assert d["schema"]=="jp.structural.deidentified.project_calculation_ledger.public.v0.1"
        assert d["source_visibility"]=="PRIVATE_DRIVE_SOURCE_NOT_PUBLISHED"
        assert d["publication"]=="USER_REQUESTED_DEIDENTIFIED_AGGREGATE_ONLY"
        assert d["derived"]["total_gate05_gate06_gate07_case_solves"]==376
        assert d["scope"]["member_count"]==165
        assert len(d["workflow"])==6 and len(d["calculation_families"])>=12
        assert d["gate07"]["case_count"]==204
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

def main():
    problems=[]
    for page in PAGES:
        p=SITE/page
        if not p.is_file():problems.append("Missing "+page);continue
        text=p.read_text(encoding="utf-8")
        parser=Parse();parser.feed(text)
        if parser.css!=["styles.css"]:problems.append(page+": inconsistent stylesheet")
        if parser.scripts!=(["app.js","d2.js"] if page in ("calculation-coverage.html","report.html") else ["app.js","project-ledger.js","private-force-viewer.js"] if page=="project-lab.html" else ["app.js"]):problems.append(page+": inconsistent app scripts")
        if parser.mains!=1:problems.append(page+": expected one main")
        for target in ("index.html","project-lab.html","calculation-coverage.html","report.html","more.html"):
            if target not in text:problems.append(page+": missing nav target "+target)
        for url in parser.links+parser.css+parser.scripts:
            u=urlparse(url)
            if u.scheme or url.startswith("//") or url.startswith("#") or url.startswith("mailto:"):continue
            local=(SITE/page).parent/unquote(u.path)
            if not local.is_file() and not (local in {SITE/"demo/SAR.html", SITE/"demo/validation_results.json"} and not (SITE/"demo").exists()):
                problems.append(page+": broken local link "+url)
    for path in ("styles.css","app.js","d2.js","data/sp16_1980_primary_source.v0.1.json","data/report-calculation-coverage.v0.1.json"):
        if not (SITE/path).is_file():problems.append("Missing "+path)
    if (SITE/"styles.css").stat().st_size>28000:problems.append("Shared CSS unexpectedly large")
    if (SITE/"app.js").stat().st_size>12000:problems.append("Shared JS unexpectedly large")
    verify_m09_case(problems)
    verify_sp16_and_d2(problems)
    verify_original_chart31_source_spots(problems)
    verify_synthetic_nbc105_esm(problems)
    verify_gate06_synthetic_source(problems)
    verify_real_project_calculation_ledger(problems)
    if problems:raise SystemExit("\n".join(problems))
    print("STRUCTURAL_SITE_QA_PASS: five pages, source-linked de-identified project journal, SP16, M09/D2, privacy checks and shared theme")
if __name__=="__main__":main()
