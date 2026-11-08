#!/usr/bin/env python3
"""R6.6 published *as-issued* ETABS-report benchmark, not a new ETABS analysis.

Builds a traceable public report from pre-existing report claims, independently
checks arithmetic and reports table/prose inconsistencies. Never silently
changes the selected ETABS21 model, old report, physical/safety acceptance or
source-controlled raw file storage. Missing full member reactions remain a
deferred enhancement and are NOT blockers for bounded follow-on work.
"""
from __future__ import annotations
import argparse
from decimal import Decimal
from hashlib import sha256
from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "registry/r6p6_reported_structural_results.v0.1.json"
GOVERNING = ROOT / "registry/r6p5_etabs21_governing_pair.v0.1.json"
GATE18 = ROOT / "registry/g15-gate18-report-mass-f3-source.v0.1.json"
SCHEMA = "jp.structural.r6p6.as_issued_report_result_benchmark.v0.1"


class BenchmarkError(ValueError):
    pass


def number(n):
    if isinstance(n, bool):
        raise BenchmarkError("boolean numeric value")
    try:
        v = Decimal(str(n))
    except (ArithmeticError, ValueError, TypeError) as exc:
        raise BenchmarkError("invalid numeric source data") from exc
    if not v.is_finite():
        raise BenchmarkError("nonfinite source data")
    return v


def load_sources(source=SOURCE, governing=GOVERNING, gate18=GATE18):
    d = json.loads(Path(source).read_text(encoding="utf8"))
    g = json.loads(Path(governing).read_text(encoding="utf8"))
    v = json.loads(Path(gate18).read_text(encoding="utf8"))
    if d.get("schema") != SCHEMA:
        raise BenchmarkError("invalid report benchmark schema")
    if g["decision"]["state"] != "USER_CONFIRMED_CURRENT_GOVERNING_ETABS21_ULS_SLS":
        raise BenchmarkError("current model authority missing")
    if g["admission_gates"]["engineering_approval"] or g["admission_gates"]["native_ETABS_solution_and_mass_per_story_tables_reproduced"]:
        raise BenchmarkError("source selection cannot be silently upgraded to engineering approval or solved mass")
    if d["source"]["report_sha256"] != v["source_pdf"]["sha256"]:
        raise BenchmarkError("source report identity mismatch")
    if d["original_mass"]["reported_seismic_weight_kN"] != v["source_mass_table"]["etabs_weight_kN"]:
        raise BenchmarkError("original report weight changed")
    original = d["original_mass"]["source_masses"]
    expected = v["source_mass_table"]["reported_stories"]
    if len(original) != 4 or [(s["storey"], s["value"]) for s in original[:3]] != [(s["storey"], s["printed_mass_value"]) for s in expected]:
        raise BenchmarkError("report story mass rows changed")
    if not original[-1]["excluded_from_report_seismic_weight"] or original[-1]["value"] != v["source_mass_table"]["base_entry"]["printed_mass_value"]:
        raise BenchmarkError("base mass inclusion changed")
    if d["original_mass"]["reported_input_units_printed"] is not False or d["original_mass"]["source_e2k21_mass_reproduced"] is not False:
        raise BenchmarkError("report mass units/model status improperly accepted")
    if d["foundation"]["report_status"] != "NOT SAFE IN ONE WAY SHEAR" or d["foundation"]["acceptance"] is not False:
        raise BenchmarkError("F3 failure cannot be cleared")
    if d["readiness"]["professional_engineering_approval"] or d["readiness"]["new_ETABS21_solution_executed"] or d["readiness"]["MRSM_scaling_executed"]:
        raise BenchmarkError("report results cannot become a new design approval")
    return d


