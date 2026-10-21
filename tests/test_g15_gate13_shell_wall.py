"""Gate13 reproducibility, actual ShellMITC4 load transfer, signed member integrity."""
import math
from scripts.run_g15_gate13_shell_wall import solve,build_plan,MODES

def test_bounded_source_panel_and_assumed_wall_topology():
    old,study,xy,extra,quads,area,walls=build_plan()
    assert len(old["column_positions_mm"])==23
    assert len(old["beam_edges"])==32
    assert len(quads)==4 and len(extra)==6
    assert math.isclose(area,17.874,abs_tol=1e-9)
    assert len(walls)==7
    assert all(x["source_verified_wall"] is False for x in walls)

def test_three_matched_opensees_models_and_global_gravity_balance():
    d=solve(summary_only=True)
    assert len(d["cases"])==27
    assert len(d["comparisons"])==9
    assert set(x["mode"] for x in d["cases"])==set(MODES)
    assert d["source_grid_3d_beam_column_segments"]==165
    assert d["subdivided_3d_frame_segments"]==171
    assert d["shell_elements_on_one_trial_floor"]==4
    assert all(x["frame_local_signed_action_count"]==171 for x in d["cases"])
    assert all(x["force_equilibrium_error_kN"]<1e-3 and
               x["moment_equilibrium_error_kNm"]<1e-3 and
               x["force_and_moment_equilibrium_pass"] is True
               for x in d["cases"])
    gravity=[c for c in d["cases"] if c["case"]=="GRAVITY"]
    assert len(gravity)==3
    assert all(math.isclose(x["applied_force_kN_xyz"][2],
       -(d["patch_total_dead_kN"]+d["uniform_beam_wall_line_load_sum_kN"]),abs_tol=.001)
       for x in gravity)
    assert all(x["shell_mitc4_elements"]==(4 if x["mode"]=="SHELLMITC4_PATCH" else 0)
               for x in d["cases"])
    assert all(math.isclose(g["measured_panel_transverse_load_kN"],d["patch_total_dead_kN"],abs_tol=1e-8)
               for g in gravity)
    assert d["engineering_approval"] is False
    assert d["real_wall_locations_verified"] is False
    assert d["shells_represent_complete_building"] is False
    assert d["source_F3_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"

def test_stiffness_case_changes_shell_movement_without_changing_seismic_weight():
    a=solve("ULS",summary_only=True)
    b=solve("SLS",summary_only=True)
    assert a["floor_seismic_weights_kN"]==b["floor_seismic_weights_kN"]
    fa=next(x for x in a["cases"] if x["mode"]=="SHELLMITC4_PATCH" and x["case"]=="EQ_X_POS_EPOS")
    fb=next(x for x in b["cases"] if x["mode"]=="SHELLMITC4_PATCH" and x["case"]=="EQ_X_POS_EPOS")
    assert abs(fa["roof_horizontal_displacement_mm"]-fb["roof_horizontal_displacement_mm"])>1e-5

def test_full_signed_member_actions_reproducible():
    d=solve(summary_only=False)
    assert all(len(x["full_frame_local_signed_actions"])==171 for x in d["cases"])
    assert all(len(p["signed"])==12 and all(math.isfinite(v) for v in p["signed"])
               for x in d["cases"] for p in x["full_frame_local_signed_actions"])
