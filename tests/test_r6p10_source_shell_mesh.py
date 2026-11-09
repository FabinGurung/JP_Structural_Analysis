"""R6.10 reproducible source shell, diaphragm and load-combination audit QA."""
import hashlib
import math
import json
from pathlib import Path
import pytest
from scripts.build_r6p10_source_shell_mesh import (
    MeshQAError,build,export,shape_at_xy,mesh_point,triangle_area_xy,triangle_area_3d,
)

def test_native_source_115_area_mesh_provenance_and_support_disconnections():
    r=build()
    assert r["source_ETABS21_geometry"]
    assert r["source_shell_count"]==115
    assert r["shells_connected_through_source_to_fixed_base"]==103
    assert r["shells_without_verified_vertical_support_path"]==12
    assert len(r["unrestrained_shell_source_ids"])==12
    assert len(r["source_graph_components"])==5
    assert sum(x["anchored"] for x in r["source_graph_components"])==2
    assert r["original_structural_frame_segments"]==165
    assert not r["engineering_approval"] and r["source_F3_one_way_shear_unsafe"]

def test_native_original_shell_mesh_instructions_not_passed_off_as_ETABS_generated_mesh():
    r=build()
    assert r["requested_mesh_mode_counts"]=={"AUTOMESH":7,"DEFAULT":2,"MESHN1XN2":106}
    assert len(r["all_shell_parameters"])==115
    assert sum(x["requested_or_proxy_element_count"] for x in r["all_shell_parameters"])==r["shell_mesh_requested_or_proxy_total_elements"]
    assert all(x["n1"]>=1 and x["n2"]>=1 for x in r["all_shell_parameters"])
    assert any(x["source_mesh_mode"]=="DEFAULT" and "PROXY" in x["mesh_rule"] for x in r["all_shell_parameters"])
    assert all(x["source_shell_model_type"]=="ShellThin" for x in r["all_shell_parameters"]), [(x["key"],x["source_section"],x["source_shell_model_type"]) for x in r["all_shell_parameters"] if x["source_shell_model_type"]!="ShellThin"]

def test_full_source_diaphragm_point_assignments_and_vertical_dof_separation():
    r=build()
    assert r["source_diaphragm_points_total"]==201
    d=r["rigid_diaphragm_source_assignments"]
    assert {(x["story"],x["diaphragm"],x["assigned_points"]) for x in d}=={
        ("GF","D1",67),("FF","D2",80),("TF","D3",54)}
    assert all(x["does_not_constrain_vertical_uz"] for x in d)
    assert len({p for x in d for p in x["source_point_ids"]})>=100

def test_30_loaded_geometric_lines_resolve_to_source_shells_without_fake_section():
    r=build()
    t=r["source_line_wall_load_to_shell_transfer_proxy"]
    assert len(t)==30
    assert all(x["line_to_shell_force_conserved"] and x["unmatched_quadrature_intervals"]==0 for x in t)
    assert all(not x["correct_etabs_native_load_path_proven"] for x in t)
    assert r["original_unsectioned_wall_load_count"]==30
    assert r["mapped_source_line_wall_load_count"]==30
    assert r["mapped_unsectioned_line_gravity_kN"]==pytest.approx(306.232,abs=.2)

def test_full_source_gravity_patterns_mass_comparison_and_source_held():
    r=build()
    mass=r["all_source_gravity_loading"]
    z=mass["pattern_source_integrated_kN"]
    assert z["WALL LOAD"]==pytest.approx(2115.49,abs=1)
    assert z["Dead"]>0
    assert z["Live"]>0
    assert z["FLOOR FINISH"]>0
    assert mass["conditional_msSrc1_gravity_weight_kN"]>3290
    assert not mass["accepted_governing_ETABS21_mass"]
    assert not r["source_mass_source_exact_ETABS_result_verified"]

def test_original_11x2_source_loadcase_register_preserves_signed_seismic_terms():
    r=build()
    assert set(r["original_loadcase_and_combination_register"])=={"ULS","SLS"}
    for role in ("ULS","SLS"):
        c=r["original_loadcase_and_combination_register"][role]
        combos=c["source_11_load_combinations"]
        assert len(combos)==11
        assert len([x for x in combos if x["contains_lateral_seismic"]])>=6
        assert all(x["type"]=="Linear Add" and x["terms"] for x in combos)
        assert all(not x["not_solved_design_envelope"] is False for x in combos)
    assert not r["independently_solved_complete_gravity_cases"]
    assert not r["independently_solved_complete_seismic_cases"]

def test_barycentric_projection_is_force_conserving_for_source_polygon():
    verts=[[0,0,0],[4000,0,0],[4000,3000,0],[0,3000,0]]
    for x,y in [(0,0),(2000,0),(4000,1500),(2000,2000)]:
        q=shape_at_xy(verts,(x,y))
        assert q is not None and sum(q)==pytest.approx(1)
        assert sum(v[0]*w for v,w in zip(verts,q))==pytest.approx(x)
        assert sum(v[1]*w for v,w in zip(verts,q))==pytest.approx(y)
    assert shape_at_xy(verts,(4300,2000)) is None
    assert mesh_point(verts,.5,.5)==[2000,1500,0]
    assert triangle_area_xy(*verts[:3])==pytest.approx(6e6)
    assert triangle_area_3d(*verts[:3])==pytest.approx(6e6)

def test_public_json_source_scan_and_hash_receipt():
    doc,summary=export()
    out=Path("site/data/r6p10-source-shell-diaphragm-loads.json")
    assert summary["source_QA_file_sha256"]==hashlib.sha256(out.read_bytes()).hexdigest()
    assert summary["original_diaphragm_point_assignments"]==201
    assert summary["original_load_combinations_by_role"]=={"ULS":11,"SLS":11}
    assert summary["F3_unsafe"] and not summary["engineering_approval"]
    text=out.read_text()
    assert "RAMBAZZAR" not in text and "E:\\\\" not in text
    assert not doc["source_ETABS21_native_solver_reproduced"]
