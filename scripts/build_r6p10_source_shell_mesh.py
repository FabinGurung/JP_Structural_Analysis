#!/usr/bin/env python3
"""R6.10 source-verified shell, diaphragm, gravity and seismic-combination intake.

All 115 original shell assignments remain in the source ledger; this is not a
claim that every shell is vertically supported, that ETABS meshing has been
reproduced, or that source seismic modal weights are validated.

No invented supports, artificial load-bearing connections, unreported design
force envelopes or certified reinforcing bar schedules are emitted.
"""
from __future__ import annotations
import hashlib
import json
import math
from collections import defaultdict, Counter
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.run_r6p9_source_frame_gravity import controls as governing_controls
from scripts.build_r6p8_native_source_catalogue import build as source_catalogue

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"site/data/r6p10-source-shell-diaphragm-loads.json"
SUMMARY=ROOT/"site/reports/r6p10-source-shell-diaphragm-summary.json"
LEVELS={"Plinth level":0.,"GF":3048.,"FF":6096.,"TF":9144.}
G=9.80665

class MeshQAError(ValueError):
    pass

def triangle_area_xy(a,b,c):
    return abs((b[0]-a[0])*(c[1]-a[1])-(c[0]-a[0])*(b[1]-a[1]))/2

def triangle_area_3d(a,b,c):
    u=[b[i]-a[i] for i in range(3)]
    v=[c[i]-a[i] for i in range(3)]
    cross=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
    return math.sqrt(sum(z*z for z in cross))/2

def shape_at_xy(vertices,pt,tol=1e-6):
    """Conservative two-triangle barycentric interpolation to the 4 original corners."""
    for indices in ((0,1,2),(0,2,3)):
        a,b,c=(vertices[i] for i in indices)
        den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1.e-9:continue
        u=((b[1]-c[1])*(pt[0]-c[0])+(c[0]-b[0])*(pt[1]-c[1]))/den
        v=((c[1]-a[1])*(pt[0]-c[0])+(a[0]-c[0])*(pt[1]-c[1]))/den
        w=1-u-v
        if min(u,v,w)>=-tol and max(u,v,w)<=1+tol:
            res=[0.]*4
            for j,value in zip(indices,(u,v,w)):
                res[j]=max(0.,min(1.,value))
            total=sum(res)
            return [q/total for q in res]
    return None

def native_components(model,controls):
    """Connectivity audit of all original frame members AND all shell corners."""
    graph=defaultdict(set)
    def join(a,b):
        graph[a].add(b);graph[b].add(a)
    for m in model["members"]:
        if m["kind"] not in ("BEAM","COLUMN"):continue
        i,j=m["point_ids"]
        story=m["storey"]
        prior={"GF":"Plinth level","FF":"GF","TF":"FF"}.get(story)
        u=(i,prior) if m["kind"]=="COLUMN" else (i,story)
        v=(j,story)
        join(u,v)
    for panel in model["shells"]:
        ids=panel["point_ids"]
        for i in range(4):
            join((ids[i],panel["storey"]),(ids[(i+1)%4],panel["storey"]))
    fixed=set(controls["roles"]["ULS"]["supports"])
    seen=set();components=[];anchored=set()
    for start in sorted(graph):
        if start in seen:continue
        stack=[start];seen.add(start);group=set()
        while stack:
            p=stack.pop();group.add(p)
            for n in graph[p]:
                if n not in seen:seen.add(n);stack.append(n)
        bases=sorted(k for k in group if k[1]=="Plinth level" and k[0] in fixed)
        if bases:anchored.update(group)
        components.append({"anchored":bool(bases),"point_storey_node_count":len(group),
                           "fixed_source_bases":len(bases),
                           "member_keys_sorted":[f"{x[1]}:{x[0]}" for x in sorted(group)]})
    shell_ok=[p["key"] for p in model["shells"] if all((i,p["storey"]) in anchored for i in p["point_ids"])]
    shell_no=[p["key"] for p in model["shells"] if p["key"] not in shell_ok]
    frame_no=[]
    for m in model["members"]:
        if m["kind"] not in ("BEAM","COLUMN"):continue
        u=(m["point_ids"][0],{"GF":"Plinth level","FF":"GF","TF":"FF"}[m["storey"]]) if m["kind"]=="COLUMN" else (m["point_ids"][0],m["storey"])
        v=(m["point_ids"][1],m["storey"])
        if u not in anchored or v not in anchored:frame_no.append(m["key"])
    if len(components)!=5 or sum(c["anchored"] for c in components)!=2:
        raise MeshQAError("Frame+shell source connectivity changed")
    if len(shell_ok)!=103 or len(shell_no)!=12 or frame_no:
        raise MeshQAError("Original unsupported shell groups changed, cannot quietly ground them")
    return components,anchored,shell_ok,shell_no

