"""R6.14 slab-to-beam source geometric candidate and strict withholding checks."""
import math
import pytest
from scripts.build_r6p14_tributary_reconciliation import (
    match_edge_to_beam,rectangle_geometry,rectangle_45deg_edge_areas,
    edge_matches,build)

def test_rectangular_45degree_tributary_areas_conserve_without_double_counting():
    slab=[[0,0,6096],[6000,0,6096],[6000,4000,6096],[0,4000,6096]]
    assert rectangle_geometry(slab)["eligible"]
    areas=rectangle_45deg_edge_areas(slab)
    assert areas==pytest.approx([8.0,4.0,8.0,4.0],abs=1e-8)
    assert sum(areas)==pytest.approx(24.0)
    square=[[0,0,6096],[4000,0,6096],[4000,4000,6096],[0,4000,6096]]
    assert rectangle_45deg_edge_areas(square)==pytest.approx([4.,4.,4.,4.])
    skew=[[0,0,6096],[6000,0,6096],[5500,4000,6096],[0,4000,6096]]
    assert rectangle_geometry(skew)["reason"]=="NON_RECTANGULAR_45_DEGREE_RULE_NOT_APPLICABLE"
    warped=[[0,0,6096],[6000,0,6096],[6000,4000,6120],[0,4000,6096]]
    assert rectangle_geometry(warped)["reason"]=="NON_HORIZONTAL_OR_WARPED_SLAB"
    with pytest.raises(ValueError):rectangle_45deg_edge_areas(skew)

def test_three_dimensional_edge_matches_do_not_become_joint_or_support_proof():
    u=[0,0,6096];v=[6000,0,6096]
    assert match_edge_to_beam(u,v,[0,0,6096],[6000,0,6096])["coverage"]=="FULL"
    assert match_edge_to_beam(u,v,[-1000,0,6096],[7000,0,6096])["coverage"]=="FULL"
    assert match_edge_to_beam(u,v,[0,0,6096],[3000,0,6096])["coverage"]=="PARTIAL"
    assert match_edge_to_beam(u,v,[6000,0,6096],[10000,0,6096])["coverage"]=="NONE"
    # Collocated in XY, not collocated in the actual model's Z: no match
    assert match_edge_to_beam(u,v,[0,0,3048],[6000,0,3048])["coverage"]=="NONE"
    assert match_edge_to_beam(u,v,[0,0,6096.01],[6000,0,6096.01])["coverage"]=="NONE"
    vertices=[u,v,[6000,4000,6096],[0,4000,6096]]
    beams=[{"storey":"FF","key":"FF:B3","point_ids":["a","b"],
            "start_xyz_mm":u,"end_xyz_mm":v}]
    matches=edge_matches(vertices,["a","b","c","d"],"FF",beams)
    assert len(matches)==4
    assert matches[0]["full_edge_candidate_beams"][0]["match_type"]=="EXACT_SOURCE_CORNER_PAIR"
    assert not matches[0]["native_joint_or_edge_constraint_verified"]
    assert all(not e["full_edge_candidate_beams"] for e in matches[1:])

def test_integrated_original_source_identity_and_no_unverified_load_transfer():
    x=build()
    assert x["schema"]=="jp.structural.r6p14.slab_beam_geometric_tributary_reconciliation.v0.1"
    c=x["coverage"]
    assert c["original_shells"]==115
    assert c["source_graph_shells_connected"]==103
    assert c["source_graph_shells_without_base_path"]==12
    assert c["conditional_complete_perimeter_shells"]+c["withheld_shells"]==115
    assert c["conditional_aggregate_beam_area_m2"]==pytest.approx(
        c["conditional_projected_area_m2"],abs=1e-5)
    assert c["beams_with_conditional_tributary_areas"]<=c["original_beams"]
    assert len({s["shell_key"] for s in x["shells"]})==115
    assert x["native_generated_joint_or_edge_constraint_verified"] is False
    assert x["physical_vertical_force_transfer_verified"] is False
    assert x["no_perimeter_inferred_from_point_contacts"]
    assert x["no_source_gravity_load_case_modified"]
    assert x["no_original_design_member_actions_modified"]
    assert x["twelve_unsupported_shells_excluded"]
    assert x["F3_one_way_shear_unsafe"] and x["engineering_approval"] is False
    for s in x["shells"]:
        assert not s["generated_ETABS_joint_connectivity_confirmed"]
        assert not s["verified_vertical_load_transfer"]
        assert s["accepted_design_beam_load_allocation_kN"] is None
        if s["status"].startswith("CONDITIONAL_"):
            assert len(s["conditional_45deg_geometry_allocations"])==4
            assert s["source_graph_has_base_path"]
            assert s["rectangle_rule"]=="RECTANGULAR_HORIZONTAL_SOURCE_GEOMETRY"
            assert len({e["beam_key"] for e in s["conditional_45deg_geometry_allocations"]})==4
            assert sum(e["area_m2"] for e in s["conditional_45deg_geometry_allocations"])==pytest.approx(
                s["projected_area_m2"],abs=5e-6)
            for e in s["conditional_45deg_geometry_allocations"]:
                assert not e["source_joint_constraint_proven"]
                assert not e["design_line_load_assigned_to_beam"]
        else:
            assert s["conditional_45deg_geometry_allocations"]==[]
    for b in x["beam_conditional_totals"]:
        assert b["approved_beam_load_kN"] is None
        assert not b["original_beam_design_force_modified"]
        assert not b["source_connectivity_proven"]
