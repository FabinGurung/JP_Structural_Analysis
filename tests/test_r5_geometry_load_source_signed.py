"""R5 verified geometric source load/mass intake and signed FE analysis regression."""
from __future__ import annotations
import copy
import csv
import hashlib
import json
import math
from pathlib import Path

import pytest
from jp_structural.solvers.native.geometry_load_intake import (
    GeometryLoadError,assemble_geometry_source_loads,polygon_area
)
from scripts.build_r5_generic_frame_case import DEFAULT,PFX,build,emit

@pytest.fixture(scope="module")
def fixture():
    return json.loads(DEFAULT.read_text())

@pytest.fixture(scope="module")
def result(fixture):
    return build(fixture)

def test_four_column_generic_frame_and_source_geometry_numerics(fixture,result):
    m=fixture["model"]
    assert len(m["nodes"])==8
    assert len(m["frame_members"])==8
    assert result["source_load_component_count"]==3
    byid={x["id"]:x for x in result["source_load_register"]}
    assert byid["ROOF-FINISH-DL"]["geometry"]["horizontal_area_m2"]==pytest.approx(12)
    assert byid["ROOF-FINISH-DL"]["gravity_weight_kN"]==pytest.approx(72)
    assert byid["ROOF-LIVE-LL"]["gravity_weight_kN"]==pytest.approx(24)
    assert byid["ROOF-LIVE-LL"]["seismic_eligible_weight_kN"]==pytest.approx(7.2)
    assert byid["EDGE-WALL-DL"]["geometry"]["length_m"]==pytest.approx(4)
    assert byid["EDGE-WALL-DL"]["gravity_weight_kN"]==pytest.approx(32)
    assert result["case_gravity_load_kN"]==pytest.approx({"DL":104,"LL":24})
    assert result["source_total_gravity_kN"]==pytest.approx(128)
    assert result["source_total_seismic_weight_kN"]==pytest.approx(111.2)
    s=result["source_seismic_center_by_floor"]
    assert len(s)==1 and s[0]["storey_id"]=="ROOF"
    assert s[0]["center_mass_x_m"]==pytest.approx(2)
    assert s[0]["center_mass_y_m"]==pytest.approx((72*1.5+24*.3*1.5+32*0)/111.2)
    assert sum(x["mx"] for x in result["nodal_source_allocation"]["nodal_masses"])*fixture["gravity_m_s2"]==pytest.approx(111.2)

def test_real_OpenSees_six_component_global_and_mass_gravity_equilibrium(result):
    assert result["gravity_solver_equilibrium"]["equilibrium"]["status"]=="VERTICAL_GLOBAL_FORCE_AND_MOMENT_EQUILIBRIUM_PASS"
    assert sum(r["Rz_kN"] for r in result["gravity_solver_equilibrium"]["support_reactions"])==pytest.approx(128,abs=1e-5)
    assert result["max_six_component_FE_balance_kN_or_kNm"]<1e-5
    assert all(x["global_equilibrium_pass"] is True for x in result["signed_FE"]["raw_cases"])
    assert result["raw_case_count"]==3 and result["signed_combination_count"]==2
    assert result["signed_end_action_count"]==5*8*2==80
    assert len(result["signed_end_actions"])*6==480
    assert result["frame_member_count"]==8

def test_source_cases_algebraically_signed_before_member_envelopes(result):
    src=result["signed_FE"]
    raw={r["case_id"]:r for r in src["raw_cases"]}
    cmb={r["combination_id"]:r for r in src["combinations"]}
    assert set(raw)=={"DL","LL","HX"}
    assert set(cmb)=={"U_PLUS","U_MINUS"}
    for mid in ("COL1","BM1","BM2"):
        for end in ("I","J"):
            for axis in ("N","Vy","Vz","T","My","Mz"):
                dl=raw["DL"]["local_end_resisting_actions"][mid][end][axis]
                ll=raw["LL"]["local_end_resisting_actions"][mid][end][axis]
                hx=raw["HX"]["local_end_resisting_actions"][mid][end][axis]
                assert cmb["U_PLUS"]["local_end_resisting_actions"][mid][end][axis]==pytest.approx(1.2*dl+1.5*ll+hx,abs=1e-5)
                assert cmb["U_MINUS"]["local_end_resisting_actions"][mid][end][axis]==pytest.approx(1.2*dl+1.5*ll-hx,abs=1e-5)
    assert src["engineering_approval"] is False

def test_same_signed_FE_to_M08_M09_M10_partial_design_checks(result):
    checks=result["bounded_member_checks"]
    assert checks["source_action_digest"]==result["signed_FE_input_sha256"]
    assert len(checks["beam_design"])==len(checks["column_design"])==len(checks["joint_design"])==1
    assert checks["beam_design"][0]["member_id"]=="BM1"
    assert checks["column_design"][0]["member_id"]=="COL1"
    assert checks["joint_design"][0]["joint_node_id"]=="R1"
    assert checks["checks"]["signed_concurrent_case_actions"] is True
    assert checks["checks"]["signed_modal_orthogonal_envelope_supported"] is False
    assert checks["engineering_approval"] is False
    assert result["engineering_approval"] is False and result["permit_eligible"] is False
    assert result["true_distributed_member_end_forces_or_member_diagrams_evaluated"] is False
    assert result["shell_or_diaphragm_FE_evaluated"] is False
    assert result["original_G15_F3_one_way_shear_flag"]=="NOT SAFE IN ONE WAY SHEAR"

