"""R6.17 genuine source-graph/8-case signed reaction QA; no invented support."""
import math
from copy import deepcopy
import pytest
from scripts.build_r6p8_native_source_catalogue import build as source_catalogue
from scripts.run_r6p9_source_frame_gravity import controls as source_controls
from scripts.build_r6p10_source_shell_mesh import build as mesh_audit
from scripts.build_r6p10_gravity_casebook import build_casebook
from scripts.build_r6p17_canonical_source_graph import (
 canonical_topology,pt_segment_distance,gravity_reaction_audit,
 unsupported_diagnostics,build,nodekey
)

@pytest.fixture(scope="module")
def authority():
    native,controls=source_controls()
    mesh=mesh_audit()
    cases=build_casebook()
    return native,controls,mesh,cases

@pytest.fixture(scope="module")
def built(authority):
    native,ctrl,mesh,casebook=authority
    return build(model=native,control=ctrl,mesh=mesh,casebook=casebook)

def test_true_3d_distance_does_not_snap_points():
    distance,t=pt_segment_distance([3000,0,200],[0,0,0],[6000,0,0])
    assert distance==pytest.approx(200)
    assert t==pytest.approx(.5)
    assert pt_segment_distance([0,0,0],[0,0,0],[6000,0,0])[0]==0
    assert pt_segment_distance([7000,0,0],[0,0,0],[6000,0,0])[0]==1000
    with pytest.raises(ValueError,match="Degenerate"):pt_segment_distance([1,1,1],[0,0,0],[0,0,0])
    assert nodekey("23","GF")!="FF:23"

def test_every_original_node_and_shell_retained_without_new_restraint(authority,built):
    native,ctrl,mesh,casebook=authority
    c=built["counts"]
    assert c["source_points_catalogued"]==127
    assert c["source_frame_objects"]==165
    assert c["source_shell_objects"]==115
    assert c["canonical_source_graph_edges"]==625
    assert c["original_source_fixed_base_point_ids"]==27
    assert c["used_in_current_coarse_FE_fixed_base_nodes"]==21
    assert c["declared_fixed_base_ids_without_frame_shell_graph_node"]==6
    assert c["source_components"]==5
    assert c["components_with_original_fixed_base_path"]==2
    assert c["source_graph_connected_shells"]==103
    assert c["original_unanchored_shells_excluded"]==12
    assert len(built["canonical_nodes"])==c["canonical_source_graph_nodes"]
    assert len(built["individual_twelve_unanchored_shell_investigations"])==12
    assert len({s["shell_key"] for s in built["individual_twelve_unanchored_shell_investigations"]})==12
    assert len(built["source_topological_edges"])==625
    assert {s["key"] for s in built["canonical_original_shells"]}=={s["key"] for s in native["shells"]}
    assert {m["key"] for m in built["canonical_original_frames"]}=={
        m["key"] for m in native["members"] if m["kind"] in ("BEAM","COLUMN")}
    assert all(e["source_adjacency_only"] and not e["native_joint_compatibility_verified"]
               for e in built["source_topological_edges"])
    assert all(not x["accepted_load_bearing_source_path"]
               for x in built["canonical_original_shells"])
    assert all(not x["native_generated_mesh_verified"]
               for x in built["canonical_original_shells"])
    assert all(not x["admitted_to_solved_model"] and x["design_load_transfer_accepted"] is None
               for x in built["individual_twelve_unanchored_shell_investigations"])
    assert not built["no_new_fixed_restraints_or_beam_shell_ties_created"] is False
    assert built["no_source_unsupported_shell_was_added_to_solver"]
    assert not built["full_ETABS21_3D_model_reconstructed_and_validated"]
    assert built["F3_one_way_shear_unsafe"] and not built["engineering_approval"]

def test_all_original_solved_gravity_cases_have_21_signed_support_reactions(authority,built):
    rec=built["coarse_trial_signed_gravity_support_reactions"]
    assert len(rec)==8
    assert built["counts"]["signed_individual_base_reactions"]==168
    assert {(x["role"],x["original_source_gravity_pattern"]) for x in rec}=={
         (role,pat) for role in ("ULS","SLS")
         for pat in ("Dead","Live","WALL LOAD","FLOOR FINISH")}
    for x in rec:
        assert x["force_equilibrium_verified_for_bounded_model"]
        assert x["vertical_equilibrium_error_N"]<=x["vertical_equilibrium_tolerance_N"]
        assert len(x["signed_support_reactions"])==21
        assert sum(q["signed_Rxyz_kN"][2] for q in x["signed_support_reactions"])==pytest.approx(
            x["applied_gravity_downward_kN"],abs=0.0002)
        assert not x["source_model_reactions_accepted_for_final_footing_design"]
        assert not x["additional_supports_created"]
        assert all(not r["actual_ETABS21_support_reaction_verified"]
                   for r in x["signed_support_reactions"])
        assert all(len(r["signed_Mxyz_kNm"])==3 for r in x["signed_support_reactions"])

def test_misreported_source_reaction_and_support_are_rejected(authority):
    native,ctrl,mesh,cb=authority
    current=canonical_topology(native,ctrl)
    assert len(unsupported_diagnostics(native,current))==12
    altered=deepcopy(cb)
    q=altered["roles"]["ULS"]["independently_run_research_patterns"]["Dead"]
    q["connected_support_signed_reactions_research_only"][0]["signed_Fxyz_N"][2]+=1200
    with pytest.raises(ValueError,match="reaction ledger"):
        gravity_reaction_audit(altered,current)
    wrong=deepcopy(ctrl)
    wrong["roles"]["ULS"]["supports"]=wrong["roles"]["ULS"]["supports"][:-1]
    with pytest.raises(ValueError,match="Original 27"):
        canonical_topology(native,wrong)
