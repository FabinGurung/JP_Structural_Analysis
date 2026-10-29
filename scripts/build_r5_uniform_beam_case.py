#!/usr/bin/env python3
"""R5 distributed beam loads: true 3D eleLoad + local I/J force recovery.

This deliberately extends the R5 source-mass case without changing its canonical
model or accepted source mass. Panel loads remain source-distributed nodal
equivalents; uniform line loads are REMOVED from the nodal force allocation and
applied instead directly to OpenSees 3D beam elements. No double counting.
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
from jp_structural.solvers.opensees.load_mass_adapter import bind_assembly_to_canonical_model
from jp_structural.solvers.opensees.member_design_bridge import (
    solve_signed_member_cases,evaluate_m08_m09_m10
)
from scripts.build_r5_generic_frame_case import DEFAULT,build as build_lumped
from scripts.build_structural_template_engine import CONTRACT,COVERAGE

PFX="r5-distributed-beam-reference"
SCHEMA="jp.structural.r5.distributed_uniform_beam_to_signed_SAR.v0.2"

class DistributedIntakeError(ValueError):
    pass

def _sha(o):
    return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf8")).hexdigest()

def build(spec=None):
    if spec is None:spec=json.loads(DEFAULT.read_text(encoding="utf8"))
    if spec.get("classification")!="SYNTHETIC_REFERENCE_NOT_A_BUILDING" or spec.get("schema")!="jp.structural.r5.input.v0.1":
        raise DistributedIntakeError("R5 verified independent synthetic source fixture required")
    model=spec["model"]
    if spec.get("case_id")!=model.get("model_id"):
        raise DistributedIntakeError("case/model identity differs")
    assembled=assemble_geometry_source_loads(model=model,loads=spec["source_loads"],
                                               gravity_m_s2=spec["gravity_m_s2"])
    bound=bind_assembly_to_canonical_model(model,assembled["audited_assembly"])
    cases={}
    for cid,parts in assembled["load_case_nodal_gravity_kN"].items():
        cases[cid]={x["node_id"]:x["downward_load_kN"] for x in parts}
    loads_by_case={}
    element_kN=0.
    for item in assembled["source_case_components"]:
        if item["kind"]!="UNIFORM_FRAME_LINE_LOAD":
            continue
        cid=item["load_case_id"]
        total=item["gravity_weight_kN"]
        for share in item["node_shares"]:
            nid=share["node_id"]
            cases[cid][nid]-=total*share["fraction"]
            if cases[cid][nid]<-1e-9:
                raise DistributedIntakeError("double counted load or excessive member subtraction")
            if abs(cases[cid][nid])<1e-9:cases[cid][nid]=0.
        geom=item["geometry"]
        if not math.isclose(geom["length_m"]*geom["intensity_kN_m"],total,rel_tol=1e-10,abs_tol=1e-8):
            raise DistributedIntakeError("source member line intensity does not conserve total")
        loads_by_case.setdefault(cid,[]).append({
            "id":item["id"],"source_key":item["source_key"],
            "member_id":geom["member_id"],"downward_kN_per_m":geom["intensity_kN_m"]})
        element_kN+=total
    if element_kN<=0:
        raise DistributedIntakeError("at least one source-identified member uniform line load required")
    raw=[]
    six=("Fx_kN","Fy_kN","Fz_kN","Mx_kNm","My_kNm","Mz_kNm")
    for cid,parts in sorted(cases.items()):
        nodal=[{"node_id":nid,**dict.fromkeys(six,0.),"Fz_kN":-value}
               for nid,value in sorted(parts.items()) if value>1e-10]
        if not nodal and cid not in loads_by_case:
            raise DistributedIntakeError("empty independent case")
        case={"case_id":cid,"source_id":"R5_AUDITED_GEOMETRIC_LOADS_"+cid,"nodal_loads":nodal}
        if cid in loads_by_case:
            case["uniform_beam_loads"]=loads_by_case[cid]
        raw.append(case)
    caseids={x["case_id"] for x in raw}
    for case in spec["lateral_cases"]:
        if case["case_id"] in caseids:
            raise DistributedIntakeError("duplicated raw case identity")
        caseids.add(case["case_id"])
        raw.append(case)
    signed=solve_signed_member_cases(model=bound,cases=raw,combinations=spec["combinations"])
    cfg=spec["design_bindings"]
    checked=evaluate_m08_m09_m10(model=bound,solved=signed,
        beam_bindings=cfg["beam"],column_bindings=cfg["column"],joint_bindings=cfg["joint"])
    if checked["source_action_digest"]!=signed["input_bundle_sha256"]:
        raise DistributedIntakeError("source signed FE/design mapping mismatch")
    if signed["engineering_approval"] or checked["engineering_approval"]:
        raise DistributedIntakeError("invalid engineering approval")
    total_nodal=math.fsum(-x["Fz_kN"] for case in raw if case["case_id"] in cases
                    for x in case["nodal_loads"])
    total_source=assembled["audited_assembly"]["total_gravity_load_kN"]
    if not math.isclose(total_nodal+element_kN,total_source,rel_tol=1e-10,abs_tol=1e-8):
        raise DistributedIntakeError("nodal + element gravity double-count/missing-source mismatch")
    if not math.isclose(element_kN,math.fsum(
        x["downward_resultant_kN"] for case in signed["raw_cases"]
        for x in case["uniform_beam_loads"]),rel_tol=1e-10,abs_tol=1e-8):
        raise DistributedIntakeError("OpenSees element load application lost source weight")
    eq=max(abs(x) for case in signed["raw_cases"] for x in
           case["global_force_moment_equilibrium_residual"].values())
    if eq>1e-5:raise DistributedIntakeError("full six-component static equilibrium failed")
    # Actual member forces differ from a half-to-each-end node replacement even
    # when global resultants are identical. This proves the old limitation was
    # addressed without rewriting or confusing the old v0.1 source.
    predecessor=build_lumped(spec)
    old_cases={x["case_id"]:x for x in predecessor["signed_FE"]["raw_cases"]}
    new_cases={x["case_id"]:x for x in signed["raw_cases"]}
    bymid={x["member_id"] for r in signed["raw_cases"] for x in r["uniform_beam_loads"]}
    changed=[]
    for mid in sorted(bymid):
        for end in ("I","J"):
            before=old_cases["DL"]["local_end_resisting_actions"][mid][end]
            after=new_cases["DL"]["local_end_resisting_actions"][mid][end]
            changed.append({"member_id":mid,"end":end,
               "predecessor_lumped_local_My_kNm":before["My"],
               "native_element_local_My_kNm":after["My"],
               "moment_difference_kNm":after["My"]-before["My"],
               "predecessor_lumped_local_Vz_kN":before["Vz"],
               "native_element_local_Vz_kN":after["Vz"]})
    if not changed or not any(abs(x["moment_difference_kNm"])>1e-4 for x in changed):
        raise DistributedIntakeError("native element load did not alter local end moments versus lumped baseline")
    template=json.loads(CONTRACT.read_text(encoding="utf8"))
    statuses={x["id"]:x for x in json.loads(COVERAGE.read_text(encoding="utf8"))["requirements"]}
    scopes={"M02":"SOURCE_AREA_NODAL_PLUS_WALL_TRUE_ELEMENT_UNIFORM_LOAD_AND_MASS_CONSERVATION",
       "M04":"OPEN_SEES_LINEAR_3D_UNIFORM_ELEMENT_LOAD_LOCAL_FORCE_SIGNED_ENDS",
       "M08":"BOUND_SIGNED_FE_BEAM_SHEAR_WITH_ASSUMED_END_STRENGTHS",
       "M09":"BOUND_SYNTHETIC_COLUMN_BIAXIAL_CHECK",
       "M10":"BOUND_SYNTHETIC_JOINT_SHEAR_CHECK",
       "S17":"SIX_COMPONENT_GLOBAL_EQUILIBRIUM_AND_NATIVE_FIXED_END_BENCHMARK"}
    chapters=[{"id":ch["id"],"title":ch["title"],"headings":ch["headings"],
       "modules":[{"id":i,"title":statuses[i]["title"],
           "existing_status":statuses[i]["status"],
           "this_run":scopes.get(i,"NOT_EVALUATED_IN_THIS_UNIFORM_BEAM_CASE")}
            for i in ch["requirement_ids"]]} for ch in template["chapters"]]
    if len(chapters)!=7 or {x["id"] for ch in chapters for x in ch["modules"]}!=set(statuses):
        raise DistributedIntakeError("7-chapter / 18-module TOC incomplete")
    force_rows=[]
    for kind,items in (("RAW",signed["raw_cases"]),("COMBINATION",signed["combinations"])):
        for item in items:
            case_id=item.get("case_id",item.get("combination_id"))
            for mid,ends in sorted(item["local_end_resisting_actions"].items()):
                for end in ("I","J"):
                    force_rows.append({"kind":kind,"case_id":case_id,"member_id":mid,"end":end,
                                       **ends[end]})
    if len(force_rows)!=(len(raw)+len(spec["combinations"]))*len(model["frame_members"])*2:
        raise DistributedIntakeError("missing signed I/J action vector")
    return {
       "schema":SCHEMA,"case_id":model["model_id"],"source_input_sha256":_sha(spec),
       "canonical_model_digest_sha256":signed["model_digest_sha256"],
       "mass_assembly_source_sha256":bound["provenance"]["load_mass_assembly_sha256"],
       "signed_FE_input_sha256":signed["input_bundle_sha256"],
       "signed_FE_result_sha256":signed["results_digest_sha256"],
       "original_source_loads":assembled["source_case_components"],
       "source_total_gravity_kN":total_source,"source_seismic_weight_kN":
           assembled["audited_assembly"]["total_seismic_weight_kN"],
       "nodal_resultants_kN":total_nodal,"true_element_uniform_resultants_kN":element_kN,
       "geometry_audited_mass_allocation":assembled["audited_assembly"],
       "signed_FE":signed,"bounded_member_checks":checked,
       "predecessor_equivalent_nodal_comparison":changed,
       "provenance_load_method":"ELEMENT_NATIVE_OPENSEES_BEAM_UNIFORM_Wz",
       "source_code_reference":"https://opensees.github.io/OpenSeesDocumentation/user/manual/model/eleLoad.html",
       "source_loads_conserved_without_double_count":True,
       "uniform_member_fixed_end_effects_recovered":True,
       "global_six_component_equilibrium_max_kN_or_kNm":eq,
       "raw_case_count":len(raw),"signed_combination_count":len(spec["combinations"]),
       "model_member_count":len(model["frame_members"]),"signed_end_action_count":len(force_rows),
       "signed_end_action_records":force_rows,
       "chapters":chapters,"calculated_scope_modules":sorted(scopes),
       "original_F3_failure":"NOT SAFE IN ONE WAY SHEAR",
       "original_building_source_accepted":False,"original_F3_design_pass":False,
       "shell_or_diaphragm_FE_integrated":False,"panel_pressure_is_still_nodal_equivalent":True,
       "full_building_load_path_validated":False,"full_steel_detailing_complete":False,
       "spectrum_or_PDelta_verified":False,
       "engineering_approval":False,"permit_eligible":False,"construction_approved":False,
       "status":"R5_NATIVE_UNIFORM_BEAM_LOAD_SIGNED_FE_MEMBER_ENDS_NOT_ENGINEER_APPROVED"
    }

def _csv(rows,fields):
    s=io.StringIO();w=csv.writer(s,lineterminator="\n");w.writerow(fields)
    for x in rows:w.writerow([x[k] for k in fields])
    return s.getvalue()

def render_html(r):
    e=lambda x:html.escape(str(x),quote=True)
    tr=lambda items:"".join("<tr>"+"".join("<td>"+e(v)+"</td>" for v in row)+"</tr>" for row in items)
    nav="".join(f'<a href="#ch-{x["id"]}">{x["id"]} {e(x["title"])}</a>' for x in r["chapters"])
    sections=[]
    for ch in r["chapters"]:
        rows=tr([[x["id"],x["title"],x["this_run"]] for x in ch["modules"]])
        extra=""
        if ch["id"]=="04":
            extra=f'<p>Source gravity {r["source_total_gravity_kN"]:.3f} kN, of which {r["true_element_uniform_resultants_kN"]:.3f} kN is physically applied as beam element load. Seismic weight {r["source_seismic_weight_kN"]:.3f} kN, independent of whether gravity is lumped or distributed.</p>'
        if ch["id"]=="05":
            comp=tr([[x["member_id"],x["end"],f'{x["predecessor_lumped_local_My_kNm"]:.5f}',f'{x["native_element_local_My_kNm"]:.5f}',f'{x["moment_difference_kNm"]:.5f}'] for x in r["predecessor_equivalent_nodal_comparison"]])
            extra='<h3>Exact uniform beam load versus prior lumped-node end moments</h3><table><tr><th>Member</th><th>I/J</th><th>Old M_y kNm</th><th>Native M_y kNm</th><th>Difference kNm</th></tr>'+comp+'</table>'
            extra+=f'<p>{r["raw_case_count"]} signed raw static cases, {r["signed_combination_count"]} combinations, {r["signed_end_action_count"]} signed I/J member records. Maximum six-component free-body residual {r["global_six_component_equilibrium_max_kN_or_kNm"]:.6g} kN or kNm.</p>'
        if ch["id"]=="06":
            b=r["bounded_member_checks"]
            extra='<p>Bounded, unapproved M08/M09/M10 checks: '+e(len(b["beam_design"]))+' beams, '+e(len(b["column_design"]))+' columns, '+e(len(b["joint_design"]))+' joints.</p>'
        sections.append(f'<section id="ch-{e(ch["id"])}"><h2>Chapter {e(ch["id"])} — {e(ch["title"])}</h2><table><tr><th>Module</th><th>Requirements</th><th>Current numerical scope</th></tr>{rows}</table>{extra}</section>')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>R5 exact distributed beam element SAR</title><style>body{{font:14px/1.6 system-ui;color:#23364e;background:#f7f9fd;max-width:1100px;margin:auto;padding:20px}}header,section{{background:#fff;border:1px solid #d9e2eb;padding:20px;margin:15px 0;border-radius:12px}}nav{{display:flex;flex-wrap:wrap;gap:8px}}nav a{{border:1px solid #b3c4d5;padding:7px;border-radius:7px;text-decoration:none}}table{{display:block;max-width:100%;overflow:auto;border-collapse:collapse;font-size:12px}}td,th{{border:1px solid #cbd4df;padding:7px;text-align:left;vertical-align:top}}th{{background:#eef2f6}}.hold{{background:#fff1eb;border-left:5px solid #b75d51;padding:12px}}@media print{{nav{{display:none}}body{{background:white}}}}</style></head><body><header>
<h1>Native uniform beam loads → signed FE → bounded RC report</h1>
<p class="hold"><strong>NOT ENGINEER APPROVED, NOT FOR BUILDING PERMIT OR CONSTRUCTION.</strong> The four-column example is synthetic. Source-defined panel pressures remain equivalent nodal resultants; only horizontal beam uniform line loading is now a native OpenSees element load. Original F3 remains NOT SAFE IN ONE WAY SHEAR.</p>
<p>Source load {r["source_total_gravity_kN"]:.1f} kN; native element load {r["true_element_uniform_resultants_kN"]:.1f} kN; {r["signed_end_action_count"]} signed frame I/J actions. <a href="{PFX}.json">Calculation JSON</a> · <a href="{PFX}-member-ends.csv">Signed force CSV</a> · <a href="{PFX}-manifest.json">SHA manifest</a></p>
<nav>{nav}</nav></header>{''.join(sections)}
<section><h2>Annex — source, software verification and safety HOLD</h2>
<p>OpenSees 3D \`eleLoad -beamUniform Wy Wz Wx\`: <a href="{e(r["source_code_reference"])}">official documentation</a>.</p>
<p>Each applied local beam load is horizontal-beam canonical local Wz. Vertical beam, inclined beam, arbitrary local-axis rotation and unvalidated slab distribution are rejected or left out rather than guessed.</p>
<p>Signed input SHA: {e(r["signed_FE_input_sha256"])}. Original building physical proof: OPEN. F3 original one-way shear failure: NOT SAFE.</p></section></body></html>"""

