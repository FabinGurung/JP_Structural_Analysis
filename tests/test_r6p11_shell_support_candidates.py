"""R6.11 geometric candidates are never accepted as verified supports."""
from scripts.build_r6p10_source_shell_mesh import build
from scripts.r6p11_support_candidates import point_to_edge

def test_contact_projection_is_three_dimensional():
    t,d=point_to_edge([500,0.0005,0],[0,0,0],[1000,0,0])
    assert t==0.5 and d<0.001
    t,d=point_to_edge([2000,0,0],[0,0,0],[1000,0,0])
    assert t==2 and d==1000

def test_original_corners_and_solver_gates():
    result=build()
    a=result["r6p11_contact_audit"]
    assert result["shells_connected_through_source_to_fixed_base"]==103
    assert result["shells_without_verified_vertical_support_path"]==12
    assert a["candidate_source_corners"]==10 and len(a["groups"])==3
    assert a["source_tolerance_mm"]==0.001
    assert sum(len(g["candidates"]) for g in a["groups"])==10
    assert sum(g["geometric_matches"] for g in a["groups"])==10
    assert a["original_unsupported_shells"]==12 and a["unsupported_shells_still_excluded"]
    assert not a["support_gate_passed"] and not a["engineering_approval"]
    assert a["F3_one_way_shear_unsafe"] and result["source_F3_one_way_shear_unsafe"]
    assert not a["native_ETABS21_joint_mesh_constraint_output_verified"]
    assert not a["ETABS21_supported_gravity_reactions_verified"]
    for group in a["groups"]:
        assert not group["support_admitted"]
        for row in group["candidates"]:
            assert row["geometry_within_tolerance"]
            assert not row["gravity_vertical_transfer_verified"]
            assert not row["native_generated_joint_verified"]
            assert row["admission"]=="ENGINEERING_HOLD"
