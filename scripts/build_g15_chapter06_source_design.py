#!/usr/bin/env python3
"""Original Chapter 6: reproduce source schedule arithmetic, never invent source acceptance."""
from __future__ import annotations
import argparse,hashlib,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.reconcile_f3_source import build as source_f3
from scripts.reconcile_cf1_source import build as source_cf1
from scripts.build_g15_gate20_crosswalk import build as gate20

REGISTRY=ROOT/"registry/g15-chapter06-source-choices.v0.1.json"
PDF_SHA="f122904444a2e2f75230d9d4e41da0093d050da25c6e8140c86d466b7e37cc52"
def bar_area(count,diameter_mm):return count*math.pi*diameter_mm**2/4
def steel(bars):return sum(bar_area(n,d) for n,d in bars)
COLUMN_GROUPS=[
 ("C1","400×400",160000,["A1","A2","C1","C3","F1","F3","F6","G6","H1","H6","H3"],[[(8,16)],[(8,16)],[(8,16)]],[1.00,1.00,1.00]),
 ("C2","400×400",160000,["C2","C6"],[[(4,20),(4,16)],[(4,20),(4,16)],[(8,16)]],[1.29,1.29,1.00]),
 ("C3","400×400",160000,["G1","G3","H2","F2"],[[(8,20)],[(8,20)],[(8,20)]],[1.57,1.57,1.57]),
 ("C4","Ø350",math.pi*350**2/4,["B4","B5","D7","E7","I2","I3"],[[(8,12)],[(8,12)],[(8,12)]],[.94,.94,.94])]
SOURCE_BEAMS=[
 {"id":"GF B46","printed_section_mm":[300,400],"Mu3_kNm":-99.4853,"Vu2_kN":129.6723,"Tu_kNm":10.7597,
  "printed_top_required_As_mm2":865,"printed_bottom_required_As_mm2":432,"citation":"Original §6.2 pp49–50"},
 {"id":"GF B19","printed_section_mm":[230,406.4],"Mu3_kNm":-60.1122,"Vu2_kN":62.5668,"Tu_kNm":11.9548,
  "printed_top_required_As_mm2":576,"printed_bottom_required_As_mm2":288,"citation":"Original §6.2 pp50–51"}]