def emit(input_path,folder):
    r=build(json.loads(Path(input_path).read_text(encoding="utf8")))
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    fields=["kind","case_id","member_id","end","N","Vy","Vz","T","My","Mz"]
    objects={
        PFX+".json":json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+"\n",
        PFX+".html":render_html(r),
        PFX+"-member-ends.csv":_csv(r["signed_end_action_records"],fields),
        PFX+"-moments-comparison.csv":_csv(r["predecessor_equivalent_nodal_comparison"],
            ["member_id","end","predecessor_lumped_local_My_kNm","native_element_local_My_kNm",
             "moment_difference_kNm","predecessor_lumped_local_Vz_kN","native_element_local_Vz_kN"])}
    for name,data in objects.items():(folder/name).write_text(data,encoding="utf8")
    manifest={"schema":"jp.structural.r5.distributed_manifest.v0.2",
      "source_sha256":r["source_input_sha256"],
      "files":{name:hashlib.sha256(data.encode("utf8")).hexdigest() for name,data in objects.items()},
      "engineering_approval":False}
    (folder/(PFX+"-manifest.json")).write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n",encoding="utf8")
    return r

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=DEFAULT)
    p.add_argument("--output-dir",type=Path,required=True)
    a=p.parse_args();r=emit(a.input,a.output_dir)
    print("R5_NATIVE_DISTRIBUTED",r["true_element_uniform_resultants_kN"],"kN",
          r["signed_end_action_count"],"SIGNED_MEMBER_END_ACTIONS_NO_APPROVAL")
if __name__=="__main__":main()
