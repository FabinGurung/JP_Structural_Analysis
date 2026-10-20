#!/usr/bin/env python3
"""Generate publicly shareable synthetic NBC 105:2025 ESM reference; NO private model."""
import argparse
import hashlib
import json
from pathlib import Path

from jp_structural.solvers.native.nbc105_2025_esm import (
    design_coefficients, equivalent_static_floor_forces,
    signed_case_combination, bounded_story_drift,
)

def build():
    # All numeric geometry and weight values below are newly invented public
    # synthetic teaching inputs, unrelated to any client's source property.
    synth={"model_id":"SYNTHETIC_ESM_REFERENCE_001",
           "description":"Three-level teaching mass-lumped building, not a client model",
           "floor_weights_kN":[400.,450.,350.],
           "floor_heights_m":[3.,6.,9.],
           "period_seconds":.4,
           "elastic_horizontal_C":.7875,
           "elastic_SLS_Cs":.1575,
           "ductility_Rmu":4.,"overstrength_ULS":1.5,
           "overstrength_SLS":1.25}
    cd=design_coefficients(
        elastic_horizontal_C=synth["elastic_horizontal_C"],
        ductility_Rmu=synth["ductility_Rmu"],
        overstrength_ULS=synth["overstrength_ULS"],
        elastic_SLS_Cs=synth["elastic_SLS_Cs"],
        overstrength_SLS=synth["overstrength_SLS"])
    cases={mode:equivalent_static_floor_forces(
        floor_weights_kN=synth["floor_weights_kN"],
        floor_heights_m=synth["floor_heights_m"],
        period_seconds=synth["period_seconds"],
        design_coefficient=cd[mode]) for mode in ("ULS","SLS")}
    combination=signed_case_combination(
        {"D":[12.,-8.,5.],"E":[20.,-15.,-9.]},
        {"D":.9,"E":-1.})
    drift={
        "ULS": bounded_story_drift(
            elastic_interstory_delta_m=.01,story_height_m=3,
            limit_state="ULS",ductility_Rmu=4),
        "SLS": bounded_story_drift(
            elastic_interstory_delta_m=.006,story_height_m=3,
            limit_state="SLS",ductility_Rmu=4)
    }
    output={"schema":"jp.structural.synthetic_nbc105_2025_esm.v0.1",
        "synthetic":True,"source":"NBC105:2025 clauses 5.2, 5.5, 5.6, 6.1–6.4",
        "model":synth,"design_coefficients":cd,
        "cases":cases,"signed_combination_demo":combination,
        "guarded_drift_checks":drift,
        "private_real_project_values_included":False,
        "safety_gates":{"effective_stiffness":False,
          "accidental_eccentricity":False,"site_Vs30_and_zoning":False,
          "source_diaphgram_and_panel_geometry":False,
          "modal_combination":False,"member_detailing":False,
          "engineer_signoff":False},
        "engineering_approval":False,"report_accepted":False,
        "status":"SYNTHETIC_BOUNDED_ESM_EQUATIONS_QA_HOLD"}
    compact=json.dumps(output,sort_keys=True,separators=(",",":"))
    output["input_output_sha256"]=hashlib.sha256(compact.encode()).hexdigest()
    return output

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    data=build()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    assert data["cases"]["ULS"]["base_shear_kN"]==157.5
    assert data["cases"]["SLS"]["base_shear_kN"]==151.2
    assert data["engineering_approval"] is False
    print("NBC105_ESM_SYNTHETIC_CASE_PASS_NOT_APPROVED",args.output)

if __name__=="__main__": main()
