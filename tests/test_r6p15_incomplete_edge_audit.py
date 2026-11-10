"""R6.15 all 77 previously withheld slab-edge cases: geometry only."""
import math
import pytest
from scripts.build_r6p15_incomplete_edge_audit import (
    build, segment_union, classify_frame_edge, hypotheses_for_slab,
    incidental_edges, TARGET
)

def beam(name,start,end,storey="GF"):
    return {"key":name,"kind":"BEAM","storey":storey,
        "start_xyz_mm":start,"end_xyz_mm":end,
        "point_ids":[name+"1",name+"2"]}

def fixture_edge(full=(),partial=(),i=0):
    return {"edge_index":i,"edge_start_xyz_mm":[0,0,3048],
        "edge_end_xyz_mm":[6000,0,3048],"length_mm":6000.0,
        "corner_source_point_ids":["a","b"],
        "full_edge_candidate_beams":[{"beam_key":x,"match_type":"COINCIDENT_OR_SPANNING_GEOMETRY_ONLY"} for x in full],
        "partial_edge_candidate_beams":[{"beam_key":x,"match_type":"COINCIDENT_OR_SPANNING_GEOMETRY_ONLY"} for x in partial],
        "native_joint_or_edge_constraint_verified":False}

def test_interval_union_classifies_complete_chain_hole_and_overlap():
    complete=segment_union([(0,.5),(.5,1.)],6000)
    assert complete["covered_fraction"]==1
    assert complete["gaps"]==[]
    assert complete["overlap_length_mm"]==0
    hole=segment_union([(0,.5),(.55,1.)],6000)
    assert hole["total_gap_mm"]==pytest.approx(300)
    assert hole["gaps"]==[{"start_fraction":.5,"end_fraction":.55,"length_mm":300}]
    overlap=segment_union([(0,.60),(.50,1.)],6000)
    assert overlap["covered_fraction"]==1
    assert overlap["overlap_length_mm"]==pytest.approx(600)
    blank=segment_union([],6000)
    assert blank["total_gap_mm"]==pytest.approx(6000)
    assert blank["gaps"][0]["start_fraction"]==0
    with pytest.raises(ValueError):segment_union([(0,1)],0)

def test_source_beam_chain_cases_do_not_prove_actual_support():
    A=beam("GF:B1",[0,0,3048],[3000,0,3048])
    B=beam("GF:B2",[3000,0,3048],[6000,0,3048])
    catalogue={x["key"]:x for x in [A,B]}
    row=classify_frame_edge(fixture_edge(partial=["GF:B1","GF:B2"]),catalogue)
    assert row["frame_match_class"]=="COMPLETE_SEGMENTED_FRAME_CHAIN_GEOMETRIC_ONLY"
    assert row["geometric_complete_frame_alignment"]
    assert not row["source_edge_constraint_verified"]
    assert row["accepted_support_or_reaction"] is None
    catalogue["GF:B2"]=beam("GF:B2",[3200,0,3048],[6000,0,3048])
    row=classify_frame_edge(fixture_edge(partial=["GF:B1","GF:B2"]),catalogue)
    assert row["frame_match_class"]=="PARTIAL_FRAME_EDGE_WITH_GAP"
    assert row["partition"]["total_gap_mm"]==pytest.approx(200)
    assert not row["geometric_complete_frame_alignment"]
    catalogue["GF:B2"]=beam("GF:B2",[2800,0,3048],[6000,0,3048])
    row=classify_frame_edge(fixture_edge(partial=["GF:B1","GF:B2"]),catalogue)
    assert row["frame_match_class"]=="COMPLETE_BUT_OVERLAPPING_FRAME_SEGMENTS"
    assert row["partition"]["overlap_length_mm"]==pytest.approx(200)
    assert not row["geometric_complete_frame_alignment"]
    catalogue["GF:Bfull"]=beam("GF:Bfull",[0,0,3048],[6000,0,3048])
    row=classify_frame_edge(fixture_edge(full=["GF:Bfull"],partial=["GF:B1"]),catalogue)
    assert row["frame_match_class"]=="COMPETING_FULL_AND_PARTIAL_BEAMS"
    row=classify_frame_edge(fixture_edge(full=["GF:Bfull"]),catalogue)
    assert row["frame_match_class"]=="SINGLE_COMPLETE_FRAME_BEAM"
    catalogue["FF:B3"]=beam("FF:B3",[0,0,6096],[6000,0,6096],"FF")
    no=classify_frame_edge(fixture_edge(),catalogue)
    assert no["frame_match_class"]=="NO_COLLINEAR_FRAME_BEAM"

def sample_slab():
    return {"shell_key":"GF:Fsynthetic","story":"GF","kind":"FLOOR",
        "vertices_xyz_mm":[[0,0,3048],[6000,0,3048],
        [6000,4000,3048],[0,4000,3048]],
        "projected_area_m2":24.0,"source_graph_has_base_path":True,
        "true_area_ownweight_proxy_kN":60.,
        "original_source_assigned_resultants_kN":{"Live":24.,"FLOOR FINISH":12.}}

def edge_set(clean=(0,2),neighbors=()):
    rows=[]
    for i in range(4):
        rows.append({"edge_index":i,"edge_length_mm":6000 if i%2==0 else 4000,
            "frame_match_class":"SINGLE_COMPLETE_FRAME_BEAM" if i in clean else "NO_COLLINEAR_FRAME_BEAM",
            "geometric_complete_frame_alignment":i in clean,
            "full_frame_keys":["GF:B"+str(i)] if i in clean else [],
            "partial_frame_keys":[],
            "adjacent_floor_shells_geometric_only":[{"source_key":"GF:Fnear"}] if i in neighbors else []})
    return rows

