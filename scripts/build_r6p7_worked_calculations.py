#!/usr/bin/env python3
"""R6.7 hand-verifiable calculation book from *existing* governed sources.

Every displayed arithmetic result is recomputed here from the existing
historical report registers or the explicitly synthetic R5 fixture.
No ETABS21 run, structural approval, reinforcement as-built quantities,
real source seismic mass verification or F3 safety is claimed.
The side-by-side model viewer consumes the *provisional* public grid only.
"""
from __future__ import annotations
import argparse
from decimal import Decimal, getcontext
from hashlib import sha256
from html import escape
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/"registry/r6p6_reported_structural_results.v0.1.json"
SEIS=ROOT/"registry/g15-chapter02-seismic-facts.v0.1.json"
MODEL=ROOT/"registry/r6p5_etabs21_governing_pair.v0.1.json"
F3=ROOT/"registry/g15-gate18-report-mass-f3-source.v0.1.json"
R5=ROOT/"examples/sanitized/r5_generic_source_geometry_frame.v0.1.json"
GRID=ROOT/"site/data/g15-working-grid.public.v0.1.json"
getcontext().prec=30

def D(v):
    if isinstance(v,bool):
        raise ValueError("boolean source numeric")
    n=Decimal(str(v))
    if not n.is_finite():
        raise ValueError("nonfinite source numeric")
    return n

def fmt(x,n=4):
    return f"{float(x):,.{n}f}"

def sources():
    vals=[json.loads(p.read_text(encoding="utf8")) for p in (REPORT,SEIS,MODEL,F3,R5,GRID)]
    report,seis,model,f3,r5,grid=vals
    assert report["schema"]=="jp.structural.r6p6.as_issued_report_result_benchmark.v0.1"
    assert report["source"]["report_sha256"]==f3["source_pdf"]["sha256"]==seis["source"]["sha256"]
    assert model["decision"]["state"]=="USER_CONFIRMED_CURRENT_GOVERNING_ETABS21_ULS_SLS"
    assert not model["admission_gates"]["engineering_approval"]
    assert report["foundation"]["report_status"]=="NOT SAFE IN ONE WAY SHEAR"
    assert not report["readiness"]["professional_engineering_approval"]
    assert r5["classification"]=="SYNTHETIC_REFERENCE_NOT_A_BUILDING"
    assert grid["status"]=="SOURCE_DERIVED_HYPOTHETICAL_FRAME_NOT_VERIFIED_AS_BUILT"
    assert not grid["safety"]["engineering_approval"]
    return vals