def shell_rule(cfg,vertices):
    mode=cfg.get("OBJMESHTYPE","UNKNOWN")
    if mode=="MESHN1XN2":
        n1=int(cfg["MESHFLOORN1"]);n2=int(cfg["MESHFLOORN2"])
        if (n1,n2)!=(8,8):raise MeshQAError("Original explicit 8x8 mesh changed")
        return n1,n2,"ORIGINAL_N1XN2_REQUEST"
    if mode=="AUTOMESH":
        n=int(cfg.get("MESHVERT","8"))
        if n!=8:raise MeshQAError("Original vertical mesh count changed")
        return n,n,"AUTO_8_BY_8_PROVISIONAL_DENSITY_NOT_VERIFIED_ETABS_MESH"
    if mode=="DEFAULT":
        edges=[math.dist(vertices[i],vertices[(i+1)%4]) for i in range(4)]
        return max(1,math.ceil(max(edges[0],edges[2])/1250)),max(1,math.ceil(max(edges[1],edges[3])/1250)),"GLOBAL_1250MM_DEFAULT_PROXY_NOT_ETABS_MESH"
    raise MeshQAError("Unknown source shell meshing mode "+mode)

def mesh_point(corners,u,v):
    """Bilinear xyz panel interpolation for preview mesh, not new source geometry."""
    w=((1-u)*(1-v),u*(1-v),u*v,(1-u)*v)
    return [sum(w[k]*corners[k][i] for k in range(4)) for i in range(3)]

