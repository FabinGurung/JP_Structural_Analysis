#!/usr/bin/env python3
"""R6.18 — independently repeated nonconforming 3D FE mesh and foundation reaction screen.

Original source E2K geometry identity is authoritative; NEVER connect a source
edge/joint or add a restraint solely because two coordinates appear near.
Full original ETABS21 generated mesh/joints, complete source loads and physical
load transfer remain unverified. This is a source-bounded alternate FE study:
103 of 115 shells, 165 beam-column segments, 21 of 27 declared restraints.

The source-to-foundation ledger is intentionally NOT a footing F3/CF1 mapping.
Each comparison is between OpenSees 2x2 and 4x4 research meshing under the
same declared source-pattern loads, not an ETABS equivalent solution.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_r6p8_native_source_catalogue import build as source_catalogue
from scripts.build_r6p10_source_shell_mesh import build as source_shell_audit,mesh_point
from scripts.build_r6p10_gravity_casebook import build_casebook
from scripts.build_r6p17_canonical_source_graph import build as r617_build,pt_segment_distance
from scripts.run_r6p10_connected_shell_gravity import solve as solve_connected

OUT=ROOT/"site/data/r6p18-fe-connection-mesh-foundation-audit.json"
RECEIPT=ROOT/"site/reports/r6p18-first-party-fe-convergence-receipt.json"
SCHEMA="jp.structural.r6p18.source_bounded_fe_mesh_and_foundation_reaction_gate.v0.1"
REFINED=(("ULS","Dead"),("SLS","Live"))
RESOLUTIONS=(2,4)
GEOMETRIC_TOLERANCE_MM=0.001
SCREEN_TOLERANCE_RELATIVE=0.05

def coord(point):
    return tuple(round(float(x),3) for x in point)

def boundary_nodes_of_shell(panel,resolution):
    corners=panel["vertices_xyz_mm"]
    # Reconstruct exactly the points the original 2x2 / 4x4 trial shell
    # generator places on each of its four source straight boundary edges.
    grids=[]
    for j in range(4):
        points=[]
        for k in range(resolution+1):
            t=k/resolution
            points.append(coord([
                (1-t)*float(corners[j][a])+t*float(corners[(j+1)%4][a])
                for a in range(3)
            ]))
        grids.append(points)
    return grids

def inspect_mesh_interfaces(model,canonical,resolution):
    """Potential hanging frame endpoints where source beam touches shell edges.

    A coordinate coincident with an interpolated shell grid point is evidence
    of geometric/nodal alignment ONLY. The real generated ETABS joint tie and
    element end releases cannot be reconstructed from these inputs.
    """
    if resolution not in RESOLUTIONS:raise ValueError("Unsupported R6.18 mesh resolution")
    shells={x["key"]:x for x in model["shells"]}
    admitted={x["key"] for x in canonical["canonical_original_shells"]
              if x["admitted_to_existing_coarse_research_solver"]}
    structural=[m for m in model["members"] if m["kind"] in ("BEAM","COLUMN")]
    records=[];class_counts=Counter();per_shell=Counter()
    for key in sorted(admitted):
        panel=shells[key]
        grids=boundary_nodes_of_shell(panel,resolution)
        for m in structural:
            if m["storey"]!=panel["storey"] and m["kind"]=="BEAM":
                continue
            for idx,(pid,endpoint) in enumerate(zip(m["point_ids"],(m["start_xyz_mm"],m["end_xyz_mm"]))):
                # The original column bottom point belongs to its lower storey.
                story=(("Plinth level" if m["storey"]=="GF" else
                        "GF" if m["storey"]=="FF" else "FF")
                        if m["kind"]=="COLUMN" and idx==0 else m["storey"])
                if story!=panel["storey"]:continue
                for boundary_idx in range(4):
                    vertices=panel["vertices_xyz_mm"]
                    dist,t=pt_segment_distance(endpoint,vertices[boundary_idx],
                                                vertices[(boundary_idx+1)%4])
                    if dist>GEOMETRIC_TOLERANCE_MM or not (-1e-9<=t<=1+1e-9):
                        continue
                    mesh_aligned=coord(endpoint) in grids[boundary_idx]
                    original_id_matches=str(pid) in [str(p) for p in panel["point_ids"]]
                    if not original_id_matches:
                        cls="GEOMETRY_ONLY_DIFFERENT_ORIGINAL_SOURCE_POINT_ID"
                    elif not mesh_aligned:
                        cls="SOURCE_ID_MATCH_BUT_NO_RESEARCH_SHELL_GRID_NODE"
                    else:
                        cls="SOURCE_ID_AND_RESEARCH_GRID_COORDINATE_ALIGNED"
                    if not mesh_aligned:
                        cls="HANGING_FRAME_ENDPOINT_ON_RESEARCH_SHELL_EDGE"
                    class_counts[cls]+=1
                    per_shell[key]+=1
                    records.append({
                      "source_shell_key":key,"source_frame_key":m["key"],
                      "source_frame_kind":m["kind"],"frame_endpoint_index":idx,
                      "source_frame_point_id":str(pid),"shell_source_story":panel["storey"],
                      "shell_boundary_index":boundary_idx,
                      "frame_endpoint_xyz_mm":endpoint,
                      "edge_parameter_fraction":round(t,9),
                      "corner_to_shell_boundary_distance_mm":round(dist,8),
                      "original_shell_corner_point_identity_matches":bool(original_id_matches),
                      "research_grid_node_at_frame_endpoint":mesh_aligned,
                      "geometry_class":cls,
                      "native_ETABS_joint_and_support_constraint_verified":False,
                      "shell_frame_support_or_load_transfer_accepted":False
                    })
    if not records:raise ValueError("No matching original source frame/shell boundary contacts")
    return {"resolution":resolution,
      "mesh_nodes_per_side":resolution+1,
      "source_connected_original_shells_examined":len(admitted),
      "original_structural_frame_members_examined":len(structural),
      "source_frame_endpoint_to_shell_boundary_encounters":len(records),
      "by_geometry_class":dict(sorted(class_counts.items())),
      "unique_source_shells_with_boundary_contact":len(per_shell),
      "geometric_contacts":records,
      "research_grid_is_native_ETABS21_generated_mesh":False,
      "source_identity_or_geometric_coincidence_accepted_as_support":False}

def collision_register(canonical):
    """Identify source point/storey IDs that existing OpenSees merges by XYZ."""
    groups=defaultdict(set)
    for node in canonical["canonical_nodes"]:
        groups[coord(node["xyz_mm"])].add(node["key"])
    ambiguous=[{"coordinate_xyz_mm":list(k),"original_node_keys":sorted(v),
                "native_joint_merger_authorised":False}
               for k,v in sorted(groups.items()) if len(v)>1]
    return {"source_identity_graph_node_count":len(canonical["canonical_nodes"]),
        "source_coordinate_rounded_collision_groups":len(ambiguous),
        "potential_ambiguous_coincident_source_nodes":ambiguous,
        "original_nodes_merged_as_verified_structural_joints":False}

def research_floating_point_validation(canonical):
    rows=canonical["individual_twelve_unanchored_shell_investigations"]
    if len(rows)!=12:raise ValueError("R6.17 original unanchored-shell count changed")
    return {"excluded_source_shell_ids":[r["shell_key"] for r in rows],
      "source_graph_unanchored_shell_count":12,
      "source_unanchored_shells_added_to_FE":0,
      "nearest_geometry_within_a_tolerance_is_not_native_support":True,
      "outstanding_generated_analysis_joint_and_edge_restraint_evidence":True,
      "original_floating_shell_source_details":[{
          "shell_key":r["shell_key"],"source_story":r["story"],
          "source_component_ids":r["source_component_ids"],
          "nearest_source_frame_keys":[q["member_key"] for q in r["nearest_original_structural_frames"]],
          "source_mesh_connection_approved":False,"excluded_from_numerical_analyses":True
      } for r in rows]}

def verify_case(case,role,pattern,resolution):
    if (case["role"]!=role or case["source_case"]!=pattern
        or case["coarse_refinement"]!=resolution
        or case["original_frame_elements_included"]!=165
        or case["original_source_restraints_declared"]!=27
        or case["source_restraints_physically_connected"]!=21
        or case["original_unsupported_shells_numerically_excluded"]!=12
        or case["vertically_supported_shells_numerically_included"]!=103
        or case["coarse_numerical_shell_elements"]!=103*resolution*resolution
        or not case["F3_one_way_shear_unsafe"] or case["professional_engineer_approved"]):
        raise ValueError("Research gravity FE model input scope or engineering HOLD changed")
    reactions=case["connected_support_signed_reactions_research_only"]
    if len(reactions)!=21:raise ValueError("Missing bounded six-DOF original base support reactions")
    applied=case["applied_gravity"]
    if applied is None or applied["lost_load_N"]!=0:
        raise ValueError("Original gravity research pattern not fully applied to admitted elements")
    values=[sum(r["signed_Fxyz_N"][i] for r in reactions) for i in range(3)]
    expected=float(applied["total_applied_downward_N"])
    tolerance=max(.05,expected*3e-5)
    errors=[abs(values[0]),abs(values[1]),abs(values[2]-expected)]
    if max(errors)>tolerance:
        raise ValueError("Three-axis research gravity force equilibrium failed")
    source_mom=applied.get("input_external_gravity_moments_Nmm")
    reaction_mom=case.get("sum_support_global_reaction_moments_Nmm")
    moment_errors=case.get("gravity_global_moment_residual_Nmm")
    moment_tolerance=case.get("gravity_global_moment_tolerance_Nmm")
    if not (isinstance(source_mom,list) and isinstance(reaction_mom,list)
            and isinstance(moment_errors,list)
            and len(source_mom)==len(reaction_mom)==len(moment_errors)==3
            and math.isfinite(float(moment_tolerance))):
        raise ValueError("Missing signed global gravity moment audit")
    for i in range(3):
        if not math.isclose(abs(source_mom[i]+reaction_mom[i]),
                            float(moment_errors[i]),abs_tol=0.05):
            raise ValueError("Source/reaction moment arithmetic does not reproduce")
    if max(moment_errors)>moment_tolerance:
        raise ValueError("Three-axis research gravity moment equilibrium failed")
    ids=set()
    for r in reactions:
        if (not r["original_base_point_ids"] or
            len(r["signed_Fxyz_N"])!=3 or len(r["signed_Mxyz_Nmm"])!=3
            or r["original_ETABS21_signed_reaction_verified"]):
            raise ValueError("Source base reaction mapping or provenance false")
        original_ids=tuple(sorted(str(x) for x in r["original_base_point_ids"]))
        if original_ids in ids:raise ValueError("Duplicate mapped source support in gravity reaction book")
        ids.add(original_ids)
    if len(ids)!=21:raise ValueError("Uncovered original source connected base restraints")
    return {"role":role,"source_gravity_pattern":pattern,
      "shell_grid_resolution":resolution,
      "source_connected_shells":103,"coarse_elements":103*resolution*resolution,
      "applied_downward_kN":round(expected/1000,7),
      "signed_base_Rxyz_kN":[round(v/1000,7) for v in values],
      "gravity_force_residual_N":[round(v,6) for v in errors],
      "gravity_force_tolerance_N":round(tolerance,6),
      "source_external_global_moments_kNm":[round(v/1e6,7) for v in source_mom],
      "base_global_reaction_moments_kNm":[round(v/1e6,7) for v in reaction_mom],
      "gravity_moment_residual_Nmm":[round(float(v),6) for v in moment_errors],
      "gravity_moment_tolerance_Nmm":round(float(moment_tolerance),6),
      "source_connected_supports":21,
      "all_three_force_and_moment_axes_reconciled":True,
      "actual_ETABS21_native_results_equivalent":False,
      "foundation_design_reactions_accepted":False,
      "signed_source_mapped_support_reactions":[{
         "original_base_point_ids":r["original_base_point_ids"],
         "xyz_mm":r["xyz_mm"],
         "signed_Rxyz_kN":[round(v/1000,7) for v in r["signed_Fxyz_N"]],
         "signed_Mxyz_kNm":[round(v/1e6,7) for v in r["signed_Mxyz_Nmm"]],
         "original_footing_or_F3_source_correspondence_verified":False
       } for r in reactions]}

def compare_reaction_mesh(coarse,fine):
    a={tuple(sorted(r["original_base_point_ids"])):r for r in coarse["signed_source_mapped_support_reactions"]}
    b={tuple(sorted(r["original_base_point_ids"])):r for r in fine["signed_source_mapped_support_reactions"]}
    if len(a)!=21 or set(a)!=set(b):
        raise ValueError("Mesh refinement must not change declared source base support set")
    total=max(1.,abs(coarse["applied_downward_kN"]))
    input_ratio=abs(coarse["applied_downward_kN"]-fine["applied_downward_kN"])/total
    details=[];peak=0.
    for key in sorted(a):
        start=a[key];end=b[key]
        if start["xyz_mm"]!=end["xyz_mm"]:
            raise ValueError("Source foundation point XYZ moved during refinement")
        diff=end["signed_Rxyz_kN"][2]-start["signed_Rxyz_kN"][2]
        peak=max(peak,abs(diff))
        details.append({"original_source_base_point_ids":list(key),
            "Rz_2x2_kN":start["signed_Rxyz_kN"][2],
            "Rz_4x4_kN":end["signed_Rxyz_kN"][2],
            "signed_change_kN":round(diff,7),
            "absolute_change_relative_to_total_source_gravity":round(abs(diff)/total,8),
            "footing_F3_or_CF1_identity_proven":False})
    screen=peak/total<=SCREEN_TOLERANCE_RELATIVE and input_ratio<=SCREEN_TOLERANCE_RELATIVE
    return {
      "refinement":"2x2_TO_4x4",
      "source_point_reaction_matching":21,
      "coarse_research_shell_elements":coarse["coarse_elements"],
      "fine_research_shell_elements":fine["coarse_elements"],
      "source_load_resultant_difference_relative":round(input_ratio,8),
      "largest_single_source_support_Rz_change_kN":round(peak,7),
      "largest_source_support_change_relative_to_total_gravity":round(peak/total,8),
      "five_percent_reaction_stability_screen_passed":screen,
      "mesh_sensitivity_review_status":(
       "BOUNDED_NUMERICAL_SCREEN_ONLY_NOT_PHYSICAL_MODEL_CONVERGENCE"
       if screen else "STILL_MESH_SENSITIVE_REQUIRES_MORE_REFINEMENT_AND_REVIEW"),
      "support_level_differences":details,
      "complete_numerical_mesh_convergence_proven":False,
      "native_ETABS21_mesh_and_joint_topology_verified":False}

def create_foundation_reaction_register(canonical,baseline):
    by_support=defaultdict(list)
    for case in baseline:
        for row in case["signed_source_mapped_support_reactions"]:
            ids=tuple(sorted(str(v) for v in row["original_base_point_ids"]))
            by_support[ids].append({
              "model_stiffness":case["role"],"source_gravity_pattern":case["source_gravity_pattern"],
              "signed_Rxyz_kN":row["signed_Rxyz_kN"],"signed_Mxyz_kNm":row["signed_Mxyz_kNm"],
              "research_source_case_only":True})
    if len(by_support)!=21 or any(len(v)!=8 for v in by_support.values()):
        raise ValueError("Not all 21 original connected source base IDs have eight research cases")
    graph={x["key"]:x for x in canonical["canonical_nodes"]}
    rows=[]
    for ids,entries in sorted(by_support.items()):
        if len(ids)!=1:
            raise ValueError("Multiple originally distinct support IDs conflated by same source coordinates")
        key="Plinth level:"+ids[0]
        if key not in graph:
            raise ValueError("Non-source foundation reaction support ID")
        rows.append({"original_source_support_point_id":ids[0],
          "source_node_key":key,
          "original_xyz_mm":graph[key]["xyz_mm"],
          "research_case_signed_reactions":entries,
          "source_footing_id":None,
          "historical_F3_or_CF1_correspondence":None,
          "approved_foundation_reaction_or_capacity":None,
          "can_use_for_construction_design":False})
    return rows

def build(canonical=None,model=None,casebook=None,refined_solutions=None):
    canonical=r617_build() if canonical is None else canonical
    model=source_catalogue() if model is None else model
    casebook=build_casebook() if casebook is None else casebook
    fingerprints=canonical["governing_ULS_SLS_input_SHA256"]
    if (casebook["source_model_fingerprints"]!=fingerprints
        or not canonical["F3_one_way_shear_unsafe"]
        or canonical["engineering_approval"]):
        raise ValueError("Source SHA / structural engineering HOLD altered")
    contacts={str(level):inspect_mesh_interfaces(model,canonical,level)
              for level in RESOLUTIONS}
    baseline=[]
    for role in ("ULS","SLS"):
        for pattern in ("Dead","Live","WALL LOAD","FLOOR FINISH"):
            original=casebook["role_results"][role]["independently_run_research_patterns"][pattern]
            baseline.append(verify_case(original,role,pattern,2))
    if len(baseline)!=8:raise ValueError("All eight model-role gravity cases must remain independently solved")
    baseline_map={(row["role"],row["source_gravity_pattern"]):row for row in baseline}
    fine=[]
    for role,pattern in REFINED:
        if refined_solutions is None:
            solved=solve_connected(role,pattern,4)
        else:
            solved=refined_solutions[(role,pattern)]
        fine.append(verify_case(solved,role,pattern,4))
    comparisons=[]
    for fine_case in fine:
        comparisons.append({"role":fine_case["role"],"source_gravity_pattern":fine_case["source_gravity_pattern"],
           **compare_reaction_mesh(baseline_map[(fine_case["role"],fine_case["source_gravity_pattern"])],
                                 fine_case)})
    foundation=create_foundation_reaction_register(canonical,baseline)
    collision=collision_register(canonical)
    unsupported=research_floating_point_validation(canonical)
    counts={"original_frame_members":165,
      "original_shells":115,"source_graph_connected_shells":103,
      "original_unanchored_shells_excluded":12,
      "original_base_restraints_declared":27,
      "source_connected_research_support_nodes":21,
      "six_declared_base_points_unmatched":6,
      "source_graph_components":5,
      "source_3D_graph_nodes":len(canonical["canonical_nodes"]),
      "baseline_gravity_cases_at_2x2":len(baseline),
      "additional_independently_solved_4x4_refinement_cases":len(fine),
      "research_signed_base_reaction_records_2x2":sum(len(x["signed_source_mapped_support_reactions"]) for x in baseline),
      "research_signed_base_reaction_records_4x4":sum(len(x["signed_source_mapped_support_reactions"]) for x in fine),
      "research_shell_elements_2x2":412,"research_shell_elements_4x4":1648}
    report={"schema":SCHEMA,"governing_ULS_SLS_input_SHA256":fingerprints,
      "original_gdrive_source_not_modified":True,
      "original_ETABS21_8x8_native_analysis_mesh_reproduced":False,
      "model_kind":"PARTIAL_SOURCE_CONNECTED_FIRST_PARTY_NONCONFORMING_COARSE_RESEARCH_FE",
      "not_complete_original_building_FE_model":True,
      "source_frame_shell_ties_physically_verified":False,
      "new_constraint_or_support_from_spatial_nearness":False,
      "sources_unsupported_shells_remain_excluded":True,
      "source_original_27_restraints_preserved":True,
      "counts":counts,
      "source_node_identity_vs_3D_coordinate_collision_audit":collision,
      "shell_frame_boundary_alignment_by_mesh_size":contacts,
      "twelve_unconnected_original_shell_holds":unsupported,
      "original_source_connected_2x2_gravity_cases_and_six_axis_equilibrium":baseline,
      "independently_solved_4x4_refinements":fine,
      "research_mesh_sensitivity_comparisons":comparisons,
      "unapproved_original_base_point_to_foundation_reaction_register":foundation,
      "mesh_2x2_to_4x4_is_a_stability_screen_not_full_convergence":True,
      "mesh_8x8_with_actual_ETABS_generated_ties_reproduced":False,
      "complete_design_gravity_load_combinations_reproduced":False,
      "original_F3_CF1_source_support_correspondence_verified":False,
      "foundation_load_transfer_and_one_two_way_shear_approved":False,
      "complete_independent_physical_FE_model_accepted":False,
      "all_12_unsupported_shells_physically_supported":False,
      "r6p18_research_force_and_moment_equilibrium_checked":True,
      "historical_F3_one_way_shear_unsafe":True,
      "engineering_approval":False}
    if (counts["source_graph_connected_shells"]!=103
        or counts["research_signed_base_reaction_records_2x2"]!=168
        or counts["research_signed_base_reaction_records_4x4"]!=42
        or counts["additional_independently_solved_4x4_refinement_cases"]!=2
        or any(v for v in (report["complete_independent_physical_FE_model_accepted"],
          report["original_F3_CF1_source_support_correspondence_verified"],
          report["engineering_approval"]))):
        raise ValueError("R6.18 numerical coverage/source restraint hold changed")
    return report

def export(canonical=None,model=None,casebook=None,refined_solutions=None):
    d=build(canonical=canonical,model=model,casebook=casebook,
            refined_solutions=refined_solutions)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(d,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    receipt={"schema":"jp.structural.r6p18.fe_mesh_reaction_receipt.v0.1",
      "input_sha256":d["governing_ULS_SLS_input_SHA256"],
      "report_body_sha256":sha256(OUT.read_bytes()).hexdigest(),
      "counts":d["counts"],"full_ETABS21_native_parity":False,
      "all_12_shells_added":False,"F3_one_way_shear_unsafe":True,
      "engineering_approval":False}
    RECEIPT.parent.mkdir(parents=True,exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return d,receipt

if __name__=="__main__":
    report,receipt=export()
    print("R6P18_SOURCE_BOUND_3D_FE_2X2_4X4_REACTION_SCREEN",
          json.dumps(report["counts"],sort_keys=True))
    print("R6P18_F3_AND_TWELVE_SHELLS_REMAIN_UNAPPROVED",
          receipt["report_body_sha256"])
