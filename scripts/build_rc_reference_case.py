#!/usr/bin/env python3
"""Deterministic, explicit-assumption numerical RC reference; not a client design."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from jp_structural.solvers.native.rc_report_kernels import (
    nbc_capacity_design_beam_shear,is456_biaxial_column,nbc_joint_shear,
    is456_centered_isolated_footing,
)
def build():
    beam=nbc_capacity_design_beam_shear(
        span_mm=6000,gravity_shear_a_kN=65,gravity_shear_b_kN=60,
        analysis_shear_a_kN=100,analysis_shear_b_kN=95,
        sway_right_moment_a_kNm=105,sway_right_moment_b_kNm=95,
        sway_left_moment_a_kNm=100,sway_left_moment_b_kNm=90,
        moment_capacity_source_id="ASSUMED_105_95_100_90_KNM_NO_MEMBER_FE_VALIDATION")
    column=is456_biaxial_column(
        width_mm=400,depth_mm=500,fck_MPa=25,fy_MPa=415,
        Ast_mm2=5538,Pu_kN=1475,Mux_kNm=252,Muy_kNm=29.5,
        Mux1_kNm=272,Muy1_kNm=340,
        clear_height_mm=2500,effective_length_x_mm=2500,effective_length_y_mm=2500,
        uniaxial_capacity_source_id="IITGN-WB-EQ06-P23-SP16-CHART-NOT_ACTUAL_BUILDING")
    joint=nbc_joint_shear(
        confinement_faces="THREE",framing="INTERIOR",fck_MPa=25,fy_MPa=415,
        joint_breadth_mm=400,joint_width_mm=400,
        Ast_top_mm2=804,Ast_bottom_mm2=603,column_shear_kN=100,
        joint_geometry_source_id="ASSUMED_400x400_JOINT_NO_PROJECT_CORRELATION")
    footing=is456_centered_isolated_footing(
        B_mm=2100,L_mm=2100,D_mm=450,d_x_mm=392,d_y_mm=392,
        column_b_mm=400,column_l_mm=400,fck_MPa=25,fy_MPa=415,
        Ast_x_mm2_per_m=1000,Ast_y_mm2_per_m=1000,
        P_service_kN=571,P_ultimate_kN=856.5,
        allowable_soil_kPa=160,
        soil_assumption_source_id="ASSUMED_REFERENCE_160KPA_NOT_SITE_BOREHOLE")
    return {
        "schema":"jp.structural.rc_assumed_reference.v0.1",
        "case_id":"ASSUMED-RC-CALC-001",
        "status":"MATHEMATICAL_REFERENCE_ONLY_NOT_AN_ENGINEER_APPROVAL",
        "engineering_approval":False,"client_project_result":False,
        "source_urls":{
            "NBC105_2025":"https://ebps.kathmandu.gov.np/UploadFiles/NBC_105_2025_Sesmic_Design.pdf",
            "IS456_2000":"https://wriddodoti.gov.np/uploads/blog/20230331071217_IS-456-with-all-ammendments.pdf",
            "IITGN_Example":"https://www.iitk.ac.in/nicee/IITGN-WB/EQ06.pdf"},
        "assumptions":{
            "beam":"Span 6m; end moment capacity strengths (105/95/100/90 kNm), FE and gravity shears are synthetic.",
            "column":"400x500mm, 5538mm2 steel, P1475kN, Mx252/My29.5kNm and SP16 Mux1=272/Muy1=340kNm from IIT example; clear/effective lengths 2500mm are assumed.",
            "joint":"400x400mm effective joint dimensions, three-face confinement, Ast top/bottom and shear are synthetic, not project-matched.",
            "footing":"2.1x2.1m footing, 400mm square column, D450/d392mm, service 571kN, factored 856.5kN, 1000mm2/m each way and allowable 160kPa are a test scenario, NOT verified F3 footing or soil.",
            "exclusions":"No unified real project, no checked building geometry, actual soil tests, approved source member actions, settlement, ductility confinement, full column section strength, or bar anchorage."
        },
        "results":{"M08_capacity_shear":beam,"M09_biaxial_PMM":column,
                   "M10_joint_shear":joint,"M12_isolated_footing":footing},
        "historical_unsafe_F3_flag":"PRESERVED_UNRESOLVED_UNSAFE_NOT_OVERRIDDEN_BY_ASSUMED_EXAMPLE",
    }
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    out=build()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf8")
    print("ASSUMED_RC_REFERENCE_PASS_NOT_ENGINEERING_APPROVAL",a.output)
if __name__=="__main__":main()