def build():
    model,src=governing_controls()
    roles=src["roles"]
    controls=roles["ULS"]
    comps,anchored,linked,unlinked=native_components(model,src)
    if controls["diaphragms"]!=roles["SLS"]["diaphragms"]:
        raise MeshQAError("Original diaphragm assignments differ between ULS and SLS")
    if controls["mesh"]!=roles["SLS"]["mesh"]:
        raise MeshQAError("Original area mesh controls differ between ULS and SLS")
    if len(model["shells"])!=115 or len(controls["mesh"])!=115:
        raise MeshQAError("Original area assignment mismatch")
    if len(controls["supports"])!=27:
        raise MeshQAError("Original supports changed")
    flat_diaphragms=[]
    for id,names in sorted(controls["diaphragms"].items()):
        story,name=id.split(":",1)
        for pid in names:
            if abs(float(model["points_xyz_local_mm"][pid][2]))>1e-6:
                raise MeshQAError("Diaphragm point has nonplanar source offset")
        flat_diaphragms.append({"story":story,"diaphragm":name,"source_point_ids":sorted(names),
                                "assigned_points":len(names),"rigid_in_plane_only":True,
                                "does_not_constrain_vertical_uz":True})
    if sum(x["assigned_points"] for x in flat_diaphragms)!=201:
        raise MeshQAError("Source diaphragm register mismatch")
    panels=[];panels_by_story=defaultdict(list)
    mass_gravity=defaultdict(float)
    meshcount=0
    for shell in model["shells"]:
        key=shell["key"];cfg=controls["mesh"].get(key)
        if not cfg:raise MeshQAError("No native source mesh setting for "+key)
        coords=shell["vertices_xyz_mm"]
        n1,n2,rule=shell_rule(cfg,coords)
        projected=float(shell["projected_area_mm2"])
        aa=triangle_area_xy(*coords[:3])+triangle_area_xy(coords[0],coords[2],coords[3])
        if abs(aa-projected)>max(1,projected*1e-8):
            raise MeshQAError("Original panel projected area is not triangulation-compatible: "+key)
        truearea=triangle_area_3d(*coords[:3])+triangle_area_3d(coords[0],coords[2],coords[3])
        if truearea < projected*(1-1e-8):
            raise MeshQAError("Invalid source panel true surface area")
        gamma=model["materials"][shell["material"]]["unit_weight_N_mm3"] # N/mm3
        deadN=truearea*shell["thickness_mm"]*gamma
        mass_gravity[shell["storey"]]+=deadN/1000
        section_token=shell["section"].strip(\x27"\x27)
        shell_types=src["roles"]["ULS"]["shell_model_type"]
        if section_token not in shell_types:
            raise MeshQAError("Original E2K shell property name cannot be mapped: "+key)
        m={
          "key":key,"id":shell["id"],"story":shell["storey"],"kind":shell["kind"],"source_section":shell["section"],
          "original_corner_ids":shell["point_ids"],"corners_xyz_mm":coords,
          "source_shell_model_type":shell_types[section_token],
          "source_section_canonical":section_token,
          "source_section_projection_token":shell["section"],
          "source_mesh_mode":cfg.get("OBJMESHTYPE"),"n1":n1,"n2":n2,
          "requested_or_proxy_element_count":n1*n2,"mesh_rule":rule,
          "source_supported_by_frame_shell_topology":key in linked,
          "projected_area_m2":round(projected/1e6,6),
          "true_triangular_surface_area_m2":round(truearea/1e6,6),
          "true_area_concrete_selfweight_kN":round(deadN/1000,6),
          "source_thickness_mm":shell["thickness_mm"],
          "source_applied_loads":shell["applied_loads"],
          "provenance":"AUTHENTICATED_ORIGINAL_E2K_INPUT_NOT_SOLVER_OUTPUT"}
        panels.append(m);panels_by_story[m["story"]].append(m);meshcount+=n1*n2
    if Counter(p["source_mesh_mode"] for p in panels)!=Counter({"MESHN1XN2":106,"AUTOMESH":7,"DEFAULT":2}):
        raise MeshQAError("Original mesh-mode profile changed")
    originalwalls=[(m,l) for m in model["members"] for l in m["applied_loads"] if l["pattern"]=="WALL LOAD"]
    lines=[(m,l) for m,l in originalwalls if m["kind"]=="LINE"]
    if len(originalwalls)!=107 or len(lines)!=30:
        raise MeshQAError("Original wall load source assignment counts changed")
    geometry_line_transfer=[]
    source_force_total=0.
    for m,load in lines:
        a=m["start_xyz_mm"];b=m["end_xyz_mm"]
        N=48
        tally=defaultdict(float);unsupported=0
        w_total=float(load["raw_integrated_kN"])
        for i in range(N):
            t=(i+.5)/N
            xyz=[a[k]+(b[k]-a[k])*t for k in range(3)]
            candidates=[]
            for p in panels_by_story[m["storey"]]:
                if p["kind"]!="FLOOR":continue
                shape=shape_at_xy(p["corners_xyz_mm"],xyz)
                if shape is None:continue
                z=sum(shape[q]*p["corners_xyz_mm"][q][2] for q in range(4))
                if abs(z-xyz[2])>1e-3:continue
                candidates.append((p,shape))
            if not candidates:
                unsupported+=1;continue
            for p,shape in candidates:
                tally[p["key"]]+=w_total/N/len(candidates)
        if unsupported:
            raise MeshQAError("Native unsectioned wall line has source-unmatched shell point: "+m["key"])
        if abs(sum(tally.values())-w_total)>1e-5:
            raise MeshQAError("Unsectioned wall transfer proxy lost source force")
        source_force_total+=w_total
        geometry_line_transfer.append({
          "source_line":m["key"],"source_wall_kN":w_total,
          "unique_matching_shells":len(tally),
          "candidate_shell_force_share_kN":{k:round(v,6) for k,v in sorted(tally.items())},
          "unmatched_quadrature_intervals":unsupported,
          "quadrature_intervals":N,
          "line_to_shell_force_conserved":True,
          "correct_etabs_native_load_path_proven":False,
          "method":"48_MIDPOINT_SOURCE_POLYGON_BARYCENTRIC_WEIGHTING_SHARED_EDGE_SPLIT_PROXY"})
    if abs(source_force_total-sum(l["raw_integrated_kN"] for _,l in lines))>1e-5:
        raise MeshQAError("Source original unsectioned line load total did not reconcile")
    gravity=defaultdict(float)
    for m in model["members"]:
        if m["kind"] in ("BEAM","COLUMN"):
            gravity["Dead"]+=float(m["source_dead_selfweight_proxy_kN"])
        for r in m["applied_loads"]:gravity[r["pattern"]]+=r["raw_integrated_kN"]
    for p in panels:
        gravity["Dead"]+=p["true_area_concrete_selfweight_kN"]
        for r in p["source_applied_loads"]:
            gravity[r["pattern"]]+=r["raw_integrated_kN"]
    if sum(1 for p in panels if not p["source_supported_by_frame_shell_topology"])!=12:
        raise MeshQAError("Unsupported source shells were silently omitted")
    cases={}
    for role,ctrl in roles.items():
        combos=[]
        for name,rows in sorted(ctrl["combos"].items()):
            loads=[];kind=None
            for row in rows:
                if row[0]=="TYPE":kind=" ".join(row[1:])
                if row[0]=="LOADCASE" and "SF" in row:
                    idx=row.index("SF");loads.append({"case":row[1],"scale":float(row[idx+1])})
            if kind!="Linear Add" or not loads:
                raise MeshQAError("Unsupported source case combination: "+name)
            combos.append({"name":name,"type":kind,"terms":loads,
                           "gravity_known_exact_source_total_kN":round(sum(
                               gravity.get(x["case"],0)*x["scale"] for x in loads),6),
                           "contains_lateral_seismic":any(x["case"].startswith(("EQX","EQY")) for x in loads),
                           "not_solved_design_envelope":True})
        if len(combos)!=11:raise MeshQAError("Source load combo count changed")
        cases[role]={
           "source_11_load_combinations":combos,
           "seismic_controls":ctrl["seismic"],
           "mass_source":ctrl["mass"],
           "source_analysis_cases":ctrl["cases"],
           "source_shell_1250_mm_auto_maxmesh_unverified":True,
           "actual_full_seismic_case_solved":False}
    # Whole-model gravity is source-derived *input* and requires shell physical
    # continuity, source mesh, mass and diaphragm validation before it is a
    # true numerical building result.
    masses={
      "pattern_source_integrated_kN":{k:round(v,6) for k,v in sorted(gravity.items())},
      "conditional_msSrc1_gravity_weight_kN":round(sum(gravity.get(k,0)*x for k,x in
         {"Dead":1.,"Live":.3,"WALL LOAD":1.,"FLOOR FINISH":1.,"TANK":.6,"STAIRCASE LOAD":.3}.items()),6),
      "conditional_mass_kg":None,
      "accepted_governing_ETABS21_mass":False,
      "reasons":["source shell connectivity disconnected at 12 shell objects",
                 "auto/default mesh layout cannot be exactly reproduced from text-only source",
                 "gross geometric member selfweight overlaps at joints",
                 "rigid diaphragm vertical load transfer not demonstrated",
                 "source mass includes additional settings requiring solved mass table reconciliation"] }
    masses["conditional_mass_kg"]=round(masses["conditional_msSrc1_gravity_weight_kN"]*1000/G,4)
    if not masses["conditional_msSrc1_gravity_weight_kN"]>model["reconciled_source_applied_mass_eligible_loads_kN"]:
        raise MeshQAError("Source gravity mass proxy unexpectedly low")
    out={
        "schema":"jp.structural.r6p10.original_e2k_source_shell_mesh_and_loadcase_audit.v0.1",
        "governing_source_sha256":{"ULS":controls["sha256"],"SLS":roles["SLS"]["sha256"]},
        "source_ETABS21_geometry":True,"source_ETABS21_native_solver_reproduced":False,
        "source_shell_count":len(panels),"original_shell_area_count":115,
        "shell_mesh_requested_or_proxy_total_elements":meshcount,
        "requested_mesh_mode_counts":dict(sorted(Counter(p["source_mesh_mode"] for p in panels).items())),
        "shells_connected_through_source_to_fixed_base":len(linked),
        "shells_without_verified_vertical_support_path":len(unlinked),
        "unrestrained_shell_source_ids":unlinked,
        "source_graph_components":[{"anchored":a["anchored"],"point_storey_node_count":a["point_storey_node_count"],
             "fixed_source_bases":a["fixed_source_bases"]} for a in comps],
        "original_structural_frame_segments":165,"original_fully_fixed_base_points":27,
        "rigid_diaphragm_source_assignments":flat_diaphragms,
        "source_diaphragm_points_total":201,
        "diaphragm_in_plane_only":True,
        "native_all_shells":[{"key":p["key"],"story":p["story"],"kind":p["kind"],
            "corners_xyz_mm":p["corners_xyz_mm"],"n1":p["n1"],"n2":p["n2"],
            "source_mesh_mode":p["source_mesh_mode"],"source_section":p["source_section"],
            "source_supported":p["source_supported_by_frame_shell_topology"],
            "source_area_m2":p["projected_area_m2"]} for p in panels],
        "all_shell_parameters":panels,
        "source_line_wall_load_to_shell_transfer_proxy":geometry_line_transfer,
        "original_unsectioned_wall_load_count":len(lines),
        "mapped_source_line_wall_load_count":len(geometry_line_transfer),
        "mapped_unsectioned_line_gravity_kN":round(source_force_total,6),
        "all_source_gravity_loading":masses,
        "original_loadcase_and_combination_register":cases,
        "comprehensive_reconstructed_gravity_loading_inputs":True,
        "independently_solved_complete_gravity_cases":False,
        "independently_solved_complete_seismic_cases":False,
        "source_mass_source_exact_ETABS_result_verified":False,
        "complete_PMV_envelopes_approved":False,
        "source_F3_one_way_shear_unsafe":True,"engineering_approval":False}
    return out

def export():
    doc=build()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(doc,indent=2,sort_keys=True,allow_nan=False)+"\n")
    summary={
      "schema":"jp.structural.r6p10.source_shell_mesh_and_loadcase_qa.v0.1",
      "source_sha256":doc["governing_source_sha256"],
      "total_shell_objects":doc["source_shell_count"],
      "source_connected_shells":doc["shells_connected_through_source_to_fixed_base"],
      "source_unrestrained_shells":doc["shells_without_verified_vertical_support_path"],
      "original_diaphragm_point_assignments":doc["source_diaphragm_points_total"],
      "original_load_combinations_by_role":{k:len(v["source_11_load_combinations"])
          for k,v in doc["original_loadcase_and_combination_register"].items()},
      "source_mapped_LINE_wall_kN":doc["mapped_unsectioned_line_gravity_kN"],
      "conditional_not_approved_mass_weight_kN":doc["all_source_gravity_loading"]["conditional_msSrc1_gravity_weight_kN"],
      "source_QA_file_sha256":hashlib.sha256(OUT.read_bytes()).hexdigest(),
      "complete_source_model_solved":False,
      "actual_nonlinear_or_seismic_modal_solution":False,
      "F3_unsafe":True,"engineering_approval":False}
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    SUMMARY.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    return doc,summary

if __name__=="__main__":
    a,b=export()
    print("R6P10_SOURCE_SHELLS_115_CONNECTED_103_FLOATING_12_DIAPHRAGMS_201_LINE_LOADS_30")
    print(json.dumps({"mesh":a["shell_mesh_requested_or_proxy_total_elements"],
        "mass_is_source_proxy":b["conditional_not_approved_mass_weight_kN"]}))
