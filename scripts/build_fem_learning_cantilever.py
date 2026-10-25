#!/usr/bin/env python3
"""Real OpenSeesPy teaching cantilever with independent Euler-Bernoulli handcheck.

PUBLIC SYNTHETIC example only; this is NOT the G+1.5 project or a real footing.
Units: kN, m, rad. Positive global X tip force; vertical cantilever in global Y.
"""
from __future__ import annotations
import argparse,hashlib,json,math
from pathlib import Path
import openseespy.opensees as ops

SCHEMA="jp.structural.teaching_cantilever.real_opensees.v0.1"
LOADS=(5.0,10.0,15.0,20.0)
E_MPA=25000.0
E_KN_M2=E_MPA*1000.0
L_M=3.0
B_M=0.30
D_M=0.30
I_M4=B_M*D_M**3/12.0
A_M2=B_M*D_M

def hand(force_kN:float)->dict:
    ei=E_KN_M2*I_M4
    return {
        "tip_displacement_m":force_kN*L_M**3/(3.0*ei),
        "tip_rotation_abs_rad":force_kN*L_M**2/(2.0*ei),
        "support_horizontal_abs_kN":force_kN,
        "support_moment_abs_kNm":force_kN*L_M,
        "shear_abs_kN":force_kN,
        "base_bending_abs_kNm":force_kN*L_M,
        "I_m4":I_M4,"EI_kN_m2":ei,
        "tip_stiffness_kN_m":3.0*ei/L_M**3
    }

def solve(force_kN:float)->dict:
    if force_kN not in LOADS:
        raise ValueError("Only published explicitly tested load cases allowed")
    ops.wipe()
    ops.model("basic","-ndm",2,"-ndf",3)
    ops.node(1,0.0,0.0)
    ops.node(2,0.0,L_M)
    ops.fix(1,1,1,1)  # illustrative fixed base UX, UY, RZ, not real site proof
    ops.geomTransf("Linear",1)
    ops.element("elasticBeamColumn",1,1,2,A_M2,E_KN_M2,I_M4,1)
    ops.timeSeries("Linear",1)
    ops.pattern("Plain",1,1)
    ops.load(2,force_kN,0.0,0.0)
    ops.system("BandGeneral")
    ops.numberer("RCM")
    ops.constraints("Plain")
    ops.integrator("LoadControl",1.0)
    ops.algorithm("Linear")
    ops.analysis("Static")
    ok=ops.analyze(1)
    if ok!=0:
        raise RuntimeError(f"OpenSees did not converge, code {ok}")
    ops.reactions()
    u=float(ops.nodeDisp(2,1))
    rotation=float(ops.nodeDisp(2,3))
    rx=float(ops.nodeReaction(1,1))
    ry=float(ops.nodeReaction(1,2))
    rm=float(ops.nodeReaction(1,3))
    local=tuple(float(i) for i in ops.eleResponse(1,"localForce"))
    if len(local)!=6:
        raise RuntimeError("OpenSees 2D localForce must have six signed components")
    hand_values=hand(force_kN)
    eps=1e-7
    def close(v,ideal,rel=1e-7,abs_tol=1e-8):
        if not math.isclose(v,ideal,rel_tol=rel,abs_tol=abs_tol):
            raise AssertionError(f"Solver/handcheck mismatch: {v} versus {ideal}")
    close(u,hand_values["tip_displacement_m"])
    close(abs(rotation),hand_values["tip_rotation_abs_rad"])
    close(rx,-force_kN)
    close(abs(rm),force_kN*L_M)
    close(ry,0.0)
    close(rx+force_kN,0.0,abs_tol=eps)
    close(rm-L_M*force_kN,0.0,abs_tol=eps)
    # Our global moment sign: tip at (0,+L), F at (+X,0) => moment -L*F.
    # Support must oppose it with +L*F.
    local_abs=[abs(x) for x in local]
    if not math.isclose(max(local_abs),force_kN*L_M,abs_tol=1e-7):
        raise AssertionError("Local element-end moment not extracted")
    return {
       "id":f"F{int(force_kN):02d}","applied_tip_fx_kN":force_kN,
       "opensees":{
          "node_tip_ux_m":u,"node_tip_rotation_rz_rad":rotation,
          "base_reaction_rx_kN":rx,"base_reaction_ry_kN":ry,
          "base_reaction_mz_kNm":rm,
          "element_local_end_forces":list(local),
          "horizontal_force_residual_kN":rx+force_kN,
          "global_moment_residual_kNm":rm-L_M*force_kN},
       "independent_hand":hand_values,
       "agreement":{
          "tip_displacement_difference_m":u-hand_values["tip_displacement_m"],
          "reaction_magnitude_difference_kN":abs(rx)-force_kN,
          "base_moment_magnitude_difference_kNm":abs(rm)-force_kN*L_M}
    }

def generate()->dict:
    rows=[solve(f) for f in LOADS]
    return {
      "schema":SCHEMA,"source_class":"SYNTHETIC_TEACHING_PARAMETERS",
      "analysis_engine":"OpenSeesPy real 2D elasticBeamColumn static linear solve",
      "project_model_used":False,"nepal_design_compliance":"NOT_EVALUATED",
      "engineering_approval":False,
      "model":{"node_positions_m":[[0.0,0.0],[0.0,L_M]],"base_support":"FIXED_ILLUSTRATIVE",
               "tip_support":"FREE","beam_type":"Euler-Bernoulli elasticBeamColumn",
               "E_MPa":E_MPA,"E_kN_m2":E_KN_M2,"b_m":B_M,"h_m":D_M,
               "I_m4":I_M4,"A_m2":A_M2,"L_m":L_M},
      "method":{"step_1":"Idealize one vertical, 2-node cantilever frame element; 2D, 3 DOF per node",
                "step_2":"Fix base UX UY RZ; free tip; apply signed +FX kN at tip",
                "step_3":"Assemble element stiffness and solve K_ff d=f with static linear OpenSees",
                "step_4":"Extract signed nodeDisp/nodeReaction and element localForce",
                "step_5":"Independently handcheck F, F L, F L^3/(3 EI) and moment equilibrium",
                "step_6":"Never infer the actual building's supports or loads from this example"},
      "cases":rows
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="site/data/opensees-cantilever-learning.v0.1.json")
    args=p.parse_args()
    o=Path(args.output);o.parent.mkdir(parents=True,exist_ok=True)
    data=generate()
    o.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("OPENSEES_CANTILEVER_HANDCHECK_PASS",
          len(data["cases"]),round(data["cases"][1]["opensees"]["node_tip_ux_m"]*1000,6),
          "mm; NO_SOURCE_BUILDING_APPROVAL")
if __name__=="__main__":main()
