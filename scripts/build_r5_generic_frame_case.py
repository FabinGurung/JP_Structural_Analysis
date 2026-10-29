#!/usr/bin/env python3
"""R5 first generic 3D geometry -> audited load/mass -> signed OpenSees → RC SAR.

The generic input is a canonical MODEL and explicitly supplied load geometry;
the shipped example is synthetic, not an original building model. Horizontal
panel/line resultants are equivalent nodal forces, NOT exact distributed-member
force diagrams or shell/diaphragm analysis. All RC checks remain bounded/HOLD.
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

from jp_structural.solvers.native.geometry_load_intake import assemble_geometry_source_loads
from jp_structural.solvers.opensees.load_mass_adapter import (
    bind_assembly_to_canonical_model,run_audited_static_gravity
)
from jp_structural.solvers.opensees.member_design_bridge import (
    solve_signed_member_cases,evaluate_m08_m09_m10
)
from scripts.build_structural_template_engine import CONTRACT,COVERAGE

DEFAULT=ROOT/"examples/sanitized/r5_generic_source_geometry_frame.v0.1.json"
SCHEMA="jp.structural.r5.generic_frame_load_mass_signed_SAR.v0.1"
PFX="r5-generic-frame-reference"

def sha(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def build(spec:dict|None=None):
    if spec is None:spec=json.loads(DEFAULT.read_text(encoding="utf-8"))
    if not isinstance(spec,dict) or spec.get("schema")!="jp.structural.r5.input.v0.1":
        raise ValueError("unsupported R5 generic input schema")
    if spec.get("classification")!="SYNTHETIC_REFERENCE_NOT_A_BUILDING":
        raise ValueError("current R5 release only supports explicitly synthetic examples")
    model=spec["model"]
    if spec.get("case_id")!=model.get("model_id"):
        raise ValueError("case identity differs from canonical model")
    a=assemble_geometry_source_loads(
        model=model,loads=spec["source_loads"],gravity_m_s2=spec["gravity_m_s2"])
    bound=bind_assembly_to_canonical_model(model,a["audited_assembly"])
    gravity=run_audited_static_gravity(model,a["audited_assembly"])
    # The individual source categories are independently solved and only
    # *then* combined. Do NOT sum independent max/min member action extrema.
    raw=[]
    components=("Fx_kN","Fy_kN","Fz_kN","Mx_kNm","My_kNm","Mz_kNm")
    case_ids=set()
    for cid,loads in a["load_case_nodal_gravity_kN"].items():
        if cid in case_ids:raise ValueError("duplicate source gravity case")
        case_ids.add(cid)
        raw.append({"case_id":cid,"source_id":"R5_AUDITED_GEOMETRIC_LOADS_"+cid,
            "nodal_loads":[{"node_id":row["node_id"],**dict.fromkeys(components,0.),
                            "Fz_kN":-row["downward_load_kN"]} for row in loads]})
    lateral=spec["lateral_cases"]
    if not isinstance(lateral,list) or not lateral:raise ValueError("explicit lateral case required")
    all_nodes={n["id"] for n in model["nodes"]}
    for case in lateral:
        cid=case["case_id"]
        if cid in case_ids:raise ValueError("duplicate case id between gravity and lateral")
        case_ids.add(cid)
        if not isinstance(case["nodal_loads"],list) or not case["nodal_loads"]:
            raise ValueError("explicit lateral nodal loads required")
        for node in case["nodal_loads"]:
            if node.get("node_id") not in all_nodes or set(node)!={"node_id",*components}:
                raise ValueError("lateral node geometry or signed force components invalid")
            if any(isinstance(node[k],bool) or not isinstance(node[k],(int,float)) or not math.isfinite(node[k])
                   for k in components):
                raise ValueError("lateral force components must be finite")
            if node["Fz_kN"]!=0:
                raise ValueError("lateral reference cannot contain duplicated gravity")
        raw.append(case)
    combos=spec["combinations"]
    signed=solve_signed_member_cases(model=bound,cases=raw,combinations=combos)
    b=spec["design_bindings"]
    designs=evaluate_m08_m09_m10(model=bound,solved=signed,
        beam_bindings=b["beam"],column_bindings=b["column"],joint_bindings=b["joint"])
    if signed["engineering_approval"] or designs["engineering_approval"]:
        raise ValueError("no certification permitted")
    if designs["source_action_digest"]!=signed["input_bundle_sha256"]:
        raise ValueError("design uses different signed FE source")
    total=a["audited_assembly"]["total_gravity_load_kN"]
    if not math.isclose(total,math.fsum(a["case_total_vertical_kN"].values()),rel_tol=1e-10,abs_tol=1e-8):
        raise ValueError("load pattern sums disagree")
    if gravity["equilibrium"]["status"]!="VERTICAL_GLOBAL_FORCE_AND_MOMENT_EQUILIBRIUM_PASS":
        raise ValueError("isolated gravity force/moment equilibrium failed")
    eq=max(abs(x) for case in signed["raw_cases"]
           for x in case["global_force_moment_equilibrium_residual"].values())
    if eq>=1e-5:raise ValueError("signed FE global equilibrium failed")
    contract=json.loads(CONTRACT.read_text(encoding="utf8"))
    coverage={x["id"]:x for x in json.loads(COVERAGE.read_text(encoding="utf8"))["requirements"]}
    scope={"M02":"GEOMETRIC_PANEL_AND_WALL_LOADS_AUDITED_NODE_MASS_EQUIVALENCE_ONLY",
       "M04":"REAL_SIGNED_STATIC_OPENSEES_MEMBER_END_EQUILIBRIUM",
       "M08":"ASSUMED_HINGE_STRENGTHS_BOUNDED_CAPACITY_SHEAR_ONLY",
       "M09":"SOURCE_BINDING_SYNTHETIC_BAR_LAYOUT_BIAXIAL_CHECK_ONLY",
       "M10":"SOURCE_BINDING_JOINT_SHEAR_UNRESOLVED_DIRECTION_ONLY",
       "S17":"SHA_AND_EQUILIBRIUM_REPRODUCIBILITY_ONLY"}
    chapters=[{"id":c["id"],"title":c["title"],"headings":c["headings"],
       "modules":[{"id":m,"title":coverage[m]["title"],
           "registered_status":coverage[m]["status"],
           "this_run":scope.get(m,"NOT_EVALUATED_IN_R5_CASE")} for m in c["requirement_ids"]]}
         for c in contract["chapters"]]
    if len(chapters)!=7 or {v["id"] for c in chapters for v in c["modules"]}!=set(coverage):
        raise ValueError("template/report-coverage contract incomplete")
    member_actions=[]
    for kind,items in (("RAW",signed["raw_cases"]),("COMBINATION",signed["combinations"])):
        for item in items:
            case_id=item.get("case_id",item.get("combination_id"))
            for mid,ends in sorted(item["local_end_resisting_actions"].items()):
                for end in ("I","J"):
                    member_actions.append({"kind":kind,"case_id":case_id,"member":mid,"end":end,
                        **ends[end]})
    row_count=(len(raw)+len(combos))*len(model["frame_members"])*2
    if len(member_actions)!=row_count:
        raise ValueError("signed I/J member actions incomplete")
    return {
       "schema":SCHEMA,"case_id":model["model_id"],"source_class":spec["classification"],
       "source_input_sha256":sha(spec),
       "source_canonical_model_sha256":a["model_sha256"],
       "bound_canonical_model_sha256":signed["model_digest_sha256"],
       "load_mass_source_sha256":bound["provenance"]["load_mass_assembly_sha256"],
       "signed_FE_input_sha256":signed["input_bundle_sha256"],
       "signed_FE_result_sha256":signed["results_digest_sha256"],
       "source_load_component_count":a["source_component_count"],
       "source_load_register":a["source_case_components"],
       "nodal_source_allocation":a["audited_assembly"],
       "case_gravity_load_kN":a["case_total_vertical_kN"],
       "source_total_gravity_kN":total,
       "source_total_seismic_weight_kN":a["audited_assembly"]["total_seismic_weight_kN"],
       "source_seismic_center_by_floor":a["audited_assembly"]["storeys"],
       "gravity_solver_equilibrium":gravity,
       "signed_FE":signed,"bounded_member_checks":designs,
       "chapters":chapters,"bounded_modules_in_this_run":sorted(scope),
       "raw_case_count":len(raw),"signed_combination_count":len(combos),
       "frame_member_count":len(model["frame_members"]),
       "signed_end_action_count":len(member_actions),
       "signed_end_actions":member_actions,
       "max_six_component_FE_balance_kN_or_kNm":eq,
       "gravity_load_resultant_and_seismic_mass_conserved":True,
       "distinct_static_case_combinations_algebraically_signed":True,
       "source_area_and_line_loads_reduced_to_nodal_resultants":True,
       "true_distributed_member_end_forces_or_member_diagrams_evaluated":False,
       "shell_or_diaphragm_FE_evaluated":False,
       "modal_seismic_verified":False,
       "physical_building_source_authenticated":False,
       "code_ULS_SLS_combinations_independently_verified":False,
       "original_G15_F3_one_way_shear_flag":"NOT SAFE IN ONE WAY SHEAR",
       "original_building_design_not_recomputed":True,
       "all_18_modules_complete":False,
       "engineer_approved":False,"permit_eligible":False,"engineering_approval":False,
       "status":"R5_GEOMETRIC_SOURCE_LOADS_TO_SIGNED_STATIC_FE_AND_PARTIAL_RC_CHECKS_NOT_APPROVED",
       "exclusions":[
          "Panel polygon is a load region, no shell stiffness, opening or diaphragm mechanics.",
          "Wall line gravity represented by nodal half-resultants; physical beam distributed-load local moments are NOT captured.",
          "No automatic gravity selfweight; source inputs must account for it without double count.",
          "Seismic mass participation is an explicitly supplied assumption, not code-determined building occupancy.",
          "No real material/drawing authenticity, actual building load paths, modal spectrum, accidental torsion, P-delta or professional approvals.",
          "M08 beam, M09 column and M10 joint checks remain bounded synthetic demonstrations.",
          "No code-compliant ULS/SLS case catalog is inferred from assumed factors."]
    }

def _csv(items,fields):
    s=io.StringIO();w=csv.writer(s,lineterminator="\n");w.writerow(fields)
    for row in items:w.writerow([row[k] for k in fields])
    return s.getvalue()

def html_report(d):
    esc=lambda x:html.escape(str(x),quote=True)
    nav="".join(f'<a href="#ch-{x["id"]}">{x["id"]} {esc(x["title"])}</a>' for x in d["chapters"])
    tr=lambda rows:"".join("<tr>"+"".join("<td>"+esc(v)+"</td>" for v in row)+"</tr>" for row in rows)
    load_rows=[[x["id"],x["kind"],x["load_case_id"],round(x["gravity_weight_kN"],6),
                round(x["seismic_eligible_weight_kN"],6),x["source_provenance"]]
               for x in d["source_load_register"]]
    parts=[]
    for chapter in d["chapters"]:
       subs="".join(f'<h3>{esc(h["number"])} {esc(h["name"])}</h3>' for h in chapter["headings"])
       mod=tr([[x["id"],x["title"],x["this_run"]] for x in chapter["modules"]])
       extra=""
       if chapter["id"]=="04":
           extra="<h3>Source-labelled geometric input</h3><table><tr><th>ID</th><th>Geometry kind</th><th>Case</th><th>Gravity kN</th><th>Seismic W kN</th><th>Source</th></tr>"+tr(load_rows)+"</table>"
       if chapter["id"]=="05":
           extra=f'<p>Actual OpenSees static FE: {d["raw_case_count"]} raw cases and {d["signed_combination_count"]} signed combinations; {d["frame_member_count"]} frame members, {d["signed_end_action_count"]} I/J signed force vectors. Maximum full force/moment equilibrium residual: {d["max_six_component_FE_balance_kN_or_kNm"]:.7g}. Data in <a href="{PFX}-member-actions.csv">member CSV</a>.</p>'
       if chapter["id"]=="06":
           b=d["bounded_member_checks"]
           beam_text=", ".join(esc(x["member_id"])+" ("+esc(x["check"]["status"])+")"
                               for x in b["beam_design"])
           column_text=", ".join(esc(x["member_id"])+" ("+esc(x["status"])+")"
                                 for x in b["column_design"])
           joint_text=", ".join(esc(x["joint_node_id"])+" ("+esc(x["status"])+")"
                                for x in b["joint_design"])
           extra="<p>Non-approved synthetic checks: "+beam_text+"; "+column_text+"; "+joint_text+".</p>"
       parts.append(f'<section id="ch-{esc(chapter["id"])}"><h2>Chapter {esc(chapter["id"])} — {esc(chapter["title"])}</h2>{subs}<h3>Module check coverage</h3><table><tr><th>Module</th><th>Requirement</th><th>R5 result</th></tr>{mod}</table>{extra}</section>')
    caveats="".join("<li>"+esc(q)+"</li>" for q in d["exclusions"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>R5 Generic Frame — Audited Load-Mass and Signed FE SAR</title><style>body{{max-width:1130px;margin:auto;padding:22px;background:#f8fafc;color:#22354d;font:14px/1.6 system-ui}}header,section{{background:white;padding:20px;margin:16px 0;border:1px solid #d7e0e8;border-radius:12px}}nav{{display:flex;gap:9px;flex-wrap:wrap}}nav a{{border:1px solid #a9c0d2;padding:7px;text-decoration:none;border-radius:6px}}.warn{{border-left:4px solid #b54e48;padding:11px;background:#fff0ed}}table{{width:100%;border-collapse:collapse;display:block;overflow:auto;max-height:500px}}td,th{{border:1px solid #d7dfe9;padding:7px;text-align:left;vertical-align:top}}th{{background:#eff3f8}}code{{overflow-wrap:anywhere}}@media print{{nav{{display:none}}body{{padding:0}}section{{border:0}}tr{{break-inside:avoid}}}}</style></head><body><header>
<small>JP STRUCTURAL · R5 SOURCE-LABELLED GENERIC LOAD INTAKE · SYNTHETIC ONLY</small>
<h1>Source geometry → gravity/mass → signed OpenSees → bounded RC checks</h1>
<p class="warn"><strong>NOT ENGINEERING APPROVED; NOT FOR CONSTRUCTION OR PERMIT.</strong> Panel and line loads are lumped as explicitly specified node resultants. Neither true distributed member moments nor floor shell/stiffness are modelled.</p>
<p><strong>Case:</strong> {esc(d["case_id"])} · Gravity total {d["source_total_gravity_kN"]:.3f} kN · seismic eligible {d["source_total_seismic_weight_kN"]:.3f} kN. All physical data synthetic.</p><nav>{nav}</nav></header>
{''.join(parts)}
<section><h2>Annex — audit and release evidence</h2>
<p>Original G+1.5 F3 warning retained: <strong>NOT SAFE IN ONE WAY SHEAR</strong>. This synthetic case is not the original building.</p>
<p>Source SHA: <code>{esc(d["source_input_sha256"])}</code> · Signed FE SHA: <code>{esc(d["signed_FE_result_sha256"])}</code></p>
<p><a href="{PFX}.json">Machine data</a> · <a href="{PFX}-member-actions.csv">Signed member-end actions CSV</a> · <a href="{PFX}-source-loads.csv">Source load ledger CSV</a> · <a href="{PFX}-manifest.json">SHA-256 manifest</a></p>
<h3>Open debt and limitations</h3><ul>{caveats}</ul><p class="warn">No full NBC compliance, engineering signoff, permit eligibility or verified actual-building source.</p></section></body></html>"""

