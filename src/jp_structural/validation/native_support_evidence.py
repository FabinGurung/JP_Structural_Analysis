"""R6.19: source-to-native connectivity evidence gate (no numerical or design approval).

This module consumes a *private* exported native-analysis topology in memory.
Only the source-bounded, non-sensitive hold summary should be published.  A
coordinate match, source point number, or a successfully solved research FE
model is never treated as proof of a physical joint or foundation identity.
"""
from __future__ import annotations

from collections import defaultdict, deque
from hashlib import sha256
import json
import math
import re
from typing import Any

SCHEMA = "jp.structural.r6p19.native_connection_evidence_gate.v0.1"
EXPORT_SCHEMA = "jp.structural.native_etabs21_topology_export.v0.1"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED = {"FRAME", "SHELL", "EXPORTED_CONSTRAINT"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _ids(rows: list[dict], field: str) -> list[str]:
    return [str(row[field]) for row in rows]


def _valid_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256.fullmatch(value))


def _native_export_candidate(export: dict, source_hashes: dict,
                             unsupported: set[str], all_frames: set[str],
                             declared_base: set[str], source_corner_keys: dict) -> dict:
    """A complete topology export is a review CANDIDATE, not authenticated design."""
    _require(export.get("schema") == EXPORT_SCHEMA, "Wrong native export schema")
    _require(export.get("governing_source_sha256") == source_hashes,
             "Native export does not match the governing ULS/SLS files")
    _require(_valid_sha(export.get("export_file_sha256")),
             "Native export requires a full byte-level SHA256 receipt")
    _require(export.get("source_software") == "ETABS21",
             "A non-native research model cannot attest ETABS21 joints")
    _require(export.get("length_unit") == "mm", "Native joint coordinates must use mm")
    _require(bool(export.get("export_method")) and bool(export.get("source_receipt_ref")),
             "Native API/export method and private original receipt are required")

    nodes = {}
    for row in export.get("analysis_joints", []):
        nid = str(row.get("analysis_joint_id", ""))
        xyz = row.get("xyz_mm")
        _require(nid and nid not in nodes, "Missing/duplicate native analysis joint ID")
        _require(isinstance(xyz, list) and len(xyz) == 3
                 and all(isinstance(v, (int, float)) and
                         not isinstance(v, bool) and math.isfinite(v) for v in xyz),
                 "Invalid native analysis joint XYZ")
        nodes[nid] = xyz
    _require(len(nodes) >= 1, "Native export contains no analysis joints")

    mapping = {}
    reverse = defaultdict(list)
    for row in export.get("original_node_to_analysis_joint", []):
        source = str(row.get("source_node_key", ""))
        nid = str(row.get("analysis_joint_id", ""))
        _require(source and source not in mapping and nid in nodes,
                 "Original source identity has duplicate/missing joint mapping")
        _require(bool(row.get("native_export_record_ref")),
                 "Every original-node correspondence requires an export record ref")
        mapping[source] = nid
        reverse[nid].append(source)
    merges = set()
    for row in export.get("explicit_native_joint_merges", []):
        nid = str(row.get("analysis_joint_id", ""))
        sources = tuple(sorted(str(s) for s in row.get("source_node_keys", [])))
        _require(nid in nodes and len(sources) >= 2 and bool(row.get("export_record_ref")),
                 "A native joint merge needs an explicit exported joint record")
        _require(set(sources) == set(reverse[nid]),
                 "Declared joint merger must exactly match original identities")
        merges.add(nid)
    _require(all(len(v) == 1 or k in merges for k, v in reverse.items()),
             "Coordinate/source-point joint merger was not explicitly proven")

    adj = defaultdict(list)
    for row in export.get("native_element_edges", []):
        a = str(row.get("joint_i", ""))
        b = str(row.get("joint_j", ""))
        kind = row.get("kind")
        original = str(row.get("original_object_key", ""))
        _require(a in nodes and b in nodes and a != b and kind in _ALLOWED,
                 "Invalid native analysis element edge")
        if kind == "FRAME":
            _require(original in all_frames,
                     "Native frame edge lacks matching original frame identity")
        if kind == "SHELL":
            _require(original in source_corner_keys,
                     "Native shell edge lacks matching original shell identity")
        if kind == "EXPORTED_CONSTRAINT":
            _require(bool(row.get("native_constraint_record_ref")),
                     "No invented edge tie: exported constraint receipt is required")
        _require(bool(row.get("native_element_record_ref")),
                 "Every native edge must have an exported element record ref")
        adj[a].append((b, kind))
        adj[b].append((a, kind))

    restraint_map = {}
    for row in export.get("native_base_restraints", []):
        pid = str(row.get("original_base_point_id", ""))
        joint = str(row.get("analysis_joint_id", ""))
        _require(pid in declared_base and pid not in restraint_map
                 and joint in nodes and joint == mapping.get("Plinth level:" + pid),
                 "Original declared source restraint / native joint mismatch")
        _require(bool(row.get("restraint_record_ref")),
                 "Native fixed restraint requires its own source API receipt")
        restraint_map[pid] = joint

    shell_joints = {}
    for row in export.get("native_shell_joint_maps", []):
        sid = str(row.get("source_shell_key", ""))
        joints = [str(n) for n in row.get("analysis_joint_ids", [])]
        _require(sid in source_corner_keys and sid not in shell_joints
                 and len(joints) >= 4 and len(set(joints)) >= 4
                 and all(n in nodes for n in joints),
                 "Native shell map is incomplete/duplicate or references unknown joint")
        _require(bool(row.get("native_shell_record_ref")),
                 "Native shell map requires a native mesh export record")
        source_corners = source_corner_keys[sid]
        _require(all(k in mapping and mapping[k] in joints for k in source_corners),
                 "Source shell corner IDs not present in exported native shell mesh")
        shell_joints[sid] = joints

    def path_to_base(starts: list[str]) -> list[str] | None:
        # The path must genuinely cross at least one exported FRAME edge before
        # reaching a mapped, restrained ORIGINAL source base joint.
        targets = set(restraint_map.values())
        queue = deque((n, False, [n]) for n in starts)
        seen = {(n, False) for n in starts}
        while queue:
            node, crossed_frame, path = queue.popleft()
            if node in targets and crossed_frame:
                return path
            for next_node, kind in adj[node]:
                state = (next_node, crossed_frame or kind == "FRAME")
                if state not in seen:
                    seen.add(state)
                    queue.append((next_node, state[1], path + [next_node]))
        return None

    shell_rows = []
    for sid in sorted(unsupported):
        joints = shell_joints.get(sid)
        path = path_to_base(joints) if joints else None
        shell_rows.append({
            "source_shell_key": sid,
            "native_export_shell_mesh_identified": joints is not None,
            "exported_frame_path_to_original_base_candidate": bool(path),
            "geometric_proximity_used_as_tie": False,
            "verified_by_independent_engineer": False,
            "admitted_to_current_research_FE_model": False,
            "engineering_decision": "REVIEW_NATIVE_PATH_CANDIDATE" if path else "HOLD"
        })
    return {
        "source_export_receipt_sha256": export["export_file_sha256"],
        "exported_analysis_joint_count": len(nodes),
        "exported_analysis_edge_count": sum(map(len, adj.values())) // 2,
        "mapped_original_base_restraints": len(restraint_map),
        "unmapped_original_base_restraint_ids": sorted(declared_base - set(restraint_map)),
        "original_unsupported_shells_with_native_frame_path_candidate":
            sum(r["exported_frame_path_to_original_base_candidate"] for r in shell_rows),
        "unsupported_shell_native_evidence": shell_rows,
        "source_original_restraints_altered_by_a_new_assumption": False,
        "native_export_complete_for_all_27_original_base_restraints":
            len(restraint_map) == len(declared_base),
        "professional_design_or_physical_connectivity_accepted": False,
    }


