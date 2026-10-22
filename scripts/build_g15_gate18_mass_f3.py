#!/usr/bin/env python3
"""Gate18: independently reconcile printed ETABS storey mass arithmetic and guard F3.

The source report's mass table lacks an explicit unit. Assuming its MASS X or Y
values are in kg yields exact reported seismic W under standard g=9.80665 m/s2.
This does NOT identify ETABS mass-source inputs, element load contributions,
the actual storey diagram, or verify that mass units are kg.
F3 source remains one-way SHEAR UNSAFE; hypothetical comparisons never pass
design acceptance, even if a simplified isolated-footing kernel returns PASS.
"""
from __future__ import annotations
import argparse,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_g15_gate17_source_audit import build as gate17
from scripts.reconcile_f3_source import build as f3
from jp_structural.solvers.native.rc_report_kernels import is456_centered_isolated_footing

REG=ROOT/"registry/g15-gate18-report-mass-f3-source.v0.1.json"

def build():
    d=json.loads(REG.read_text(encoding="utf-8"))
    source=d["source_mass_table"]
    orig=gate17()
    source_f3=f3()
    assert d["source_pdf"]["sha256"]==orig["source_pdf_sha256"]
    assert source["units_explicitly_printed"] is False
    assert orig["source_mass_reconciled"] is False
    assert source_f3["status"]=="FAIL_SOURCE_UNSAFE_DO_NOT_ADOPT"
    g=source["g_m_s2_for_inference"]
    rows=[]
    for item in source["reported_stories"]:
        w=item["printed_mass_value"]*g/1000
        rows.append({"storey":item["storey"],"reported_mass_number":item["printed_mass_value"],
          "conditional_assumption":"KILOGRAMS_INFERRED_NOT_PRINTED",
          "conditional_seismic_W_kN":w,"source_mass_element_components_verified":False})
    inferred_total=math.fsum(q["conditional_seismic_W_kN"] for q in rows)
    reported=source["etabs_weight_kN"]
    error=reported-inferred_total
    # Source prints each of 3 masses to 0.01, W to 0.0001.
    # The implied tolerance follows strictly from those source display resolutions.
    tolerance=(len(rows)*.005*g/1000)+.00005
    assert abs(error)<=tolerance,(error,tolerance)
    base_mass=source["base_entry"]["printed_mass_value"]
    with_base=(math.fsum(x["reported_mass_number"] for x in rows)+base_mass)*g/1000
    assert abs(with_base-reported)>100
    remaining={
      "trial_G08_not_source_reconciled_kN":orig["gap_scenarios"][0]["trial_kN"],
      "G08_vs_source_difference_kN":orig["gap_scenarios"][0]["unexplained_kN"],
      "trial_G10_EDGE_COMM_not_source_reconciled_kN":orig["gap_scenarios"][1]["trial_kN"],
      "G10_vs_source_difference_kN":orig["gap_scenarios"][1]["unexplained_kN"],
      "source_floor_weights_from_table_not_assigned_to_provisional_slab_objects":True}
    footing=source_f3["source_extraction"]
    assert source_f3["source_extraction"]["source_f3_one_way_shear_flag"]==d["f3_source"]["as_issued_one_way_shear_verdict"]
    assert d["f3_source"]["sheet_effective_depth_d_mm"]>source_f3["reconciliation"]["missing_source_effective_depth_mm_assumed"]
    assert d["f3_source"]["sheet_one_way_nominal_shear_rounded_MPa"]==d["f3_source"]["sheet_one_way_permissible_shear_rounded_MPa"]
    area_steel=math.pi*12**2/4*1000/150
    # Sensitivities are NEVER design alternatives or construction advice:
    # use source P=571 and an explicitly hypothetical 25kN/m3 selfweight
    # and 1.5 factor on that subtotal, with original plan kept fixed.
    options=[]
    for D in (450,500,550,600):
        B=L=2100
        d_eff=D-56
        kN_self=25*(B/1000)*(L/1000)*(D/1000)
        Pservice=footing["source_axial_kN"]+kN_self
        Pult=1.5*Pservice
        res=is456_centered_isolated_footing(
          B_mm=B,L_mm=L,D_mm=D,d_x_mm=d_eff,d_y_mm=d_eff,
          column_b_mm=footing["source_column_width_mm"],
          column_l_mm=footing["source_column_width_mm"],fck_MPa=20,fy_MPa=500,
          Ast_x_mm2_per_m=area_steel,Ast_y_mm2_per_m=area_steel,
          P_service_kN=Pservice,P_ultimate_kN=Pult,
          allowable_soil_kPa=160,
          soil_assumption_source_id="SOURCE_QUOTED_SBC_160_KPA_NOT_VERIFIED_GEOTECHNICS")
        options.append({
          "trial_overall_thickness_mm":D,
          "assumed_min_effective_depth_mm":d_eff,
          "assumed_plan_mm":[B,L],
          "hypothetical_footing_selfweight_kN":kN_self,
          "service_P_assumed_kN":Pservice,
          "ultimate_P_assumed_kN":Pult,
          "service_bearing_kPa":res["service_pressure_kPa"],
          "ultimate_soil_pressure_kPa":res["factored_pressure_kPa"],
          "oneway_tau_v_MPa":[v["tau_v_MPa"] for v in res["axis_checks"]],
          "oneway_tau_c_MPa":[v["tau_c_MPa"] for v in res["axis_checks"]],
          "numeric_checks":res["checks"],
          "kernel_only_status":res["status"],
          "redesign_accepted":False,
          "source_f3_fail_override_prohibited":True
        })
    assert len(options)==4 and all(not x["redesign_accepted"] for x in options)
    return {
      "schema":"jp.structural.g15.gate18.story_mass_and_f3_safety.v0.1",
      "source_report_sha256":d["source_pdf"]["sha256"],
      "source_report_reference":{"mass_pdf_page":34,"auto_seismic_pdf_page":25,"F3_pdf_page":61},
      "reported_mass_table_units_printed":False,
      "kilograms_inferred_not_native_ETABS_verified":True,
      "source_aggregate_mass_arithmetic_consistent_given_kg_and_standard_g":True,
      "conversion_gravity_m_s2":g,
      "source_three_storey_sum_reported_mass_number":math.fsum(x["reported_mass_number"] for x in rows),
      "source_floor_conditional_weights":rows,
      "source_report_ETABS_seismic_W_kN":reported,
      "reconstructed_from_story_table_W_kN":inferred_total,
      "reported_minus_story_table_W_kN":error,
      "max_rounding_bound_kN":tolerance,
      "source_base_mass_number":base_mass,
      "base_mass_conditional_equivalent_kN":base_mass*g/1000,
      "weight_including_base_mass_kN":with_base,
      "base_mass_excluded_from_reproduced_total":True,
      "base_mass_actual_ETABS_mass_source_exclusion_setting_verified":False,
      "source_story_masses_explain_reported_total_not_gravity_composition":True,
      "ETABS_source_mass_settings_observed":False,
      "actual_slab_and_wall_assignments_observed":False,
      "mass_source_reconciled":False,
      "older_trial_composition_gap_remains_unresolved":remaining,
      "f3_source_explicit_verdict":"NOT SAFE IN ONE WAY SHEAR",
      "f3_source_sheet_effective_depth_mm":d["f3_source"]["sheet_effective_depth_d_mm"],
      "f3_prior_reconstruction_assumed_depth_mm":d["f3_source"]["reconstruction_previous_assumed_d_mm"],
      "f3_source_displayed_shear_stresses_coarsely_rounded":True,
      "f3_source_worksheet_vs_reconstruction_input_depth_conflict":True,
      "f3_source_load_factor_selfweight_inconsistency_preserved":True,
      "f3_current_design_accepted":False,
      "f3_hypothetical_depth_screen_is_NOT_redesign":True,
      "f3_hypothetical_depth_trials":options,
      "f3_actual_geotechnics_verified":False,
      "native_ETABS_model_identified_for_this_building":False,
      "engineering_approval":False,
      "roadmap_next":[
        "Obtain this building's ETABS EDB/E2K mass source and storey-mass unit settings to confirm conditional kg inference",
        "Map source mass by level and component from authenticated material/area/line/load assignments; keep older 715-772 kN composition gaps as open",
        "Obtain F3 geotechnics, foundation detail and load combinations and perform redesigned one-way/two-way shear, flexure, punching and settlement",
        "After P0, perform verified diaphragm, NBC drift, second-order P-Delta and signed ULS/SLS design checks"
      ]
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    d=build();a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(d,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("GATE18_CONDITIONAL_STORY_MASS_MATCH_AND_UNSAFE_F3",d["reported_minus_story_table_W_kN"],d["max_rounding_bound_kN"])

if __name__=="__main__":main()