def build():
    reg=json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert reg["source_pdf"]["sha256"]==PDF_SHA
    gate=gate20()
    assert gate["source_report_sha256"]==PDF_SHA
    assert gate["accepted_gate_count"]==0 and len(gate["gates"])==15
    assert not any(x["accepted"] for x in gate["gates"])
    assert not reg["status"]["physical_source_accepted"]
    assert reg["status"]["original_F3_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"
    f3=source_f3()
    cf1=source_cf1()
    assert f3["source_extraction"]["source_f3_one_way_shear_flag"]=="NOT SAFE IN ONE WAY SHEAR"
    assert not f3["adopted_design_accepted"] and not cf1["engineering_approval"]
    column_rows=[]
    names=[]
    for mark,section,area,grids,schedules,percents in COLUMN_GROUPS:
        names+=grids
        for i,(bars,reported) in enumerate(zip(schedules,percents)):
            mm2=steel(bars);pct=100*mm2/area
            assert abs(pct-reported)<.025
            column_rows.append({"mark":mark,"level":["GROUND","FIRST","TOP"][i],
              "section":section,"nominal_bars": " + ".join(str(n)+"Ø"+str(d) for n,d in bars),
              "grid_count":len(grids),"grid_labels":grids,"computed_As_mm2":mm2,
              "computed_rho_percent":pct,"source_reported_rho_percent":reported,
              "source_percentage_difference_points":pct-reported,
              "status":"SOURCE_SCHEDULE_ARITHMETIC_ONLY",
              "original_ETABS_object_link_verified":False,
              "citations":["Original PDF §6.1.2 printed pp42–43","IS456:2000 rebar nominal area"]})
    assert len(names)==23 and len(set(names))==23 and len(column_rows)==12
    # Standalone source ETABS outputs have no proven FK to source-grid schedule.
    original_column_examples=[
      {"id":"TF C24","source_section_mm":[400,400],"Pu_kN":174.6942,
       "Mu2_kNm":-121.5281,"Mu3_kNm":-37.8202,"reported_As_mm2":2134,
       "source_rebar_ratio_percent":1.33,"recalculated_As_percent":2134/160000*100,
       "citation":"Original §6.1.1 pp39–40","schedule_link_authenticated":False},
      {"id":"GF C31","source_section_diameter_mm":350,"Mu2_kNm":-31.695,
       "Mu3_kNm":-34.7803,"reported_As_mm2":839,
       "source_rebar_ratio_percent":.87,
       "recalculated_As_percent":839/(math.pi*350**2/4)*100,
       "citation":"Original §6.1.1 pp40–41","schedule_link_authenticated":False}]
    slab={"grid_bay":"1–2–F–G","citation":"Original §6.3 printed pp54–56",
      "sample_Lx_m":3.60,"sample_Ly_m":4.97,
      "sample_D_mm":125,"general_schedule_D_mm":120,
      "sample_cover_mm":20,"bar_diameter_mm":8,"bar_spacing_mm":150,
      "computed_provided_As_mm2_per_m":bar_area(1000/150,8),
      "worksheet_selfweight_kPa":3.13,
      "computed_selfweight_for_M20_RC25_kPa":.125*25,
      "printed_dead_load_kPa":5.13,"printed_live_load_kPa":2.00,
      "computed_trial_factored_load_kPa":1.5*(5.13+2),
      "printed_factored_load_kPa":10.69,
      "source_thickness_conflict_resolved":False,
      "slab_reinforcement_approved":False}
    assert abs(slab["computed_trial_factored_load_kPa"]-slab["printed_factored_load_kPa"])<.01
    f3area=(2100/1000)**2
    f3_p=571*1.5/f3area
    scenario_d=450-50-12/2
    footing={"citation":"Original §6.4 printed pp57–63; Gate18 and F3 reconciliation",
      "F3_printed":{"size_mm":[2100,2100],"D_mm":450,"d_mm":423.46278,"bar_mm":12,
        "bar_spacing_mm":150,"selfweight_included_kN":600,"axial_kN":571,
        "printed_factored_pressure_kPa":194.22,"printed_SBC_kPa":160},
      "F3_derived":{"area_m2":f3area,"original_factored_pressure_recomputed_kPa":f3_p,
        "service_pressure_from_printed_total_kPa":600/f3area,
        "cover_based_scenario_effective_d_mm":scenario_d,
        "rebar_nominal_As_mm2_per_m":bar_area(1000/150,12),
        "worksheet_d_exceeds_cover_scenario_mm":423.46278-scenario_d},
      "F3_warning":"NOT SAFE IN ONE WAY SHEAR",
      "F3_original_schedule_accepted":False,
      "F3_soil_SBC_verified":False,
      "CF1_source_status":cf1["status"],
      "CF1_footing_length_m":4.0,"CF1_footing_width_m":1.5,
      "CF1_source_service_loads_kN":[46,409],
      "CF1_reconstructed_total_weight_kN":501,
      "CF1_selfweight_inferred_kN":501-46-409,
      "CF1_verified_in_native_ETABS":False}
    assert abs(f3_p-194.22)<.01
    assert f3["reconciliation"]["source_shear_not_safe_retained"]
    stair={"citation":"Original §6.5 physical pp63–65 (source misnumbered 6.4.1)",
      "rise_mm":170,"tread_mm":254,"width_mm":1200,
      "general_waist_mm":150,"worksheet_adopted_D_mm":127,
      "worksheet_adopted_d_mm":106,"flight_AB_reported_M_kNm":20.88,
      "flight_BC_reported_M_kNm":14.96,
      "flight_AB_reported_shear_kN":21.98,
      "flight_BC_reported_shear_kN":18.48,
      "printed_live_load_kPa":3,"printed_total_flight_kPa":11.41,
      "calculated_1_5_factored_flight_kPa":1.5*11.41,
      "reported_factored_flight_kPa":17.11,
      "printed_main_rebar_dia_mm":12,"printed_main_spacing_mm":127,
      "computed_provided_main_As_mm2_per_m":bar_area(1000/127,12),
      "printed_BC_adopted_As_mm2":995.26,
      "source_150_vs_127_depth_resolved":False,
      "staircase_flexure_shear_design_approved":False}
    return {"schema":"jp.structural.g15.chapter06.original_element_source_arithmetic.v0.1",
      "original_pdf_SHA256":PDF_SHA,"source_decisions_registry":"registry/g15-chapter06-source-choices.v0.1.json",
      "registry_SHA256":hashlib.sha256(REGISTRY.read_bytes()).hexdigest(),
      "code_references":reg["codes"],
      "section6_1_columns":{"source_schedule_rows":column_rows,
        "source_grid_count":23,"reported_ETABS_examples":original_column_examples,
        "column_moment_axial_capacity_approved":False},
      "section6_2_beams":{"source_ETABS_examples":SOURCE_BEAMS,
        "original_FEM_end_action_data_authentic":False,
        "project_beam_flexure_shear_torsion_approved":False},
      "section6_3_slab":slab,"section6_4_footing":footing,
      "section6_5_staircase":stair,
      "source_acceptance_gates":[{"id":g["id"],"status":g["status"],
         "required_by_role":g["required_by_role"],
         "evidence_needed":g["evidence_needed"],"accepted":g["accepted"]}
          for g in gate["gates"]],
      "source_acceptance_count":0,"open_source_acceptance_count":15,
      "code_standard_document_identified":True,
      "code_project_compliance_demonstrated":False,
      "native_original_ETABS_member_parity":False,
      "engineering_approval":False,"original_F3_one_way_shear":"NOT SAFE IN ONE WAY SHEAR",
      "allowed_purpose":"traceable source arithmetic and options for licensed-engineer review",
      "not_allowed_purpose":"permit, structural safety certificate, construction instructions or engineering signoff"}

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path)
    a=p.parse_args();out=build()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("CHAPTER6_23_ORIGINAL_COLUMN_GRID_NAMES_12_SCHEDULE_ROWS_F3_UNSAFE_SOURCE_GATES_15_OPEN")
if __name__=="__main__":main()
