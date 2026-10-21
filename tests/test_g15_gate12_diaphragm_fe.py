"""Actual-source frame, OpenSees rigid-multi-point-constraint regression."""
import math
from scripts.run_g15_gate12_diaphragm_fe import solve, floor_nodal_lateral

def test_same_165_member_frame_flexible_vs_rigid_opensees():
    d=solve(summary_only=True)
    assert d["schema"]=="jp.structural.g15.gate12.diaphragm_openSees_comparison.v0.1"
    assert d["source_grid_members"]==165
    assert d["source_columns"]==23
    assert len(d["cases"])==18
    assert len(d["comparisons"])==9
    assert {x["boundary"] for x in d["cases"]}=={"FLEXIBLE","RIGID_MPC_TRIAL"}
    assert all(c["members"]==165 and c["local_signed_member_action_count"]==165
               for c in d["cases"])
    assert all(c["reaction_equilibrium_verified"] and
               c["max_force_equilibrium_residual_kN"]<.001 and
               c["max_moment_equilibrium_residual_kNm"]<.001 for c in d["cases"])
    assert all(len(c["floor_drifts"])==3 and len(c["governing_signed_local_12_actions"])==12
               for c in d["cases"])
    assert any(abs(c["flexible_roof_mm"]-c["rigid_roof_mm"])>.00001
               for c in d["comparisons"] if c["signed_axis"]!="GRAVITY")
    assert d["source_F3_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"
    assert d["engineering_approval"] is False
    assert d["seismic_mass_reconciled"] is False
    assert d["actual_slab_shell_elements"] is False
    assert d["displacement_limit_compliance_verified"] is False
    assert d["signed_combinations_implemented"].startswith("INDEPENDENT_")

def test_signed_case_reversal_and_accidental_torsion():
    d=solve(summary_only=True)
    a={x["case"]:x for x in d["cases"] if x["boundary"]=="RIGID_MPC_TRIAL"}
    xp=a["EQ_X_POS_EPOS"]
    xn=a["EQ_X_NEG_EPOS"]
    assert xp["signed_applied_force_kN_xyz"][0]==-xn["signed_applied_force_kN_xyz"][0]
    assert math.isclose(xp["signed_applied_global_moment_kNm_xyz"][2],
                       -xn["signed_applied_global_moment_kNm_xyz"][2],abs_tol=.001)
    assert not math.isclose(
       a["EQ_X_POS_EPOS"]["signed_applied_global_moment_kNm_xyz"][2],
       a["EQ_X_POS_ENEG"]["signed_applied_global_moment_kNm_xyz"][2],abs_tol=.001)

def test_equivalent_nodal_lateral_couple_has_signed_force_and_moment():
    pts=[(0.,0.),(10.,0.),(0.,5.),(10.,5.)]
    for axis in ("X","Y"):
        for sign in (-1,1):
            forces=floor_nodal_lateral(axis,sign*100.,pts,(4.,3.),-.5)
            assert math.isclose(sum(x for x,y in forces),sign*100. if axis=="X" else 0.,abs_tol=1e-8)
            assert math.isclose(sum(y for x,y in forces),sign*100. if axis=="Y" else 0.,abs_tol=1e-8)

def test_full_signed_record_is_preserved_for_actions_artifact():
    d=solve(summary_only=False)
    assert all(len(c["full_local_member_signed_actions"])==165 for c in d["cases"])
    assert all(len(f["signed"])==12 for c in d["cases"]
               for f in c["full_local_member_signed_actions"])
    assert any(c["governing_absolute_member_end_moment_kNm"]>0 for c in d["cases"])
