#!/usr/bin/env python3
"""R5.4 explicit one-way slab load-to-edge-beam -> signed OpenSees SAR.

The user-provided one-way support scheme is a bounded synthetic premise.
Transfer geometry, load resultants and X/Y plan moments are audited; real
shell slab stiffness, diaphragm coupling and original building acceptance
are NOT asserted. Native horizontal beamUniform member load preserves
elastic member end forces and signed static load combinations.
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
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from jp_structural.solvers.native.one_way_panel_to_beams import transfer_one_way_panels
from jp_structural.solvers.opensees.load_mass_adapter import bind_assembly_to_canonical_model
from jp_structural.solvers.opensees.member_design_bridge import (
    solve_signed_member_cases,evaluate_m08_m09_m10,
)
from jp_structural.solvers.native.beam_span_diagrams import build_signed_span_diagrams
from scripts.build_r5_generic_frame_case import DEFAULT
from scripts.build_structural_template_engine import CONTRACT,COVERAGE

PFX="r5-oneway-panel-transfer"
ROUTES=ROOT/"examples/sanitized/r5_oneway_slab_routes.v0.1.json"
SCHEMA="jp.structural.r5.one_way_slab_beam_SAR.v0.1"

def sha(o):
    return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def build(spec:dict|None=None,plan:dict|None=None):
    if spec is None:spec=json.loads(DEFAULT.read_text(encoding="utf8"))
    if plan is None:plan=json.loads(ROUTES.read_text(encoding="utf8"))
    if (spec.get("schema")!="jp.structural.r5.input.v0.1"
        or spec.get("classification")!="SYNTHETIC_REFERENCE_NOT_A_BUILDING"
        or plan.get("schema")!="jp.structural.r5.one_way_route_plan.v0.1"
        or spec.get("case_id")!=plan.get("reference_case_id")):
        raise ValueError("R5.4 requires source-matched explicit synthetic frame and one-way route plan")
    model=spec["model"]
    routing=transfer_one_way_panels(model=model,loads=spec["source_loads"],
        routes=plan["routes"],gravity_m_s2=spec["gravity_m_s2"])
    bound=bind_assembly_to_canonical_model(model,routing["source_assembly"])
    if bound["provenance"]["load_mass_assembly_sha256"]!=sha(routing["source_assembly"]):
        raise ValueError("assigned seismic mass does not match original audited source")
    raw=[]
    for cid,loads in routing["native_element_loads_by_case"].items():
        raw.append({"case_id":cid,"source_id":"R5P4_SOURCE_AUDITED_ONE_WAY_"+cid,
            "nodal_loads":[],"uniform_beam_loads":loads})
    rawid={x["case_id"] for x in raw}
    six={"Fx_kN","Fy_kN","Fz_kN","Mx_kNm","My_kNm","Mz_kNm"}
    for src in spec["lateral_cases"]:
        if src["case_id"] in rawid:raise ValueError("duplicate raw static load case ID")
        for n in src["nodal_loads"]:
            if set(n)!={"node_id",*six}:raise ValueError("lateral signed source missing component")
        raw.append(src)
        rawid.add(src["case_id"])
    solved=solve_signed_member_cases(model=bound,cases=raw,combinations=spec["combinations"])
    d=spec["design_bindings"]
    checked=evaluate_m08_m09_m10(model=bound,solved=solved,
       beam_bindings=d["beam"],column_bindings=d["column"],joint_bindings=d["joint"])
    diagrams=build_signed_span_diagrams(model=bound,solved=solved,raw_cases=raw,
       combinations=spec["combinations"])
    if checked["source_action_digest"]!=solved["input_bundle_sha256"]:
        raise ValueError("design source not same as actual signed analysis")
    if diagrams["source_signed_result_sha256"]!=solved["results_digest_sha256"]:
        raise ValueError("beam diagrams source result digest mismatch")
    if not diagrams["all_J_cut_boundary_equilibrium_pass"]:
        raise ValueError("J section/member-end force equilibrium failed")
    for row in solved["raw_cases"]:
        if not row["global_equilibrium_pass"]:raise ValueError("global frame equilibrium failed")
    max_res=max(abs(val) for row in solved["raw_cases"]
             for val in row["global_force_moment_equilibrium_residual"].values())
    if max_res>1e-5:raise ValueError("six-component frame equilibrium exceeded tolerance")
    applied=math.fsum(x["downward_resultant_kN"] for r in solved["raw_cases"]
          for x in r["uniform_beam_loads"])
    if not math.isclose(applied,routing["source_total_gravity_kN"],rel_tol=1e-10,abs_tol=1e-8):
        raise ValueError("native OpenSees beam element load total differs from physical source")
    by_case={r["case_id"]:r for r in solved["raw_cases"]}
    for case,records in routing["native_element_loads_by_case"].items():
        a=by_case[case]["uniform_beam_loads"]
        if len(a)!=len(records):
            raise ValueError("OpenSees failed to apply all physical routed beam load sources")
        for source in records:
            matches=[x for x in a if x["source_key"]==source["source_key"]
                     and x["member_id"]==source["member_id"]]
            if len(matches)!=1 or not math.isclose(matches[0]["downward_resultant_kN"],
                      source["downward_kN_per_m"]*matches[0]["span_m"],
                      abs_tol=1e-8,rel_tol=1e-10):
                raise ValueError("source-key to applied element force mismatch")
    chapters=json.loads(CONTRACT.read_text(encoding="utf8"))["chapters"]
    coverage={r["id"]:r for r in json.loads(COVERAGE.read_text(encoding="utf8"))["requirements"]}
    scope={
       "M02":"SOURCE_RECTANGULAR_ONE_WAY_PANEL_TO_TWO_BEAMS_PLUS_AUDITED_MASS",
       "M04":"SIGNED_ELASTIC_3D_FRAME_UNIFORM_ELEMENT_LOADING_AND_GLOBAL_EQUILIBRIUM",
       "M08":"SIGNED_BEAM_CASE_END_AND_SPAN_ACTIONS_PARTIAL_RC_SHEAR_HOLD",
       "M09":"BOUNDED_SYNTHETIC_COLUMN_SECTION_CHECK",
       "M10":"BOUNDED_SYNTHETIC_JOINT_FORCE_CHECK",
       "S17":"SOURCE_ROUTE_FIRST_MOMENT_AND_MEMBER_IJ_END_SHA_VALIDATION",
    }
    chapter_out=[{"id":c["id"],"title":c["title"],"headings":c["headings"],
       "modules":[{"id":i,"title":coverage[i]["title"],
                   "status":scope.get(i,"NOT_CALCULATED_IN_THIS_BOUNDED_RUN")}
                  for i in c["requirement_ids"]]} for c in chapters]
    if len(chapter_out)!=7 or {m["id"] for c in chapter_out for m in c["modules"]}!=set(coverage):
        raise ValueError("source report TOC/coverage not complete")
    return {
       "schema":SCHEMA,"case_id":model["model_id"],
       "source_input_SHA256":sha(spec),"route_plan_SHA256":sha(plan),
       "routing_SHA256":routing["source_route_input_SHA256"],
       "source_mass_SHA256":bound["provenance"]["load_mass_assembly_sha256"],
       "signed_input_SHA256":solved["input_bundle_sha256"],
       "signed_result_SHA256":solved["results_digest_sha256"],
       "source_total_gravity_kN":routing["source_total_gravity_kN"],
       "source_seismic_weight_kN":routing["source_seismic_weight_kN"],
       "source_panel_count":routing["panel_source_count"],
       "source_panel_routes":routing["panel_routes"],
       "source_routed_element_loads":routing["member_element_load_sources"],
       "native_element_gravity_kN":applied,
       "edge_member_load_count":routing["panel_edge_element_load_count"],
       "independent_wall_load_count":routing["source_wall_element_count"],
       "raw_case_count":len(raw),"combination_count":len(spec["combinations"]),
       "frame_member_count":len(model["frame_members"]),
       "signed_end_action_count":(len(raw)+len(spec["combinations"]))*2*len(model["frame_members"]),
       "source_route_conservation":routing["global_gravity_force_conserved"],
       "source_first_moment_conservation":routing["gravity_plan_first_moments_conserved"],
       "source_seismic_mass_unmodified":routing["seismic_mass_assumptions_reused_unchanged"],
       "signed_FE":solved,"bounded_M08_M09_M10":checked,
       "source_signed_beam_diagrams":diagrams,
       "max_global_force_moment_residual":max_res,
       "chapters":chapter_out,
       "one_way_slab_assumption_not_physically_verified":True,
       "original_F3_failure":"NOT SAFE IN ONE WAY SHEAR",
       "original_building_source_verified":False,
       "actual_shell_and_diaphragm_FE":False,
       "full_RC_design_complete":False,
       "engineering_approval":False,"permit_eligible":False,
       "status":"R5P4_ONEWAY_RECTANGULAR_PANEL_TO_NATIVE_BEAM_UDL_SYNTHETIC_QA_NO_APPROVAL",
       "limits":[
         "Only user-selected one-way simply supported horizontal rectangular slab panels on two full opposite edge beams.",
         "No two-way slab action, actual plate/shell stiffness, rigid diaphragm, openings, cantilevers, slab serviceability or rebar.",
         "Source seismic mass participation and node shares are prior user-assumed audit inputs; not derived from the support-force transfer.",
         "The source synthetic load patterns/factors are NOT independent code-approved ULS/SLS load combinations.",
         "Original G+1.5 revised report source and F3 unsafe finding are not recalculated by this synthetic test.",
       ],
    }

def _csv(rows,cols):
    b=io.StringIO();w=csv.writer(b,lineterminator="\n");w.writerow(cols)
    for row in rows:w.writerow([row.get(k) for k in cols])
    return b.getvalue()

def render_html(r):
    e=lambda x:html.escape(str(x),quote=True)
    chapter_links="".join(f'<a href="#ch-{x["id"]}">{x["id"]} {e(x["title"])}</a> ' for x in r["chapters"])
    panels=[]
    for p in r["source_panel_routes"]:
        lines="".join(f'<tr><td>{e(x["member_id"])}</td><td>{x["area_tributary_m2"]:.3f}</td>'
          f'<td>{x["downward_kN_per_m"]:.3f}</td><td>{x["downward_resultant_kN"]:.3f}</td></tr>' for x in p["beam_loads"])
        panels.append(f'<section><h3>{e(p["panel_source_id"])} — {e(p["span_direction"])} one-way span</h3>'
           f'<p>Area {p["source_panel_area_m2"]:.2f} m², source gravity {p["source_total_kN"]:.2f} kN, '
           f'load span {p["support_spacing_m"]:.2f} m. Exact force and X/Y first-moment conservation passed.</p>'
           f'<table><tr><th>Beam</th><th>Tributary area (m²)</th><th>Line load (kN/m)</th><th>Beam load (kN)</th></tr>{lines}</table></section>')
    chapters=[]
    for ch in r["chapters"]:
        rows="".join(f'<tr><td>{e(m["id"])}</td><td>{e(m["title"])}</td><td>{e(m["status"])}</td></tr>'
                     for m in ch["modules"])
        extra="".join(panels) if ch["id"]=="04" else ""
        if ch["id"]=="05":
            extra=f'<p>{r["raw_case_count"]} independently solved OpenSees cases plus {r["combination_count"]} concurrent signed combinations; {r["signed_end_action_count"]} signed I/J end vectors. Global residual maximum: {r["max_global_force_moment_residual"]:.8g} (kN/kNm). All beam-span J-end force/moment equilibrium tests passed.</p>'
        chapters.append(f'<section id="ch-{e(ch["id"])}"><h2>Chapter {e(ch["id"])} — {e(ch["title"])}</h2><div class="sc"><table><tr><th>ID</th><th>Requirement</th><th>Run scope</th></tr>{rows}</table></div>{extra}</section>')
    notes="".join("<li>"+e(x)+"</li>" for x in r["limits"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>R5.4 Explicit one-way slab to beam SAR</title><style>body{{font:14px/1.55 system-ui;background:#f7f9fd;color:#25364c;max-width:1100px;margin:auto;padding:16px}}header,section{{padding:20px;background:white;border:1px solid #d6e0ec;border-radius:11px;margin:14px 0}}h1{{font-size:26px}}h2{{font-size:20px}}a{{color:#31577e}}nav a{{display:inline-block;padding:5px;border:1px solid #a8bdce;border-radius:6px;margin:3px}}.warn{{background:#fff0ec;border-left:5px solid #b8594e;padding:12px}}.sc{{overflow:auto}}table{{border-collapse:collapse;min-width:560px;width:100%}}td,th{{border:1px solid #cdd7e2;padding:7px;text-align:left;font-size:12px}}th{{background:#f1f4f8}}@media print{{body{{background:white}}nav{{display:none}}}}</style></head><body><header>
<small>JP STRUCTURAL · R5.4 · SOURCE-DECLARED ONE-WAY SLAB LOAD TRANSFER · SYNTHETIC MODEL</small>
<h1>Floor panel pressure → supporting beams → signed frame analysis</h1>
<p class="warn"><strong>NOT A CERTIFIED DESIGN, PERMIT OR CONSTRUCTION CALCULATION.</strong> One-way slab support is assumed and restricted to rectangular panels. Original foundation F3 remains NOT SAFE IN ONE WAY SHEAR.</p>
<p>Gravity {r["source_total_gravity_kN"]:.2f} kN = {r["native_element_gravity_kN"]:.2f} kN audited native beam element loads; seismic-eligible weight {r["source_seismic_weight_kN"]:.2f} kN independently preserved.</p>
<p><a href="{PFX}.json">Machine-readable results</a> · <a href="{PFX}-routes.csv">Tributary route CSV</a> · <a href="{PFX}-member-ends.csv">Signed member ends CSV</a> · <a href="{PFX}-manifest.json">SHA-256 manifest</a></p><nav>{chapter_links}</nav></header>
{''.join(chapters)}<section><h2>Annex — limitations, source and approval holds</h2><ul>{notes}</ul><p>Physical building source approved: NO. Professional engineering approval: NO. Original F3 failure: NOT SAFE IN ONE WAY SHEAR.</p></section></body></html>"""

