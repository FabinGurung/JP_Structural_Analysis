"""Synthetic physically connected ShellMITC4 floor-to-beam test; no approval."""
import copy
import hashlib
import json
import math
from pathlib import Path
import pytest
from scripts.build_r5_connected_shell_frame import (
    build,exact_reference,solve_mesh,ShellBridgeError,DEFAULT,MESHES,PFX
)
from scripts.build_r5_oneway_panel_beam_case import build as one_way

@pytest.fixture(scope="module")
def original():return json.loads(DEFAULT.read_text(encoding="utf8"))

@pytest.fixture(scope="module")
def calculation():return build()

def test_real_connected_shell_2_4_8_meshes_and_reactions(calculation):
    c=calculation
    assert c["schema"]=="jp.structural.r5.connected_shell_frame_FE.v0.1"
    assert c["mesh_sizes"]==[2,4,8]
    assert len(c["mesh_case_results"])==9
    assert c["source_total_gravity_kN"]==pytest.approx(128)
    assert c["source_seismic_weight_kN"]==pytest.approx(111.2)
    assert c["shell_elements_actual_connected_frame"] is True
    assert c["shared_edge_beam_shell_nodes"] is True
    for row in c["mesh_case_results"]:
        n=row["mesh_divisions"]
        assert row["shell_elements"]==n*n
        assert row["shell_nodes"]==(n+1)**2
        assert row["connected_boundary_beam_segments"]==4*n
        assert row["shell_to_beam_same_node_count"]==4*n
        assert row["member_end_vector_count"]==2*(4+4*n)
        assert row["global_equilibrium_pass"]
        assert max(abs(v) for v in row["global_force_moment_residual"].values())<1e-4
        assert row["source_seismic_weight_kN"]==pytest.approx(111.2)
        if row["case_id"]=="DL":
            assert row["applied_force_kN"][2]==pytest.approx(-104)
            assert row["support_reaction_total_Fz_kN"]==pytest.approx(104,abs=1e-4)
        if row["case_id"]=="LL":
            assert row["applied_force_kN"][2]==pytest.approx(-24)
            assert row["support_reaction_total_Fz_kN"]==pytest.approx(24,abs=1e-4)
        if row["case_id"]=="HX":
            assert row["applied_force_kN"][0]==pytest.approx(40)
            assert row["support_reaction_total_Fz_kN"]==pytest.approx(0,abs=1e-4)
    assert c["convergence_improvement"] is True
    assert all(v<0 for v in c["gravity_mesh_center_Uz_m"].values())

def test_mass_source_matches_prior_one_way_case_while_slab_gravity_path_differs(original,calculation):
    prior=one_way(original)
    assert calculation["source_audited_mass_SHA256"]==prior["source_mass_SHA256"]
    assert calculation["source_total_gravity_kN"]==prior["source_total_gravity_kN"]
    assert calculation["source_seismic_weight_kN"]==prior["source_seismic_weight_kN"]
    assert calculation["shell_elements_actual_connected_frame"]
    assert calculation["signed_combo_executed_on_connected_shell"] is False
    assert calculation["physical_diaphragm_constraint_tested"] is False

def test_shell_mesh_produces_real_numerical_center_deflection_under_pressure(calculation):
    r=calculation["gravity_mesh_center_Uz_m"]
    assert len(set(round(float(v),11) for v in r.values()))==3
    assert all(math.isfinite(v) and v<0 for v in r.values())
    dif=calculation["convergence_abs_displacement_differences_m"]
    assert len(dif)==2 and dif[1]<dif[0]
    assert dif[1]/abs(r["8"])<.20

def test_complete_signed_local_IJ_actions_of_connected_frame_members(calculation):
    for row in calculation["mesh_case_results"]:
        n=row["mesh_divisions"]
        d=row["signed_member_end_actions"]
        assert set(d)=={"BM1","BM2","BM3","BM4","COL1","COL2","COL3","COL4"}
        assert all(len(d[f"BM{i}"])==n for i in range(1,5))
        assert all(len(d[f"COL{i}"])==1 for i in range(1,5))
        for segments in d.values():
            for segment in segments:
                assert set(segment["I"])==set(segment["J"])=={"N","Vy","Vz","T","My","Mz"}
                assert all(math.isfinite(x) for end in ("I","J") for x in segment[end].values())

@pytest.mark.parametrize("change,expected",[
    (lambda x:x["model"]["nodes"][6].update(y=2.5),"rectangle|axis-aligned"),
    (lambda x:x["model"]["nodes"][5].update(z=2.8),"horizontal"),
    (lambda x:x["model"]["frame_members"][4].update(i_node="R2"),"topology"),
    (lambda x:x["source_loads"][0].update(pressure_kPa=-1),"positive"),
    (lambda x:x["model"].update(nodal_masses=[{"node_id":"R1","mx":1}]),"existing loads/mass"),
])
def test_unverified_source_geometry_mass_and_loads_fail_closed(original,change,expected):
    src=copy.deepcopy(original);change(src)
    with pytest.raises((ShellBridgeError,ValueError),match=expected):
        exact_reference(src)

def test_seven_original_chapters_eighteen_modules_and_original_F3_holds(calculation):
    assert [c["id"] for c in calculation["chapters"]]==[f"{i:02d}" for i in range(1,8)]
    assert {x["id"] for c in calculation["chapters"] for x in c["modules"]}=={
        *(f"M{i:02d}" for i in range(1,17)),"S17","S18"}
    assert calculation["original_F3_failure"]=="NOT SAFE IN ONE WAY SHEAR"
    assert calculation["full_floor_shell_or_original_building"] is False
    assert calculation["engineering_approval"] is False
    assert calculation["permit_eligible"] is False
    assert calculation["signed_combo_executed_on_connected_shell"] is False