def compute():
    r,seis,model,f3,r5,grid=sources()
    m=r["original_mass"]
    masses=m["source_masses"][:3]
    g=D(m["conditional_g_m_per_s2"])
    heights=[D("3.048"),D("6.096"),D("9.144")]
    weights=[D(x["value"])*g/D(1000) for x in masses]
    total=sum(weights,D(0))
    historical=D(m["reported_seismic_weight_kN"])
    assert abs(total-historical)<D(".0002")
    C=D(seis["seismic"]["source_reported_uls_coefficient_rounded"])
    Cs=D(seis["seismic"]["source_reported_sls_coefficient_rounded"])
    base_uls=historical*C
    base_sls=historical*Cs
    cases=r["equivalent_static"]["cases"]
    for row in cases:
        expect=base_uls if row["limit_state"]=="ULS" else base_sls
        assert abs(expect-D(row["base_shear_kN"]))<D(".0001")
    s=seis["seismic"]
    ce=D(s["source_z"])*D(s["source_spectral_shape_factor"])*D(s["source_importance"])
    c_uls=ce/(D(s["source_ductility_Rmu"])*D(s["source_overstrength_ULS"]))
    c_sls=ce*D(s["source_sls_spectral_scale"])/D(s["source_overstrength_SLS"])
    assert c_uls==D(".13125") and c_sls==D(".126")
    period=D(s["empirical_period_amplification"])*D(s["empirical_period_coefficient_kt"])*D(s["height_m"])**D(".75")
    assert abs(period-D(s["reported_period_seconds"])) < D(".005")
    # "k=1" is the source coefficient/mode for a transparent *conditional*
    # equivalent-static hand distribution, not a reconstructed ETABS result.
    distribut=[w*h for w,h in zip(weights,heights)]
    den=sum(distribut,D(0))
    floors=[{
        "storey":masses[i]["storey"],"reported_mass_unprinted_unit":float(D(masses[i]["value"])),
        "assumed_weight_kN":float(weights[i]),"height_m":float(heights[i]),
        "weight_times_height_kNm":float(distribut[i]),
        "hand_distributed_force_uls_kN":float(base_uls*distribut[i]/den),
        "hand_distributed_force_sls_kN":float(base_sls*distribut[i]/den),
        "explicitly_not_reported_ETABS_floor_force":True
    } for i in range(3)]
    assert abs(sum((D(v["hand_distributed_force_uls_kN"]) for v in floors),D(0))-base_uls)<D("0.000001")
    modes=r["modal"]["source_rows"]
    first=next((v["mode"] for v in modes if D(v["sum_ux"])>=D(".9") and D(v["sum_uy"])>=D(".9")),None)
    assert first==5 and r["modal"]["calculated_by_report_table_first_mode_meeting_90pct_both_axes"]==5
    assert "6 modes" in r["modal"]["printed_claim"]
    modal_rows=[]
    prevx=prevy=D(0)
    for item in modes:
        x,y=D(item["sum_ux"]),D(item["sum_uy"])
        assert x>=prevx and y>=prevy
        modal_rows.append({**item,"ux_increment":float(x-prevx),"uy_increment":float(y-prevy)})
        prevx,prevy=x,y
    foundation=f3["f3_source"]
    footing_b=D(foundation["sheet_footing_plan_m"][0])
    footing_l=D(foundation["sheet_footing_plan_m"][1])
    pu=D(foundation["sheet_column_axial_kN"])*D("1.5")
    q=pu/(footing_b*footing_l)
    assert abs(q-D(foundation["sheet_nominal_upward_factored_kPa"]))<D(".005")
    bars_per_m=Decimal(str(math.pi))*D(12)*D(12)/D(4)*D(1000)/D(150)
    source_loads={x["id"]:x for x in r5["source_loads"]}
    dead=source_loads["ROOF-FINISH-DL"];live=source_loads["ROOF-LIVE-LL"];wall=source_loads["EDGE-WALL-DL"]
    assert dead["pressure_kPa"]==6 and live["pressure_kPa"]==2 and live["participation_factor"]==.3
    assert wall["intensity_kN_m"]==8
    # All lengths are from SYNTHETIC R5 fixture, not the real project.
    pts={n["id"]:(D(n["x"]),D(n["y"])) for n in r5["model"]["nodes"]}
    p1,p2=pts["R1"],pts["R2"];L=((p2[0]-p1[0])**2+(p2[1]-p1[1])**2).sqrt()
    A=D(4)*D(3)
    panel_dead=A*D(dead["pressure_kPa"])
    panel_live=A*D(live["pressure_kPa"])*D(live["participation_factor"])
    line=L*D(wall["intensity_kN_m"])
    assert panel_dead==D(72) and panel_live==D("7.2") and line==D(32)
    footprint = {"points":len(grid["column_positions_mm"]),"edges":len(grid["beam_edges"]),
                 "hypothetical_edges":len(grid["hypothetical_beam_edge_indices"]),
                 "level_heights_mm":grid["floor_levels_mm"],
                 "is_current_ETABS21_geometry":False}
    assert footprint["points"]==23 and footprint["hypothetical_edges"]==2
    steps=[
      {"id":"MASS-01","chapter":"Mass","provenance":"PDF §5.10; unit inference","formula":"W_i = m_i × g ÷ 1000",
       "substitution":"270,076.47 × 9.80665 ÷ 1000","result":fmt(weights[0],6)+" kN",
       "checks":"Three nonbase entries total "+fmt(total,6)+" kN; historical printed "+fmt(historical,4)+" kN",
       "status":"REPRODUCED_CONDITIONALLY"},
      {"id":"SEIS-01","chapter":"Seismic coefficient","provenance":"PDF §2.6.4; reported factors; site not verified",
       "formula":"C_elastic = Z × S × I; C_ULS = C_elastic ÷ (Rμ × Ω_ULS)",
       "substitution":"0.35 × 2.25 × 1 = 0.7875; 0.7875 ÷ (4 × 1.5)",
       "result":fmt(c_uls,5)+" (printed coefficient 0.131)","checks":"SLS = 0.7875 × 0.2 ÷ 1.25 = 0.126",
       "status":"REPORT_ASSUMPTIONS_ONLY"},
      {"id":"BASE-01","chapter":"Base shear","provenance":"PDF §5.1 and §5.12",
       "formula":"V = C × W","substitution":"0.131 × 6,831.9109",
       "result":fmt(base_uls,6)+" kN (historical ULS 894.9803 kN)",
       "checks":"SLS: 0.126 × 6,831.9109 = "+fmt(base_sls,6)+" kN",
       "status":"SOURCE_ARITHMETIC_REPRODUCED"},
      {"id":"FLOOR-01","chapter":"Floor distribution","provenance":"Conditional hand example: h = 3.048, 6.096, 9.144 m; k = 1",
       "formula":"F_i = V × (W_i h_i) ÷ Σ(W_j h_j)",
       "substitution":"Level 1: "+fmt(base_uls,4)+" × ("+fmt(weights[0],3)+" × 3.048) ÷ "+fmt(den,3),
       "result":fmt(floors[0]["hand_distributed_force_uls_kN"],4)+" kN",
       "checks":"ΣF_i = "+fmt(sum(D(x["hand_distributed_force_uls_kN"]) for x in floors),4)+" kN",
       "status":"CONDITIONAL_DISTRIBUTION_NOT_ETABS"},
      {"id":"MODE-01","chapter":"Modal participation","provenance":"PDF §5.5 table vs narrative",
       "formula":"threshold = first mode where ΣUX ≥ 0.90 AND ΣUY ≥ 0.90",
       "substitution":"Mode 5: ΣUX = 0.9297; ΣUY = 0.9538",
       "result":"Mode 5 (table arithmetic); prose states six",
       "checks":"Increments at mode 5: UX "+fmt(modal_rows[4]["ux_increment"],4)+", UY "+fmt(modal_rows[4]["uy_increment"],4),
       "status":"CONTRADICTORY_REPORT_TEXT"},
      {"id":"FOOT-01","chapter":"Foundation F3","provenance":"PDF §6.4.2 F3 worksheet; unsafe source result",
       "formula":"q_u = P_u ÷ (B×L); A_s/m = (πd²/4)×(1000/s)",
       "substitution":"(1.5 × 571) ÷ (2.1 × 2.1); (π×12²÷4)×(1000÷150)",
       "result":fmt(q,4)+" kPa; "+fmt(bars_per_m,2)+" mm²/m",
       "checks":"Printed q=194.22 kPa; original one-way-shear verdict NOT SAFE",
       "status":"RECONSTRUCTED_PRESSURE_ONLY_UNSAFE"},
      {"id":"R5-01","chapter":"Load-path teaching fixture","provenance":"Explicitly synthetic R5 public fixture; not this building",
       "formula":"F_panel = pA; F_line = wL; F_seismic_eligible = Dead + α Live",
       "substitution":"6×(4×3)=72; 2×(4×3)×0.3=7.2; 8×4=32",
       "result":"111.2 kN total (synthetic fixture only)",
       "checks":"BM1 nodal wall-load shares: 32 × 0.5 = 16 kN at each end in lumped demonstration",
       "status":"SYNTHETIC_HAND_CALC_NOT_PROJECT"}
    ]
    return {
       "schema":"jp.structural.r6p7.worked_calculations.v0.1",
       "source":"HISTORICAL_REPORT_REPRODUCTION_PLUS_DISTINCT_SYNTHETIC_FIXTURE",
       "governing_ETABS21_model_user_selected":True,
       "ETABS21_results_reproduced":False,
       "engineer_approval":False,
       "f3_unsafe":True,
       "historical_mass_total_kN":float(total),
       "historical_mass_printed_kN":float(historical),
       "historical_mass_roundoff_kN":float(historical-total),
       "elastic_coefficient_report":float(ce),
       "uls_unrounded_source_coefficient":float(c_uls),
       "uls_printed_coefficient":float(C),
       "sls_coefficient":float(c_sls),
       "reported_empirical_period_s":float(D(s["reported_period_seconds"])),
       "computed_empirical_period_s":float(period),
       "historical_uls_base_shear_hand_kN":float(base_uls),
       "historical_sls_base_shear_hand_kN":float(base_sls),
       "conditional_distribution_exponent":1,
       "floor_distribution":floors,
       "floor_distribution_method":"CONDITIONAL_HAND_EXAMPLE_NOT_PRINTED_FLOOR_FORCES",
       "reported_mode_rows_augmented":modal_rows,
       "first_both_axes_90pct_mode_by_printed_table":first,
       "report_prose_says_six_modes":True,
       "f3_factored_pressure_kPa":float(q),
       "f3_bar_area_mm2_per_m":float(bars_per_m),
       "f3_shear_capacity_not_recomputed":True,
       "synthetic_R5":{
           "panel_area_m2":float(A),"dead_panel_kN":float(panel_dead),
           "seismic_live_panel_kN":float(panel_live),
           "wall_line_kN":float(line),"total_seismic_eligible_kN":float(panel_dead+panel_live+line),
           "not_project_data":True},
       "provisional_viewer_geometry":footprint,
       "provisional_grid_not_ETABS21":True,
       "steps":steps,
    }

