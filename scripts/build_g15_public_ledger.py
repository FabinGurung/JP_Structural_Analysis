#!/usr/bin/env python3
"""Generate PUBLIC de-identified, source-linked real-case calculation JOURNAL.

This artifact is a curated projection of private validated Gate02–07 records;
it does not reproduce private member grids, building plans, raw FE vectors,
names, source document bytes or location. Public source identifiers are only
opaque checksums for independent authorized readback in private Drive.
Not a building-design certificate.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"registry"/"g15-public-case-ledger.v0.2.json"

def build():
    d=json.loads(SOURCE.read_text(encoding="utf-8"))
    assert d["schema"]=="jp.structural.deidentified.project_calculation_ledger.source.v0.2"
    assert d["publication"]=="USER_REQUESTED_DEIDENTIFIED_AGGREGATE_ONLY"
    assert d["scope"]["member_count"]==d["scope"]["column_segments"]+d["scope"]["beam_segments"]
    assert d["gate05"]["case_count"]+d["gate06"]["case_count"]+d["gate07"]["case_count"]==376
    assert d["gate07"]["case_count"]==4*51
    assert len(d["workflow"])==7 and len(d["calculation_families"])>=13
    assert set(v["id"] for v in d["workflow"])=={"G02","G03","G04","G05","G06","G07","G08"}
    w=d["gravity_mass"]
    assert math.isclose(w["member_selfweight_kN"]+w["floor_added_dead_kN"]+
       w["seismic_live_share_kN"],w["gate06_reconstructed_kN"],abs_tol=.01)
    assert math.isclose(w["report_W_kN"]-w["gate06_reconstructed_kN"],
       w["gate06_gap_kN"],abs_tol=.001)
    assert math.isclose(w["wall_proxy_line_rate_kN_m"]*w["wall_proxy_length_per_level_m"]*
       w["wall_proxy_levels"],w["wall_trial_added_weight_kN"],abs_tol=1e-6)
    assert math.isclose(w["gate06_reconstructed_kN"]+w["wall_trial_added_weight_kN"],
       w["gate07_conditionally_reconstructed_kN"],abs_tol=.001)
    assert math.isclose(w["report_W_kN"]-w["gate07_conditionally_reconstructed_kN"],
       w["gate07_remaining_gap_kN"],abs_tol=.001)
    assert w["gate07_remaining_gap_kN"]>0 and w["mass_reconciled"] is False
    gate=d["gate06"];status=d["safety"]
    assert gate["case_count"]==153 and gate["signed_member_action_records"]==25245
    assert d["gate07"]["signed_action_records"]==33660
    assert all(v is False for v in status.values())
    assert d["member_checks"]["F3_source_status"]=="NOT SAFE IN ONE WAY SHEAR"
    assert d["member_checks"]["F3_repaired"] is False
    assert d["member_checks"]["C24_true_mapping_verified"] is False
    assert set(x["id"] for x in gate["stiffness"])=={"GROSS","ULS","SLS"}
    assert len(gate["eccentric_scenarios"])==8
    assert len(d["gate07"]["variants"])==4
    for v in gate["eccentric_scenarios"]:
        assert v["state"] in ("ULS","SLS")
        assert v["sign"] in ("NEG","POS") and v["axis"] in ("X","Y")
        assert v["roof_mm"]>0 and v["design_drift"]>0
        v["numerical_limit"]=gate["code_drift_limit"][v["state"]]
        v["screening_exceeds_limit"]=v["design_drift"]>v["numerical_limit"]
    for v in d["gate07"]["variants"]:
        assert v["roof_mm"]>0 and v["drift"]>0
        v["numerical_limit"]=gate["code_drift_limit"][v["state"]]
        v["screening_exceeds_limit"]=v["drift"]>v["numerical_limit"]
    assert d["gate08"]["cases"]==816 and d["gate08"]["variant_count"]==16
    assert d["gate08"]["signed_member_action_records"]==134640
    assert d["gate08"]["source_sha256"]=="37d3ab85d96953a74a773358fb9d56de1858ed163c896bb99de8e43844ee0a48"
    assert d["gate08"]["model_real_project_approved"] is False
    d["derived"]={
       "total_gate05_to_gate08_case_solves":1192,
       "total_gate05_gate06_gate07_case_solves":376,
       "gate06_mass_shortfall_pct":100*w["gate06_gap_kN"]/w["report_W_kN"],
       "conditional_gate07_mass_shortfall_pct":100*w["gate07_remaining_gap_kN"]/w["report_W_kN"],
       "conditional_wall_fraction_of_prior_shortfall_pct":100*w["wall_trial_added_weight_kN"]/w["gate06_gap_kN"],
       "maximum_gate06_ULS_screening_ratio":max(x["design_drift"] for x in gate["eccentric_scenarios"] if x["state"]=="ULS"),
       "maximum_gate06_SLS_screening_ratio":max(x["design_drift"] for x in gate["eccentric_scenarios"] if x["state"]=="SLS"),
       "private_raw_member_force_vectors_public":False,
       "professional_design_approved":False,
    }
    source_bytes=SOURCE.read_bytes()
    d["source_register_sha256"]=hashlib.sha256(source_bytes).hexdigest()
    d["schema"]="jp.structural.deidentified.project_calculation_ledger.public.v0.2"
    # Deliberate privacy fail-closed test before publishing under public Pages.
    serialized=json.dumps(d,ensure_ascii=False,sort_keys=True,allow_nan=False)
    for token in ("drive.google.com/file/d/","drive.google.com/drive/folders/","@gmail.com",
                  "Fabin Gurung","Sankalp Singh","PRIVATE_INPUT_GRID"):
        if token in serialized:
            raise ValueError("private source identifier in public journal: "+token)
    return d

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    d=build()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(d,indent=2,ensure_ascii=False,sort_keys=True,
            allow_nan=False)+"\n",encoding="utf-8")
    print("G15_REAL_SOURCE_DEIDENTIFIED_CALCULATION_LEDGER_PASS_WITH_ENGINEERING_HOLD",
          args.output,len(d["calculation_families"]),len(d["workflow"]))

if __name__=="__main__":main()