def build_readiness(canonical: dict, research_fe: dict,
                    native_export: dict | None = None) -> dict:
    """Emit a public-safe backlog.  Private exports are never copied to output."""
    expected = canonical["governing_ULS_SLS_input_SHA256"]
    _require(research_fe["governing_ULS_SLS_input_SHA256"] == expected,
             "R6.17/R6.18 governing source SHA mismatch")
    _require(canonical["F3_one_way_shear_unsafe"] is True
             and research_fe["historical_F3_one_way_shear_unsafe"] is True
             and canonical["engineering_approval"] is False
             and research_fe["engineering_approval"] is False,
             "Source F3 or engineering HOLD has been changed")
    shells = canonical["individual_twelve_unanchored_shell_investigations"]
    unsupported = set(_ids(shells, "shell_key"))
    _require(len(shells) == len(unsupported) == 12,
             "All twelve source graph unsupported shells must be preserved")
    _require(research_fe["counts"]["source_graph_connected_shells"] == 103
             and research_fe["counts"]["original_unanchored_shells_excluded"] == 12
             and research_fe["counts"]["source_connected_research_support_nodes"] == 21
             and research_fe["counts"]["original_base_restraints_declared"] == 27,
             "R6.18 original model/support scope changed")
    foundation_rows = research_fe[
        "unapproved_original_base_point_to_foundation_reaction_register"]
    base_ids = set(_ids(foundation_rows, "original_source_support_point_id"))
    _require(len(base_ids) == len(foundation_rows) == 21,
             "21 original source-point reaction records required")
    _require(all(r["source_footing_id"] is None and
                 r["approved_foundation_reaction_or_capacity"] is None
                 for r in foundation_rows), "Research footing reactions were silently approved")

    contact_sets = research_fe["shell_frame_boundary_alignment_by_mesh_size"]
    _require(set(contact_sets) == {"2", "4"}, "Required mesh interface ledgers missing")
    contacts = contact_sets["2"]["geometric_contacts"]
    hanging = [r for r in contacts if
               r["geometry_class"] == "HANGING_FRAME_ENDPOINT_ON_RESEARCH_SHELL_EDGE"]
    _require(len(contacts) == contact_sets["2"]["source_frame_endpoint_to_shell_boundary_encounters"],
             "R6.18 interface encounter count mismatch")

    all_frames = {r["key"] for r in canonical["canonical_original_frames"]}
    all_shells = {r["key"] for r in canonical["canonical_original_shells"]}
    _require(unsupported <= all_shells, "Unanchored shell not found in canonical register")
    corner_keys = {r["key"]: list(r["nodes"])
                   for r in canonical["canonical_original_shells"]}
    declared = set(str(i) for i in canonical["original_fixed_base_ids"])
    _require(len(declared) == 27 and base_ids <= declared,
             "Canonical declared source base inventory mismatch")

    native = (_native_export_candidate(native_export, expected, unsupported,
                                       all_frames, declared, corner_keys)
              if native_export is not None else None)
    shell_records = (native["unsupported_shell_native_evidence"] if native else [
        {"source_shell_key": sid, "native_export_shell_mesh_identified": False,
         "exported_frame_path_to_original_base_candidate": False,
         "verified_by_independent_engineer": False,
         "admitted_to_current_research_FE_model": False,
         "engineering_decision": "HOLD"} for sid in sorted(unsupported)])
    return {
        "schema": SCHEMA,
        "governing_source_sha256": expected,
        "source_model_kind": "RESEARCH_ONLY_PENDING_AUTHENTICATED_NATIVE_ETABS21_CONNECTIVITY",
        "native_export_supplied": native is not None,
        "native_export_candidate_metadata": (None if native is None else
            {k: v for k, v in native.items()
             if k not in {"unsupported_shell_native_evidence",
                          "source_export_receipt_sha256"}}),
        "counts": {
            "original_source_shells": len(all_shells),
            "connected_shells_in_existing_bounded_FE": 103,
            "unsupported_original_shells_held": len(unsupported),
            "unresolved_research_2x2_hanging_frame_edge_encounters": len(hanging),
            "original_base_restraints_declared": len(declared),
            "original_support_points_with_bounded_research_reactions": len(base_ids),
            "source_base_points_not_associated_with_research_reactions": 6,
            "original_source_footings_verified": 0,
            "native_source_paths_requiring_engineer_review": (
                native["original_unsupported_shells_with_native_frame_path_candidate"]
                if native else 0),
        },
        "twelve_original_shell_dispositions": shell_records,
        "research_hanging_frame_edge_review": [
            {"source_shell_key": r["source_shell_key"],
             "source_frame_key": r["source_frame_key"],
             "source_frame_endpoint_index": r["frame_endpoint_index"],
             "shell_boundary_index": r["shell_boundary_index"],
             "native_joint_tie_verified": False}
            for r in hanging],
        "unapproved_original_source_base_point_ids": sorted(base_ids),
        "needed_private_evidence": [
            "Native ETABS21 generated joint/element/constraint export with signed source receipts",
            "Native frame-shell joint and hanging-node compatibility verification",
            "Original base-point-to-footing schedule with structural drawing correspondence",
            "Signed governing ULS/SLS source mass, loads, modal and seismic combinations",
            "Code-design calculations and independent F3 one-way shear redesign check"
        ],
        "model_authorised_for_governing_member_design": False,
        "model_authorised_for_footing_design": False,
        "new_source_unsupported_shells_accepted": 0,
        "native_joint_identity_accepted_by_nearest_XYZ": False,
        "original_F3_one_way_shear_unsafe": True,
        "full_independent_engineering_QA_completed": False,
        "release_authorised": False,
        "engineering_approval": False
    }


def public_receipt(report: dict) -> dict:
    """Hash safe-to-publish output; never serialize user-supplied private exports."""
    _require(report["schema"] == SCHEMA and report["engineering_approval"] is False,
             "Cannot publish a non-HOLD R6.19 report")
    body = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return {
        "schema": "jp.structural.r6p19.public_safe_evidence_gate_receipt.v0.1",
        "report_sha256": sha256(body.encode()).hexdigest(),
        "source_fingerprints": report["governing_source_sha256"],
        "counts": report["counts"],
        "no_native_analysis_original_data_embedded": True,
        "engineering_approval": False,
    }