def evaluate(d):
    m = d["original_mass"]
    wi = sum((number(s["value"]) for s in m["source_masses"][:3]),Decimal(0)) * number(m["conditional_g_m_per_s2"]) / Decimal(1000)
    report_mass = number(m["reported_seismic_weight_kN"])
    if abs(wi-report_mass) > Decimal("0.0002"):
        raise BenchmarkError("reported story mass arithmetic did not reproduce old seismic weight")
    cases=d["equivalent_static"]["cases"]
    if {(c["limit_state"],c["direction"]) for c in cases} != {("ULS","X"),("ULS","Y"),("SLS","X"),("SLS","Y")}:
        raise BenchmarkError("missing seismic case direction")
    for c in cases:
        implied=report_mass*number(c["coefficient"])
        if abs(implied-number(c["base_shear_kN"]))>Decimal("0.0005"):
            raise BenchmarkError("report static base shear does not match report weight and coefficient")
    modes=d["modal"]["source_rows"]
    if len(modes)!=12 or [r["mode"] for r in modes]!=list(range(1,13)):
        raise BenchmarkError("missing modal rows")
    if any(not (Decimal(0) <= number(r[k]) <= Decimal(1)) for r in modes for k in ("sum_ux","sum_uy")):
        raise BenchmarkError("invalid modal cumulative participation")
    first = next((r["mode"] for r in modes if number(r["sum_ux"])>=Decimal("0.90") and number(r["sum_uy"])>=Decimal("0.90")),None)
    if first != d["modal"]["calculated_by_report_table_first_mode_meeting_90pct_both_axes"] or first != 5:
        raise BenchmarkError("report modal threshold is not five")
    if "6 modes" not in d["modal"]["printed_claim"]:
        raise BenchmarkError("source prose-vs-table discrepancy was removed")
    if len(d["selected_member_design_samples"])!=3:
        raise BenchmarkError("selected sample coverage changed")
    return {
      "schema":"jp.structural.r6p6.reported_results_comparison.v0.1",
      "source_status":"HISTORICAL_AS_ISSUED_REPORT_VALUES_NOT_GOVERNING_ETABS21_SOLVER_OUTPUT",
      "current_governing_source":"USER_CONFIRMED_ETABS21_ULS_SLS",
      "report_seismic_weight_kN":float(report_mass),
      "report_story_mass_arithmetic_kN_if_kg":float(wi),
      "reported_units_explicit":False,
      "reported_static_cases":cases,
      "report_modal_rows":modes,
      "first_report_table_mode_to_reach_90pct_in_both_axes":first,
      "report_prose_claims_six_modes":True,
      "mode_count_source_disagreement":"REPORT_PROSE_SIX_VS_CUMULATIVE_TABLE_FIVE",
      "report_serviceability":d["reported_serviceability"],
      "selected_member_force_samples":d["selected_member_design_samples"],
      "selected_member_samples_not_comprehensive":True,
      "independent_current_etabs21_results_reproduced":False,
      "report_reuse_for_read_only_workbench":True,
      "physical_mass_reconciled":False,
      "F3_one_way_shear_unsafe":True,
      "MRSM_scaling_executed":False,
      "engineering_approval":False
    }