def emit(specfile:Path,routefile:Path,directory:Path):
    a=json.loads(specfile.read_text(encoding="utf8"))
    p=json.loads(routefile.read_text(encoding="utf8"))
    result=build(a,p)
    directory.mkdir(parents=True,exist_ok=True)
    rows=[]
    for panel in result["source_panel_routes"]:
        for load in panel["beam_loads"]:
            rows.append({"panel_source_id":panel["panel_source_id"],
              "member_id":load["member_id"],
              "span_direction":panel["span_direction"],
              "source_panel_area_m2":panel["source_panel_area_m2"],
              "tributary_area_m2":load["area_tributary_m2"],
              "uniform_beam_kN_m":load["downward_kN_per_m"],
              "resultant_kN":load["downward_resultant_kN"]})
    ends=[]
    for kind,sources in (("RAW",result["signed_FE"]["raw_cases"]),("COMBINATION",result["signed_FE"]["combinations"])):
        for s in sources:
            cid=s["case_id"] if kind=="RAW" else s["combination_id"]
            for mid,e in sorted(s["local_end_resisting_actions"].items()):
                for end in ("I","J"):
                    ends.append({"kind":kind,"case_id":cid,"member_id":mid,"end":end,**e[end]})
    files={
      PFX+".json":json.dumps(result,sort_keys=True,allow_nan=False,indent=2)+"\n",
      PFX+".html":render_html(result),
      PFX+"-routes.csv":_csv(rows,["panel_source_id","member_id","span_direction","source_panel_area_m2","tributary_area_m2","uniform_beam_kN_m","resultant_kN"]),
      PFX+"-member-ends.csv":_csv(ends,["kind","case_id","member_id","end","N","Vy","Vz","T","My","Mz"]),
    }
    for filename,data in files.items():(directory/filename).write_text(data,encoding="utf8")
    manifest={"schema":"jp.structural.r5.one_way_panel_manifest.v0.1",
              "source_input_SHA256":result["source_input_SHA256"],
              "route_plan_SHA256":result["route_plan_SHA256"],
              "files":{k:hashlib.sha256(v.encode("utf8")).hexdigest() for k,v in files.items()},
              "engineering_approval":False}
    (directory/(PFX+"-manifest.json")).write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n",encoding="utf8")
    return result

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--input",type=Path,default=DEFAULT)
    a.add_argument("--routes",type=Path,default=ROUTES)
    a.add_argument("--output-dir",type=Path,required=True)
    args=a.parse_args()
    r=emit(args.input,args.routes,args.output_dir)
    print("R5P4_SLAB_TO_BEAM",r["source_panel_count"],"PANELS",r["native_element_gravity_kN"],"KN",r["signed_end_action_count"],"SIGNED_IJ_NO_APPROVAL")
if __name__=="__main__":main()
