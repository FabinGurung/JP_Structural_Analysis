#!/usr/bin/env python3
"""R6.14 conservative native-source slab/beam geometric tributary audit.

This is an INPUT-geometry reconciliation and a conditional 45-degree two-way
area proxy only when a horizontal rectangular FLOOR shell has four unique
fully covering same-storey frame BEAM edges. It NEVER proves ETABS generated
joint connectivity, true shell edge constraints, vertical load transfer,
member design forces, or structural safety. Partial/coincident point-only
contacts and incomplete perimeters are explicitly withheld.
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
from scripts.build_r6p10_source_shell_mesh import build as shell_mesh

OUT=ROOT/"site/data/r6p14-slab-beam-tributary-audit.json"
RECEIPT=ROOT/"site/reports/r6p14-slab-beam-tributary-receipt.json"
SOURCE="jp.structural.r6p14.slab_beam_geometric_tributary_reconciliation.v0.1"
GEOM_TOL_MM=0.001
RECT_TOL=1e-5
PATTERNS=("Dead","Live","FLOOR FINISH","WALL LOAD","TANK","STAIRCASE LOAD")
FLOOR_STORIES=("GF","FF","TF")

def finite(x,name):
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x):
        raise ValueError(f"{name} not finite number")
    return float(x)

def dot(a,b):
    return sum(x*y for x,y in zip(a,b))

def subtract(a,b):
    return tuple(float(x)-float(y) for x,y in zip(a,b))

def norm(a):
    return math.sqrt(dot(a,a))

def point_to_segment_line(point,a,b):
    """Parametric position and perpendicular residual to infinite BEAM line."""
    direction=subtract(b,a)
    length=norm(direction)
    if length<=GEOM_TOL_MM:raise ValueError("Degenerate beam source")
    t=dot(subtract(point,a),direction)/(length*length)
    foot=tuple(float(a[i])+t*direction[i] for i in range(3))
    return t,norm(subtract(point,foot))

def match_edge_to_beam(edge0,edge1,beam0,beam1,tol=GEOM_TOL_MM):
    """Classify FULL, PARTIAL, or NONE by actual 3D line, not 2D crossing."""
    edge_length=norm(subtract(edge1,edge0))
    beam_length=norm(subtract(beam1,beam0))
    if min(edge_length,beam_length)<=tol:
        return {"coverage":"NONE","overlap_mm":0.0}
    t0,d0=point_to_segment_line(edge0,beam0,beam1)
    t1,d1=point_to_segment_line(edge1,beam0,beam1)
    if max(d0,d1)>tol:
        return {"coverage":"NONE","overlap_mm":0.0}
    allowance=tol/beam_length
    if min(t0,t1)>=-allowance and max(t0,t1)<=1+allowance:
        return {"coverage":"FULL","overlap_mm":round(edge_length,6),
                "residual_mm":round(max(d0,d1),9)}
    # Edge-line collinear, but source beam covers only a subsegment.
    u0,e0=point_to_segment_line(beam0,edge0,edge1)
    u1,e1=point_to_segment_line(beam1,edge0,edge1)
    if max(e0,e1)>tol:
        return {"coverage":"NONE","overlap_mm":0.0}
    overlap=max(0.0,min(1.0,max(u0,u1))-max(0.0,min(u0,u1)))*edge_length
    if overlap<=tol:
        return {"coverage":"NONE","overlap_mm":0.0}
    return {"coverage":"PARTIAL","overlap_mm":round(overlap,6),
            "residual_mm":round(max(d0,d1,e0,e1),9)}

def plan_area(points):
    return abs(sum(float(points[i][0])*float(points[(i+1)%len(points)][1])
        -float(points[(i+1)%len(points)][0])*float(points[i][1])
        for i in range(len(points))))/2

def rectangle_geometry(vertices):
    """Check four distinct corners, horizontal plane, right-angle projection."""
    if len(vertices)!=4:return {"eligible":False,"reason":"NOT_QUADRILATERAL"}
    if max(float(x[2]) for x in vertices)-min(float(x[2]) for x in vertices)>GEOM_TOL_MM:
        return {"eligible":False,"reason":"NON_HORIZONTAL_OR_WARPED_SLAB"}
    xy=[(float(x[0]),float(x[1])) for x in vertices]
    side=[subtract(xy[(i+1)%4],xy[i]) for i in range(4)]
    lengths=[norm(e) for e in side]
    if min(lengths)<=GEOM_TOL_MM or plan_area(vertices)<1:
        return {"eligible":False,"reason":"DEGENERATE_PROJECTED_AREA"}
    for i in range(4):
        if abs(dot(side[i],side[(i+1)%4]))/(lengths[i]*lengths[(i+1)%4])>RECT_TOL:
            return {"eligible":False,"reason":"NON_RECTANGULAR_45_DEGREE_RULE_NOT_APPLICABLE"}
    if any(abs(lengths[i]-lengths[(i+2)%4])>max(0.005,lengths[i]*RECT_TOL)
           for i in (0,1)):
        return {"eligible":False,"reason":"OPPOSITE_EDGES_DO_NOT_MATCH"}
    area=plan_area(vertices)
    if abs(area-lengths[0]*lengths[1])>max(.01,area*RECT_TOL):
        return {"eligible":False,"reason":"PROJECTED_AREA_NOT_RECTANGULAR"}
    return {"eligible":True,"reason":"RECTANGULAR_HORIZONTAL_SOURCE_GEOMETRY",
            "edge_lengths_mm":lengths,"area_m2":area/1e6}

def rectangle_45deg_edge_areas(vertices):
    """Nearest-edge 45 degree areas: for a>=b, each short edge b²/4.

    Each long edge has ab/2-b²/4; all four sum to ab.
    This is an ASSUMED two-way tributary pattern, never FE reactions.
    """
    shape=rectangle_geometry(vertices)
    if not shape["eligible"]:raise ValueError("45-degree rule requires flat rectangle")
    lengths=shape["edge_lengths_mm"]
    a,b=max(lengths[0],lengths[1]),min(lengths[0],lengths[1])
    short=b*b/4/1e6
    long=(a*b/2-b*b/4)/1e6
    result=[long if abs(x-a)<=max(.005,a*RECT_TOL) else short for x in lengths]
    if not math.isclose(sum(result),shape["area_m2"],rel_tol=1e-8,abs_tol=1e-7):
        raise ValueError("Tributary allocation does not preserve source slab area")
    return result

def edge_matches(vertices,corner_ids,story,beams,tolerance=GEOM_TOL_MM):
    out=[]
    for i in range(4):
        a,b=vertices[i],vertices[(i+1)%4]
        ids=(str(corner_ids[i]),str(corner_ids[(i+1)%4]))
        full=[];partial=[]
        for beam in beams:
            if beam["storey"]!=story:continue
            m=match_edge_to_beam(a,b,beam["start_xyz_mm"],beam["end_xyz_mm"],tolerance)
            if m["coverage"]=="NONE":continue
            source_pair=set(map(str,beam["point_ids"]))==set(ids)
            row={"beam_key":beam["key"],"beam_source_point_ids":beam["point_ids"],
                 "match_type":"EXACT_SOURCE_CORNER_PAIR" if source_pair else "COINCIDENT_OR_SPANNING_GEOMETRY_ONLY",
                 "overlap_mm":m["overlap_mm"],"residual_mm":m["residual_mm"]}
            if m["coverage"]=="FULL":full.append(row)
            else:partial.append(row)
        out.append({"edge_index":i,"corner_source_point_ids":list(ids),
                    "edge_start_xyz_mm":a,"edge_end_xyz_mm":b,
                    "length_mm":round(norm(subtract(b,a)),6),
                    "full_edge_candidate_beams":sorted(full,key=lambda x:x["beam_key"]),
                    "partial_edge_candidate_beams":sorted(partial,key=lambda x:x["beam_key"]),
                    "native_joint_or_edge_constraint_verified":False})
    return out

def build(model=None,mesh=None):
    model=source_catalogue() if model is None else model
    mesh=shell_mesh() if mesh is None else mesh
    assert model["schema"]=="jp.structural.r6p8.native_input_member_calculation_book.v0.1"
    assert mesh["schema"]=="jp.structural.r6p10.original_e2k_source_shell_mesh_and_loadcase_audit.v0.1"
    governing=dict(zip(("ULS","SLS"),model["source"]["source_ulssls_hashes"]))
    if governing!=mesh["governing_source_sha256"]:
        raise ValueError("ULS/SLS source hashes do not match previous shell mesh")
    if (len(model["shells"]),len(model["members"]),mesh["source_shell_count"],
        mesh["shells_connected_through_source_to_fixed_base"],
        mesh["shells_without_verified_vertical_support_path"])!=(115,199,115,103,12):
        raise ValueError("Governing source object counts changed")
    if mesh["engineering_approval"] or not mesh["source_F3_one_way_shear_unsafe"]:
        raise ValueError("Engineering approval or F3 hold unexpectedly changed")
    beams=[m for m in model["members"] if m["kind"]=="BEAM"]
    if any(m["section"]=="NONE" for m in beams):raise ValueError("Not a concrete structural beam")
    audited={s["key"]:s for s in mesh["all_shell_parameters"]}
    if len(audited)!=115:raise ValueError("Original panel audit IDs changed")
    rows=[];beam_ledger=defaultdict(lambda:{"tributary_area_m2":0.,
        "geometric_slab_count":0,"source_resultants_kN":defaultdict(float),
        "originating_slabs":[]})
    for shell in model["shells"]:
        key=shell["key"];p=audited[key]
        if key!=p["key"]:raise ValueError("Shell source identity mismatch")
        if shell["storey"]!=p["story"]:raise ValueError("Shell story source mismatch")
        original_loads=defaultdict(float)
        for assignment in shell["applied_loads"]:
            pattern=assignment["pattern"]
            if pattern not in PATTERNS:raise ValueError("Unregistered source load pattern "+pattern)
            original_loads[pattern]+=finite(assignment["raw_integrated_kN"],"slab applied kN")
        original_loads={k:round(original_loads.get(k,0.),6) for k in PATTERNS}
        own_weight=finite(p["true_area_concrete_selfweight_kN"],"source own-weight")
        record={"shell_key":key,"story":shell["storey"],"kind":shell["kind"],
            "source_corner_ids":shell["point_ids"],"vertices_xyz_mm":shell["vertices_xyz_mm"],
            "source_section":shell["section"],"thickness_mm":shell["thickness_mm"],
            "projected_area_m2":round(shell["projected_area_mm2"]/1e6,6),
            "true_area_ownweight_proxy_kN":own_weight,
            "original_source_assigned_resultants_kN":original_loads,
            "source_graph_has_base_path":p["source_supported_by_frame_shell_topology"],
            "generated_ETABS_joint_connectivity_confirmed":False,
            "verified_vertical_load_transfer":False,
            "accepted_design_beam_load_allocation_kN":0.0,
            "conditional_45deg_geometry_allocations":[]}
        if shell["kind"]!="FLOOR":
            record["status"]="WITHHELD_NOT_FLOOR_SHELL"
            record["edges"]=[];rows.append(record);continue
        shape=rectangle_geometry(shell["vertices_xyz_mm"])
        record["rectangle_rule"]=shape["reason"]
        e=edge_matches(shell["vertices_xyz_mm"],shell["point_ids"],shell["storey"],beams)
        record["edges"]=e
        if not p["source_supported_by_frame_shell_topology"]:
            record["status"]="WITHHELD_ORIGINAL_SHELL_UNSUPPORTED";rows.append(record);continue
        if not shape["eligible"]:
            record["status"]="WITHHELD_NON_RECTANGULAR_OR_NON_HORIZONTAL";rows.append(record);continue
        if any(any(z<-.000001 for z in original_loads.values()) for _ in (0,)):
            record["status"]="WITHHELD_SOURCE_LOAD_SIGN_REVIEW";rows.append(record);continue
        if any(len(edge["full_edge_candidate_beams"])!=1 for edge in e):
            record["status"]="WITHHELD_INCOMPLETE_OR_AMBIGUOUS_BEAM_PERIMETER"
            rows.append(record);continue
        ids=[x["full_edge_candidate_beams"][0]["beam_key"] for x in e]
        if len(set(ids))!=4:
            record["status"]="WITHHELD_NON_UNIQUE_PERIMETER_MEMBERS";rows.append(record);continue
        portions=rectangle_45deg_edge_areas(shell["vertices_xyz_mm"])
        if not math.isclose(sum(portions),record["projected_area_m2"],abs_tol=1e-5):
            raise ValueError("Published panel area inconsistent with tributary areas")
        totals={"GROSS_SELFWEIGHT_PROXY":own_weight}
        totals.update({k:v for k,v in original_loads.items() if v})
        exact=all(x["full_edge_candidate_beams"][0]["match_type"]=="EXACT_SOURCE_CORNER_PAIR" for x in e)
        record["status"]=("CONDITIONAL_FOUR_SOURCE_CORNER_PAIR_EDGES" if exact
            else "CONDITIONAL_FOUR_FULL_GEOMETRIC_EDGE_MATCHES")
        record["method"]="Two-way 45-degree nearest-edge tributary proxy for a four-edge rectangular source shell"
        for edge,area,beamid in zip(e,portions,ids):
            weight=area/shape["area_m2"]
            alloc={k:round(q*weight,8) for k,q in totals.items()}
            section={"edge_index":edge["edge_index"],"beam_key":beamid,
                     "area_m2":round(area,8),"fraction_of_shell":round(weight,10),
                     "edge_match_type":edge["full_edge_candidate_beams"][0]["match_type"],
                     "conditional_source_resultants_kN":alloc,
                     "source_joint_constraint_proven":False,
                     "design_line_load_assigned_to_beam":False}
            record["conditional_45deg_geometry_allocations"].append(section)
            b=beam_ledger[beamid]
            b["tributary_area_m2"]+=area;b["geometric_slab_count"]+=1
            b["originating_slabs"].append(key)
            for k,v in totals.items():b["source_resultants_kN"][k]+=v*weight
        for name,total in totals.items():
            if not math.isclose(sum(z["conditional_source_resultants_kN"][name]
                      for z in record["conditional_45deg_geometry_allocations"]),total,abs_tol=5e-7):
                raise ValueError("Load/area conservation failed for "+key+" "+name)
        rows.append(record)
    status=dict(sorted(Counter(x["status"] for x in rows).items()))
    provisional=[]
    for m in beams:
        entry=beam_ledger.get(m["key"])
        if not entry:continue
        provisional.append({"beam_key":m["key"],"story":m["storey"],
            "source_section":m["section"],"length_m":round(m["length_mm"]/1000,6),
            "matched_tributary_area_m2":round(entry["tributary_area_m2"],7),
            "geometrically_matching_shell_edge_count":entry["geometric_slab_count"],
            "conditional_source_resultants_kN":{
                k:round(v,7) for k,v in sorted(entry["source_resultants_kN"].items())},
            "source_shell_ids":sorted(entry["originating_slabs"]),
            "source_connectivity_proven":False,
            "original_beam_design_force_modified":False,
            "approved_beam_load_kN":0.0})
    assert len(rows)==115
    assert sum(not x["source_graph_has_base_path"] for x in rows)==12
    eligible=[x for x in rows if x["status"].startswith("CONDITIONAL_")]
    for r in rows:
        if not r["status"].startswith("CONDITIONAL_") and r["conditional_45deg_geometry_allocations"]:
            raise ValueError("Withheld slab acquired invented beam allocations")
    area1=sum(x["projected_area_m2"] for x in eligible)
    area2=sum(y["matched_tributary_area_m2"] for y in provisional)
    if not math.isclose(area1,area2,abs_tol=max(1e-5,len(eligible)*5e-6)):
        raise ValueError("Slab and beam conditional area balance lost")
    return {"schema":SOURCE,"governing_model_sha256":governing,
        "member_source_schema":model["schema"],"shell_source_schema":mesh["schema"],
        "methodology":"Geometric source boundary candidate only; 45-degree two-way area if 4 unambiguous full beam edges",
        "source_3d_edge_tolerance_mm":GEOM_TOL_MM,"shells":rows,"beam_conditional_totals":provisional,
        "coverage":{"original_shells":115,"original_beams":len(beams),
           "source_graph_shells_connected":103,"source_graph_shells_without_base_path":12,
           "conditional_complete_perimeter_shells":len(eligible),
           "withheld_shells":115-len(eligible),
           "conditional_projected_area_m2":round(area1,6),
           "conditional_aggregate_beam_area_m2":round(area2,6),
           "beams_with_conditional_tributary_areas":len(provisional),
           "status_counts":status},
        "no_perimeter_inferred_from_point_contacts":True,
        "no_source_gravity_load_case_modified":True,
        "no_original_design_member_actions_modified":True,
        "native_generated_joint_or_edge_constraint_verified":False,
        "physical_vertical_force_transfer_verified":False,
        "twelve_unsupported_shells_excluded":True,
        "F3_one_way_shear_unsafe":True,"engineering_approval":False}

def export(model=None,mesh=None):
    d=build(model=model,mesh=mesh)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(d,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    receipt={"schema":"jp.structural.r6p14.slab_beam_tributary_receipt.v0.1",
             "source_governing_pair":d["governing_model_sha256"],
             "coverage":d["coverage"],"public_json_sha256":sha256(OUT.read_bytes()).hexdigest(),
             "accepted_load_transfer":False,"native_solver_reproduced":False,
             "F3_one_way_shear_unsafe":True,"engineering_approval":False}
    RECEIPT.parent.mkdir(parents=True,exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return d,receipt

if __name__=="__main__":
    d,_=export()
    print("R6P14_TRIBUTARY_GEOMETRIC_CANDIDATES_ONLY",d["coverage"],"F3 HOLD")
