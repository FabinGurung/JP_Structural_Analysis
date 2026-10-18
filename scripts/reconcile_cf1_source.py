#!/usr/bin/env python3
"""CF1 source numerical reconstruction — NOT a validated client footing.

Original revised report §6.4.1 gives two loads 46/409 kN and separation
1.50m, stated property-line distance for A 0.45m, footing 4.0m by 1.5m,
total including assumed footing weight 501kN, concrete M20 and Fe500,
top and bottom Ø16/150. We ASSUME x_A=.45m is column CENTRE from left
edge, x_B=1.95m, Wf=46kN distributed uniformly. These assumptions must be
source-plan validated. The section has no established soil contact test.
"""
from __future__ import annotations
import math,json,argparse
from pathlib import Path
from jp_structural.solvers.native.rc_report_kernels import (
    is456_combined_footing_rigid_contact,
)
def build():
    source={
        "report":"new nbc2025 report REVISED(1).pdf",
        "section":"6.4.1 COMBINED FOOTING / CF1",
        "column_service_loads_kN":[46,409],
        "distance_between_columns_m":1.5,
        "distance_column_A_to_property_line_m":0.45,
        "footing_length_m":4.0,"footing_width_m":1.5,
        "stated_total_load_including_self_weight_kN":501,
        "stated_allowable_bearing_kPa":160,
        "concrete_fck_MPa":20,"steel_fy_MPa":500,
        "report_bar_diameter_mm":16,"report_bar_spacing_mm":150,
    }
    As=math.pi*(16**2)/4*(1000/150)
    calculation=is456_combined_footing_rigid_contact(
       length_mm=4000,breadth_mm=1500,
       column_loads=[
          {"x_from_left_mm":450,"service_load_kN":46},
          {"x_from_left_mm":1950,"service_load_kN":409},
       ],
       uniform_footing_weight_kN=46,allowable_soil_pressure_kPa=160,
       load_factor=1.5,footing_depth_mm=450,effective_depth_mm=392,
       top_Ast_mm2_per_m=As,bottom_Ast_mm2_per_m=As,
       fck_MPa=20,fy_MPa=500,
       layout_source_id="PROVISIONAL_CF1_A_COLUMN_CENTRE_ASSUMED_AT_PROPERTY_LINE_OFFSET")
    return {
      "schema":"jp.structural.cf1_source_reconstruction.v0.1",
      "source":source,
      "assumptions":[
        "Column-A centre placed at x=0.45m from left despite property-line distance ambiguity.",
        "Column-B centre at x=0.45+1.50=1.95m from left.",
        "46kN distributed footing/backfill load derives as 501-(46+409), not independently weighed.",
        "Service SBC=160kPa is reproduced from old report, NOT approved from site tests.",
        "ULS multiplier 1.5 is historical assumed illustration, not a verified NBC105:2025 governing combination.",
        "d=392mm from 450mm thickness is an assumption; no independent effective-cover/bar stack proof.",
        "Linear full-contact soil only; punching, one-way shear, joint transfer and settlement remain mandatory checks."
      ],
      "results":calculation,
      "engineering_approval":False,
      "client_project_result":False,
      "status":"CF1_SOURCE_HYPOTHESIS_NUMERIC_EQUILIBRIUM_ONLY"
    }
def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(build(),sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("CF1_EQUILIBRIUM_AND_FLEXURE_BOUNDED",a.output)
if __name__=="__main__":main()