def markdown(d):
    lines=["# R5 Geometry-to-analysis SAR — governed synthetic reference","",
       f"**Case:** {d['case_id']} · **Status:** NOT ENGINEERING APPROVED","",
       f"Input SHA256: {d['source_input_sha256']}; signed FE results SHA256: {d['signed_FE_result_sha256']}.","",
       f"Source geometry components: {d['source_load_component_count']}; gravity {d['source_total_gravity_kN']:.4f} kN; seismic eligible {d['source_total_seismic_weight_kN']:.4f} kN.","",
       f"Actual FE: {d['raw_case_count']} raw signed cases × {d['frame_member_count']} members, plus {d['signed_combination_count']} concurrent signed combinations; {d['signed_end_action_count']} I/J action vectors.","",
       "## Seven-chapter original report TOC"]
    lines += [f"- [{x['id']} — {x['title']}](#ch-{x['id']})" for x in d["chapters"]]
    for chapter in d["chapters"]:
        lines.extend(["",f'<a id="ch-{chapter["id"]}"></a>',f'## Chapter {chapter["id"]} — {chapter["title"]}',""])
        for m in chapter["modules"]:lines.append(f"- **{m['id']} {m['title']}:** {m['this_run']}")
    lines.extend(["","## Explicit missing capabilities",""])
    lines.extend("- "+x for x in d["exclusions"])
    lines.extend(["","Original F3: **NOT SAFE IN ONE WAY SHEAR**, unchanged. **No engineering approval.**",""])
    return "\n".join(lines)

