#!/usr/bin/env python3
"""Build a full synthetic OpenSees case → signed actions → M08/M09/M10 artifact."""
import argparse
import hashlib
import json
from pathlib import Path

from jp_structural.solvers.opensees.synthetic_d2_example import case_fixture
from jp_structural.solvers.opensees.member_design_bridge import (
    solve_signed_member_cases,evaluate_m08_m09_m10,
)


def build():
    model,cases,combinations,beam,column,joint=case_fixture()
    signed=solve_signed_member_cases(model=model,cases=cases,combinations=combinations)
    checked=evaluate_m08_m09_m10(model=model,solved=signed,
        beam_bindings=beam,column_bindings=column,joint_bindings=joint)
    if not checked["beam_design"] or not checked["column_design"] or not checked["joint_design"]:
        raise RuntimeError("D2 M08/M09/M10 result missing")
    if signed["engineering_approval"] or checked["engineering_approval"]:
        raise RuntimeError("D2 report must remain engineering HOLD")
    result={
        "schema":"jp.structural.d2_m08_m09_m10_synthetic_demo.v0.1",
        "case_id":"SYNTHETIC-D2-FRAME-001",
        "provenance":"Entire case is synthetic; units kN,m,s; no client data",
        "limitations":"Elastic 3D frame, explicit nodal static cases only; no response spectrum, nonlinear hinges, signed MRSM recovery, real-source equivalence, slenderness or complete detailing",
        "signed_fe_actions":signed,
        "design_checks":checked,
        "engineering_approval":False,
        "report_accepted":False,
    }
    compact=json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False)
    result["payload_sha256"]=hashlib.sha256(compact.encode()).hexdigest()
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    result=build()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
    print("SIGNED_OPENSEES_M08_M09_M10_BUILT_NOT_APPROVED",args.output)
    for row in result["design_checks"]["column_design"]:
        print("Column governing PMM utilization",row["governing_interaction_utilization"])


if __name__=="__main__":
    main()