def markup(d, result):
    esc=escape
    f=lambda v: str(v)
    cases="".join("<tr><td>"+esc(x["limit_state"])+"</td><td>"+esc(x["direction"])+"</td><td>"+f(x["coefficient"])+"</td><td>"+f(x["base_shear_kN"])+"</td></tr>" for x in result["reported_static_cases"])
    modes="".join("<tr><td>"+f(x["mode"])+"</td><td>"+f(x["period_s"])+"</td><td>"+f(x["sum_ux"])+"</td><td>"+f(x["sum_uy"])+"</td></tr>" for x in result["report_modal_rows"])
    members="".join("<tr><td>"+esc(x["member"])+"</td><td>"+esc(x["element_type"])+"</td><td>"+esc(x["combination"])+"</td><td>"+f(x.get("moment3_kNm","—"))+"</td><td>"+f(x.get("shear2_kN","—"))+"</td></tr>" for x in d["selected_member_design_samples"])
    style="""<style>
    :root{font-family:system-ui,-apple-system,Segoe UI,sans-serif;color-scheme:light dark}
    body{margin:0;background:#f8f7f2;color:#17212c}main{max-width:1060px;margin:0 auto;padding:24px}
    nav{padding:12px 0}a{color:#1a5a94}h1{font-size:clamp(1.9rem,5vw,3rem);line-height:1.1}
    .lead{color:#46515e;font-size:1.08rem;max-width:750px}.banner{background:#fff0d6;border:1px solid #cfad73;padding:16px;border-radius:12px}
    .stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:20px 0}
    .stat{border:1px solid #cbd2db;border-radius:12px;background:#fff;padding:16px}.stat strong{font-size:1.7rem;display:block}
    section{border:1px solid #d6dce4;border-radius:14px;background:white;margin:18px 0;padding:20px}
    .scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}td,th{border-bottom:1px solid #dee3e9;text-align:left;padding:10px}th{background:#eaf0f7}
    p,li{line-height:1.65}small{color:#586575}.bad{color:#94251a;font-weight:700}.btn{display:inline-block;padding:9px 13px;background:#183e67;color:white;border-radius:8px;text-decoration:none}
    </style>"""
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>R6.6 · Existing report results | JP Structural Analysis</title>"""+style+"""</head><body><main>
<nav><a href="../index.html">Home</a> / <a href="../report.html#annex-r6p6-reported-results">Annex R</a> / R6.6</nav>
<p><small>8 November 2026 · AS-ISSUED REPORT BENCHMARK · NO ETABS RERUN</small></p>
<h1>Use the results already documented.</h1>
<p class="lead">R6.6 extracts and checks the original structural report's documented seismic, modal, drift and selected member outputs. It does not fabricate a fresh solution from the user-designated ETABS21 model.</p>
<div class="banner"><strong>Decision:</strong> historical report results are reusable for documented comparisons, educational analysis and read-only engineering workbench development. They cannot by themselves certify current ETABS21 model masses, complete member forces or construction safety. The F3 footing's unsafe one-way-shear result remains open.</div>
<div class="stats">
<div class="stat"><small>Reported original weight</small><strong>6,831.9109</strong><small>kN · historical source</small></div>
<div class="stat"><small>ULS base shear</small><strong>894.9803</strong><small>kN · EQX/EQY source table</small></div>
<div class="stat"><small>SLS base shear</small><strong>860.8208</strong><small>kN · EQX/EQY source table</small></div>
<div class="stat"><small>Reported modal rows</small><strong>12</strong><small>Original section 5.5</small></div></div>
<section><h2>1. Equivalent-static seismic results</h2><p>Reproduced from section 5.1.1 auto seismic table and section 5.12 base-reaction table; these are <em>not</em> every support reaction under gravity loads.</p>
<div class="scroll"><table><thead><tr><th>Limit state</th><th>Axis</th><th>Source coefficient</th><th>Reported base shear (kN)</th></tr></thead><tbody>"""+cases+"""</tbody></table></div></section>
<section><h2>2. Modal periods and cumulative participation</h2>
<p>All twelve rows below are as printed in section 5.5. <strong>Source QA discrepancy:</strong> the report's prose says 90% participation in six modes, but its cumulative UX and UY rows first both exceed 90% at <strong>mode 5</strong>. Preserve both and obtain clarification during a later design review.</p>
<div class="scroll"><table><thead><tr><th>Mode</th><th>Period (s)</th><th>Cumulative UX</th><th>Cumulative UY</th></tr></thead><tbody>"""+modes+"""</tbody></table></div></section>
<section><h2>3. Displacement and drift summaries</h2><p>As-issued maximum ULS displacement: <strong>22.9069 mm</strong>; SLS displacement: <strong>12.846306 mm</strong>. Reported ULS maximum storey drift ratio: <strong>0.00288</strong>; SLS: <strong>0.002174</strong>. The PDF labels them safe; that claim is not independently accepted as a current-model design approval.</p></section>
<section><h2>4. Reported member-design examples</h2><p>These are selected excerpts from sections 6.1–6.2, not full output for every frame, end or combination.</p>
<div class="scroll"><table><thead><tr><th>Example member</th><th>Type</th><th>Report combination</th><th>M3 (kN·m)</th><th>Shear V2 (kN)</th></tr></thead><tbody>"""+members+"""</tbody></table></div>
<p>Current model input geometry and load assignments can be explored separately; full signed member results require an ETABS solution or a bounded independent recomputation, not extrapolation from these examples.</p></section>
<section><h2>5. Foundation finding and next implementation stage</h2><p class="bad">F3: NOT SAFE IN ONE WAY SHEAR — source report section 6.4.2.</p>
<p><strong>Proceed with:</strong> source-backed 2D/3D frame-and-floor presentation; report-value comparison; bounded independent load and quantity checks; member/result availability flags; design-report chapter navigation. Keep old mass versus new model separate, and retain engineer approval gates for design decisions.</p>
<p><a class="btn" href="r6p6-report-results-review.json">Inspect validated comparison JSON</a></p></section>
<p><small>Source: original revised structural report (governed Drive source ID in JSON); current ETABS21 ULS/SLS pair in existing source register. No private model bytes, parcel records or client documents are published here.</small></p>
</main></body></html>"""


def build(output_dir):
    d=load_sources()
    result=evaluate(d)
    root=Path(output_dir);root.mkdir(parents=True,exist_ok=True)
    stem="r6p6-report-results-review"
    j=root/(stem+".json");html=root/(stem+".html")
    j.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf8")
    html.write_text(markup(d,result),encoding="utf8")
    receipt={"schema":"jp.structural.r6p6.as_issued_report_public_manifest.v0.1",
             "file_sha256":{n:sha256((root/n).read_bytes()).hexdigest() for n in (j.name,html.name)},
             "report_sha256":d["source"]["report_sha256"],
             "model_reanalysis_performed":False,"engineering_approval":False,
             "raw_private_source_published":False}
    (root/(stem+"-manifest.json")).write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf8")
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir",type=Path,default=ROOT/"site/reports")
    args=p.parse_args()
    d=build(args.output_dir)
    print("R6P6_OLD_REPORT_VALUES_REUSED_MODAL_PROSE_TABLE_CONFLICT_5_VS_6_F3_UNSAFE",d["first_report_table_mode_to_reach_90pct_in_both_axes"])
