#!/usr/bin/env python3
"""F3 report-source versus reconstructed footing: retain source UNSAFE flag.

The precedent revised NBC2025 structural report (private Drive original)
prints "NOT SAFE IN ONE WAY SHEAR" in the F3 worksheet, then lists IF3 in
the summary. This is a source conflict: NEVER promote the summary as safe.

Print-extracted figures: base 2100x2100 mm, approx column 360mm, thickness
450mm, M20 Fe500, 12mm dia @150mm, load P=571kN, load+selfweight=600kN,
claimed SBC=160kPa. Worksheet's 194.22kPa is 1.5*571/4.41, NOT
1.5*600/4.41. Effective depth 394mm is NOT directly authoritative;
ASSUME 50mm cover and 6mm to bar-centre (450-50-6).
Site bearing/soil, load combinations and actual bar placement UNVERIFIED.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
from jp_structural.solvers.native.rc_report_kernels import is456_centered_isolated_footing

def build():
    raw={
       "source_title":"new nbc2025 report REVISED(1).pdf",
       "source_section":"6.4.2 isolated footing F3, printed page 61-62",
       "source_f3_one_way_shear_flag":"NOT SAFE IN ONE WAY SHEAR",
       "source_adopted_schedule_label":"IF3 2100 x 2100 12mm @150mm",
       "source_column_width_mm":360,
       "source_footing_size_mm":[2100,2100],
       "source_overall_thickness_mm":450,
       "source_axial_kN":571,
       "source_axial_with_selfweight_kN":600,
       "source_claimed_SBC_kPa":160,
       "source_factored_upward_pressure_kPa":194.22,
       "source_concrete_grade_MPa":20,
       "source_steel_grade_MPa":500,
       "source_bar_diameter_mm":12,"source_bar_spacing_mm":150,
    }
    area=math.pi*12**2/4*1000/150
    reconstructed=is456_centered_isolated_footing(
        B_mm=2100,L_mm=2100,D_mm=450,d_x_mm=394,d_y_mm=394,
        column_b_mm=360,column_l_mm=360,fck_MPa=20,fy_MPa=500,
        Ast_x_mm2_per_m=area,Ast_y_mm2_per_m=area,
        P_service_kN=600,P_ultimate_kN=1.5*571,
        allowable_soil_kPa=160,
        soil_assumption_source_id="UNVERIFIED_SOURCE_CLAIM_160kPA_F3")
    source_v={ "source_reconstructed_pressure_matches":math.isclose(
                  reconstructed["factored_pressure_kPa"],194.22,rel_tol=.0001),
               "ultimate_load_factor_on_source_with_selfweight":
                  (1.5*571)/600,
               "missing_source_effective_depth_mm_assumed":394,
               "source_shear_not_safe_retained":True,
               "source_adopted_summary_is_not_design_evidence":True}
    return {"schema":"jp.structural.f3_source_conflict.v0.1",
        "status":"FAIL_SOURCE_UNSAFE_DO_NOT_ADOPT",
        "source_extraction":raw,
        "reconciliation":source_v,
        "assumptions":[
           "Effective depth 394mm is assumed from 450-50 cover-6mm bar radius.",
           "F3 uses extracted 360mm column: verify original drawing and precise footprint.",
           "Historical 1.5 factored factor and 160kPa soil claim are reproduced, not verified for NBC105:2025.",
           "Historical worksheet's one-way shear FAIL dominates any reconstructed pass.",
           "Original worksheet's load with self-weight 600kN and factored pressure use different bases.",
           "No actual geotechnical borehole, settlement verification or engineer signoff."],
        "reconstructed_numerics":reconstructed,
        "adopted_design_accepted":False,"engineering_approval":False}
def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(build(),indent=2,sort_keys=True,allow_nan=False)+"\n")
    print("F3_SOURCE_UNSAFE_PRESERVED",a.output)
if __name__=="__main__":main()
