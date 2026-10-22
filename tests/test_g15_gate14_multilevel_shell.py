"""Gate14 multi-level ShellMITC4 numerical reproducibility and engineering HOLD."""
import math
from scripts.run_g15_gate14_multilevel_shell import build_plan, solve, MODES, PATCH_LEVELS

def test_gate14_two_level_topology_and_source_boundary():
    original,study,xy,extra,quads,area,walls=build_plan()
    assert PATCH_LEVELS==(1,2)
    assert len(original["column_positions_mm"])==23
    assert len(original["beam_edges"])==32
    assert len(quads)==4 and len(extra)==6
    assert math.isclose(area,17.874,abs_tol=1e-9)
    assert all(w["source_verified_wall"] is False for w in walls)

def test_gate14_matched_three_models_gravity_and_full_equilibrium():
    d=solve(summary_only=True)
    assert d["schema"]=="jp.structural.g15.gate14.multilevel_bay_shell_wall.v0.1"
    assert d["chosen_assumed_panel_levels"]==[1,2]
    assert d["source_grid_3d_beam_column_segments"]==165
    assert d["subdivided_3d_frame_segments"]==177
    assert d["shell_elements_across_assumed_levels"]==8
    assert len(d["cases"])==27 and len(d["comparisons"])==9
    assert set(c["mode"] for c in d["cases"])==set(MODES)
    assert math.isclose(d["patch_total_area_m2"],2*17.874,abs_tol=1e-8)
    assert math.isclose(d["patch_total_dead_kN"],2*17.874*5.13,abs_tol=1e-8)
    for c in d["cases"]:
        assert c["frame_local_signed_action_count"]==177
        assert c["force_and_moment_equilibrium_pass"] is True
        assert c["force_equilibrium_error_kN"]<.001
        assert c["moment_equilibrium_error_kNm"]<.001
        assert c["shell_mitc4_elements"]==(8 if c["mode"]=="SHELLMITC4_PATCH_2F" else 0)
    for c in (c for c in d["cases"] if c["case"]=="GRAVITY"):
        assert math.isclose(c["measured_panel_transverse_load_kN"],d["patch_total_dead_kN"],abs_tol=1e-8)
        assert math.isclose(c["applied_force_kN_xyz"][2],
              -(d["patch_total_dead_kN"]+d["uniform_beam_wall_line_load_sum_kN"]),abs_tol=.001)
    assert d["source_bay_geometry_repeated_on_real_floor_verified"] is False
    assert d["real_wall_locations_verified"] is False
    assert d["shells_represent_complete_building"] is False
    assert d["seismic_mass_reconciled"] is False
    assert d["engineering_approval"] is False
    assert d["source_F3_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"

def test_gate14_signed_actions_and_stiffness_without_mass_retuning():
    a=solve("ULS",summary_only=False)
    b=solve("SLS",summary_only=True)
    assert a["floor_seismic_weights_kN"]==b["floor_seismic_weights_kN"]
    assert all(len(c["full_frame_local_signed_actions"])==177 for c in a["cases"])
    assert all(len(f["signed"])==12 and all(math.isfinite(n) for n in f["signed"])
        for c in a["cases"] for f in c["full_frame_local_signed_actions"])
    def pick(d):
        return next(c for c in d["cases"] if c["mode"]=="SHELLMITC4_PATCH_2F" and c["case"]=="EQ_X_POS_EPOS")
    assert abs(pick(a)["roof_horizontal_displacement_mm"]-
               pick(b)["roof_horizontal_displacement_mm"])>1e-5
