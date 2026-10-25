#!/usr/bin/env python3
"""Original PDF Chapter 2.6.4–2.8 numeric audit: source-conditional, never physical approval."""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
from jp_structural.solvers.native.equivalent_lateral import empirical_period
from jp_structural.solvers.native.nbc105_2025_esm import (
 design_coefficients,equivalent_static_floor_forces,period_exponent)
from jp_structural.solvers.native.load_combinations import generate_load_combinations
ROOT=Path(__file__).resolve().parents[1]
def build():
 d=json.loads((ROOT/"registry/g15-chapter02-seismic-facts.v0.1.json").read_text())
 mass=json.loads((ROOT/"registry/g15-gate18-report-mass-f3-source.v0.1.json").read_text())
 assert d["schema"]=="jp.structural.g15.chapter02.seismic_wind_combination_facts.v0.1"
 assert d["source"]["sha256"]==mass["source_pdf"]["sha256"]
 assert d["holds"]["source_F3_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"
 assert not d["holds"]["engineering_approval"] and not d["seismic"]["native_source_mass_verified"]
 s=d["seismic"]
 h=s["height_m"]
 period=empirical_period(h,s["empirical_period_coefficient_kt"],
                          s["empirical_period_exponent"],s["empirical_period_amplification"])
 ch=s["source_spectral_shape_factor"]
 elastic=ch*s["source_z"]*s["source_importance"]
 cs=elastic*s["source_sls_spectral_scale"]
 design=design_coefficients(elastic_horizontal_C=elastic,
                            ductility_Rmu=s["source_ductility_Rmu"],
                            overstrength_ULS=s["source_overstrength_ULS"],
                            elastic_SLS_Cs=cs,overstrength_SLS=s["source_overstrength_SLS"])
 wsource=s["source_reported_seismic_weight_kN"]
 g=mass["source_mass_table"]["g_m_s2_for_inference"]
 story_values=mass["source_mass_table"]["reported_stories"]
 floor_weights=[x["printed_mass_value"]*g/1000 for x in story_values]
 heights=[3.048,6.096,9.144]
 assert math.isclose(math.fsum(floor_weights),wsource,abs_tol=.001)
 assert period_exponent(s["reported_period_seconds"])==1
 assert math.isclose(design["ULS"],.13125,abs_tol=1e-14)
 assert math.isclose(design["SLS"],.126,abs_tol=1e-14)
 rounded_uls=s["source_reported_uls_coefficient_rounded"]
 rounded_sls=s["source_reported_sls_coefficient_rounded"]
 c_uls=equivalent_static_floor_forces(floor_weights_kN=floor_weights,
    floor_heights_m=heights,period_seconds=s["reported_period_seconds"],
    design_coefficient=rounded_uls)
 c_sls=equivalent_static_floor_forces(floor_weights_kN=floor_weights,
    floor_heights_m=heights,period_seconds=s["reported_period_seconds"],
    design_coefficient=rounded_sls)
 source_uls_shear=rounded_uls*wsource
 source_sls_shear=rounded_sls*wsource
 assert math.isclose(source_uls_shear,s["source_printed_base_shear_ULS_kN"],abs_tol=.0001)
 assert math.isclose(source_sls_shear,s["source_printed_base_shear_SLS_kN"],abs_tol=.0001)
 assert not d["wind"]["wind_load_computed"] and not d["soft_storey"]["original_claim_independently_accepted"]
 comb=d["combinations"]
 for expr in ("1.2DL+1.5LL","1.2DL+0.5LL+S","DL+lambda LL ± E","0.9DL ± E"):
  assert expr in comb["parallel_report_expressions"]
 hypothetical=generate_load_combinations(comb["unit_case_for_kernel_benchmark"])
 assert hypothetical["lsm_parallel"]["1_2DL_plus_1_5LL"]==195
 assert hypothetical["lsm_parallel"]["DL_plus_lambdaLL_pm_E"]==[95.,135.]
 assert not comb["original_load_patterns_authenticated"]
 assert len(d["open_tasks"])==6
 return {
 "schema":"jp.structural.g15.chapter02.seismic_wind_combinations_audit.v0.1",
 "original_pdf_sha256":d["source"]["sha256"],
 "inputs_source_label":"SOURCE_REPORTED_PLUS_CONDITIONAL_KG_INFERENCE_NO_NATIVE_ETABS_MASS_PATH",
 "source_summary":{
   "reported_period_s":s["reported_period_seconds"],
   "empirical_formula_period_s":period,
   "reported_spectral_shape":ch,
   "elastic_C_computed":elastic,
   "SLS_Cs_computed":cs,
   "formula_ULS_coefficient_unrounded":design["ULS"],
   "source_ULS_coefficient_printed":rounded_uls,
   "formula_SLS_coefficient":design["SLS"],
   "source_SLS_coefficient_printed":rounded_sls,
   "coefficient_rounding_ULS_difference":design["ULS"]-rounded_uls,
   "base_shear_source_reported_ULS_kN":s["source_printed_base_shear_ULS_kN"],
   "base_shear_rounded_source_coefficient_kN":source_uls_shear,
   "base_shear_unrounded_formula_kN":design["ULS"]*wsource,
   "base_shear_difference_solely_coefficient_rounding_kN":(design["ULS"]-rounded_uls)*wsource,
   "base_shear_source_reported_SLS_kN":s["source_printed_base_shear_SLS_kN"],
   "base_shear_SLS_formula_kN":source_sls_shear,
   "source_period_distribution_exponent":period_exponent(s["reported_period_seconds"]),
   "mass_story_units_inferred_not_printed":True,
   "ETABS_source_mass_composition_verified":False,
   "location_hazard_verified":False,
   "accidental_eccentricity_ratio_reported":s["source_accidental_eccentricity_ratio_reported"],
   "accidental_eccentricity_applied_in_numeric_distribution":False
 },
 "source_conditional_floor_weights_and_forces":[
    {"story":x["storey"],"height_m":heights[i],
     "conditional_mass_value_kg_if_inference_correct":x["printed_mass_value"],
     "conditional_weight_kN":floor_weights[i],
     "ULS_lateral_force_kN":c_uls["floor_forces_kN"][i],
     "SLS_lateral_force_kN":c_sls["floor_forces_kN"][i],
     "original_ETABS_story_mass_verified":False,
     "accepted_load_target_object_id":None}
    for i,x in enumerate(story_values)],
 "balanced_distribution_by_inferred_floor_weights_kN":{
    "ULS":c_uls["base_shear_kN"],"SLS":c_sls["base_shear_kN"],
    "ULS_floor_force_sum_kN":math.fsum(c_uls["floor_forces_kN"]),
    "SLS_floor_force_sum_kN":math.fsum(c_sls["floor_forces_kN"]),
    "not_accepted_as_real_model_loading":True},
 "wind_screen":{"source_statement":d["wind"]["original_claim"],"wind_dominance_proven":False,
    "wind_load_computed":False,"engineering_status":"HOLD_NO_WIND_PRESSURE_OR_LOAD_COMPARISON"},
 "soft_storey_screen":{"source_statement":d["soft_storey"]["original_claim"],
    "actual_story_stiffnesses_verified":False,"engineering_status":"HOLD_NO_VERIFIED_STORY_STIFFNESS"},
 "parallel_combination_expressions":comb["parallel_report_expressions"],
 "lambda_documented":{"storage":comb["reported_lambda_for_storage"],"other":comb["reported_lambda_other"]},
 "synthetic_load_combination_fixture":{"input_status":"SYNTHETIC_NUMERICAL_BENCHMARK_NOT_SOURCE_PROJECT_DEMAND",
      "scalar_inputs":comb["unit_case_for_kernel_benchmark"],"result":hypothetical,
      "actual_project_member_or_case_ID":None},
 "open_tasks":d["open_tasks"],"physical_evidence_accepted":False,
 "project_signed_demand_envelope_generated":False,
 "source_mass_reconciled":False,"source_geometry_verified":False,
 "source_f3_verdict":"NOT SAFE IN ONE WAY SHEAR",
 "engineering_approval":False
 }
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--output",default="site/data/g15-chapter02-seismic-audit.v0.1.json")
 a=p.parse_args()
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 d=build();out.write_text(json.dumps(d,sort_keys=True,indent=2)+"\n")
 print("CHAPTER2_SEISMIC_WIND_SOFTSTOREY_COMBINATION_AUDIT_PASS",
       len(d["source_conditional_floor_weights_and_forces"]),len(d["open_tasks"]),
       "ULS",round(d["source_summary"]["base_shear_rounded_source_coefficient_kN"],4),
       "SLS",round(d["source_summary"]["base_shear_SLS_formula_kN"],4),"NO_APPROVAL")
if __name__=="__main__":main()
