"""Independent signed FE transfer, free-body and bounded RC bridge checks."""
import copy
import math
import pytest

from jp_structural.solvers.opensees.synthetic_d2_example import case_fixture
from jp_structural.solvers.opensees.member_design_bridge import (
    DesignBridgeError,solve_signed_member_cases,evaluate_m08_m09_m10,
)

def _run():
    m,c,k,b,col,j=case_fixture()
    solved=solve_signed_member_cases(model=m,cases=c,combinations=k)
    return m,c,k,b,col,j,solved

def test_synthetic_open_sees_static_force_moment_balance_all_six_dofs():
    m,c,k,b,col,j,s=_run()
    assert s["schema"]=="jp.structural.signed_design_actions.v0.1"
    assert s["engineering_approval"] is False
    assert len(s["raw_cases"])==2
    assert len(s["combinations"])==2
    for case in s["raw_cases"]:
        assert case["global_equilibrium_pass"]
        assert max(abs(x) for x in case["global_force_moment_equilibrium_residual"].values())<1e-5
    assert set(s["combinations"][0]["local_end_resisting_actions"])=={"COL1","COL2","BM1","BM2"}

def test_signed_load_combination_not_sum_of_absolute_values():
    *_,s=_run()
    raw={r["case_id"]:r for r in s["raw_cases"]}
    cmb={r["combination_id"]:r for r in s["combinations"]}
    for mid in ("COL1","BM1"):
        for end in ("I","J"):
            for key in ("N","Vy","Vz","T","My","Mz"):
                g=raw["G"]["local_end_resisting_actions"][mid][end][key]
                h=raw["HX"]["local_end_resisting_actions"][mid][end][key]
                uplus=cmb["U_PLUS"]["local_end_resisting_actions"][mid][end][key]
                uminus=cmb["U_MINUS"]["local_end_resisting_actions"][mid][end][key]
                assert uplus==pytest.approx(1.2*g+1.2*h,abs=1e-5)
                assert uminus==pytest.approx(1.2*g-1.2*h,abs=1e-5)
    # Linear opposite-sign horizontal load directions must reverse the bending.
    plus=cmb["U_PLUS"]["local_end_resisting_actions"]["COL1"]["I"]["My"]
    minus=cmb["U_MINUS"]["local_end_resisting_actions"]["COL1"]["I"]["My"]
    assert plus*minus<0

def test_real_opensees_signed_column_compression_and_shear():
    *_,s=_run()
    for x in s["combinations"]:
        member=x["local_end_resisting_actions"]["COL1"]
        assert member["I"]["N"]>0
        assert member["J"]["N"]<0
        assert abs(member["I"]["N"]+member["J"]["N"])<1e-5
        assert abs(member["I"]["Vz"])>1e-3

def test_direct_design_bridge_includes_m08_m09_m10_same_combinations_and_provenance():
    m,c,k,b,col,j,s=_run()
    result=evaluate_m08_m09_m10(model=m,solved=s,
        beam_bindings=b,column_bindings=col,joint_bindings=j)
    assert result["schema"]=="jp.structural.m08_m09_m10_design_bridge.v0.1"
    assert result["engineering_approval"] is False
    assert result["checks"]["signed_modal_orthogonal_envelope_supported"] is False
    assert len(result["beam_design"])==len(result["column_design"])==len(result["joint_design"])==1
    beam=result["beam_design"][0]
    assert beam["shear_component"]=="Vy"
    assert beam["check"]["engineering_approval"] is False
    assert set(x["combination_id"] for x in beam["signed_combination_end_shear"])=={"U_PLUS","U_MINUS"}
    columns=result["column_design"][0]
    assert len(columns["scenarios"])==4
    assert all(x["axial_compression_kN"]>0 for x in columns["scenarios"])
    assert all(x["check"]["engineering_approval"] is False for x in columns["scenarios"])
    assert columns["governing_interaction_utilization"]==pytest.approx(
        max(x["check"]["legacy_interaction"]["interaction_utilization"] for x in columns["scenarios"]))
    joint=result["joint_design"][0]
    assert len(joint["scenarios"])==2
    assert all(x["check"]["engineering_approval"] is False for x in joint["scenarios"])
    assert result["source_action_digest"]==s["input_bundle_sha256"]

