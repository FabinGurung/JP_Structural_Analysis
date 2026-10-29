"""Verify native OpenSees 3D distributed elastic-beam loading and SAR handoff.

Hand benchmark fixed-fixed beam: V=wL/2 and end M=wL^2/12.
No real building/soil/source code-compliance approval.
"""
from __future__ import annotations
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
import pytest
from jp_structural.solvers.opensees.member_design_bridge import (
    DesignBridgeError,solve_signed_member_cases
)
from scripts.build_r5_uniform_beam_case import DEFAULT,PFX,build,emit

@pytest.fixture(scope="module")
def result():
    return build()

def _fixed_beam():
    src=json.loads(DEFAULT.read_text(encoding="utf8"))
    m=copy.deepcopy(src["model"])
    m["model_id"]="SYNTHETIC-FIXED-FIXED-4M-UDL"
    m["nodes"]=[x for x in m["nodes"] if x["id"] in ("R1","R2")]
    m["frame_members"]=[x for x in m["frame_members"] if x["id"]=="BM1"]
    fixed=["UX","UY","UZ","RX","RY","RZ"]
    m["supports"]=[{"id":"FIX-"+n,"node_id":n,"restrained_dofs":fixed} for n in ("R1","R2")]
    m["diaphragms"]=[];m["nodal_masses"]=[];m["mass_source"]={}
    case={"case_id":"DISTRIBUTED","source_id":"SYNTHETIC-8KN_PER_M_4M_FIXED_BEAM",
          "nodal_loads":[],"uniform_beam_loads":[{
             "id":"W","source_key":"SYNTHETIC_FIXED_BEAM_UDL",
             "member_id":"BM1","downward_kN_per_m":8.}]}
    combo=[{"combination_id":"W_FACTORED","source_id":"SYNTHETIC_FACTOR_1P5",
            "components":[{"case_id":"DISTRIBUTED","factor":1.5}]}]
    return m,case,combo

def test_independent_fixed_fixed_beam_matches_exact_uniform_load_hand_solution():
    model,case,comb=_fixed_beam()
    a=solve_signed_member_cases(model=model,cases=[case],combinations=comb)
    assert a["engineering_approval"] is False
    g=a["raw_cases"][0]
    assert g["global_equilibrium_pass"] is True
    assert max(abs(v) for v in g["global_force_moment_equilibrium_residual"].values())<1e-7
    assert len(g["uniform_beam_loads"])==1
    assert g["uniform_beam_loads"][0]["downward_resultant_kN"]==pytest.approx(32)
    assert g["uniform_beam_loads"][0]["local_load_components_kN_m"]=={"Wy":0.,"Wz":-8.,"Wx":0.}
    ends=g["local_end_resisting_actions"]["BM1"]
    for end in ("I","J"):
        assert abs(ends[end]["Vz"])==pytest.approx(8*4/2,abs=1e-6)
        assert abs(ends[end]["My"])==pytest.approx(8*4**2/12,abs=1e-6)
        assert ends[end]["N"]==pytest.approx(0,abs=1e-8)
        assert ends[end]["T"]==pytest.approx(0,abs=1e-8)
    fact=a["combinations"][0]["local_end_resisting_actions"]["BM1"]
    for end in ("I","J"):
        for axis in ("N","Vy","Vz","T","My","Mz"):
            assert fact[end][axis]==pytest.approx(1.5*ends[end][axis],abs=1e-6)

def test_fixed_fixed_lumped_nodal_load_not_same_member_end_moment():
    m,c,k=_fixed_beam()
    exact=solve_signed_member_cases(model=m,cases=[c],combinations=k)
    lump=copy.deepcopy(c)
    lump.pop("uniform_beam_loads")
    zero=lambda n:{"node_id":n,**dict.fromkeys(("Fx_kN","Fy_kN","Fz_kN","Mx_kNm","My_kNm","Mz_kNm"),0.),
                    "Fz_kN":-16.}
    lump["nodal_loads"]=[zero("R1"),zero("R2")]
    wrong=solve_signed_member_cases(model=m,cases=[lump],combinations=k)
    for end in ("I","J"):
        correct=exact["raw_cases"][0]["local_end_resisting_actions"]["BM1"][end]
        crude=wrong["raw_cases"][0]["local_end_resisting_actions"]["BM1"][end]
        assert abs(correct["My"])==pytest.approx(10.6666666667,abs=1e-5)
        assert abs(crude["My"])<1e-6
    assert wrong["raw_cases"][0]["global_equilibrium_pass"] is True

def test_r5_native_element_loading_keeps_mass_and_replaces_only_wall_line_forces(result):
    assert result["schema"]=="jp.structural.r5.distributed_uniform_beam_to_signed_SAR.v0.2"
    assert result["source_total_gravity_kN"]==pytest.approx(128)
    assert result["source_seismic_weight_kN"]==pytest.approx(111.2)
    assert result["true_element_uniform_resultants_kN"]==pytest.approx(32)
    assert result["nodal_resultants_kN"]==pytest.approx(96)
    assert result["source_loads_conserved_without_double_count"] is True
    assert result["global_six_component_equilibrium_max_kN_or_kNm"]<1e-5
    assert result["raw_case_count"]==3 and result["signed_combination_count"]==2
    assert result["model_member_count"]==8 and result["signed_end_action_count"]==80
    byid={x["case_id"]:x for x in result["signed_FE"]["raw_cases"]}
    assert len(byid["DL"]["uniform_beam_loads"])==1
    assert not byid["LL"]["uniform_beam_loads"] and not byid["HX"]["uniform_beam_loads"]
    assert byid["DL"]["uniform_beam_loads"][0]["member_id"]=="BM1"
    assert byid["DL"]["uniform_beam_loads"][0]["downward_resultant_kN"]==pytest.approx(32)
    assert sum(-x["Fz_kN"] for x in byid["DL"]["nodal_loads"])==pytest.approx(72)
    assert sum(-x["Fz_kN"] for x in byid["LL"]["nodal_loads"])==pytest.approx(24)
    assert all(x["global_equilibrium_pass"] for x in byid.values())