def test_one_way_and_cantilever_are_only_hypothetical_and_force_conserving():
    slab=sample_slab()
    one=hypotheses_for_slab(slab,edge_set(clean=(0,2)))
    assert len(one)==1
    assert one[0]["scenario"]=="POSSIBLE_ONE_WAY_TWO_OPPOSITE_ALIGNED_FRAME_EDGES"
    assert one[0]["hypothetical_area_to_each_opposite_edge_m2"]==12
    assert one[0]["each_edge_example"]["source_uniform_resultants_half_kN"]["Live"]==12
    assert one[0]["normal_span_m"]==4
    assert not one[0]["physical_support_or_design_reaction_verified"]
    assert one[0]["not_redistributed_into_legacy_beam_case"]
    c=hypotheses_for_slab(slab,edge_set(clean=(0,)))
    assert len(c)==1
    assert c[0]["scenario"]=="POSSIBLE_CANTILEVER_SINGLE_ALIGNED_FRAME_ROOT"
    assert c[0]["normal_projection_m"]==4
    assert c[0]["hypothetical_uniform_load_root_M_kNm"]["GROSS_SELFWEIGHT_PROXY"]==120
    assert not c[0]["free_edge_and_root_fixity_verified"]
    assert hypotheses_for_slab(slab,edge_set(clean=(0,),neighbors=(1,)))==[]
    assert hypotheses_for_slab(slab,edge_set(clean=(0,1)))==[]
    without=dict(slab,source_graph_has_base_path=False)
    assert hypotheses_for_slab(without,edge_set(clean=(0,2)))==[]

def test_neighbouring_floor_and_nonstructural_line_are_not_promoted_to_beam():
    edge=fixture_edge()
    near={"key":"GF:F9","storey":"GF","kind":"FLOOR",
        "vertices_xyz_mm":[[0,0,3048],[6000,0,3048],[6000,-4000,3048],[0,-4000,3048]]}
    mismatched={"key":"FF:F9","storey":"FF","kind":"FLOOR",
        "vertices_xyz_mm":[[0,0,6096],[6000,0,6096],[6000,-4000,6096],[0,-4000,6096]]}
    result=incidental_edges(edge,[near,mismatched],
        {"story":"GF","type":"FLOOR_NEIGHBOUR","exclude_key":"GF:F0"})
    assert any(x["source_key"]=="GF:F9" for x in result)
    assert all(not x["structural_support_proven"] for x in result)
    assert not any(x["source_key"]=="FF:F9" for x in result)
    line={"key":"GF:L9","storey":"GF","kind":"LINE",
          "start_xyz_mm":[0,0,3048],"end_xyz_mm":[6000,0,3048]}
    result=incidental_edges(edge,[line],
        {"story":"GF","type":"NONSECTIONED_LINE","exclude_key":None})
    assert len(result)==1 and not result[0]["structural_support_proven"]

def test_all_77_governing_perimeters_exhaustive_without_making_design_reactions():
    d=build()
    assert d["schema"]=="jp.structural.r6p15.incomplete_slab_beam_edge_classification.v0.1"
    assert d["r614_baseline_status"]==TARGET
    assert d["baseline"]["shells"]==115
    assert d["baseline"]["r614_complete_four_edge_shells"]==25
    assert d["baseline"]["r614_withheld_incomplete_perimeter"]==77
    assert d["baseline"]["r614_other_withheld"]==13
    c=d["coverage"]
    assert c["slabs_examined"]==77
    assert c["source_edges_examined"]==308
    assert sum(c["by_story"].values())==77
    assert sum(c["review_group_counts"].values())==77
    assert sum(c["frame_edge_class_counts"].values())==308
    assert len({x["shell_key"] for x in d["cases"]})==77
    assert d["governing_ULS_SLS_input_SHA256"]=={
        "ULS":"8860223c80171cd7437b2d54841171f1bafe4ce98c71fd86024e2ec95d08aaa3",
        "SLS":"7b6ca674447e38302d0647d89fbca1830e7d120795ad260bcf926bb9d335227e"}
    assert d["F3_one_way_shear_unsafe"] and d["twelve_unsupported_shells_still_excluded"]
    assert not d["engineering_approval"] and not d["member_design_loads_modified"]
    assert not d["shell_contact_gate_promoted"] and not d["original_source_gravity_actions_modified"]
    assert not d["original_R614_45deg_allocations_modified"]
    for slab in d["cases"]:
        assert len(slab["edge_cases"])==4
        assert slab["historical_R614_status"]==TARGET
        assert slab["accepted_slab_to_beam_force_kN"] is None
        assert slab["verified_support_edges"] is None
        assert not slab["original_solver_frame_actions_modified"]
        assert not slab["native_ETABS21_generated_edge_connectivity_verified"]
        for e in slab["edge_cases"]:
            assert not e["source_edge_constraint_verified"]
            assert e["accepted_support_or_reaction"] is None
            assert not any(x["structural_support_proven"]
                for x in e["adjacent_floor_shells_geometric_only"])
            assert not any(x["structural_support_proven"]
                for x in e["coincident_unsectioned_SOURCE_LINE_not_a_beam"])
        for scenario in slab["provisional_scenarios"]:
            assert not scenario["physical_support_or_design_reaction_verified"]
            assert scenario["not_redistributed_into_legacy_beam_case"]
