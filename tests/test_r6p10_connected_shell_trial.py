"""R6.10 research-only real source shell/diaphragm finite element trial QA."""
import math
import pytest
from scripts.run_r6p10_connected_shell_gravity import rig,solve

def test_native_2x2_shell_mesh_includes_supported_103_shells_and_real_diaphragms():
    model=rig("ULS",2)
    assert len(model["frames"])==165
    assert len(model["cells"])==103
    assert sum(len(x) for x in model["cells"].values())==412
    assert set(model["masters"])=={"GF","FF","TF"}
    assert sum(d["original_source_point_assignments"] for d in model["diaphragms"])==201
    assert len(model["supports"])==21
    assert model["original_declared_supports"]==27
    assert len(model["unconnected_declared_source_support_ids"])==6
    model["ops"].wipe()

def test_uls_source_connected_shell_frame_dead_load_gravity_case_passes_reaction_equilibrium():
    s=solve("ULS","Dead",2)
    assert s["status"]=="INDEPENDENT_RESEARCH_CONNECTED_SHELL_FRAME_GRAVITY_NOT_FULL_SOURCE"
    assert s["role"]=="ULS" and s["source_case"]=="Dead"
    assert s["coarse_numerical_shell_elements"]==412
    assert s["original_frame_elements_included"]==165
    assert s["source_diaph_points"]==201
    assert s["vertical_equilibrium_residual_N"]<.05 or s["vertical_equilibrium_residual_N"]<s["applied_gravity"]["total_applied_downward_N"]*3e-5
    assert len(s["signed_member_end_actions_bounded"])==165
    assert all(len(v)==12 and all(math.isfinite(x) for x in v) for v in s["signed_member_end_actions_bounded"].values())
    assert not s["full_building_analysis"]
    assert not s["design_load_combination"] and not s["professional_engineer_approved"]
    assert s["F3_one_way_shear_unsafe"]