def test_actual_local_member_moments_are_distinct_from_lumped_approximation(result):
    diffs=result["predecessor_equivalent_nodal_comparison"]
    assert len(diffs)==2
    assert set(x["end"] for x in diffs)=={"I","J"}
    assert all(x["member_id"]=="BM1" for x in diffs)
    assert any(abs(x["moment_difference_kNm"])>1e-4 for x in diffs)
    assert all(math.isfinite(x["native_element_local_My_kNm"]) for x in diffs)
    assert result["uniform_member_fixed_end_effects_recovered"] is True
    assert result["shell_or_diaphragm_FE_integrated"] is False

def test_concurrent_signed_combination_actions_with_native_element_load(result):
    s=result["signed_FE"]
    raw={x["case_id"]:x for x in s["raw_cases"]}
    combo={x["combination_id"]:x for x in s["combinations"]}
    for mid in ("BM1","COL1","BM2"):
        for end in ("I","J"):
            for axis in ("N","Vy","Vz","T","My","Mz"):
                g=raw["DL"]["local_end_resisting_actions"][mid][end][axis]
                l=raw["LL"]["local_end_resisting_actions"][mid][end][axis]
                h=raw["HX"]["local_end_resisting_actions"][mid][end][axis]
                assert combo["U_PLUS"]["local_end_resisting_actions"][mid][end][axis]==pytest.approx(1.2*g+1.5*l+h,abs=1e-5)
                assert combo["U_MINUS"]["local_end_resisting_actions"][mid][end][axis]==pytest.approx(1.2*g+1.5*l-h,abs=1e-5)
    checks=result["bounded_member_checks"]
    assert checks["source_action_digest"]==result["signed_FE_input_sha256"]
    assert checks["engineering_approval"] is False
    assert len(checks["beam_design"])==len(checks["column_design"])==len(checks["joint_design"])==1

def test_seven_chapter_cover_all_18_requirements_and_safety_unchanged(result):
    assert [c["id"] for c in result["chapters"]]==[f"{i:02d}" for i in range(1,8)]
    allids={m["id"] for c in result["chapters"] for m in c["modules"]}
    assert allids=={*(f"M{i:02d}" for i in range(1,17)),"S17","S18"}
    assert result["original_F3_failure"]=="NOT SAFE IN ONE WAY SHEAR"
    assert result["original_building_source_accepted"] is False
    assert result["original_F3_design_pass"] is False
    assert result["engineering_approval"] is False
    assert result["permit_eligible"] is False
    assert result["construction_approved"] is False
    assert result["panel_pressure_is_still_nodal_equivalent"] is True

@pytest.mark.parametrize("mutate,expected",[
    (lambda m,c:c["uniform_beam_loads"][0].update(member_id="COL1"),"unknown member"),
    (lambda m,c:c["uniform_beam_loads"][0].update(downward_kN_per_m=-1),"positive"),
    (lambda m,c:c["uniform_beam_loads"][0].update(downward_kN_per_m=float("nan")),"finite"),
    (lambda m,c:c["uniform_beam_loads"][0].update(source_key=""),"source_key"),
    (lambda m,c:c["uniform_beam_loads"].append(copy.deepcopy(c["uniform_beam_loads"][0])),"duplicate"),
    (lambda m,c:m["frame_members"][0].update(local_axis_vector=[0,1,0]),"custom local"),
    (lambda m,c:m["nodes"][1].update(z=3.1),"horizontal"),
    (lambda m,c:c["uniform_beam_loads"][0].update(extra=True),"uniform beam source"),
])
def test_element_source_rejects_bad_member_or_provenance(mutate,expected):
    m,c,k=_fixed_beam()
    mutate(m,c)
    with pytest.raises(DesignBridgeError,match=expected):
        solve_signed_member_cases(model=m,cases=[c],combinations=k)

def test_output_package_is_deterministic_hashed_and_report_linked(tmp_path,result):
    r=emit(DEFAULT,tmp_path)
    p=PFX
    manifest=json.loads((tmp_path/(p+"-manifest.json")).read_text())
    assert manifest["engineering_approval"] is False
    assert len(manifest["files"])==4
    for name,checksum in manifest["files"].items():
        assert hashlib.sha256((tmp_path/name).read_bytes()).hexdigest()==checksum
    assert json.loads((tmp_path/(p+".json")).read_text())["schema"]==r["schema"]
    vectors=list(csv.DictReader((tmp_path/(p+"-member-ends.csv")).open()))
    assert len(vectors)==80
    assert len(list(csv.DictReader((tmp_path/(p+"-moments-comparison.csv")).open())))==2
    h=(tmp_path/(p+".html")).read_text()
    assert "NOT ENGINEER APPROVED" in h and "Chapter 05" in h
    assert "NOT SAFE IN ONE WAY SHEAR" in h
    site=(Path(__file__).resolve().parents[1]/"site/report.html").read_text()
    assert "reports/r5-distributed-beam-reference.html" in site
