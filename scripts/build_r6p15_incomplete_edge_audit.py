#!/usr/bin/env python3
"""R6.15: every R6.14 incomplete slab perimeter, no invented vertical supports.

Read original ULS/SLS *input* geometry. Distinguish exact full beams,
segmented collinear beam chains, overlaps, gaps, nonstructural source LINEs,
and adjacent FLOOR shells. One-way/cantilever scenarios are mechanically
hypothetical and NEVER applied to R6.10 solver or R6.13 design members.
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
from scripts.build_r6p14_tributary_reconciliation import (
    build as r614_build, GEOM_TOL_MM, rectangle_geometry,
    point_to_segment_line, match_edge_to_beam, norm, subtract,
)
from scripts.build_r6p8_native_source_catalogue import build as source_catalogue

OUT=ROOT/"site/data/r6p15-incomplete-slab-edge-audit.json"
RECEIPT=ROOT/"site/reports/r6p15-incomplete-slab-edge-receipt.json"
SCHEMA="jp.structural.r6p15.incomplete_slab_beam_edge_classification.v0.1"
TARGET="WITHHELD_INCOMPLETE_OR_AMBIGUOUS_BEAM_PERIMETER"
NEAR=GEOM_TOL_MM

def signed_interval_on_source_edge(edge, source):
    """Projection of a collinear source segment onto its edge; dimensionless."""
    a,b=edge["edge_start_xyz_mm"],edge["edge_end_xyz_mm"]
    c,d=source["start_xyz_mm"],source["end_xyz_mm"]
    t0,r0=point_to_segment_line(c,a,b)
    t1,r1=point_to_segment_line(d,a,b)
    if max(r0,r1)>NEAR:return None
    left,right=max(0.,min(t0,t1)),min(1.,max(t0,t1))
    if right<=left+NEAR/max(float(edge["length_mm"]),1.):
        return None
    return (left,right)

def segment_union(intervals,edge_length_mm,tol_mm=NEAR):
    """Exact interval union, interior holes and overlapping material length."""
    L=float(edge_length_mm)
    if not math.isfinite(L) or L<=tol_mm:raise ValueError("Degenerate source edge")
    eps=tol_mm/L
    segments=sorted((max(0.,float(lo)),min(1.,float(hi))) for lo,hi in intervals
                    if float(hi)>float(lo) and min(1.,float(hi))>max(0.,float(lo)))
    merged=[]
    overlapping_mm=0.
    for lo,hi in segments:
        if not merged or lo>merged[-1][1]+eps:
            merged.append([lo,hi])
        else:
            last=merged[-1]
            overlapping_mm+=max(0.,min(hi,last[1])-lo)*L
            last[1]=max(last[1],hi)
    coverage=sum((hi-lo)*L for lo,hi in merged)
    cursor=0.
    gaps=[]
    for lo,hi in merged:
        if lo>cursor+eps:gaps.append({"start_fraction":round(cursor,8),
             "end_fraction":round(lo,8),"length_mm":round((lo-cursor)*L,6)})
        cursor=max(cursor,hi)
    if 1-cursor>eps:gaps.append({"start_fraction":round(cursor,8),
         "end_fraction":1.,"length_mm":round((1-cursor)*L,6)})
    result={"covered_mm":round(coverage,6),"covered_fraction":round(coverage/L,8),
        "total_gap_mm":round(sum(x["length_mm"] for x in gaps),6),
        "gaps":gaps,"overlap_length_mm":round(overlapping_mm,6),
        "interval_count":len(segments),
        "unions":[[round(lo,8),round(hi,8)] for lo,hi in merged]}
    assert abs(result["covered_mm"]+result["total_gap_mm"]-L)<max(1.e-4,tol_mm*len(gaps)+2e-5)
    return result

def classify_frame_edge(edge, beam_by_key):
    """A FULL edge with competing segments or a gap is not a clean support."""
    full=edge["full_edge_candidate_beams"]
    partial=edge["partial_edge_candidate_beams"]
    keys=[x["beam_key"] for x in full+partial]
    if len(keys)!=len(set(keys)):raise ValueError("Repeated original beam key on one edge")
    segments=[]
    for item in full+partial:
        beam=beam_by_key[item["beam_key"]]
        interval=signed_interval_on_source_edge(edge,beam)
        if interval is None:raise ValueError("Registered source matching beam no longer on edge")
        segments.append({"beam_key":beam["key"],"interval":interval,
                         "match_type":item["match_type"],
                         "source_frame_not_solver_joint":True})
    partition=segment_union([x["interval"] for x in segments],edge["length_mm"])
    gaps=partition["total_gap_mm"]
    overlaps=partition["overlap_length_mm"]
    if len(full)>1:code="AMBIGUOUS_MULTIPLE_FULL_BEAMS"
    elif len(full)==1 and partial:code="COMPETING_FULL_AND_PARTIAL_BEAMS"
    elif len(full)==1:code="SINGLE_COMPLETE_FRAME_BEAM"
    elif len(partial)==0:code="NO_COLLINEAR_FRAME_BEAM"
    elif gaps>max(0.001,GEOM_TOL_MM*3):code="PARTIAL_FRAME_EDGE_WITH_GAP"
    elif overlaps>max(0.001,GEOM_TOL_MM*3):code="COMPLETE_BUT_OVERLAPPING_FRAME_SEGMENTS"
    elif len(partial)>=2:code="COMPLETE_SEGMENTED_FRAME_CHAIN_GEOMETRIC_ONLY"
    else:code="PARTIAL_FRAME_EDGE_WITH_GAP"
    clean=code in ("SINGLE_COMPLETE_FRAME_BEAM","COMPLETE_SEGMENTED_FRAME_CHAIN_GEOMETRIC_ONLY")
    return {"edge_index":edge["edge_index"],"source_corner_ids":edge["corner_source_point_ids"],
            "edge_start_xyz_mm":edge["edge_start_xyz_mm"],"edge_end_xyz_mm":edge["edge_end_xyz_mm"],
            "edge_length_mm":edge["length_mm"],
            "frame_match_class":code,"geometric_complete_frame_alignment":clean,
            "full_frame_keys":[x["beam_key"] for x in full],
            "partial_frame_keys":[x["beam_key"] for x in partial],
            "frame_intervals":[{"beam_key":x["beam_key"],
                "start_fraction":round(x["interval"][0],8),
                "end_fraction":round(x["interval"][1],8),
                "match_type":x["match_type"]} for x in segments],
            "partition":partition,"source_edge_constraint_verified":False,
            "accepted_support_or_reaction":None}

def incidental_edges(edge,items,kind):
    result=[]
    for item in items:
        if item.get("storey")!=kind["story"]:continue
        if kind["exclude_key"]==item["key"]:continue
        if kind["type"]=="FLOOR_NEIGHBOUR":
            polygon=item["vertices_xyz_mm"]
            pieces=[(polygon[i],polygon[(i+1)%len(polygon)]) for i in range(len(polygon))]
        else:pieces=[(item["start_xyz_mm"],item["end_xyz_mm"])]
        for i,(p,q) in enumerate(pieces):
            candidate=match_edge_to_beam(edge["edge_start_xyz_mm"],
                  edge["edge_end_xyz_mm"],p,q)
            if candidate["coverage"]=="NONE":continue
            result.append({"source_key":item["key"],"source_edge_index":i,
                "collinear_geometric_coverage":candidate["coverage"],
                "overlap_mm":candidate["overlap_mm"],
                "structural_support_proven":False})
    return sorted(result,key=lambda x:(x["source_key"],x["source_edge_index"]))

def hypotheses_for_slab(shell,edges):
    """Only algebraic thought experiments for *clean* 2-edge or 1-edge cases."""
    shape=rectangle_geometry(shell["vertices_xyz_mm"])
    all_clean=[x["edge_index"] for x in edges if x["geometric_complete_frame_alignment"]]
    seen_neighbours=sum(len(x["adjacent_floor_shells_geometric_only"]) for x in edges)
    scenario=[]
    if not shape["eligible"] or not shell["source_graph_has_base_path"]:
        return scenario
    area=shape["area_m2"]
    loads={"GROSS_SELFWEIGHT_PROXY":shell["true_area_ownweight_proxy_kN"]}
    loads.update({k:v for k,v in shell["original_source_assigned_resultants_kN"].items() if v})
    uncertain=set(x["edge_index"] for x in edges
        if x["frame_match_class"]!="NO_COLLINEAR_FRAME_BEAM" and
           not x["geometric_complete_frame_alignment"])
    if len(all_clean)==2 and (all_clean[0]+2)%4==all_clean[1] and not uncertain:
        sides={edges[i]["edge_length_mm"] for i in all_clean}
        if len(sides)!=1: raise ValueError("Opposite source rectangle edge lengths differ")
        per_edge={"A_over_2_m2":round(area/2,7),
                  "source_uniform_resultants_half_kN":{k:round(v/2,7) for k,v in loads.items()}}
        scenario.append({"scenario":"POSSIBLE_ONE_WAY_TWO_OPPOSITE_ALIGNED_FRAME_EDGES",
            "beam_roots":[{"edge_index":i,"beam_keys":
                edges[i]["full_frame_keys"]+edges[i]["partial_frame_keys"]} for i in all_clean],
            "free_edges_verified":False,
            "adjacent_floor_continuity_observations":seen_neighbours,
            "hypothetical_area_to_each_opposite_edge_m2":round(area/2,7),
            "normal_span_m":round(edges[(all_clean[0]+1)%4]["edge_length_mm"]/1000,6),
            "each_edge_example":per_edge,
            "physical_support_or_design_reaction_verified":False,
            "not_redistributed_into_legacy_beam_case":True})
    if len(all_clean)==1 and not uncertain:
        other=[e for e in edges if e["edge_index"]!=all_clean[0]]
        if all(e["frame_match_class"]=="NO_COLLINEAR_FRAME_BEAM" and
             not e["adjacent_floor_shells_geometric_only"] for e in other):
            root=all_clean[0]
            projection=edges[(root+1)%4]["edge_length_mm"]/1000
            scenario.append({"scenario":"POSSIBLE_CANTILEVER_SINGLE_ALIGNED_FRAME_ROOT",
                "root_edge_index":root,
                "root_source_frame_keys":edges[root]["full_frame_keys"]+edges[root]["partial_frame_keys"],
                "normal_projection_m":round(projection,6),
                "hypothetical_root_resultants_kN":{k:round(v,7) for k,v in loads.items()},
                "hypothetical_uniform_load_root_M_kNm":{
                    k:round(v*projection/2,7) for k,v in loads.items()},
                "full_depth_slab_rebar_or_restraint_known":False,
                "free_edge_and_root_fixity_verified":False,
                "physical_support_or_design_reaction_verified":False,
                "not_redistributed_into_legacy_beam_case":True})
    return scenario

def build(base=None,source=None):
    base=r614_build() if base is None else base
    source=source_catalogue() if source is None else source
    assert base["schema"]=="jp.structural.r6p14.slab_beam_geometric_tributary_reconciliation.v0.1"
    assert source["schema"]=="jp.structural.r6p8.native_input_member_calculation_book.v0.1"
    pair=dict(zip(("ULS","SLS"),source["source"]["source_ulssls_hashes"]))
    if pair!=base["governing_model_sha256"]:raise ValueError("Original ULS/SLS model changed")
    c=base["coverage"]
    if c["original_shells"]!=115 or c["source_graph_shells_without_base_path"]!=12 or c["source_graph_shells_connected"]!=103:
        raise ValueError("R6.14 source shell count changed")
    if (c["status_counts"].get(TARGET)!=77 or c["conditional_complete_perimeter_shells"]!=25 or
        not base["twelve_unsupported_shells_excluded"] or not base["F3_one_way_shear_unsafe"] or
        base["physical_vertical_force_transfer_verified"] or base["engineering_approval"]):
        raise ValueError("R6.14 baseline scope/HOLD not verified")
    all_beams=[m for m in source["members"] if m["kind"]=="BEAM"]
    beam_keys={m["key"]:m for m in all_beams}
    if len(all_beams)!=105:raise ValueError("Original BEAM count changed")
    floor_s=[m for m in source["shells"] if m["kind"]=="FLOOR"]
    nonsectioned=[m for m in source["members"] if m["kind"]=="LINE"]
    if len(nonsectioned)!=34:raise ValueError("Original 34 non-sectioned LINE records changed")
    details=[];per_story=Counter();edge_codes=Counter();hypotheses=Counter();priority=Counter()
    for slab in base["shells"]:
        if slab["status"]!=TARGET:continue
        per_story[slab["story"]]+=1
        if slab["kind"]!="FLOOR" or not slab["source_graph_has_base_path"]:
            raise ValueError("R6.14 incomplete perimeter scope unexpectedly includes excluded objects")
        if len(slab["edges"])!=4:raise ValueError("Source four-edge classification changed")
        e=[]
        for original in slab["edges"]:
            row=classify_frame_edge(original,beam_keys)
            row["adjacent_floor_shells_geometric_only"]=incidental_edges(original,floor_s,
                {"type":"FLOOR_NEIGHBOUR","story":slab["story"],"exclude_key":slab["shell_key"]})
            row["coincident_unsectioned_SOURCE_LINE_not_a_beam"]=incidental_edges(original,nonsectioned,
                {"type":"NONSECTIONED_LINE","story":slab["story"],"exclude_key":None})
            edge_codes[row["frame_match_class"]]+=1
            e.append(row)
        scenarios=hypotheses_for_slab(slab,e)
        for scenario in scenarios:hypotheses[scenario["scenario"]]+=1
        clean=sum(x["geometric_complete_frame_alignment"] for x in e)
        partial=sum(x["frame_match_class"]=="PARTIAL_FRAME_EDGE_WITH_GAP" for x in e)
        duplicates=sum(x["frame_match_class"] in (
            "AMBIGUOUS_MULTIPLE_FULL_BEAMS","COMPETING_FULL_AND_PARTIAL_BEAMS",
            "COMPLETE_BUT_OVERLAPPING_FRAME_SEGMENTS") for x in e)
        missing=sum(x["frame_match_class"]=="NO_COLLINEAR_FRAME_BEAM" for x in e)
        adjacency=sum(len(x["adjacent_floor_shells_geometric_only"]) for x in e)
        unsectioned_count=sum(len(x["coincident_unsectioned_SOURCE_LINE_not_a_beam"]) for x in e)
        if duplicates:group="FRAME_EDGE_OVERLAP_OR_AMBIGUITY_REVIEW"
        elif partial:group="PARTIAL_BEAM_EDGE_GAP_REVIEW"
        elif any(x["frame_match_class"]=="COMPLETE_SEGMENTED_FRAME_CHAIN_GEOMETRIC_ONLY" for x in e):
            group="MULTI_SEGMENT_FRAME_CHAIN_REVIEW"
        elif scenarios:group="ONE_WAY_OR_CANTILEVER_HYPOTHESIS_REVIEW"
        elif adjacency:group="ADJACENT_SLAB_CONTINUITY_HYPOTHESIS_REVIEW"
        else:group="UNMATCHED_SOURCE_BEAM_EDGE_REVIEW"
        priority[group]+=1
        details.append({"shell_key":slab["shell_key"],"story":slab["story"],
            "source_kind":slab["kind"],"source_section":slab["source_section"],
            "source_corner_ids":slab["source_corner_ids"],
            "vertices_xyz_mm":slab["vertices_xyz_mm"],
            "source_graph_has_base_path":True,
            "projected_area_m2":slab["projected_area_m2"],
            "historical_R614_status":slab["status"],
            "original_source_applied_resultants_kN":slab["original_source_assigned_resultants_kN"],
            "source_true_area_selfweight_proxy_kN":slab["true_area_ownweight_proxy_kN"],
            "edge_cases":e,"complete_frame_edge_count":clean,
            "incomplete_frame_gap_edge_count":partial,
            "ambiguous_overlap_edge_count":duplicates,
            "no_aligned_frame_edge_count":missing,
            "coincident_floor_neighbour_observation_count":adjacency,
            "coincident_unsectioned_line_observation_count":unsectioned_count,
            "provisional_scenarios":scenarios,
            "review_group":group,
            "verified_support_edges":None,"accepted_slab_to_beam_force_kN":None,
            "original_solver_frame_actions_modified":False,
            "native_ETABS21_generated_edge_connectivity_verified":False,
            "not_a_design_load_or_safety_acceptance":True})
    if len(details)!=77 or sum(per_story.values())!=77 or sum(priority.values())!=77:
        raise ValueError("Not all 77 original withheld-perimeter cases are audited")
    if sum(edge_codes.values())!=77*4:raise ValueError("Edge-by-edge audit not exhaustive")
    if any(d["accepted_slab_to_beam_force_kN"] is not None for d in details):
        raise ValueError("Unverified design load was invented")
    return {"schema":SCHEMA,"governing_ULS_SLS_input_SHA256":pair,
        "r614_baseline_status":TARGET,
        "baseline":{"shells":115,"source_graph_connected":103,"source_graph_unanchored":12,
            "r614_complete_four_edge_shells":25,"r614_withheld_incomplete_perimeter":77,
            "r614_other_withheld":13,
            "r614_conditional_area_m2":c["conditional_projected_area_m2"]},
        "coverage":{"slabs_examined":len(details),"source_edges_examined":sum(edge_codes.values()),
            "by_story":dict(sorted(per_story.items())),
            "frame_edge_class_counts":dict(sorted(edge_codes.items())),
            "review_group_counts":dict(sorted(priority.items())),
            "hypothesis_counts":dict(sorted(hypotheses.items())),
            "slabs_with_geometry_only_hypotheses":sum(bool(x["provisional_scenarios"]) for x in details),
            "slabs_with_adjacent_floor_geometry":sum(x["coincident_floor_neighbour_observation_count"]>0 for x in details),
            "slabs_with_nonsectioned_lines_along_edges":sum(x["coincident_unsectioned_line_observation_count"]>0 for x in details)},
        "source_edge_tolerance_mm":GEOM_TOL_MM,
        "method":"strict 3D beam-segment interval union, edge gaps/overlaps, adjacent FLOOR and nonsectioned LINE geometry, hypothetical one-way/cantilever scenarios only",
        "cases":details,
        "member_design_loads_modified":False,"shell_contact_gate_promoted":False,
        "original_source_gravity_actions_modified":False,
        "original_R614_45deg_allocations_modified":False,
        "source_joint_or_restraint_verified":False,
        "F3_one_way_shear_unsafe":True,
        "twelve_unsupported_shells_still_excluded":True,
        "engineering_approval":False}

def export(base=None,source=None):
    d=build(base=base,source=source)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(d,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
    receipt={"schema":"jp.structural.r6p15.incomplete_edge_audit_receipt.v0.1",
        "governing_ULS_SLS_SHA256":d["governing_ULS_SLS_input_SHA256"],
        "count":d["coverage"],"public_json_sha256":sha256(OUT.read_bytes()).hexdigest(),
        "accepted_engineering_loads":False,"F3_one_way_shear_unsafe":True,
        "twelve_unsupported_shells_still_excluded":True,"engineering_approval":False}
    RECEIPT.parent.mkdir(parents=True,exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return d,receipt

if __name__=="__main__":
    d,_=export()
    print("R6P15_ALL_77_SOURCE_EDGE_GAPS_AND_GEOMETRIC_HYPOTHESES",json.dumps(d["coverage"],sort_keys=True))
    print("R6P15_ONLY_RESEARCH_F3_AND_TWELVE_SHELLS_HELD")
