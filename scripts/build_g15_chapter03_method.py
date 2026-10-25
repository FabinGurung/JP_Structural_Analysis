#!/usr/bin/env python3
"""Chapter 3 source-method-to-real-OpenSees calculation crosswalk.

Reuses the actual Gate21 OpenSees calculation, checks numerical equilibrium,
and keeps every real-building engineering acceptance gate CLOSED/ON HOLD.
"""
from __future__ import annotations
import argparse,json,math,hashlib
from pathlib import Path
from scripts.build_g15_gate21_report import calculate,PDF_SHA
ROOT=Path(__file__).resolve().parents[1]
REG=ROOT/"registry/g15-chapter03-method.v0.1.json"
SCHEMA="jp.structural.g15.chapter03.method_execution.v0.1"

def build():
    reg=json.loads(REG.read_text(encoding="utf-8"))
    if reg["schema"]!="jp.structural.g15.chapter03.procedure_source.v0.1":
        raise ValueError("Method registry schema incorrect")
    if reg["original"]["sha256"]!=PDF_SHA or len(reg["methodology"])!=12:
        raise ValueError("Original source identity or stage count wrong")
    if len({x["id"] for x in reg["methodology"]})!=12:
        raise ValueError("Nonunique method stage IDs")
    if reg["acceptance_policy"]["F3"]!="NOT SAFE IN ONE WAY SHEAR":
        raise ValueError("Original unsafe footing verdict cannot change")
    g,forces=calculate() # ACTUAL OpenSees solved cases, not source ETABS results
    if g["case_count"]!=5 or len(forces)!=825 or g["signed_end_action_count"]!=825:
        raise ValueError("Real OpenSees signed calculation invariant failed")
    if g["counts"]["nodes"]!=92 or g["counts"]["members"]!=165:
        raise ValueError("Provisional topology changed without revised source audit")
    if g["engineering_approval"] or g["model_ETABS_source_verified"] or g["source_actual_mass_composition_verified"]:
        raise ValueError("False physical engineering approval")
    if g["F3_verdict"]!="NOT SAFE IN ONE WAY SHEAR":
        raise ValueError("Unsafe F3 finding disappeared")
    labels=["GRAVITY","EQ_PLUS_X","EQ_MINUS_X","EQ_PLUS_Y","EQ_MINUS_Y"]
    if [x["name"] for x in g["cases"]]!=labels:
        raise ValueError("Unexpected solved cases")
    if any(c["force_residual_kN"]>=.001 or c["moment_residual_kNm"]>=.001 for c in g["cases"]):
        raise ValueError("OpenSees global equilibrium failed")
    max_axial=max(abs(float(v[k])) for v in forces for k in ("Ni","Nj"))
    max_shear=max(abs(float(v[k])) for v in forces for k in ("Vyi","Vzi","Vyj","Vzj"))
    max_moment=max(abs(float(v[k])) for v in forces for k in ("Myi","Mzi","Myj","Mzj"))
    max_torsion=max(abs(float(v[k])) for v in forces for k in ("Ti","Tj"))
    if not all(math.isfinite(x) for x in (max_axial,max_shear,max_moment,max_torsion)):
        raise ValueError("Nonfinite physical signed local force")
    stage_ids=[x["id"] for x in reg["methodology"]]
    assert stage_ids==["M"+str(i).zfill(2) for i in range(1,13)]
    stages=[{**stage,"physical_building_accepted":False,
       "source_document_section":reg["original"]["section"]} for stage in reg["methodology"]]
    observed={
       "solver_name":g["solver"],"model_state":g["model_state"],
       "nodes":g["counts"]["nodes"],"members":g["counts"]["members"],
       "case_count":g["case_count"],"case_labels":labels,
       "signed_member_end_action_records":len(forces),
       "signed_local_components_per_record":12,
       "max_equilibrium_force_residual_kN":max(c["force_residual_kN"] for c in g["cases"]),
       "max_equilibrium_moment_residual_kNm":max(c["moment_residual_kNm"] for c in g["cases"]),
       "max_roof_displacement_mm_provisional":max(c["roof_max_mm"] for c in g["cases"]),
       "max_abs_member_axial_kN":max_axial,
       "max_abs_member_shear_kN":max_shear,
       "max_abs_member_bending_kNm":max_moment,
       "max_abs_member_torsion_kNm":max_torsion,
       "floor_weight_kN_conditional":g["ESM"]["W_kN"],
       "floor_force_base_shear_kN_conditional":g["ESM"]["V_kN"],
       "model_grid_SHA256":g["grid_SHA256"],"solver_request_SHA256":g["request_SHA256"],
       "result_scope":"FIVE_REAL_OPENSEES_STATIC_CASES_ON_PROVISIONAL_FRAME"
    }
    # Source-enforced missing physical capabilities: modal, P-delta, design and full combinations
    for field in ("modal_performed","p_delta_performed","member_rebar_design_performed",
                  "ULS_SLS_design_combinations_performed","real_slab_and_wall_assignments_verified"):
        if g[field] is not False:
            raise ValueError("Unapproved scope changed: "+field)
    return {
       "schema":SCHEMA,"source_pdf_sha256":PDF_SHA,"original_report_section":"3.0",
       "original_programs":reg["original_programs"],"original_member_schedule":reg["original_member_schedule"],
       "source_code_citation_conflicts":reg["original_code_notes"],
       "reported_SBC_kPa":reg["source_soil"]["reported_SBC_kPa"],
       "reported_settlement_mm":reg["source_soil"]["reported_settlement_mm"],
       "source_geotechnics_authenticated":False,
       "stages":stages,"real_OpenSees_numerical_snapshot":observed,
       "model_provenance":g["provenance"],
       "original_native_ETABS_model_authenticated":False,
       "source_floor_loads_and_mass_authenticated":False,
       "actual_structural_member_design_completed":False,
       "accepted_engineering_method_stages":0,
       "source_gates_open":g["source_gates_open"],
       "original_F3_one_way_shear":"NOT SAFE IN ONE WAY SHEAR",
       "engineering_approval":False,
       "reference_artifacts":[
          "reports/g15-gate21-calculation-report.html",
          "reports/g15-gate21-report.v0.1.json",
          "reports/g15-gate21-signed-member-actions.csv",
          "reports/g15-gate21-manifest.json"
       ],
       "limitations":"Source report methodology mapped and prototype solved; not a verified design calculation for the original building."
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="site/data/g15-chapter03-method.v0.1.json")
    args=p.parse_args()
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    data=build();out.write_text(json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
    snapshot=data["real_OpenSees_numerical_snapshot"]
    print("CHAPTER3_REAL_OPENSEES_METHOD_CROSSWALK_PASS",
          len(data["stages"]),snapshot["case_count"],snapshot["signed_member_end_action_records"],
          "SOURCE_GATES",data["source_gates_open"],"NOT_APPROVED")
if __name__=="__main__":
    main()