def html_page(calc):
    floorrows="".join("<tr><td>"+escape(x["storey"])+"</td><td>"+fmt(x["reported_mass_unprinted_unit"],2)+"</td><td>"+fmt(x["assumed_weight_kN"],5)+"</td><td>"+fmt(x["height_m"],3)+"</td><td>"+fmt(x["weight_times_height_kNm"],2)+"</td><td>"+fmt(x["hand_distributed_force_uls_kN"],4)+"</td></tr>" for x in calc["floor_distribution"])
    modes="".join("<tr><td>"+str(x["mode"])+"</td><td>"+fmt(x["period_s"],3)+"</td><td>"+fmt(x["sum_ux"],4)+"</td><td>"+fmt(x["sum_uy"],4)+"</td><td>"+fmt(x["ux_increment"],4)+"</td><td>"+fmt(x["uy_increment"],4)+"</td></tr>" for x in calc["reported_mode_rows_augmented"])
    cards=""
    for s in calc["steps"]:
        cards+='<article class="calc-card" id="'+escape(s["id"])+'"><div class="step-header"><span>'+escape(s["id"])+'</span><span>'+escape(s["status"].replace("_"," "))+'</span></div><h3>'+escape(s["chapter"])+'</h3><p class="source">Source: '+escape(s["provenance"])+'</p><ol><li><strong>Formula</strong><code>'+escape(s["formula"])+'</code></li><li><strong>Substitute</strong><code>'+escape(s["substitution"])+'</code></li><li><strong>Calculate</strong><code>'+escape(s["result"])+'</code></li><li><strong>Verify / limit</strong><span>'+escape(s["checks"])+'</span></li></ol></article>'
    nav_items=[("Mass","MASS-01"),("Seismic","SEIS-01"),("Base shear","BASE-01"),("Floor loads","FLOOR-01"),("Modal","MODE-01"),("F3","FOOT-01"),("Load path","R5-01"),("2D/3D + BOQ","linked-member")]
    nav="".join("<a href='#"+ref+"'>"+name+"</a>" for name,ref in nav_items)
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>R6.7 · Hand calculations and linked structural views | JP</title>
<meta name="description" content="Hand calculation steps, substituted values, units and auditable results alongside linked provisional 2D/3D member inspector.">
<link rel="stylesheet" href="styles.css"><link rel="stylesheet" href="worked-calculations.css"></head>
<body><header class="site-header"><div class="wrap nav-row"><a class="brand" href="index.html"><span class="brand-mark" aria-hidden="true">JP</span><span><strong>Structural Analysis</strong><small>CALCULATION BOOK · R6.7</small></span></a><nav class="navigation" aria-label="Primary navigation"><a href="index.html">Home</a><a href="report.html#annex-r6p7-worked-calculations">Report</a><a href="project-lab.html">Project</a></nav></div></header>
<main class="worked-layout"><aside class="worked-toc"><strong>Chapters</strong><nav aria-label="Worked calculation chapters">"""+nav+"""</nav><p>Every source, assumption, formula, unit and result remains visible.</p></aside><article class="worked-content">
<div class="worked-hero"><small>R6.7 · SOURCE-LED · HAND REPRODUCIBLE</small><h1>From input to equation to answer.</h1><p>Follow the complete arithmetic, not just the last number. Reported historic results, conditional reconstructions, verified synthetic teaching fixtures and present-day model inputs are kept separate.</p><div class="worked-tags"><span>Historical report: reproduced where possible</span><span>ETABS21 ULS/SLS: governing inputs</span><span>No new source-model analysis</span></div></div>
<div class="worked-warning"><strong>Engineering boundary.</strong> User-selected ETABS21 models are the governing inputs; the old PDF numbers below are historical report outputs. Some steps use conditional assumptions. The 2D/3D viewer is an older public provisional grid, not imported ETABS21 geometry. F3 remains NOT SAFE IN ONE WAY SHEAR and no construction approval is provided.</div>
<section class="worked-section" id="procedure"><h2>How to follow the calculation</h2>
<div class="procedure"><div><b>01</b><strong>Find the source</strong><p>Read the printed report section, E2K configuration or explicit test fixture.</p></div><div><b>02</b><strong>Declare assumptions</strong><p>Write the units, story order and conditional input factors before computing.</p></div><div><b>03</b><strong>Substitute numbers</strong><p>Keep each conversion and multiplication visible.</p></div><div><b>04</b><strong>Check equilibrium</strong><p>Compare to the source within stated precision and preserve conflicting claims.</p></div></div></section>
<section class="worked-section" id="worked-steps"><h2>Worked source calculations</h2><p class="section-lead">Seven fully numbered procedures: formulas → substituted values → intermediate quantities → checks and limitations. Open the source crosswalk after each chapter.</p><div class="calc-stack">"""+cards+"""</div></section>
<section class="worked-section" id="floor-table"><h2>Floor-by-floor hand distribution</h2><p class="section-lead">Conditional example applying printed ULS coefficient 0.131, inferred kilogram story masses, height levels 3.048 / 6.096 / 9.144 m and exponent k=1. These are NOT original ETABS floor shears.</p>
<div class="overflow"><table><thead><tr><th>Story</th><th>Printed mass (assumed kg)</th><th>Converted weight (kN)</th><th>h (m)</th><th>Wh (kN·m)</th><th>Conditional Fi (kN)</th></tr></thead><tbody>"""+floorrows+"""</tbody></table></div>
<p>Check: Σ Fi = """+fmt(calc["historical_uls_base_shear_hand_kN"],4)+""" kN (within displayed rounding). This hand distribution can be recalculated from the same reported input rows and coefficients.</p></section>
<section class="worked-section" id="modal-table"><h2>Modal participation — every source row</h2><p class="section-lead">The mode rows were reported by ETABS, not calculated here from eigenvectors. Increments are derived by subtracting successive cumulative sums. Both horizontal cumulative thresholds are crossed at mode 5, despite the report's six-mode prose.</p>
<div class="overflow"><table><thead><tr><th>Mode</th><th>T (s)</th><th>ΣUX</th><th>ΣUY</th><th>ΔUX</th><th>ΔUY</th></tr></thead><tbody>"""+modes+"""</tbody></table></div>
<details><summary>What must a solver do to obtain these periods?</summary><p>Assemble element stiffness and mass, impose supports, solve the eigenproblem Kϕ = ω² Mϕ, then T=2π/ω. Participation requires eigenvectors and directional influence vectors, not only the printed cumulative table. Without those, the displayed modal periods are source-reported, not independently reproduced eigenvalues.</p></details></section>
<section class="worked-section" id="fe-method"><h2>What the OpenSees or ETABS engine actually calculates</h2>
<div class="procedure"><div><b>A</b><strong>Element definition</strong><p>Coordinates, material E, beam/column I, A, torsion, releases and support constraints.</p></div><div><b>B</b><strong>Assemble</strong><p>Transform local k to global; K = Σ(Tᵀ k T); assemble applied loads F and consistent fixed-end member loads.</p></div><div><b>C</b><strong>Solve</strong><p>With restraints imposed, solve Kff × uf = Ff. Check residual reactions R = K u − F and equilibrium.</p></div><div><b>D</b><strong>Recover members</strong><p>End actions from local displacements and fixed-end terms, then report V(x), M(x), envelopes and RC checks. Never infer complete member end forces from one printed design sample.</p></div></div>
<div class="worked-warning">The existing project has verified bounded OpenSees signed-end-force examples; their numeric solutions require the full published input matrices and executed solver. R6.7 does not reverse-engineer the historical report's selected member moments from their final values.</div>
<p><a href="g15-3d.html#g15-solved">Inspect existing signed OpenSees results</a> · <a href="reports/r6p6-report-results-review.html">Inspect old report member excerpts</a></p></section>
<section class="worked-section" id="linked-member"><h2>Linked 2D plan + 3D member inspection</h2><p class="section-lead">This is the 23-point / 32-edge <em>provisional public grid</em>, not the accepted ETABS21 geometry. Select a floor and click the same member in either view; the opposite view and quantities update together.</p>
<div class="worked-controls"><label>Level <select id="worked-level"><option value="1">L1 · 3.048 m</option><option value="2">L2 · 6.096 m</option><option value="3">L3 · 9.144 m</option></select></label><label>Member <select id="worked-member"></select></label><button id="worked-prev" type="button">Previous</button><button id="worked-next" type="button">Next</button></div>
<div class="linked-views"><div><h3>2D plan</h3><svg id="worked-plan" viewBox="0 0 600 370" role="img" aria-label="Selectable provisional grid beams and columns"></svg></div><div><h3>3D source-derived frame</h3><svg id="worked-perspective" viewBox="0 0 600 370" role="img" aria-label="Selectable provisional member highlighted across storeys"></svg></div></div>
<p id="worked-member-detail" class="worked-member-detail" aria-live="polite">Loading the provisional source-derived grid…</p>
<h3>Concrete quantity and illustrative reinforcement take-off</h3><p class="section-lead">Gross concrete volume uses selected provisional dimensions. Reinforcing defaults are teaching inputs only, NOT source schedules; edit them to explore a transparent calculation, and do not use the output as a construction BOQ.</p>
<div class="worked-controls" id="worked-steel-form">
<label>Longitudinal bars, count <input id="worked-nbars" type="number" min="1" max="40" value="4"></label>
<label>Longitudinal diameter (mm) <input id="worked-longdia" type="number" min="6" max="40" value="16"></label>
<label>Stirrup / tie diameter (mm) <input id="worked-tiedia" type="number" min="6" max="16" value="8"></label>
<label>Stirrup spacing (mm) <input id="worked-spacing" type="number" min="50" max="500" value="150"></label>
<label>Clear cover (mm) <input id="worked-cover" type="number" min="10" max="100" value="40"></label>
<label>Extra anchorage per end (mm) <input id="worked-anchorage" type="number" min="0" max="1500" value="0"></label>
</div><div id="worked-quantity" class="quantity-output" role="status" aria-live="polite">Waiting for geometry…</div>
<details open><summary>Actual bar-counting procedure and exclusions</summary><ol><li>Section area (m²) × centerline length (m) → gross concrete volume (m³); intersections and openings are not deducted.</li><li>Longitudinal steel: n × [πd²/4] × (L + 2a), converted mm³ → kg using 7,850 kg/m³.</li><li>Ties/stirrups: number = ceil[(L − 2 cover)/spacing] + 1, with approximate cut length = 2[(b−2cover)+(h−2cover)] + 20d; multiply by circular bar area and density.</li><li>Hooks, bends, anchorage, laps, seismic confinement, starter bars, concrete cover, wastage and node intersections require actual drawings and detailing review. This teaching estimator is <strong>not</strong> a validated cutting list.</li></ol></details></section>
<section class="worked-section" id="next-stage"><h2>What is derived, what still needs actual design output?</h2>
<div class="boundary-grid"><p><strong>Derived in this page</strong> — source mass arithmetic, report coefficients, reported base shear, conditional floor-force distribution, mode-threshold crosscheck, F3 factored pressure and As/m, source-fixture load path, provisional geometry and illustrative bar take-off.</p><p><strong>Reported, not reconstructed</strong> — selected member N/V/M/T, modal eigenvectors and periods, ETABS21 solver mass/reactions, verified diaphragm and reinforcement arrangements, true floor BOQs and structural safety.</p></div></section>
<footer class="worked-footer"><p>Audit-safe source files remain in Drive and governed GitHub. <a href="reports/r6p7-worked-calculations.json">Machine-checkable working steps</a> · <a href="reports/r6p7-worked-calculations-manifest.json">Provenance manifest</a> · <a href="report.html#annex-r6p7-worked-calculations">Main report Annex R</a></p><p>F3 NOT SAFE IN ONE WAY SHEAR · engineering approval: no.</p></footer>
</article></main><script src="worked-calculations.js" defer></script></body></html>"""

def build(output=ROOT/"site"):
    c=compute()
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    page=output/"worked-calculations.html"
    page.write_text(html_page(c),encoding="utf8")
    reports=output/"reports";reports.mkdir(exist_ok=True)
    data=reports/"r6p7-worked-calculations.json"
    data.write_text(json.dumps(c,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf8")
    receipt={"schema":"jp.structural.r6p7.manifest.v0.1",
             "source_registers":{
                 "historical_report_sha256":json.loads(REPORT.read_text())["source"]["report_sha256"],
                 "governing_ETABS21_register_sha256":sha256(MODEL.read_bytes()).hexdigest(),
                 "R5_fixture_sha256":sha256(R5.read_bytes()).hexdigest(),
                 "provisional_public_grid_sha256":sha256(GRID.read_bytes()).hexdigest()
             },
             "generated_sha256":{p.name:sha256(p.read_bytes()).hexdigest() for p in (page,data)},
             "source_report_engineering_approved":False,
             "new_ETABS21_run":False,
             "private_model_raw_bytes_published":False}
    manifest=reports/"r6p7-worked-calculations-manifest.json"
    manifest.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf8")
    return c

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output-site",type=Path,default=ROOT/"site")
    args=p.parse_args()
    a=build(args.output_site)
    print("R6P7_HAND_CALCULATION_BOOK_REPORT_ARITHMETIC_VERIFIED_MASS_AND_F3_APPROVAL_HOLD",len(a["steps"]))
