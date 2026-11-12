"""Synthetic R6.19 evidence gate tests; no client ETABS/Drive files are used."""
from copy import deepcopy

import pytest

from jp_structural.validation.native_support_evidence import (
    EXPORT_SCHEMA, SCHEMA, build_readiness, public_receipt
)


def synthetic_prior():
    source = {"ULS": "a" * 64, "SLS": "b" * 64}
    shells = [
        {"key": f"S{i:03}", "nodes": [f"FF:p{i}_{j}" for j in range(4)]}
        for i in range(1, 116)
    ]
    disconnected = shells[-12:]
    canonical = {
        "governing_ULS_SLS_input_SHA256": source,
        "F3_one_way_shear_unsafe": True,
        "engineering_approval": False,
        "canonical_original_frames": [{"key": "B1"}],
        "canonical_original_shells": shells,
        "individual_twelve_unanchored_shell_investigations": [
            {"shell_key": row["key"]} for row in disconnected
        ],
        "original_fixed_base_ids": [str(i) for i in range(1, 28)],
    }
    encounters = [
        {"source_shell_key": "S104", "source_frame_key": "B1",
         "frame_endpoint_index": 0, "shell_boundary_index": i % 4,
         "geometry_class": "HANGING_FRAME_ENDPOINT_ON_RESEARCH_SHELL_EDGE"}
        for i in range(15)
    ]
    fe = {
        "governing_ULS_SLS_input_SHA256": source,
        "historical_F3_one_way_shear_unsafe": True,
        "engineering_approval": False,
        "counts": {
            "source_graph_connected_shells": 103,
            "original_unanchored_shells_excluded": 12,
            "source_connected_research_support_nodes": 21,
            "original_base_restraints_declared": 27,
        },
        "unapproved_original_base_point_to_foundation_reaction_register": [
            {"original_source_support_point_id": str(i),
             "source_footing_id": None,
             "approved_foundation_reaction_or_capacity": None}
            for i in range(1, 22)
        ],
        "shell_frame_boundary_alignment_by_mesh_size": {
            "2": {"geometric_contacts": encounters,
                  "source_frame_endpoint_to_shell_boundary_encounters": 15},
            "4": {"geometric_contacts": []},
        },
    }
    return canonical, fe


def native_candidate(canonical):
    shell = canonical["canonical_original_shells"][-12]
    corners = shell["nodes"]
    return {
        "schema": EXPORT_SCHEMA,
        "governing_source_sha256": dict(canonical["governing_ULS_SLS_input_SHA256"]),
        "export_file_sha256": "c" * 64,
        "source_software": "ETABS21",
        "length_unit": "mm",
        "export_method": "ETABS API native joint + mesh table",
        "source_receipt_ref": "private:source-receipt",
        "analysis_joints": [
            {"analysis_joint_id": "p" + str(i),
             "xyz_mm": [1000.0 * i, 0.0, 3000.0]} for i in range(4)
        ] + [{"analysis_joint_id": "b1", "xyz_mm": [0.0, 0.0, 0.0]}],
        "original_node_to_analysis_joint": [
            {"source_node_key": key, "analysis_joint_id": f"p{i}",
             "native_export_record_ref": f"joint-row-{i}"}
            for i, key in enumerate(corners)
        ] + [
            {"source_node_key": "Plinth level:1", "analysis_joint_id": "b1",
             "native_export_record_ref": "joint-row-base"}
        ],
        "explicit_native_joint_merges": [],
        "native_element_edges": [
            {"joint_i": "p0", "joint_j": "b1", "kind": "FRAME",
             "original_object_key": "B1",
             "native_element_record_ref": "frame-export-1"}
        ],
        "native_base_restraints": [
            {"original_base_point_id": "1", "analysis_joint_id": "b1",
             "restraint_record_ref": "support-row-1"}
        ],
        "native_shell_joint_maps": [
            {"source_shell_key": shell["key"],
             "analysis_joint_ids": ["p0", "p1", "p2", "p3"],
             "native_shell_record_ref": "area-mesh-export-1"}
        ],
    }


