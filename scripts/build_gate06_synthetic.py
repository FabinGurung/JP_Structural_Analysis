#!/usr/bin/env python3
"""Publish only new synthetic test vectors; never derive public client geometry."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from jp_structural.solvers.native.nbc105_gate06_validation import (
 effective_EI_ratios,signed_eccentric_floor_wrenches,
 reconcile_trial_seismic_weight,governing_signed_component,
)
from jp_structural.solvers.native.nbc105_2025_esm import (
 equivalent_static_floor_forces,bounded_story_drift,
)

def build():
    # All parameters are newly invented instructional values.
    example={"model_id":"SYNTH_GATE06_001",
       "plan_x_m":12.,"plan_y_m":9.,
       "floor_heights_m":[3.,6.,9.],
       "floor_seismic_weights_kN":[250.,280.,220.],
       "source_W_kN":900.,
       "member_dead_kN":250.,
       "added_floor_dead_kN":350.,
       "nonroof_imposed_load_kN":120.,
       "period_s":.42,"ULS_Cd":.13125,"SLS_Cd":.126}
    distribution={state:equivalent_static_floor_forces(
      floor_weights_kN=example["floor_seismic_weights_kN"],
      floor_heights_m=example["floor_heights_m"],
      period_seconds=example["period_s"],
      design_coefficient=example[f"{state}_Cd"]) for state in ("ULS","SLS")}
    wrenches=[]
    for state in ("ULS","SLS"):
      for axis in ("X","Y"):
        for load_sign in (-1,1):
          for ecc_sign in (-1,1):
            w=signed_eccentric_floor_wrenches(
              floor_forces_kN=distribution[state]["floor_forces_kN"],
              axis=axis,
              orthogonal_plan_breadth_m=example["plan_y_m"] if axis=="X" else example["plan_x_m"],
              eccentricity_sign=ecc_sign,load_direction_sign=load_sign)
            wrenches.append({"limit_state":state,**w})
    mass=reconcile_trial_seismic_weight(
      source_W_kN=example["source_W_kN"],member_dead_kN=example["member_dead_kN"],
      floor_extra_dead_kN=example["added_floor_dead_kN"],
      nonroof_live_kN=example["nonroof_imposed_load_kN"])
    names=("Ni","Vyi","Vzi","Ti","Myi","Mzi","Nj","Vyj","Vzj","Tj","Myj","Mzj")
    def row(name,n,m):
      v={c:0. for c in names}
      v.update(Ni=n,Myi=m,Nj=-n)
      return {"combination_id":name,"signed_local_end_forces":v}
    envelope=governing_signed_component(member_id="SYNTH-COL-01",
      component="Myi",combination_actions=[row("ASSUMED-U-1",120,45),
                                            row("ASSUMED-U-2",60,-90)])
    drift=bounded_story_drift(elastic_interstory_delta_m=.021,
      story_height_m=3.,limit_state="ULS",ductility_Rmu=4)
    out={"schema":"jp.structural.public_synthetic_gate06.v0.1",
      "synthetic":True,
      "private_project_input_values_included":False,
      "basis":"NBC105:2025 §3.4 Table3-1, §5.2 Table5-1, §5.5.1/3, §5.6 and §6.3",
      "example":example,"distribution":distribution,
      "effective_stiffness":{x:effective_EI_ratios(limit_state=x)
                             for x in ("GROSS","ULS","SLS")},
      "signed_accidental_eccentricity_cases":wrenches,
      "source_mass_reconciliation_demonstration":mass,
      "same_case_member_action_selection":envelope,
      "source_gate_drift_example":drift,
      "source_handoff":"private run is NOT encoded here; generic code & synthetic demo only",
      "unverified_checks":["actual diaphragm torsion","site mass/W","member releases and torsion classification","nonlinear seismic phase coherence","as-built bars","second order","professional acceptance"],
      "engineering_approval":False,"report_accepted":False}
    assert len(wrenches)==16
    assert mass["source_to_trial_mass_closed"] is False
    assert drift["numerical_limit_exceeded"] is True
    compact=json.dumps(out,sort_keys=True,separators=(",",":"),allow_nan=False)
    out["payload_sha256"]=hashlib.sha256(compact.encode()).hexdigest()
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    out=build()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("GATE06_SYNTHETIC_16_ECCENTRICITY_CASES_MASS_AND_STIFFNESS_HOLD",args.output)

if __name__=="__main__":main()
