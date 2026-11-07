"""R5.6 numerical QA: matching shell geometry, real MPC, signed FE combos."""
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
import pytest
from scripts.build_r5_connected_shell_frame import DEFAULT,exact_reference,solve_mesh,ShellBridgeError
from scripts.build_r5_shell_diaphragm_signed import (
    PFX,build,emit,_source_combinations,MODES,CASE_IDS)

@pytest.fixture(scope="module")
def result():
    return build()

def test_exact_same_shell_and_raw_source_for_two_diaphragm_options(result):
    assert result["schema"]=="jp.structural.r5.connected_shell_mpc_signed_combinations.v0.1"
    assert result["mesh_divisions"]==[2,4,8]
    assert result["diaphragm_modes"]==list(MODES)
    assert result["solver_run_count"]==30
    assert result["mpc_comparison_count"]==15
    assert result["superposition_check_count"]==12
    assert result["synthetic_source_gravity_kN"]==pytest.approx(128)
    assert result["synthetic_source_seismic_weight_kN"]==pytest.approx(111.2)
    assert all(x["global_equilibrium_pass"] for x in result["case_results"])
    assert all(x["source_seismic_weight_kN"]==pytest.approx(111.2)
        for x in result["case_results"])
    assert all(x["source_forces_identical"] and x["same_3D_material_mesh_member_topology"]
        for x in result["diaphragm_comparisons"])

def test_inplane_MPC_only_UX_UY_RZ_and_vertical_shell_stays_flexible(result):
    runs=result["case_results"]
    rigid=[x for x in runs if x["diaphragm_mode"]=="RIGID_INPLANE_MPC"]
    flex=[x for x in runs if x["diaphragm_mode"]=="FLEXIBLE_SHELL"]
    assert len(rigid)==len(flex)==15
    assert all(x["master_tag"]==9900 and x["master_retained_dofs"]=="UX_UY_RZ" for x in rigid)
    assert all(x["master_tag"] is None and x["master_retained_dofs"] is None for x in flex)
    assert all(x["rigid_compatibility_residual_m"]<1e-8 for x in rigid)
    assert all(x["inplane_row_UX_difference_m"]<1e-8 and
               x["inplane_col_UY_difference_m"]<1e-8 for x in rigid)
    assert all(math.isfinite(x["center_shell_Uz_m"]) for x in runs)
    assert any(abs(x["center_shell_Uz_m"])>1e-9 for x in rigid if x["case_id"]=="DL")
    assert any(x["flexible_inplane_UX_strain_metric_m"] >
               x["rigid_inplane_UX_strain_metric_m"]+1e-12 for x in
               result["diaphragm_comparisons"] if x["case_id"]=="HX")

def test_concurrent_case_source_factors_and_exact_elastic_superposition(result):
    labels={x["combination_id"]:x["components"] for x in result["source_combinations"]}
    assert labels["U_PLUS"]=={"DL":1.2,"LL":1.5,"HX":1.}
    assert labels["U_MINUS"]=={"DL":1.2,"LL":1.5,"HX":-1.}
    assert result["all_combination_superposition_checks_pass"]
    assert all(x["concurrent_signed_member_actions_match_raw_case_superposition"]
               for x in result["signed_checks"])
    for case in result["case_results"]:
        if case["case_id"] not in labels:continue
        sign=labels[case["case_id"]]["HX"]
        assert case["applied_force_kN"][2]==pytest.approx(-160.8,abs=1e-6)
        assert case["applied_force_kN"][0]==pytest.approx(40*sign,abs=1e-6)
        assert len(case["signed_member_end_actions"])==8
        assert max(abs(v) for v in case["global_force_moment_residual"].values())<1e-4

@pytest.mark.parametrize("change,match",[
    (lambda s:s["combinations"][0]["components"][0].update(factor=float("nan")),"nonfinite"),
    (lambda s:s["combinations"][0]["components"].append({"case_id":"DL","factor":.5}),"duplicate"),
    (lambda s:s["combinations"][0].update(combination_id="DL"),"conflicting"),
    (lambda s:s["combinations"][0]["components"][1].update(case_id="MISSING"),"unknown"),
])
def test_invalid_signed_case_sources_rejected(change,match):
    spec=json.loads(DEFAULT.read_text())
    change(spec)
    with pytest.raises(ShellBridgeError,match=match):
        _source_combinations(spec)

def test_invalid_MPC_name_or_combination_factor_rejected():
    ref=exact_reference(json.loads(DEFAULT.read_text()))
    with pytest.raises(ShellBridgeError,match="unknown diaphragm"):
        solve_mesh(ref,2,"HX",diaphragm_mode="FULLY_FIXED")
    with pytest.raises(ShellBridgeError,match="invalid signed"):
        solve_mesh(ref,2,"U_BAD",factors={"HX":float("inf")})

def test_original_source_safety_holds_and_toc_complete(result):
    assert [x["id"] for x in result["chapters"]]==[f"{i:02d}" for i in range(1,8)]
    assert {m["id"] for c in result["chapters"] for m in c["modules"]}=={
       *(f"M{i:02d}" for i in range(1,17)),"S17","S18"}
    assert result["original_F3_failure"]=="NOT SAFE IN ONE WAY SHEAR"
    assert result["original_building_evidence_gates_accepted"]==0
    assert not result["engineering_approval"] and not result["permit_eligible"]
    assert not result["code_load_factors_approved"]
    assert not result["modal_or_PDelta_completed"]

def test_hashed_report_csv_and_annex(tmp_path):
    r=emit(tmp_path,meshes=(2,))
    manifest=json.loads((tmp_path/(PFX+"-manifest.json")).read_text())
    assert manifest["engineering_approval"] is False
    assert len(manifest["files"])==4
    for name,digest in manifest["files"].items():
        assert hashlib.sha256((tmp_path/name).read_bytes()).hexdigest()==digest
    assert len(list(csv.DictReader((tmp_path/(PFX+"-comparisons.csv")).open())))==5
    assert len(list(csv.DictReader((tmp_path/(PFX+"-member-actions.csv")).open())))==2*5*2*(4+8)
    html=(tmp_path/(PFX+".html")).read_text()
    assert "NOT ENGINEER APPROVED" in html
    assert "NOT SAFE IN ONE WAY SHEAR" in html
    site=(Path(__file__).resolve().parents[1]/"site/report.html").read_text()
    assert 'id="annex-r5p6-shell-mpc"' in site
    assert "reports/r5-shell-diaphragm-signed.html" in site