def emit(input_file:Path,output_dir:Path):
    d=build(json.loads(input_file.read_text(encoding="utf8")))
    output_dir.mkdir(parents=True,exist_ok=True)
    fields=["kind","case_id","member","end","N","Vy","Vz","T","My","Mz"]
    sf=["id","source_key","load_case_id","kind","category","gravity_weight_kN","seismic_eligible_weight_kN","source_provenance"]
    outputs={PFX+".json":json.dumps(d,sort_keys=True,indent=2,allow_nan=False)+"\n",
      PFX+".html":html_report(d),PFX+".md":markdown(d),
      PFX+"-member-actions.csv":_csv(d["signed_end_actions"],fields),
      PFX+"-source-loads.csv":_csv(d["source_load_register"],sf)}
    for name,value in outputs.items():(output_dir/name).write_text(value,encoding="utf8")
    m={"schema":"jp.structural.r5.output_manifest.v0.1","case_id":d["case_id"],
       "input_sha256":d["source_input_sha256"],
       "files":{name:hashlib.sha256(v.encode("utf8")).hexdigest() for name,v in outputs.items()},
       "engineering_approval":False}
    (output_dir/(PFX+"-manifest.json")).write_text(json.dumps(m,indent=2,sort_keys=True)+"\n",encoding="utf8")
    return d

def main():
    p=argparse.ArgumentParser();p.add_argument("--input",type=Path,default=DEFAULT)
    p.add_argument("--output-dir",type=Path,required=True)
    args=p.parse_args();d=emit(args.input,args.output_dir)
    print("R5_GENERIC_LOAD_MASS_SIGNED_FE",d["source_total_gravity_kN"],d["source_total_seismic_weight_kN"],d["frame_member_count"],d["signed_end_action_count"],"UNAPPROVED")
if __name__=="__main__":main()
