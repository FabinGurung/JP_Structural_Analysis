#!/usr/bin/env python3
"""Reusable original-TOC SAR calculation orchestrator.

Independent synthetic case; invokes existing tested bounded RC/ESM kernels.
Produces numerical records and a seven-chapter submission-PREPARATION package,
not a stamped SAR, design, original-source ETABS reproduction or site approval.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import math
from pathlib import Path

from jp_structural.solvers.native.nbc105_2025_esm import equivalent_static_floor_forces
from jp_structural.solvers.native.rc_beam_strength import rectangular_singly_reinforced_flexure
from jp_structural.solvers.native.rc_report_kernels import (
    is456_biaxial_column, is456_centered_isolated_footing, nbc_joint_shear,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "registry/report-template-contract.v0.2.json"
COVERAGE = ROOT / "registry/report-calculation-coverage.v0.1.json"
DEFAULT_CASE = ROOT / "examples/sanitized/template_engine_independent.v0.2.json"
SCHEMA = "jp.structural.template.calculation_package.v0.2"
INPUT_SCHEMA = "jp.structural.template.input.v0.2"

class TemplateInputError(ValueError):
    """Invalid provenance/units/case contract; calculation must fail closed."""

def positive(x, key, *, allow_zero=False):
    if isinstance(x, bool) or not isinstance(x, (float, int)) or not math.isfinite(x):
        raise TemplateInputError(key + ": numeric finite value required")
    if x < 0 if allow_zero else x <= 0:
        raise TemplateInputError(key + ": nonnegative" if allow_zero else key + ": positive value required")
    return float(x)

def validate(case: dict, contract: dict) -> None:
    if not isinstance(case,dict) or case.get("schema") != INPUT_SCHEMA:
        raise TemplateInputError("Unknown canonical template input")
    if case.get("classification") not in ("SYNTHETIC_REFERENCE_NOT_A_BUILDING","SOURCE_DERIVED_UNVERIFIED"):
        raise TemplateInputError("Case must be explicitly synthetic or unverified source")
    if not isinstance(case.get("case_id"),str) or len(case["case_id"])<8:
        raise TemplateInputError("Explicit stable case ID required")
    if not isinstance(case.get("source_document"),str) or len(case["source_document"])<10:
        raise TemplateInputError("Case source documentation required")
    flags=case.get("original_unsafe_flags")
    if not isinstance(flags,list) or any(not isinstance(s,str) or not s for s in flags):
        raise TemplateInputError("Explicit original source unsafe flag list required")
    if "NOT SAFE IN ONE WAY SHEAR" in flags and case["classification"]=="SYNTHETIC_REFERENCE_NOT_A_BUILDING":
        raise TemplateInputError("Original unsafe source flags cannot belong to synthetic case")
    keys=("seismic","beam","column","joint","slab","stair","footing")
    provenance=case.get("provenance")
    if not isinstance(provenance,dict) or set(provenance)!=set(keys) or any(
        not isinstance(provenance[k],str) or len(provenance[k])<12 for k in keys):
        raise TemplateInputError("Per-domain source/assumption provenance required")
    f=case.get("footing")
    if not isinstance(f,dict) or f.get("assumed_concentric_placement") is not True or f.get("loads_include_footing_and_backfill") is not True:
        raise TemplateInputError("Footing loads must include weight/backfill with concentric assumption")
    for k in ("plan_mm","overall_depth_mm","bar_spacing_mm"):
        if not isinstance(f.get(k),list) or not (1<=len(f[k])<=8) or len(set(f[k]))!=len(f[k]):
            raise TemplateInputError("Footing candidate list must be unique bounded and nonempty: "+k)
        for x in f[k]:positive(x,k)
    if len(f["plan_mm"])*len(f["overall_depth_mm"])*len(f["bar_spacing_mm"])>150:
        raise TemplateInputError("Maximum 150 explicitly bounded candidate combinations")
    if f.get("cover_mm") is None or f.get("bar_diameter_mm") is None:
        raise TemplateInputError("Explicit footing cover/bar diameter required")
    for B in f["plan_mm"]:
        for D in f["overall_depth_mm"]:
            positive(D-f["cover_mm"]-f["bar_diameter_mm"]/2,"effective footing depth")
            if B<=f["column_b_mm"] or B<=f["column_l_mm"]:
                raise TemplateInputError("Footing dimensions must exceed both column faces")
    s=case.get("seismic")
    if not isinstance(s,dict) or not isinstance(s.get("stories"),list) or len(s["stories"])<1:
        raise TemplateInputError("Explicit story seismic weights required")
    if len(s["stories"])>100:raise TemplateInputError("Unbounded story count")
    elevations=[positive(x.get("elevation_m"),"elevation_m") for x in s["stories"]]
    if any(b<=a for a,b in zip(elevations,elevations[1:])):
        raise TemplateInputError("Story elevations must strictly increase")
    if len(set(x.get("id") for x in s["stories"]))!=len(s["stories"]):
        raise TemplateInputError("Story IDs must be unique")
    for story in s["stories"]:positive(story.get("weight_kN"),"story seismic weight")
    positive(s.get("design_coefficient"),"design_coefficient")
    positive(s.get("period_seconds"),"period_seconds")
    if case.get("material",{}).get("fck_MPa") not in (20,25,30,35,40) or case["material"].get("fy_MPa") not in (415,500):
        raise TemplateInputError("Only tested M20..M40/Fe415-Fe500 material values")
    assert len(contract["chapters"])==7
    if set(x["id"] for x in contract["chapters"])!={f"{i:02d}" for i in range(1,8)}:
        raise TemplateInputError("Chapter index mismatch")

def strip(case, key, fck, fy):
    x=case[key]
    if x.get("span_model") not in ("SIMPLY_SUPPORTED_ONE_WAY_STRIP","SIMPLY_SUPPORTED_EQUIVALENT_HORIZONTAL_PROJECTION"):
        raise TemplateInputError(key + ": simple strip model must be specified")
    L=positive(x["span_m"] if key=="slab" else x["horizontal_span_m"],key+".span")
    q=positive(x["dead_kPa"],key+".dead")+positive(x["live_kPa"],key+".live")
    qu=positive(x["load_factor"],key+".factor")*q
    Mu=qu*L*L/8 # 1-m strip: kPa = kN/m, kN m per metre
    bar=positive(x["bar_diameter_mm"],key+".bar")
    spacing=positive(x["bar_spacing_mm"],key+".spacing")
    As=math.pi*bar**2/4*1000/spacing
    flex=rectangular_singly_reinforced_flexure(
        width_mm=1000,effective_depth_mm=x["effective_depth_mm"],
        overall_depth_mm=x["overall_depth_mm"],fck_MPa=fck,fy_MPa=fy,
        tension_steel_area_mm2=As,factored_moment_kNm=Mu)
    return {
       "model":x["span_model"],"q_factored_kPa":qu,"one_m_strip_Mu_kNm_per_m":Mu,
       "provided_As_mm2_per_m":As,"flexure":flex,
       "numerical_scope":"SIMPLY_SUPPORTED_ONEWAY_FLEXURE_ONLY",
       "actual_supports_and_load_path_verified":False,
       "deflection_shear_development_and_detailing_checked":False,
       "engineering_approval":False}

def build(case:dict|None=None):
    if case is None:case=json.loads(DEFAULT_CASE.read_text(encoding="utf-8"))
    contract=json.loads(CONTRACT.read_text(encoding="utf-8"))
    coverage=json.loads(COVERAGE.read_text(encoding="utf-8"))
    validate(case,contract)
    req={x["id"]:x for x in coverage["requirements"]}
    assert len(req)==18 and set(req)=={f"M{i:02d}" for i in range(1,17)}|{"S17","S18"}
    assert {r for c in contract["chapters"] for r in c["requirement_ids"]}==set(req)
    fck,fy=case["material"]["fck_MPa"],case["material"]["fy_MPa"]
    seismic=case["seismic"]
    esm=equivalent_static_floor_forces(
       floor_weights_kN=[x["weight_kN"] for x in seismic["stories"]],
       floor_heights_m=[x["elevation_m"] for x in seismic["stories"]],
       period_seconds=seismic["period_seconds"],
       design_coefficient=seismic["design_coefficient"])
    beam=case["beam"]
    beam_result=rectangular_singly_reinforced_flexure(
       width_mm=beam["width_mm"],overall_depth_mm=beam["overall_depth_mm"],
       effective_depth_mm=beam["effective_depth_mm"],fck_MPa=fck,fy_MPa=fy,
       tension_steel_area_mm2=beam["tension_steel_area_mm2"],
       factored_moment_kNm=beam["factored_moment_kNm"])
    col=case["column"]
    column_result=is456_biaxial_column(
       width_mm=col["width_mm"],depth_mm=col["depth_mm"],fck_MPa=fck,fy_MPa=fy,
       Ast_mm2=col["Ast_mm2"],Pu_kN=col["Pu_kN"],
       Mux_kNm=col["Mux_kNm"],Muy_kNm=col["Muy_kNm"],
       Mux1_kNm=col["Mux1_kNm"],Muy1_kNm=col["Muy1_kNm"],
       clear_height_mm=col["clear_height_mm"],
       effective_length_x_mm=col["effective_length_x_mm"],
       effective_length_y_mm=col["effective_length_y_mm"],
       uniaxial_capacity_source_id=case["provenance"]["column"])
    joint=case["joint"]
    joint_result=nbc_joint_shear(
       confinement_faces=joint["confinement_faces"],framing=joint["framing"],
       fck_MPa=fck,fy_MPa=fy,joint_breadth_mm=joint["joint_breadth_mm"],
       joint_width_mm=joint["joint_width_mm"],
       Ast_top_mm2=joint["Ast_top_mm2"],Ast_bottom_mm2=joint["Ast_bottom_mm2"],
       column_shear_kN=joint["column_shear_kN"],
       joint_geometry_source_id=case["provenance"]["joint"])
    slab_result=strip(case,"slab",fck,fy)
    stair_result=strip(case,"stair",fck,fy)
    foot=case["footing"]
    candidates=[]
    for B in foot["plan_mm"]:
       for D in foot["overall_depth_mm"]:
          d=D-foot["cover_mm"]-foot["bar_diameter_mm"]/2
          for spacing in foot["bar_spacing_mm"]:
             As=math.pi*foot["bar_diameter_mm"]**2/4*1000/spacing
             r=is456_centered_isolated_footing(
                B_mm=B,L_mm=B,D_mm=D,d_x_mm=d,d_y_mm=d,
                column_b_mm=foot["column_b_mm"],column_l_mm=foot["column_l_mm"],
                fck_MPa=fck,fy_MPa=fy,Ast_x_mm2_per_m=As,Ast_y_mm2_per_m=As,
                P_service_kN=foot["P_service_kN"],P_ultimate_kN=foot["P_ultimate_kN"],
                allowable_soil_kPa=foot["allowable_soil_kPa"],
                soil_assumption_source_id=foot["soil_assumption_source_id"])
             numeric=all(r["checks"].values())
             candidates.append({
                 "id":f"F_B{B:g}_D{D:g}_S{spacing:g}",
                 "B_mm":B,"L_mm":B,"D_mm":D,"d_mm":d,"bar_mm":foot["bar_diameter_mm"],
                 "bar_spacing_mm":spacing,"Ast_mm2_per_m":As,
                 "indicative_concrete_volume_m3":(B/1000)**2*D/1000,
                 "bounded_numeric_checks_all_true":numeric,
                 "precheck_status":r["status"],
                 "checks":r["checks"],"calculation":r,
                 "verified_site_bearing":False,
                 "verified_footing_reactions":False,"full_foundation_design":False,
                 "design_approved":False})
    candidates.sort(key=lambda x:(not x["bounded_numeric_checks_all_true"],
                                  x["indicative_concrete_volume_m3"],x["Ast_mm2_per_m"],x["id"]))
    assert len({x["id"] for x in candidates})==len(candidates)
    assert all(not x["design_approved"] for x in candidates)
    modes={
      "M03":{"numerical":"ESM floor forces only","status":"NUMERICALLY_SOLVED_LIMITED"},
      "M08":{"numerical":"Single positive uniaxial beam flexure","status":"BOUNDED_PRECHECK"},
      "M09":{"numerical":"Biaxial formula using user-provided uniaxial capacities","status":"BOUNDED_ASSUMED_CAPACITY"},
      "M10":{"numerical":"Joint shear with source-supplied reinforcement","status":"BOUNDED_PRECHECK"},
      "M11":{"numerical":"One-way slab simply supported strip flexure","status":"BOUNDED_PRECHECK"},
      "M12":{"numerical":"Centered isolated soil footing options with six bounded checks","status":"BOUNDED_PRECHECK"},
      "M14":{"numerical":"Stair flight simply supported strip flexure","status":"BOUNDED_PRECHECK"},
    }
    chapters=[]
    for c in contract["chapters"]:
       chapters.append({"chapter":c["id"],"title":c["title"],"headings":c["headings"],
           "requirement_ids":c["requirement_ids"],
           "requirements":[{"id":i,"title":req[i]["title"],
              "registry_status":req[i]["status"],
              "this_runner":modes.get(i,{"numerical":"Not implemented in this run",
                           "status":"NOT_EVALUATED_THIS_RUN"})} for i in c["requirement_ids"]]})
    conditions=[
      "No authentic building site or soil input; allowable bearing is hypothetical",
      "No member-by-member 3D geometry or applied FEM loads are imported in this runner",
      "No modal/eccentricity/P-delta, wind or complete signed ULS/SLS case combinations",
      "Beam flexure is singly reinforced rectangular positive demand only",
      "Column uniaxial capacities are caller-provided, not independently solved in this case",
      "Joint confinement, bar development and ductile full-design checks remain open",
      "Slab/stair flexure assumes simple supports; real support conditions and stair dead loads unverified",
      "Footing candidate check excludes settlement, eccentric bearing, punching edge interactions, sliding, uplift, anchorage, and detail drawings",
      "Original-source unsafe verdicts, if any, dominate this conditional numerical comparison",
      "Submission checklists are preparation tasks, not an official authority approval",
    ]
    result={
       "schema":SCHEMA,"template_contract":"registry/report-template-contract.v0.2.json",
       "case_id":case["case_id"],"source_class":case["classification"],
       "input_source_document":case["source_document"],"provenance":case["provenance"],
       "input_sha256":hashlib.sha256(json.dumps(case,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
       "material_input":case["material"],"case_input":case,
       "codes":contract["codes"],"chapters":chapters,
       "numerical_results":{"M03_ESM":esm,"M08_beam_flexure":beam_result,
           "M09_biaxial_column":column_result,"M10_joint_shear":joint_result,
           "M11_slab_strip":slab_result,"M14_stair_strip":stair_result},
       "M12_footing_candidates":candidates,
       "M12_numeric_candidate_count":sum(x["bounded_numeric_checks_all_true"] for x in candidates),
       "M12_candidate_count":len(candidates),
       "M12_shortlist_conditional_only":[x["id"] for x in candidates if x["bounded_numeric_checks_all_true"]][:5],
       "modules_calculated":sorted(modes),
       "all_18_modules_complete":False,
       "original_unsafe_flags_preserved":case["original_unsafe_flags"],
       "standards_research_not_equivalent_to_site_source":True,
       "source_evidence_verified":False,
       "independent_engineering_design_validation_complete":False,
       "submission_items":[{**x,"evidence_provided":False,"accepted":False} for x in contract["submission_documents"]],
       "submitted_to_municipality":False,"permit_eligible":False,"engineer_approved":False,
       "public_issue_for_construction":False,"engineering_approval":False,
       "limitations":conditions,
       "overall_status":"REFERENCE_NUMERICAL_PACKAGE_READY_FOR_VERIFICATION_NOT_APPROVED"}
    return result

def fmt(x):
    return f"{x:,.4f}" if isinstance(x,(int,float)) and not isinstance(x,bool) else str(x)

def markdown(r):
    ch=r["chapters"];nr=r["numerical_results"]
    lines=[
      "# Reusable Structural Analysis / SAR Template — Numerical Draft",
      "",
      f"**Case:** {r['case_id']} · **Authority:** {r['source_class']}",
      "",
      "**Not an approved structural design, signed report, construction detail or permit submission.**",
      "",
      f"Module math in this run: {', '.join(r['modules_calculated'])}; "
      f"{r['M12_candidate_count']} bounded isolated-footing scenarios, "
      f"{r['M12_numeric_candidate_count']} with all numerical checks true (NOT approved).",
      "",
      "## Table of contents",
    ]
    lines += [f"- [{c['chapter']}. {c['title']}](#chapter-{c['chapter']})" for c in ch]
    lines+=["","## Numerical audit","",
      f"- ESM seismic weight (assumed): {fmt(nr['M03_ESM']['seismic_weight_kN'])} kN",
      f"- ESM base shear (assumed coefficient): {fmt(nr['M03_ESM']['base_shear_kN'])} kN",
      f"- Beam flexure: {nr['M08_beam_flexure']['status']}",
      f"- Column biaxial: {nr['M09_biaxial_column']['status']}",
      f"- Joint shear: {nr['M10_joint_shear']['status']}",
      f"- Slab strip flexure: {nr['M11_slab_strip']['flexure']['status']}",
      f"- Stair strip flexure: {nr['M14_stair_strip']['flexure']['status']}",
      "",]
    for c in ch:
      lines += [f'<a id="chapter-{c["chapter"]}"></a>',f"## Chapter {c['chapter']} — {c['title']}",""]
      for h in c["headings"]:
         lines.append(f"### {h['number']} {h['name']}")
      lines+=["","**Coverage against original-report requirements**","","| Module | Original registry status | Template runner |","|---|---|---|"]
      for x in c["requirements"]:
         lines.append("| "+x["id"]+" | "+x["registry_status"]+" | "+x["this_runner"]["status"]+" |")
      lines.append("")
      if c["chapter"]=="06":
         lines+=["### Isolated footing candidate comparison (assumption-only)","",
          "| Candidate | B / D / spacing mm | q service kPa | all bounded checks | Physical approval |",
          "|---|---|---|---|---|"]
         for x in r["M12_footing_candidates"]:
           lines.append(f"| {x['id']} | {fmt(x['B_mm'])} / {fmt(x['D_mm'])} / {fmt(x['bar_spacing_mm'])} | "+
             f"{fmt(x['calculation']['service_pressure_kPa'])} | {x['bounded_numeric_checks_all_true']} | NO |")
         lines.append("")
    lines+=["## Submission preparation checklist (all NOT ACCEPTED)","","| Item | Evidence | Accepted |","|---|---|---|"]
    for x in r["submission_items"]:lines.append("| "+x["id"]+" | "+x["title"]+" | NO |")
    lines+=["","## Authorities and code clause indexing",""]
    for x in r["codes"]:lines.append(f"- {x['id']}: {x['url']} (clauses: {', '.join(x['clauses'])})")
    lines+=["","## Outstanding conditions",""]
    lines+=["- "+q for q in r["limitations"]]
    lines+=["","**Source verdict flags retained:** "+(", ".join(r["original_unsafe_flags_preserved"]) or "none for synthetic fixture"),
      "**Approval:** NO · **Permit eligible:** NO · **Engine completeness:** PARTIAL",""]
    return "\n".join(lines)

def report_html(r):
    esc=lambda x:html.escape(str(x),quote=True)
    nr=r["numerical_results"]
    nav="".join(f'<a href="#chapter-{c["chapter"]}">{c["chapter"]} {esc(c["title"])}</a>' for c in r["chapters"])
    parts=[]
    for c in r["chapters"]:
      head="".join(f'<h3>{esc(s["number"])} {esc(s["name"])}</h3>' for s in c["headings"])
      rows="".join(f'<tr><th>{esc(x["id"])}</th><td>{esc(x["title"])}</td><td>{esc(x["registry_status"])}</td><td>{esc(x["this_runner"]["status"])}</td></tr>' for x in c["requirements"])
      extra=""
      if c["chapter"]=="05":
        rows2="".join(f'<tr><th>{esc(i+1)}</th><td>{esc(fmt(w))}</td><td>{esc(fmt(h))}</td><td>{esc(fmt(f))}</td></tr>' for i,(w,h,f) in enumerate(zip(nr["M03_ESM"]["floor_seismic_weights_kN"],nr["M03_ESM"]["floor_heights_m"],nr["M03_ESM"]["floor_forces_kN"])))
        extra='<h3>Assumed ESM floor-force result, not seismic approval</h3><table><tr><th>Story</th><th>Wi kN</th><th>Elevation m</th><th>Fi kN</th></tr>'+rows2+'</table>'
      if c["chapter"]=="06":
        footrows="".join("<tr>"+ "".join("<td>"+esc(v)+"</td>" for v in (
         x["id"],fmt(x["B_mm"]),fmt(x["D_mm"]),fmt(x["d_mm"]),
         fmt(x["bar_spacing_mm"]),fmt(x["calculation"]["service_pressure_kPa"]),
         fmt(x["calculation"]["factored_pressure_kPa"]),
         "YES—NUMERIC ONLY" if x["bounded_numeric_checks_all_true"] else "NO",
         "NOT APPROVED"))+"</tr>" for x in r["M12_footing_candidates"])
        extra='<h3>Footing options — bounded arithmetic only</h3><p>All candidate dimensions, soil and loads are hypothetical. No actual F3 solution is adopted. If any original F3 unsafe verdict exists, it remains governing.</p><div class="scroll"><table><tr><th>ID</th><th>Plan B mm</th><th>D mm</th><th>d mm</th><th>Bar spacing mm</th><th>Service q kPa</th><th>Ultimate q kPa</th><th>Six numeric checks</th><th>Building approval</th></tr>'+footrows+'</table></div>'
      parts.append(f'<section id="chapter-{c["chapter"]}"><h2>Chapter {c["chapter"]}: {esc(c["title"])}</h2>{head}<h3>Machine coverage and remaining verification</h3><div class="scroll"><table><tr><th>Module</th><th>Capability</th><th>Repository status</th><th>This run</th></tr>{rows}</table></div>{extra}</section>')
    codes="".join(f'<li><a href="{esc(x["url"])}">{esc(x["id"])}</a> — {esc(x["role"])}</li>' for x in r["codes"])
    check="".join("<tr><th>"+esc(x["id"])+"</th><td>"+esc(x["title"])+"</td><td>NOT ACCEPTED</td></tr>" for x in r["submission_items"])
    cond="".join("<li>"+esc(x)+"</li>" for x in r["limitations"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SAR Template Engine — Conditional Reference Package</title>
<style>
:root{{color-scheme:light}}*{{box-sizing:border-box}}body{{margin:0 auto;max-width:1100px;padding:24px;background:#f8fafc;color:#24364a;font:14px/1.55 system-ui,sans-serif}}header,section{{background:white;border:1px solid #d8e1eb;border-radius:12px;padding:21px;margin:18px 0}}header{{border-top:5px solid #395c83}}h1{{font-size:28px}}h2{{font-size:21px;margin-top:0}}h3{{font-size:15px}}nav{{display:flex;flex-wrap:wrap;gap:9px}}nav a{{border:1px solid #a9bccd;padding:7px;border-radius:8px;text-decoration:none;color:#31547d}}.warning{{border-left:5px solid #aa594b;background:#fff1ed;padding:13px}}.scroll{{overflow:auto}}table{{border-collapse:collapse;min-width:600px;width:100%;font-size:12px}}td,th{{border:1px solid #d3dae5;padding:8px;text-align:left;vertical-align:top}}th{{background:#eef3f7}}small{{color:#65758a}}@media print{{body{{padding:0;background:#fff}}nav{{display:none}}section{{break-inside:auto;border:0;padding:8px 0}}tr{{break-inside:avoid}}@page{{margin:14mm}}}}
</style></head><body>
<header><small>JP STRUCTURAL · REUSABLE CALCULATION PACKAGE · MACHINE-GENERATED AND NOT CERTIFIED</small>
<h1>Structural Analysis and Design Report Template</h1>
<p><strong>Reference case:</strong> {esc(r["case_id"])} · <strong>Class:</strong> {esc(r["source_class"])}</p>
<p class="warning"><strong>NOT ENGINEERING APPROVED / NOT VALID FOR PERMIT OR CONSTRUCTION.</strong> This report is a partial-engine demonstration with explicit assumed data. It does not establish the safety of the G+1.5 precedent building, and does not override an unsafe F3 source finding.</p>
<nav>{nav}</nav>
<p>Assumed seismic W = <strong>{esc(fmt(nr["M03_ESM"]["seismic_weight_kN"]))} kN</strong>, ESM base shear = <strong>{esc(fmt(nr["M03_ESM"]["base_shear_kN"]))} kN</strong>. Footing: {r["M12_candidate_count"]} scenarios, {r["M12_numeric_candidate_count"]} conditionally pass the six LIMITED numeric checks; no field design approval.</p></header>
{''.join(parts)}
<section><h2>Annex — code authorities, provenance and submission preparation</h2><h3>Research/code sources</h3><ul>{codes}</ul>
<h3>Required external evidence and submission documentation</h3><table><tr><th>ID</th><th>Required record</th><th>Status</th></tr>{check}</table>
<h3>Excluded or unresolved technical scope</h3><ul>{cond}</ul>
<p class="warning">Submission eligibility: NO · Original unsafe flags: {esc(', '.join(r["original_unsafe_flags_preserved"]) or 'none for synthetic fixture')} · Neither a government certificate nor engineer's signature has been generated.</p></section>
</body></html>"""

