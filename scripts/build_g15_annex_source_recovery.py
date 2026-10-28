#!/usr/bin/env python3
"""Annex evidence-recovery planning and original F3 geometry sensitivity.

No material properties, footing alternatives or original ETABS assignments are
authenticated. Sole mechanical result: a concentric uniform-pressure DEMAND
proxy under two source-reported vertical-load interpretations. NOT a design.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_g15_gate20_crosswalk import build as gate20
from scripts.build_g15_chapter06_source_design import build as chapter06

REG=ROOT/"registry/g15-annex-source-recovery.v0.1.json"
PDF_SHA="f122904444a2e2f75230d9d4e41da0093d050da25c6e8140c86d466b7e37cc52"
SCHEMA="jp.structural.g15.annex.source_recovery_f3_demand_sensitivity.v0.1"

def demand(q_kPa,B_m,column_m,d_mm):
    d_m=d_mm/1000
    cantilever=max((B_m-column_m)/2-d_m,0)
    # pressure [kN/m2] x cantilever [m] / d [m] -> kPa -> MPa.
    tau_MPa=q_kPa*cantilever/d_m/1000
    return {"cantilever_outside_d_m":cantilever,"one_way_uniform_pressure_stress_MPa":tau_MPa}

def build():
    r=json.loads(REG.read_text(encoding="utf-8"))
    assert r["schema"]=="jp.structural.g15.annex.source_evidence_strategy.v0.1"
    assert r["source_pdf"]["sha256"]==PDF_SHA
    g=gate20()
    ch=chapter06()
    assert ch["source_acceptance_count"]==0 and g["accepted_gate_count"]==0
    assert len(g["gates"])==15
    assert g["f3"]["source_verdict"]=="NOT SAFE IN ONE WAY SHEAR"
    x=r["f3_scenario_definition"]
    source_f3=ch["section6_4_footing"]["F3_printed"]
    assert x["base_B_m"]==source_f3["size_mm"][0]/1000
    assert x["source_D_mm"]==source_f3["D_mm"]
    assert x["source_d_mm"]==source_f3["d_mm"]
    assert x["source_axial_kN"]==source_f3["axial_kN"]
    assert x["printed_one_way_tau_MPa_rounded"]==.2
    assert x["source_soil_allowable_kPa_unverified"]==source_f3["printed_SBC_kPa"]
    assert len(set(r["evidence_recovery"]["priority_order"]))==15
    all_ids={o["id"] for o in g["gates"]}
    assert set(r["evidence_recovery"]["priority_order"])==all_ids

    plans=[]
    for B in x["chosen_plan_m"]:
        for D in x["chosen_dimensions_mm"]:
            d=D-x["cover_scenario_mm"]-x["bar_diameter_mm"]/2
            q_axial=x["factor_for_source_arithmetic"]*x["source_axial_kN"]/B**2
            q_incl=x["factor_for_source_arithmetic"]*x["source_axial_including_selfweight_kN"]/B**2
            d_axial=demand(q_axial,B,x["source_column_m"],d)
            d_incl=demand(q_incl,B,x["source_column_m"],d)
            plans.append({"scenario_id":f"SCENARIO_B{int(round(B*1000))}_D{int(D)}",
              "plan_B_and_L_m":B,"overall_D_mm":D,
              "cover_based_effective_d_mm":d,"source_original_footing_geometry":B==2.1 and D==450,
              "q_1p5_axial_571_kPa":q_axial,
              "q_1p5_reported_total_600_kPa":q_incl,
              "reported_total_service_q_kPa":x["source_axial_including_selfweight_kN"]/B**2,
              "base_source_160kPa_number_used_as_verified_soil_strength":False,
              "axial_only_demand":d_axial,"includes_600_demand":d_incl,
              "comparison_to_rounded_0p2MPa":("BELOW_PRINTED_ROUNDED_NUMBER" if d_incl["one_way_uniform_pressure_stress_MPa"]<.2 else "ABOVE_PRINTED_ROUNDED_NUMBER"),
              "true_one_way_shear_strength_determined":False,
              "punching_bending_settlement_and_rebar_anchorage_verified":False,
              "design_pass":False,"engineering_approval":False})
    assert len(plans)==12
    # Distinct as-reported effective-depth sensitivity never becomes a
    # geometric or reinforcement certification.
    q0=x["factor_for_source_arithmetic"]*x["source_axial_kN"]/x["base_B_m"]**2
    src_depth=demand(q0,x["base_B_m"],x["source_column_m"],x["source_d_mm"])
    cover_depth=demand(q0,x["base_B_m"],x["source_column_m"],
                        x["source_D_mm"]-x["cover_scenario_mm"]-x["bar_diameter_mm"]/2)
    assert src_depth["one_way_uniform_pressure_stress_MPa"]<cover_depth["one_way_uniform_pressure_stress_MPa"]
    assert all(not y["design_pass"] for y in plans)

    gates=[]
    for o in g["gates"]:
        name=o["id"]
        refs=(["NBC105_2025","IS456_2000","NEPAL_STRUCTURAL_GUIDANCE"]
              if name.startswith("G20-F3") else ["NBC105_2025"] if o["domain"] in ("DESIGN","MASS","GEOMETRY") else ["IS456_2000"])
        gates.append({"gate_id":name,"key":o["key"],"domain":o["domain"],"priority":o["priority"],
          "depends_on":o["depends_on"],"required_by_role":o["required_by_role"],
          "evidence_needed":o["evidence_needed"],"acceptance_test":o["acceptance_test"],
          "source_observation_ids":o["source_observation_ids"],
          "research_reference_ids":refs,
          "not_equivalent_to_native_source":"CODE_REFERENCE_IS_REQUIREMENT_NOT_EVIDENCE",
          "prerequisites_received":False,"independent_review_passed":False,
          "owner_study_authorized":True,
          "physical_source_acceptance":False,
          "next_step":("Recover original native model and signed object identity" if name=="G20-SRC-001"
             else "Obtain independently validated geotechnical measurements" if name=="G20-F3-012"
             else "Recover original issued drawing and reinforcement/cover evidence" if name=="G20-F3-013"
             else "Provide source proof and complete acceptance test")})
    ready=[x["gate_id"] for x in gates if not x["depends_on"]]
    assert set(ready)=={"G20-SRC-001","G20-F3-012","G20-F3-013"}

    return {"schema":SCHEMA,
      "source_original_sha256":PDF_SHA,
      "original_source_drive_id":r["source_pdf"]["id"],
      "authoritative_references":r["standards"],
      "registry_sha256":hashlib.sha256(REG.read_bytes()).hexdigest(),
      "owner_work_authorized":True,"owner_original_source_authenticated":False,
      "claim_scope":"STANDARDS_RESEARCH_PLUS_CONDITIONAL_NUMERICAL_DEMAND_SCREEN",
      "gates":gates,"gate_count":len(gates),"accepted_gate_count":0,
      "independent_evidence_starting_tasks":ready,
      "original_F3_verdict":"NOT SAFE IN ONE WAY SHEAR",
      "source_F3_axial_only_pressure_demand_at_worksheet_d_MPa":src_depth["one_way_uniform_pressure_stress_MPa"],
      "source_F3_axial_only_pressure_demand_at_cover_based_d_MPa":cover_depth["one_way_uniform_pressure_stress_MPa"],
      "source_F3_effective_depth_conflict_mm":x["source_d_mm"]-
         (x["source_D_mm"]-x["cover_scenario_mm"]-x["bar_diameter_mm"]/2),
      "scenario_inputs":x,
      "F3_sensitivity_scenarios":plans,
      "F3_sensitivity_count":len(plans),
      "comparison_is_not_a_code_design_pass":True,
      "original_ETABS_building_parity_verified":False,
      "site_soil_or_bearing_verified":False,
      "F3_replacement_approved":False,
      "engineer_signoff":False,
      "engineering_approval":False,
      "limitations":r["limitations"],
      "next_implementation_stage":"Original-model intake with SHA-256, data schema and independently verified physical load paths before site design"}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True,type=Path)
    opts=p.parse_args()
    result=build()
    opts.output.parent.mkdir(parents=True,exist_ok=True)
    opts.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("ANNEX_SOURCE_RECOVERY_15_OPEN_F3_UNSAFE_12_DEMAND_SENSITIVITIES_NO_DESIGN_PASS")
if __name__=="__main__":main()
