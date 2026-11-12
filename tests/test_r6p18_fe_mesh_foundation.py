"""R6.18 real 3D FE mesh sensitivity, gravity moment equilibrium, source-footing holds."""
from copy import deepcopy
import math
import pytest
from scripts.build_r6p8_native_source_catalogue import build as native_source
from scripts.build_r6p10_gravity_casebook import build_casebook
from scripts.build_r6p17_canonical_source_graph import build as canonical_build
from scripts.build_r6p18_fe_mesh_foundation import (
    SCHEMA,build,boundary_nodes_of_shell,inspect_mesh_interfaces,
    compare_reaction_mesh,verify_case,create_foundation_reaction_register
)

@pytest.fixture(scope="module")
def source():
    return native_source(),canonical_build(),build_casebook()

@pytest.fixture(scope="module")
def audited(source):
    native,canonical,cases=source
    return build(canonical=canonical,model=native,casebook=cases)

def test_reconstructed_shell_boundary_grid_must_follow_original_3d_endpoints():
    polygon={"vertices_xyz_mm":[[0,0,3048],[4000,0,3048],
                               [4000,2000,3048],[0,2000,3048]]}
    for res in (2,4):
        grids=boundary_nodes_of_shell(polygon,res)
        assert len(grids)==4
        assert all(len(g)==res+1 for g in grids)
        assert grids[0][0]==(0.,0.,3048.) and grids[0][-1]==(4000.,0.,3048.)
        assert grids[0][1]==(4000/res,0.,3048.)
    with pytest.raises(ValueError):
        inspect_mesh_interfaces({"shells":[],"members":[]},
                                {"canonical_original_shells":[]},8)

def test_bounded_3d_coarse_solvers_all_eight_have_3_force_and_3_moment_balance(audited):
    d=audited
    assert d["schema"]==SCHEMA
    assert d["governing_ULS_SLS_input_SHA256"]=={
        "ULS":"8860223c80171cd7437b2d54841171f1bafe4ce98c71fd86024e2ec95d08aaa3",
        "SLS":"7b6ca674447e38302d0647d89fbca1830e7d120795ad260bcf926bb9d335227e"}
    c=d["counts"]
    assert c["original_frame_members"]==165
    assert c["original_shells"]==115
    assert c["source_graph_connected_shells"]==103
    assert c["original_unanchored_shells_excluded"]==12
    assert c["original_base_restraints_declared"]==27
    assert c["source_connected_research_support_nodes"]==21
    assert c["six_declared_base_points_unmatched"]==6
    assert c["source_graph_components"]==5
    assert c["baseline_gravity_cases_at_2x2"]==8
    assert c["additional_independently_solved_4x4_refinement_cases"]==2
    assert c["research_signed_base_reaction_records_2x2"]==168
    assert c["research_signed_base_reaction_records_4x4"]==42
    assert (c["research_shell_elements_2x2"],c["research_shell_elements_4x4"])==(412,1648)
    cases=d["original_source_connected_2x2_gravity_cases_and_six_axis_equilibrium"]
    assert len(cases)==8
    assert {(q["role"],q["source_gravity_pattern"]) for q in cases}=={
        (r,p) for r in ("ULS","SLS") for p in ("Dead","Live","WALL LOAD","FLOOR FINISH")}
    for case in cases:
        assert case["all_three_force_and_moment_axes_reconciled"]
        assert max(case["gravity_force_residual_N"])<=case["gravity_force_tolerance_N"]
        assert max(case["gravity_moment_residual_Nmm"])<=case["gravity_moment_tolerance_Nmm"]
        assert len(case["signed_source_mapped_support_reactions"])==21
        assert case["coarse_elements"]==412
        assert not case["foundation_design_reactions_accepted"]
        assert not case["actual_ETABS21_native_results_equivalent"]
    assert d["r6p18_research_force_and_moment_equilibrium_checked"]
    assert not d["engineering_approval"]
    assert d["historical_F3_one_way_shear_unsafe"]
    assert not d["complete_independent_physical_FE_model_accepted"]