def test_7_chapters_18_governed_requirement_ids(result):
    assert [x["id"] for x in result["chapters"]]==[f"{i:02d}" for i in range(1,8)]
    assert {m["id"] for ch in result["chapters"] for m in ch["modules"]}=={
        *(f"M{i:02d}" for i in range(1,17)),"S17","S18"}
    assert result["bounded_modules_in_this_run"]==["M02","M04","M08","M09","M10","S17"]
    assert not result["all_18_modules_complete"]

@pytest.mark.parametrize("mutate,error",[
    (lambda s:s["source_loads"][0].update(boundary_node_ids=["R1","R3","R2","R4"]),"self-intersecting"),
    (lambda s:s["source_loads"][0].update(pressure_kPa=float("nan")),"finite"),
    (lambda s:s["source_loads"][0].update(participation_factor=1.2),"above 1"),
    (lambda s:s["source_loads"][0]["node_shares"][0].update(fraction=.3),"total exactly one"),
    (lambda s:s["source_loads"][0]["node_shares"][0].update(node_id="B1"),"out-of-region"),
    (lambda s:s["source_loads"][1].update(source_key="ROOF-FINISH-DL-REGION-001"),"duplicate"),
    (lambda s:s["source_loads"][2].update(member_id="COL1"),"vertical/sloped"),
    (lambda s:s["source_loads"][2]["node_shares"][0].update(fraction=.55),"total exactly one"),
    (lambda s:s["model"]["nodes"][5].update(z=4),"not horizontal"),
    (lambda s:s["model"].update(nodal_masses=[{"node_id":"R1","mx":3}]),"existing loads/mass"),
])
def test_geometry_source_rejects_unsafe_loads_without_guessing(mutate,error,fixture):
    s=copy.deepcopy(fixture);mutate(s)
    with pytest.raises(GeometryLoadError,match=error):
        assemble_geometry_source_loads(model=s["model"],loads=s["source_loads"],gravity_m_s2=s["gravity_m_s2"])

def test_arbitrary_rectangular_panel_geometry_from_4x3_to_5x3_and_line_length(fixture):
    s=copy.deepcopy(fixture)
    for n in s["model"]["nodes"]:
        if n["x"]==4:n["x"]=5
    a=assemble_geometry_source_loads(model=s["model"],loads=s["source_loads"],gravity_m_s2=s["gravity_m_s2"])
    loads={x["id"]:x for x in a["source_case_components"]}
    assert loads["ROOF-FINISH-DL"]["geometry"]["horizontal_area_m2"]==pytest.approx(15)
    assert loads["EDGE-WALL-DL"]["geometry"]["length_m"]==pytest.approx(5)
    assert a["case_total_vertical_kN"]==pytest.approx({"DL":130,"LL":30})
    assert a["audited_assembly"]["total_seismic_weight_kN"]==pytest.approx(90+9+40)

def test_zero_and_self_intersecting_polygons_rejected_and_winding_independent():
    assert polygon_area([(0,0),(4,0),(4,3),(0,3)])==pytest.approx(12)
    assert polygon_area([(0,3),(4,3),(4,0),(0,0)])==pytest.approx(12)
    with pytest.raises(GeometryLoadError):
        polygon_area([(0,0),(2,2),(0,2),(2,0)])
    with pytest.raises(GeometryLoadError):
        polygon_area([(0,0),(1,0),(2,0)])

def test_hashed_html_json_and_csv_outputs(tmp_path,result):
    d=emit(DEFAULT,tmp_path)
    names={PFX+".json",PFX+".html",PFX+".md",PFX+"-member-actions.csv",PFX+"-source-loads.csv"}
    m=json.loads((tmp_path/(PFX+"-manifest.json")).read_text())
    assert set(m["files"])==names
    assert m["engineering_approval"] is False
    for name in names:assert hashlib.sha256((tmp_path/name).read_bytes()).hexdigest()==m["files"][name]
    csvrows=list(csv.DictReader((tmp_path/(PFX+"-member-actions.csv")).open()))
    assert len(csvrows)==80
    assert set(x["end"] for x in csvrows)=={"I","J"}
    assert set(x["case_id"] for x in csvrows)=={"DL","LL","HX","U_PLUS","U_MINUS"}
    assert len(list(csv.DictReader((tmp_path/(PFX+"-source-loads.csv")).open())))==3
    body=(tmp_path/(PFX+".html")).read_text()
    assert "NOT ENGINEERING APPROVED" in body and "Chapter 06" in body
    assert "NOT SAFE IN ONE WAY SHEAR" in body
    site=(Path(__file__).resolve().parents[1]/"site/report.html").read_text()
    assert "reports/r5-generic-frame-reference.html" in site