@pytest.mark.parametrize("mutate,part",[
    (lambda m,c,k: m["units"].update(length="mm"), "kN, m, s"),
    (lambda m,c,k: m["frame_loads"].append({"id":"DUPLICATE"}), "double counting"),
    (lambda m,c,k: c[0]["nodal_loads"][0].pop("My_kNm"), "six signed"),
    (lambda m,c,k: c[0]["nodal_loads"].append(copy.deepcopy(c[0]["nodal_loads"][0])), "duplicated"),
    (lambda m,c,k: k[0]["components"].append({"case_id":"G","factor":1.5}), "duplicated"),
    (lambda m,c,k: k[0]["components"][0].update(case_id="UNKNOWN"), "missing"),
    (lambda m,c,k: c[0].update(source_id=""), "source_id"),
    (lambda m,c,k: k[0]["components"][0].update(factor=float("nan")), "finite"),
])
def test_fail_closed_missing_or_ambiguous_action_provenance(mutate,part):
    m,c,k,*_=case_fixture()
    mutate(m,c,k)
    with pytest.raises(DesignBridgeError,match=part):
        solve_signed_member_cases(model=m,cases=c,combinations=k)

@pytest.mark.parametrize("mutate,part",[
    (lambda m,b,col,j: col[0]["moment_component_mapping"].update(Mux="My"), "unique"),
    (lambda m,b,col,j: col[0]["section"].update(width_mm=450), "differs"),
    (lambda m,b,col,j: j[0].update(joint_node_id="TM"), "does not coincide"),
    (lambda m,b,col,j: j[0].update(shear_component="VX"), "Vy/Vz"),
    (lambda m,b,col,j: b[0].update(gravity_case_id="NO"), "gravity case"),
    (lambda m,b,col,j: b[0].update(combination_ids=["UNKNOWN"]), "combination"),
])
def test_design_bridge_refuses_invalid_member_geometry_or_sign_mapping(mutate,part):
    m,c,k,b,col,j,s=_run()
    mutate(m,b,col,j)
    with pytest.raises(DesignBridgeError,match=part):
        evaluate_m08_m09_m10(model=m,solved=s,
            beam_bindings=b,column_bindings=col,joint_bindings=j)

def test_design_bridge_rejects_model_drift_after_solve():
    m,c,k,b,col,j,s=_run()
    m["nodes"][2]["x"]=.125
    with pytest.raises(DesignBridgeError,match="differs"):
        evaluate_m08_m09_m10(model=m,solved=s,
            beam_bindings=b,column_bindings=col,joint_bindings=j)

def test_negative_axial_noncompression_cannot_be_turned_into_pmm_pass():
    m,c,k,b,col,j,s=_run()
    tampered=copy.deepcopy(s)
    tampered["combinations"][0]["local_end_resisting_actions"]["COL1"]["I"]["N"]=-50
    with pytest.raises(DesignBridgeError,match="signed action digest mismatch"):
        evaluate_m08_m09_m10(model=m,solved=tampered,
            beam_bindings=b,column_bindings=col,joint_bindings=j)


def test_recomputed_digest_still_rejects_true_column_axial_tension():
    import hashlib
    import json
    m,c,k,b,col,j,s=_run()
    tampered=copy.deepcopy(s)
    tampered["combinations"][0]["local_end_resisting_actions"]["COL1"]["I"]["N"]=-50
    # Even someone regenerating the checksum must not fabricate compression.
    tampered["results_digest_sha256"]=hashlib.sha256(
        json.dumps({"raw_cases":tampered["raw_cases"],
                    "combinations":tampered["combinations"]},
                   sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    with pytest.raises(DesignBridgeError,match="signed combination algebra"):
        evaluate_m08_m09_m10(model=m,solved=tampered,
            beam_bindings=b,column_bindings=col,joint_bindings=j)


def test_missing_solved_action_digest_rejects_precheck():
    m,c,k,b,col,j,s=_run()
    s.pop("results_digest_sha256")
    with pytest.raises(DesignBridgeError,match="signed action digest mismatch"):
        evaluate_m08_m09_m10(model=m,solved=s,
            beam_bindings=b,column_bindings=col,joint_bindings=j)


def test_m10_adverse_signed_column_shear_direction_blocks_false_nominal_pass():
    """A subtractive column-shear-only check must not create a fake pass."""
    m,c,k,b,col,j,s=_run()
    j[0]["joint"]["Ast_top_mm2"]=1200
    j[0]["joint"]["Ast_bottom_mm2"]=700
    result=evaluate_m08_m09_m10(model=m,solved=s,
        beam_bindings=b,column_bindings=col,joint_bindings=j)
    jn=result["joint_design"][0]
    assert jn["status"]=="FAIL_UNCERTAIN_JOINT_FORCE_DIRECTION_BOUND"
    assert any(x["check"]["joint_nominal_shear_pass"] for x in jn["scenarios"])
    assert any(not x["upper_direction_bound_nominal_shear_pass"] for x in jn["scenarios"])
    for row in jn["scenarios"]:
        assert row["unresolved_shear_direction_upper_kN"] >= row["check"]["factored_Vjh_kN"]
    assert not result["engineering_approval"]