def csv_text(r):
    s=io.StringIO()
    w=csv.writer(s,lineterminator="\n")
    w.writerow(["case_id","scenario_id","B_mm","D_mm","d_mm","bar_spacing_mm","service_q_kPa","ultimate_q_kPa","bounded_checks_all_true","engineering_approval"])
    for row in r["M12_footing_candidates"]:
       d=row["calculation"]
       w.writerow([r["case_id"],row["id"],row["B_mm"],row["D_mm"],row["d_mm"],
         row["bar_spacing_mm"],f'{d["service_pressure_kPa"]:.8f}',f'{d["factored_pressure_kPa"]:.8f}',
         row["bounded_numeric_checks_all_true"],False])
    return s.getvalue()

def emit(case_path:Path,output_dir:Path,prefix="template-engine-reference"):
    case=json.loads(case_path.read_text(encoding="utf-8"))
    r=build(case)
    output_dir.mkdir(parents=True,exist_ok=True)
    data={prefix+".json":json.dumps(r,indent=2,allow_nan=False,sort_keys=True)+"\n",
          prefix+".md":markdown(r),prefix+".html":report_html(r),
          prefix+"-footing-candidates.csv":csv_text(r)}
    for name,content in data.items():(output_dir/name).write_text(content,encoding="utf-8")
    manifest={"schema":"jp.structural.template.output_manifest.v0.2",
      "case_id":r["case_id"],"source_sha256":r["input_sha256"],
      "files":{name:hashlib.sha256(content.encode("utf-8")).hexdigest() for name,content in data.items()},
      "engineering_approval":False,"report_status":r["overall_status"]}
    (output_dir/(prefix+"-manifest.json")).write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return r

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=DEFAULT_CASE)
    p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--prefix",default="template-engine-reference")
    a=p.parse_args()
    if not a.prefix.replace("-","").replace("_","").isalnum() or len(a.prefix)>70:
        raise TemplateInputError("Safe output prefix required")
    r=emit(a.input,a.output_dir,a.prefix)
    print("TEMPLATE_REFERENCE_RUN",r["case_id"],"modules",len(r["modules_calculated"]),
       "footing_cases",r["M12_candidate_count"],"conditional_numeric",r["M12_numeric_candidate_count"],
       "APPROVAL_FALSE")
if __name__=="__main__":
    main()
