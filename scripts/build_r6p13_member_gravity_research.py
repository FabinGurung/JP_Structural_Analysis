#!/usr/bin/env python3
"""R6.13 traceable member-by-member source gravity & research action workbook.

Existing registered ULS/SLS E2K SOURCE -> geometry and assignments.
Existing R6.10 nonconforming 103-shell OpenSees RESEARCH -> end actions.
No ETABS21 solution, authentic native mesh, RCC strength, geotechnical
acceptance, new fictitious support, or designer-approved member envelope.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from hashlib import sha256
import json, math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_r6p8_native_source_catalogue import build as source_catalogue
from scripts.build_r6p10_gravity_casebook import build_casebook
from scripts.build_r6p10_source_shell_mesh import build as source_mesh_audit

SITE=ROOT/"site"
OUT=SITE/"data/r6p13-member-gravity-research.json"
RECEIPT=SITE/"reports/r6p13-member-gravity-research-summary.json"
GRAVITY=("Dead","Live","WALL LOAD","FLOOR FINISH")
ROLES=("ULS","SLS")
ORDER=("Ni_kN","Vyi_kN","Vzi_kN","Ti_kNm","Myi_kNm","Mzi_kNm",
       "Nj_kN","Vyj_kN","Vzj_kN","Tj_kNm","Myj_kNm","Mzj_kNm")
MAX_ABS={"axial_kN":(0,6),"shear_kN":(1,2,7,8),
         "bending_kNm":(4,5,10,11),"torsion_kNm":(3,9)}
SCHEMA="jp.structural.r6p13.source_gravity_research_member_ledger.v0.1"

def finite(value,field):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError(f"{field} must be a finite real numeric value")
    return float(value)

def action_metrics(values):
    if len(values)!=12:
        raise ValueError("Signed local member end-action vector must contain 12 values")
    vals=[finite(x,"local action") for x in values]
    return {
      "signed_local_end_actions":dict(zip(ORDER,vals)),
      "max_abs_component_of_end_actions":{
          label:round(max(abs(vals[i]) for i in indexes),5)
          for label,indexes in MAX_ABS.items()},
      "units":{"force":"kN","moment":"kN·m"},
      "original_ETABS21_solved_end_actions":False,
      "engineering_member_design_accepted":False}

def source_load_summary(m):
    length=finite(m["length_mm"],"L_mm")/1000
    assert length>0
    integrated=defaultdict(float);methods=[]
    for load in m["applied_loads"]:
        q=finite(load["raw_integrated_kN"],"load kN")
        integrated[load["pattern"]]+=q
        methods.append({"pattern":load["pattern"],"method":load["method"],
              "raw_resultant_kN":q,"working":load["working"],
              "mass_factor_not_design_factor":load["mass_participation_factor"]})
    wall=integrated.get("WALL LOAD",0.0)
    uniform_wall=all(x["method"]=="U" for x in methods if x["pattern"]=="WALL LOAD")
    has_wall=any(x["pattern"]=="WALL LOAD" for x in methods)
    simple=None
    if m["kind"]=="BEAM" and has_wall and uniform_wall:
        # Single simply-supported member counterfactual, never an actual
        # frame connection, FEM action, design moment or approved capacity.
        q=wall/length
        simple={"assumed_only_wall_kN_per_m":round(q,6),
                "assumed_pin_support_each_reaction_kN":round(wall/2,6),
                "assumed_pin_support_midspan_M_kNm":round(q*length*length/8,6),
                "formula":"Ri=Rj=wL/2; Mmid=wL^2/8",
                "not_a_source_frame_end_action":True}
    return {"assigned_resultants_by_pattern_kN":{k:round(v,6) for k,v in sorted(integrated.items())},
            "source_member_wall_resultant_kN":round(wall,6),
            "original_source_loads":methods,"simple_span_wall_only_counterfactual":simple,
            "wall_segment_requires_partial_span_analysis":has_wall and not uniform_wall}

def build(model=None,cases=None,mesh=None):
    model=source_catalogue() if model is None else model
    cases=build_casebook() if cases is None else cases
    mesh=source_mesh_audit() if mesh is None else mesh
    assert model["schema"]=="jp.structural.r6p8.native_input_member_calculation_book.v0.1"
    assert cases["schema"]=="jp.structural.r6p10.connected_source_shell_gravity_and_conditional_seismic_casebook.v0.2"
    assert mesh["schema"]=="jp.structural.r6p10.original_e2k_source_shell_mesh_and_loadcase_audit.v0.1"
    fingerprints=dict(zip(ROLES,model["source"]["source_ulssls_hashes"]))
    assert fingerprints==cases["source_model_fingerprints"]==mesh["governing_source_sha256"]
    assert len(model["members"])==199 and len(model["shells"])==115
    assert cases["original_structural_frames_numerically_solved"]==165
    assert cases["source_shells_numerically_solved"]==103
    assert cases["original_shells_source_vertically_unanchored"]==12
    assert mesh["shells_without_verified_vertical_support_path"]==12
    assert mesh["shells_connected_through_source_to_fixed_base"]==103
    assert not cases["engineering_approval"] and cases["F3_one_way_shear_unsafe"]
    assert not mesh["engineering_approval"] and mesh["source_F3_one_way_shear_unsafe"]
    assert not model["result_scope"]["engineering_approval"]
    structural=[m for m in model["members"] if m["kind"] in ("BEAM","COLUMN")]
    unsectioned=[m for m in model["members"] if m["kind"]=="LINE"]
    if len(structural)!=165 or len(unsectioned)!=34:
        raise ValueError("Governing structural and unsectioned line counts changed")
    keys=[m["key"] for m in structural]
    if len(set(keys))!=165:raise ValueError("Duplicate native member key")
    prepared={}
    for role in ROLES:
        c=cases["role_results"][role]
        if c["original_role_specific_stiffness"]!=role:raise ValueError("Stiffness role mismatch")
        raw=c["independently_run_research_patterns"]
        for pattern in GRAVITY:
            x=raw[pattern]
            if x["source_case"]!=pattern or x["role"]!=role:
                raise ValueError("Case role/name mismatch")
            if (x["original_unsupported_shells_numerically_excluded"]!=12
                or x["vertically_supported_shells_numerically_included"]!=103
                or set(x["signed_member_end_actions_bounded"])!=set(keys)):
                raise ValueError("Scope or frame key mismatch in research case")
            if x["vertical_equilibrium_residual_N"]>max(
                    .05,x["applied_gravity"]["total_applied_downward_N"]*3e-5):
                raise ValueError("Gravity case force equilibrium lost")
        gravity_combos=[q for q in c["recombined_original_11_linear_add_expressions"]
                        if not q["source_seismic_combination"]]
        if len(gravity_combos)!=3:raise ValueError("Original gravity-only combo coverage changed")
        for q in gravity_combos:
            if (set(q["signed_member_end_actions_non_design"])!=set(keys) or
                q["design_envelope_approved"] or q["fully_reproduced_original_source_case"] or
                q["source_eccentricity_plus_minus_5pct_applied"]):
                raise ValueError("Invalid original source combo boundary")
        prepared[role]={"raw":raw,"gravity_combos":gravity_combos}
    members=[]
    for m in structural:
        key=m["key"];geom={
          "start_xyz_mm":m["start_xyz_mm"],"end_xyz_mm":m["end_xyz_mm"],
          "length_m":round(m["length_mm"]/1000,6),
          "section_area_mm2":m["section_area_mm2"],
          "gross_concrete_volume_m3":m["section_gross_volume_m3"],
          "gross_member_selfweight_proxy_kN":m["source_dead_selfweight_proxy_kN"]
        }
        loads=source_load_summary(m)
        runs={}
        for role in ROLES:
            part=prepared[role]
            trials={name:action_metrics(part["raw"][name]["signed_member_end_actions_bounded"][key])
                    for name in GRAVITY}
            combo_rows=[]
            for q in part["gravity_combos"]:
                vals=q["signed_member_end_actions_non_design"][key]
                combo_rows.append({"source_expression":q["original_source_name"],
                   "original_source_terms":q["original_source_terms"],
                   "metrics":action_metrics(vals)["max_abs_component_of_end_actions"],
                   "not_an_ETABS21_design_load_combination_solution":True})
            runs[role]={"raw_gravity_case_trial":trials,
                 "three_original_gravity_combo_research_trials":combo_rows,
                 "ULS_SLS_is_source_stiffness_variant_not_load_factoring":True,
                 "member_capacity_or_safety": "NOT_DETERMINED"}
        members.append({"key":key,"story":m["storey"],"kind":m["kind"],
            "section":m["section"],"material":m["material"],
            "source_point_ids":m["point_ids"],"geometry":geom,
            "source_loading":loads,"trial_actions_by_source_stiffness":runs,
            "capacity_verification":"NOT_PERFORMED",
            "reason_capacity_not_approved":"No authenticated complete design action envelope, section detail and joint/support compatibility",
            "unverified_as_built_rebar":True,
            "source_member_identity_authenticated":True})
    shell_verified={x["key"]:x for x in mesh["all_shell_parameters"]}
    if len(shell_verified)!=115:raise ValueError("Source panel audit changed")
    panels=[]
    for s in model["shells"]:
        p=shell_verified[s["key"]]
        panels.append({"key":s["key"],"story":s["storey"],"kind":s["kind"],
            "section":s["section"],"thickness_mm":s["thickness_mm"],
            "projected_area_m2":round(s["projected_area_mm2"]/1e6,6),
            "gross_plan_selfweight_proxy_kN":s["source_dead_selfweight_proxy_kN"],
            "source_applied_resultants_kN":{
                pattern:round(sum(x["raw_integrated_kN"] for x in s["applied_loads"]
                    if x["pattern"]==pattern),6)
                for pattern in ("Live","FLOOR FINISH")},
            "included_in_103_shell_research_trial":p["source_supported_by_frame_shell_topology"],
            "shell_strength_and_load_path_verified":False})
    if sum(p["included_in_103_shell_research_trial"] for p in panels)!=103:
        raise ValueError("Shell connectivity admission changed")
    line_summary=[]
    for m in unsectioned:
        load=source_load_summary(m)
        line_summary.append({"key":m["key"],"story":m["storey"],
            "source_wall_resultant_kN":load["source_member_wall_resultant_kN"],
            "structural_member":False,"separate_concrete_capacity":False,
            "source_loading":load})
    if sum(len(x["source_loading"]["original_source_loads"]) for x in line_summary
           if x["source_loading"]["source_member_wall_resultant_kN"]!=0)!=30:
        raise ValueError("Unsectioned wall load count changed")
    by_story={}
    for story in ("GF","FF","TF"):
        subset=[m for m in members if m["story"]==story]
        by_story[story]={"beams":sum(m["kind"]=="BEAM" for m in subset),
                         "columns":sum(m["kind"]=="COLUMN" for m in subset),
                         "gross_frame_concrete_m3":round(sum(m["geometry"]["gross_concrete_volume_m3"]
                             for m in subset),6),
                         "direct_source_wall_on_concrete_frames_kN":round(
                             sum(m["source_loading"]["source_member_wall_resultant_kN"]
                                 for m in subset),6),
                         "shells_original":sum(p["story"]==story for p in panels),
                         "shells_research_excluded":sum(p["story"]==story and
                           not p["included_in_103_shell_research_trial"] for p in panels)}
    b46=next(m for m in members if m["key"]=="GF:B46")
    if not math.isclose(b46["source_loading"]["source_member_wall_resultant_kN"],
                        44.61275,abs_tol=1e-5):
        raise ValueError("Verified B46 source wall force changed")
    return {"schema":SCHEMA,"provenance":{"governing_model_SHA256":fingerprints,
        "input_catalogue_schema":model["schema"],"research_casebook_schema":cases["schema"],
        "native_ETABS21_solver_executed":False,"historical_report_member_IDs_not_inherited":True},
        "method":"source load and gross volume arithmetic + existing bounded research OpenSees member end actions",
        "local_force_order":list(ORDER),
        "count":{"actual_structural_frame_members":len(members),
                 "unsectioned_line_source_records":len(line_summary),
                 "source_shell_objects":len(panels),
                 "research_shells_included":103,"research_shells_excluded":12,
                 "source_gravity_patterns_by_stiffness":4,
                 "source_gravity_only_expressions_by_stiffness":3},
        "by_story":by_story,"members":members,"shells":panels,"unsectioned_lines":line_summary,
        "historic_foundation_crosswalk":{
            "F3":"Historic printed pressure/one-way shear checks have no authenticated current source reaction map",
            "CF1":"Historic service load/soil inputs do not establish current footing response"},
        "research_member_strength_or_capacity_accepted":False,
        "original_ETABS21_native_mesh_or_reactions_reproduced":False,
        "twelve_unsupported_shells_excluded":True,
        "F3_one_way_shear_unsafe":True,
        "engineering_approval":False}

def export(model=None,cases=None,mesh=None):
    result=build(model=model,cases=cases,mesh=mesh)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    summary={"schema":"jp.structural.r6p13.member_load_evidence_receipt.v0.1",
        "counts":result["count"],"governing_model_SHA256":result["provenance"]["governing_model_SHA256"],
        "sha256":sha256(OUT.read_bytes()).hexdigest(),
        "research_member_capacity_accepted":False,"original_ETABS21_solver_reproduced":False,
        "F3_one_way_shear_unsafe":True,"engineering_approval":False}
    RECEIPT.parent.mkdir(parents=True,exist_ok=True)
    RECEIPT.write_text(json.dumps(summary,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return result,summary

if __name__=="__main__":
    d,receipt=export()
    print("R6.13 source members",d["count"],"F3 unsafe; no design acceptance")