def test_missing_native_export_does_not_promote_nearby_research_shell_or_footing():
    canonical, fe = synthetic_prior()
    report = build_readiness(canonical, fe)
    assert report["schema"] == SCHEMA
    assert not report["native_export_supplied"]
    assert report["counts"] == {
        "original_source_shells": 115,
        "connected_shells_in_existing_bounded_FE": 103,
        "unsupported_original_shells_held": 12,
        "unresolved_research_2x2_hanging_frame_edge_encounters": 15,
        "original_base_restraints_declared": 27,
        "original_support_points_with_bounded_research_reactions": 21,
        "source_base_points_not_associated_with_research_reactions": 6,
        "original_source_footings_verified": 0,
        "native_source_paths_requiring_engineer_review": 0,
    }
    assert len(report["twelve_original_shell_dispositions"]) == 12
    assert len(report["research_hanging_frame_edge_review"]) == 15
    assert all(row["engineering_decision"] == "HOLD"
               for row in report["twelve_original_shell_dispositions"])
    assert not report["model_authorised_for_footing_design"]
    assert not report["model_authorised_for_governing_member_design"]
    assert report["original_F3_one_way_shear_unsafe"]
    assert not report["release_authorised"]
    assert public_receipt(report)["engineering_approval"] is False


def test_native_analysis_path_is_only_candidate_and_never_solver_approval():
    canonical, fe = synthetic_prior()
    export = native_candidate(canonical)
    report = build_readiness(canonical, fe, export)
    assert report["native_export_supplied"]
    assert report["counts"]["native_source_paths_requiring_engineer_review"] == 1
    assert report["native_export_candidate_metadata"]["mapped_original_base_restraints"] == 1
    assert len(report["native_export_candidate_metadata"][
        "unmapped_original_base_restraint_ids"]) == 26
    assert sum(r["engineering_decision"] == "REVIEW_NATIVE_PATH_CANDIDATE"
               for r in report["twelve_original_shell_dispositions"]) == 1
    assert report["new_source_unsupported_shells_accepted"] == 0
    assert not report["engineering_approval"]
    assert "export_file_sha256" not in str(report)
    assert export["source_receipt_ref"] not in str(report)


def test_no_source_manifest_or_F3_unsafe_can_be_cleared_by_export():
    canonical, fe = synthetic_prior()
    export = native_candidate(canonical)
    export["governing_source_sha256"]["ULS"] = "f" * 64
    with pytest.raises(ValueError, match="governing ULS/SLS"):
        build_readiness(canonical, fe, export)
    canonical, fe = synthetic_prior()
    fe["historical_F3_one_way_shear_unsafe"] = False
    with pytest.raises(ValueError, match="F3"):
        build_readiness(canonical, fe)


def test_original_base_reactions_cannot_be_relabelled_verified_foundation_for_free():
    canonical, fe = synthetic_prior()
    fe["unapproved_original_base_point_to_foundation_reaction_register"][0][
        "source_footing_id"] = "F3"
    with pytest.raises(ValueError, match="silently approved"):
        build_readiness(canonical, fe)


def test_nearest_coordinate_is_not_native_joint_correspondence():
    canonical, fe = synthetic_prior()
    export = native_candidate(canonical)
    export["original_node_to_analysis_joint"][1]["analysis_joint_id"] = "p0"
    with pytest.raises(ValueError, match="joint merger"):
        build_readiness(canonical, fe, export)
    export = native_candidate(canonical)
    export["native_element_edges"][0]["kind"] = "EXPORTED_CONSTRAINT"
    with pytest.raises(ValueError, match="exported constraint receipt"):
        build_readiness(canonical, fe, export)


def test_corrupt_native_shell_mesh_and_unregistered_support_are_fail_closed():
    canonical, fe = synthetic_prior()
    export = native_candidate(canonical)
    export["native_shell_joint_maps"][0]["analysis_joint_ids"] = ["p0", "p1", "p2", "b1"]
    with pytest.raises(ValueError, match="shell corner"):
        build_readiness(canonical, fe, export)
    export = native_candidate(canonical)
    export["native_base_restraints"][0]["original_base_point_id"] = "99"
    with pytest.raises(ValueError, match="restraint"):
        build_readiness(canonical, fe, export)


def test_export_does_not_use_research_reaction_sum_as_native_support_proof():
    canonical, fe = synthetic_prior()
    export = native_candidate(canonical)
    export["native_element_edges"].clear()
    report = build_readiness(canonical, fe, export)
    assert report["counts"]["native_source_paths_requiring_engineer_review"] == 0
    assert not report["engineering_approval"]
    assert not report["model_authorised_for_footing_design"]