def test_independent_full_4x4_bounded_refinements_and_convergence_status(audited):
    d=audited
    fine=d["independently_solved_4x4_refinements"]
    assert len(fine)==2
    assert {(x["role"],x["source_gravity_pattern"]) for x in fine}=={
        ("ULS","Dead"),("SLS","Live")}
    assert len(d["research_mesh_sensitivity_comparisons"])==2
    for case in fine:
        assert case["coarse_elements"]==1648
        assert len(case["signed_source_mapped_support_reactions"])==21
        assert max(case["gravity_force_residual_N"])<=case["gravity_force_tolerance_N"]
        assert max(case["gravity_moment_residual_Nmm"])<=case["gravity_moment_tolerance_Nmm"]
    for compare in d["research_mesh_sensitivity_comparisons"]:
        assert compare["source_point_reaction_matching"]==21
        assert compare["coarse_research_shell_elements"]==412
        assert compare["fine_research_shell_elements"]==1648
        assert len(compare["support_level_differences"])==21
        assert not compare["complete_numerical_mesh_convergence_proven"]
        assert not compare["native_ETABS21_mesh_and_joint_topology_verified"]
        assert compare["mesh_sensitivity_review_status"] in (
          "BOUNDED_NUMERICAL_SCREEN_ONLY_NOT_PHYSICAL_MODEL_CONVERGENCE",
          "STILL_MESH_SENSITIVE_REQUIRES_MORE_REFINEMENT_AND_REVIEW"
        )

def test_canonical_original_identity_and_unconnected_shells_remain_excluded(audited):
    d=audited
    link=d["shell_frame_boundary_alignment_by_mesh_size"]
    assert set(link)=={"2","4"}
    assert all(e["source_connected_original_shells_examined"]==103 for e in link.values())
    for level in ("2","4"):
        records=link[level]["geometric_contacts"]
        assert len(records)==link[level]["source_frame_endpoint_to_shell_boundary_encounters"]
        assert sum(link[level]["by_geometry_class"].values())==len(records)
        assert all(not x["native_ETABS_joint_and_support_constraint_verified"] and
                   not x["shell_frame_support_or_load_transfer_accepted"] for x in records)
    assert not d["source_frame_shell_ties_physically_verified"]
    assert not d["original_ETABS21_8x8_native_analysis_mesh_reproduced"]
    assert d["new_constraint_or_support_from_spatial_nearness"] is False
    assert not d["complete_design_gravity_load_combinations_reproduced"]
    assert not d["original_F3_CF1_source_support_correspondence_verified"]
    unsupported=d["twelve_unconnected_original_shell_holds"]
    assert len(unsupported["excluded_source_shell_ids"])==12
    assert unsupported["source_unanchored_shells_added_to_FE"]==0
    assert all(r["excluded_from_numerical_analyses"] and
               not r["source_mesh_connection_approved"]
               for r in unsupported["original_floating_shell_source_details"])
    collision=d["source_node_identity_vs_3D_coordinate_collision_audit"]
    assert not collision["original_nodes_merged_as_verified_structural_joints"]

def test_21_source_supports_do_not_pretend_to_be_known_footings(audited):
    d=audited
    foundation=d["unapproved_original_base_point_to_foundation_reaction_register"]
    assert len(foundation)==21
    assert len({x["original_source_support_point_id"] for x in foundation})==21
    for row in foundation:
        assert len(row["research_case_signed_reactions"])==8
        assert row["source_footing_id"] is None
        assert row["historical_F3_or_CF1_correspondence"] is None
        assert row["approved_foundation_reaction_or_capacity"] is None
        assert not row["can_use_for_construction_design"]

def test_false_solver_reactions_are_rejected_even_if_vertical_sum_preserved(source):
    native,canonical,book=source
    baseline=book["role_results"]["ULS"]["independently_run_research_patterns"]["Dead"]
    broken=deepcopy(baseline)
    broken["connected_support_signed_reactions_research_only"][0]["signed_Fxyz_N"][0]+=500
    with pytest.raises(ValueError,match="Three-axis"):
        verify_case(broken,"ULS","Dead",2)
    broken=deepcopy(baseline)
    broken["sum_support_global_reaction_moments_Nmm"][1]+=100000
    with pytest.raises(ValueError,match="moment arithmetic"):
        verify_case(broken,"ULS","Dead",2)
    broken=deepcopy(baseline)
    broken["original_unsupported_shells_numerically_excluded"]=11
    with pytest.raises(ValueError,match="input scope"):
        verify_case(broken,"ULS","Dead",2)
    missing=deepcopy(audited_comparison_like(baseline))
    missing["signed_source_mapped_support_reactions"]=missing["signed_source_mapped_support_reactions"][:-1]
    with pytest.raises(ValueError,match="support set"):
        compare_reaction_mesh(audited_comparison_like(baseline),missing)

def audited_comparison_like(raw):
    return verify_case(raw,raw["role"],raw["source_case"],2)
