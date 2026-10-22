"""Gate15 FEM shell mesh and explicitly hypothetical opening sensitivity."""
import math
from scripts.run_g15_gate15_mesh_opening import MODES, build_plan, mesh_for, solve

def test_three_mesh_topologies_source_geometry_and_normals():
    old,study,xy,extra,quads,area,walls=build_plan()
    assert len(old["column_positions_mm"])==23
    assert len(old["beam_edges"])==32
    assert math.isclose(area,17.874,abs_tol=1e-8)
    expected=[(2,4,17.874),(4,16,17.874),(4,12,17.874*.75)]
    for mode,(n,q,active) in zip(MODES,expected):
        m=mesh_for(mode,xy)
        assert m["n"]==n and len(m["quads"])==q
        assert math.isclose(m["active_area_per_level_m2"],active,abs_tol=1e-8)
        assert m["source_location_verified"] is False
    assert all(not w["source_verified_wall"] for w in walls)

def test_matched_refined_full_mesh_and_conditional_opening_gravity():
    d=solve(summary_only=True)
    assert d["schema"]=="jp.structural.g15.gate15.mesh_opening_source_bay.v0.1"
    assert len(d["cases"])==27 and len(d["comparisons"])==9
    assert [v["active_shells"] for v in d["models"]]==[8,32,24]
    assert math.isclose(d["estimated_conditional_mass_deduction_both_floors_kN"],45.84681,abs_tol=1e-6)
    assert math.isclose(d["trial_mass_without_aperture_kN"]-
                        d["trial_mass_with_aperture_kN"],45.84681,abs_tol=1e-6)
    for mode,nframe,nshell in zip(MODES,[177,193,193],[8,32,24]):
        sub=[c for c in d["cases"] if c["mode"]==mode]
        assert len(sub)==9
        assert all(c["source_physical_frame_members"]==165 for c in sub)
        assert all(c["frame_local_signed_action_count"]==nframe for c in sub)
        assert all(c["shell_mitc4_elements"]==nshell for c in sub)
        assert all(c["force_and_moment_equilibrium_pass"] is True and
                   c["force_equilibrium_error_kN"]<.001 and
                   c["moment_equilibrium_error_kNm"]<.001 for c in sub)
        gravity=next(c for c in sub if c["case"]=="GRAVITY")
        full_gravity=2*17.874*5.13*(.75 if mode==MODES[2] else 1.)
        assert math.isclose(gravity["measured_panel_transverse_load_kN"],full_gravity,abs_tol=1e-6)
        assert math.isclose(gravity["applied_force_kN_xyz"][2],
              -(full_gravity+d["uniform_beam_wall_line_load_sum_kN"]),abs_tol=.001)
    assert next(c for c in d["cases"] if c["mode"]==MODES[0])["conditional_seismic_floor_weights_kN"] == next(
        c for c in d["cases"] if c["mode"]==MODES[1])["conditional_seismic_floor_weights_kN"]
    assert d["opening_geometry_and_structural_trim_verified"] is False
    assert d["mesh_convergence_verified"] is False
    assert d["mass_source_reconciled"] is False
    assert d["full_floor_slab_geometry_verified"] is False
    assert d["source_F3_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"
    assert d["engineering_approval"] is False

def test_all_signed_member_actions_and_no_invented_mass_match():
    d=solve(summary_only=False)
    for c in d["cases"]:
        f=c["full_frame_local_signed_actions"]
        assert len(f)==c["frame_local_signed_action_count"]
        assert all(len(v["signed"])==12 and all(math.isfinite(x) for x in v["signed"]) for v in f)
    assert not math.isclose(d["trial_mass_with_aperture_kN"],
                            d["reported_source_ETABS_seismic_weight_kN"],abs_tol=1.0)
    assert all(v["refinement_convergence_verified"] is False for v in d["comparisons"])
