#!/usr/bin/env python3
"""R6.17 canonical ETABS21-input topology and equilibrium-checked *research* reactions.

Source node identity is (original point ID, story), NOT XYZ proximity. All
115 original shells stay in the register; 12 without an original source graph
path to base remain explicitly excluded from the numerical 2x2 shell trial.
Nearness to a slab/beam is a diagnostic only; no joints or restraints added.

Existing R6.10 OpenSees casebook provides 8 genuinely solved bounded gravity
cases with individual signed 6-DOF reactions; these are NOT native ETABS21
support outputs and not actual accepted footing demands.
"""
from __future__ import annotations
from collections import Counter,defaultdict,deque
from hashlib import sha256
from pathlib import Path
import json, math, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_r6p8_native_source_catalogue import build as source_catalogue
from scripts.run_r6p9_source_frame_gravity import controls as source_controls
from scripts.build_r6p10_source_shell_mesh import build as source_shell_audit,native_components
from scripts.build_r6p10_gravity_casebook import build_casebook
from scripts.r6p11_support_candidates import contact_audit
OUT=ROOT/"site/data/r6p17-canonical-3d-source-graph.json"
RECEIPT=ROOT/"site/reports/r6p17-canonical-model-reaction-receipt.json"
SCHEMA="jp.structural.r6p17.canonical_source_topology_and_bounded_gravity.v0.1"
ROLES=("ULS","SLS")
CASES=("Dead","Live","WALL LOAD","FLOOR FINISH")
PRIOR={"GF":"Plinth level","FF":"GF","TF":"FF"}
TOL_MM=0.001

def nodekey(point,story):return str(story)+":"+str(point)
def vec(p):return tuple(float(z) for z in p)
def pt_segment_distance(p,a,b):
    p,a,b=vec(p),vec(a),vec(b)
    v=[b[i]-a[i] for i in range(3)]
    vv=sum(x*x for x in v)
    if vv<=1.e-16:raise ValueError("Degenerate source segment")
    t=max(0.,min(1.,sum((p[i]-a[i])*v[i] for i in range(3))/vv))
    closest=[a[i]+t*v[i] for i in range(3)]
    return math.dist(p,closest),t

def canonical_topology(model,registry):
    if model["source"]["governing_etabs_major"]!=21:
        raise ValueError("Wrong source engine version")
    if len(model["members"])!=199 or len(model["shells"])!=115:
        raise ValueError("Original source scope changed")
    declared=set(registry["roles"]["ULS"]["supports"])
    if len(declared)!=27 or declared!=set(registry["roles"]["SLS"]["supports"]):
        raise ValueError("Original 27 base restraints changed")
    nodes={};adj=defaultdict(set);edges=[]
    def ensure(pid,story,xyz):
        key=nodekey(pid,story);coords=vec(xyz)
        if key in nodes and math.dist(nodes[key]["xyz_mm"],coords)>TOL_MM:
            raise ValueError("Conflicting source point/story geometry: "+key)
        if key not in nodes:
            nodes[key]={"key":key,"source_point_id":str(pid),"story":story,
                "xyz_mm":[round(v,6) for v in coords],
                "source_identity_not_generated_solver_node":True}
        adj[key]
        return key
    def edge(key,kind,u,v,index=None):
        if u==v:raise ValueError("Zero-length canonical source identity edge")
        adj[u].add(v);adj[v].add(u)
        row={"element_key":key,"element_kind":kind,"node_i":u,"node_j":v,
            "source_adjacency_only":True,"native_joint_compatibility_verified":False,
            "real_shell_frame_load_transfer_verified":False}
        if index is not None:row["polygon_edge_index"]=index
        edges.append(row)
    frames=[]
    for member in sorted(model["members"],key=lambda x:x["key"]):
        if member["kind"] not in ("BEAM","COLUMN"):continue
        id1,id2=member["point_ids"]
        low=PRIOR[member["storey"]] if member["kind"]=="COLUMN" else member["storey"]
        u=ensure(id1,low,member["start_xyz_mm"])
        v=ensure(id2,member["storey"],member["end_xyz_mm"])
        edge(member["key"],member["kind"],u,v)
        frames.append({"key":member["key"],"kind":member["kind"],
            "source_story":member["storey"],"node_i":u,"node_j":v,
            "source_section":member["section"],"original_E2K_geometry_only":True,
            "actual_element_end_releases_and_offsets_verified":False})
    shell_details=[]
    for panel in sorted(model["shells"],key=lambda x:x["key"]):
        cornerids=[str(v) for v in panel["point_ids"]]
        vertices=panel["vertices_xyz_mm"]
        if len(cornerids)!=4 or len(vertices)!=4:
            raise ValueError("Original unsupported nonquad shell cannot be quietly meshed")
        corners=[ensure(pid,panel["storey"],p) for pid,p in zip(cornerids,vertices)]
        if len(set(corners))!=4:raise ValueError("Repeated source shell corner")
        for i in range(4):
            edge(panel["key"],"SHELL_SOURCE_BOUNDARY",corners[i],corners[(i+1)%4],i)
        shell_details.append({"key":panel["key"],"kind":panel["kind"],
            "story":panel["storey"],"source_section":panel["section"],
            "source_corner_point_ids":cornerids,"nodes":corners,
            "corner_xyz_mm":vertices,
            "projected_source_area_m2":round(panel["projected_area_mm2"]/1e6,6),
            "source_loads":panel["applied_loads"],
            "native_generated_mesh_verified":False})
    if len(frames)!=165 or len(edges)!=165+115*4:
        raise ValueError("Canonical source element totals changed")
    components=[];seen=set();component_of={}
    for start in sorted(nodes):
        if start in seen:continue
        q=deque([start]);seen.add(start);group=[]
        while q:
            u=q.popleft();group.append(u)
            for v in sorted(adj[u]):
                if v not in seen:seen.add(v);q.append(v)
        base=sorted(u for u in group if nodes[u]["story"]=="Plinth level" and
                    nodes[u]["source_point_id"] in declared)
        cid=f"CC{len(components)+1:02d}"
        for k in group:component_of[k]=cid
        components.append({"id":cid,"original_node_count":len(group),
          "source_base_point_ids":[nodes[k]["source_point_id"] for k in base],
          "has_declared_base_reachability":bool(base),
          "native_solver_node_equivalence_verified":False,
          "source_nodes":sorted(group)})
    if len(components)!=5 or sum(c["has_declared_base_reachability"] for c in components)!=2:
        raise ValueError("Source 5 component/2 anchored component invariant changed")
    source_supported=[s["key"] for s in shell_details if all(
        components[int(component_of[k][2:])-1]["has_declared_base_reachability"] for k in s["nodes"])]
    withheld=[s["key"] for s in shell_details if s["key"] not in source_supported]
    classic,_,classic_supported,classic_withheld=native_components(model,registry)
    if len(source_supported)!=103 or len(withheld)!=12 or set(withheld)!=set(classic_withheld) or set(source_supported)!=set(classic_supported):
        raise ValueError("Canonical graph diverges from original R6.10 immutable source-shell graph")
    if len(classic)!=len(components):raise ValueError("Original source component count changed")
    original_source_support_nodes=sorted(
      nodekey(pid,"Plinth level") for pid in declared if nodekey(pid,"Plinth level") in nodes)
    if len(original_source_support_nodes)!=21:
        raise ValueError("Connected source support count differs from R6.10 OpenSees trial")
    unused=sorted(pid for pid in declared if nodekey(pid,"Plinth level") not in nodes)
    if len(unused)!=6:raise ValueError("Source orphan restraint IDs changed")
    for x in nodes.values():
        x["source_component_id"]=component_of[x["key"]]
        x["declared_fixed_base"]=x["key"] in original_source_support_nodes
        x["source_graph_base_reachable"]=components[int(component_of[x["key"]][2:])-1]["has_declared_base_reachability"]
        x["actual_joint_constraint_verified"]=False
    for x in frames:
        x["original_source_graph_base_reachable"]=nodes[x["node_i"]]["source_graph_base_reachable"] and nodes[x["node_j"]]["source_graph_base_reachable"]
    if sum(not f["original_source_graph_base_reachable"] for f in frames):
        raise ValueError("Original structural frame topology unexpectedly gained unsupported members")
    for x in shell_details:
        x["source_graph_base_reachable"]=x["key"] in source_supported
        x["component_ids"]=sorted(set(component_of[k] for k in x["nodes"]))
        x["admitted_to_existing_coarse_research_solver"]=x["key"] in source_supported
        x["accepted_load_bearing_source_path"]=None
        x["accepted_design_shell_reactions"]=None
        x["approved_engineering_support"]=False
    return {"nodes":nodes,"frames":frames,"shells":shell_details,"edges":edges,
      "components":components,"connected_support_node_keys":original_source_support_nodes,
      "declared_support_ids":sorted(declared),"unmatched_declared_support_ids":unused,
      "unsupported_shell_ids":sorted(withheld),"connected_shell_ids":sorted(source_supported),
      "frame_shell_source_graph_reproduces_R610":True}

def unsupported_diagnostics(model,graph):
    shells={p["key"]:p for p in model["shells"]}
    frames=[m for m in model["members"] if m["kind"] in ("BEAM","COLUMN")]
    supported_shells=[shells[k] for k in graph["connected_shell_ids"]]
    diagnostics=[]
    for key in graph["unsupported_shell_ids"]:
        panel=shells[key]
        corners=panel["vertices_xyz_mm"]
        frame_hits=[]
        for m in frames:
            # A nearest spatial candidate does not prove shared nodes, releases, or support.
            distance=min(pt_segment_distance(p,m["start_xyz_mm"],m["end_xyz_mm"])[0] for p in corners)
            frame_hits.append((distance,m["key"],m["storey"],m["kind"]))
        shell_hits=[]
        for other in supported_shells:
            if other["storey"]!=panel["storey"]:continue
            vertices=other["vertices_xyz_mm"]
            distance=min(pt_segment_distance(p,vertices[i],vertices[(i+1)%4])[0]
                     for p in corners for i in range(4))
            shell_hits.append((distance,other["key"]))
        nearest_frame=sorted(frame_hits)[:3]
        nearest_shell=sorted(shell_hits)[:3]
        diagnostics.append({
          "shell_key":key,"story":panel["storey"],"kind":panel["kind"],
          "original_point_ids":panel["point_ids"],
          "source_component_ids":next(x["component_ids"] for x in graph["shells"] if x["key"]==key),
          "nearest_original_structural_frames":[
             {"member_key":mid,"story":story,"kind":kind,"minimum_corner_to_segment_mm":round(dist,6),
              "source_identity_still_unconnected":True,"source_support_admitted":False}
             for dist,mid,story,kind in nearest_frame],
          "nearest_source_graph_connected_shell_edges_same_storey":[
             {"shell_key":sid,"minimum_corner_to_edge_mm":round(dist,6),
               "actual_ETABS21_generated_joint_constraint_verified":False}
             for dist,sid in nearest_shell],
          "r611_tolerance_geometric_proximity_not_structural_support":True,
          "source_graph_path_to_base":False,
          "source_model_mesh_and_vertical_reaction_verified":False,
          "original_ETABS21_native_connection_evidence_missing":True,
          "new_contact_or_support_created":False,
          "admitted_to_solved_model":False,
          "design_load_transfer_accepted":None,
          "review_priority":"SOURCE_NODE_MAPPING_AND_DRAWING_JOINT_VERIFICATION",
        })
    if len(diagnostics)!=12:raise ValueError("Missing individual unanchored source shell report")
    return diagnostics

def gravity_reaction_audit(casebook,graph):
    if casebook["schema"]!="jp.structural.r6p10.connected_source_shell_gravity_and_conditional_seismic_casebook.v0.2":
        raise ValueError("R6.10 casebook schema changed")
    if casebook["source_shells_numerically_solved"]!=103 or casebook["original_shells_source_vertically_unanchored"]!=12:
        raise ValueError("Original numerical shell admission changed")
    rows=[]; support_sets=[]
    for role in ROLES:
        group=casebook["role_results"][role]["independently_run_research_patterns"]
        for pattern in CASES:
            d=group[pattern]
            if d["role"]!=role or d["source_case"]!=pattern:raise ValueError("Coarse gravity pattern case drift")
            if d["original_source_restraints_declared"]!=27 or d["source_restraints_physically_connected"]!=21:
                raise ValueError("Canonical original base support register changed")
            if d["original_unsupported_shells_numerically_excluded"]!=12 or d["vertically_supported_shells_numerically_included"]!=103:
                raise ValueError("Coarse shell admission changed")
            reactions=d.get("connected_support_signed_reactions_research_only")
            if not isinstance(reactions,list) or len(reactions)!=21:
                raise ValueError("Missing all signed 21-source-support reaction records")
            ids=[]
            for r in reactions:
                if len(r["signed_Fxyz_N"])!=3 or len(r["signed_Mxyz_Nmm"])!=3:
                    raise ValueError("Original bounded support force-moment vector incomplete")
                if any(not math.isfinite(float(v)) for v in r["signed_Fxyz_N"]+r["signed_Mxyz_Nmm"]):
                    raise ValueError("Nonfinite source support reaction")
                ids.append(tuple(sorted(str(q) for q in r["original_base_point_ids"])))
                if not ids[-1]:raise ValueError("Per-support source ID missing")
                xyz=[float(v) for v in r["xyz_mm"]]
                for pid in ids[-1]:
                    key=nodekey(pid,"Plinth level")
                    if key not in graph["connected_support_node_keys"] or math.dist(xyz,graph["nodes"][key]["xyz_mm"])>0.0011:
                        raise ValueError("Research support mapped to non-original or displaced base joint")
            support_sets.append(set(ids))
            sumv=[sum(float(r["signed_Fxyz_N"][i]) for r in reactions) for i in range(3)]
            stored=d["sum_native_fixed_base_reactions_N"]
            if any(abs(a-b)>1e-4 for a,b in zip(sumv,stored)):
                raise ValueError("Signed support-level reaction ledger differs from coarse FE totals")
            applied=float(d["applied_gravity"]["total_applied_downward_N"])
            res=abs(sumv[2]-applied)
            tol=max(0.05,abs(applied)*3e-5)
            if res>tol or abs(res-float(d["vertical_equilibrium_residual_N"]))>1e-4:
                raise ValueError("Research vertical equilibrium fails")
            rows.append({"role":role,"original_source_gravity_pattern":pattern,
               "native_source_stiffness_variant":role,
               "applied_gravity_downward_kN":round(applied/1000,6),
               "sum_signed_connected_base_reaction_kN":[round(v/1000,6) for v in sumv],
               "vertical_equilibrium_error_N":round(res,7),
               "vertical_equilibrium_tolerance_N":round(tol,7),
               "force_equilibrium_verified_for_bounded_model":True,
               "signed_support_reactions":[
                  {"original_source_base_point_ids":r["original_base_point_ids"],
                   "xyz_mm":r["xyz_mm"],"signed_Rxyz_kN":[round(v/1000,7) for v in r["signed_Fxyz_N"]],
                   "signed_Mxyz_kNm":[round(v/1e6,7) for v in r["signed_Mxyz_Nmm"]],
                   "actual_ETABS21_support_reaction_verified":False}
                  for r in reactions],
               "source_model_reactions_accepted_for_final_footing_design":False,
               "coarse_shell_mesh_elements":d["coarse_numerical_shell_elements"],
               "additional_supports_created":False})
    if len(rows)!=8 or any(s!=support_sets[0] for s in support_sets):
        raise ValueError("Original source support mapping changed between ULS/SLS gravity cases")
    return rows

def build(model=None,control=None,mesh=None,casebook=None):
    if model is None:model=source_catalogue()
    if control is None:
        native,control=source_controls()
        if native["source"]["source_ulssls_hashes"]!=model["source"]["source_ulssls_hashes"]:
            raise ValueError("ETABS21 input source and solver controls differ")
    if mesh is None:mesh=source_shell_audit()
    if casebook is None:casebook=build_casebook()
    hashes=dict(zip(ROLES,model["source"]["source_ulssls_hashes"]))
    if mesh["governing_source_sha256"]!=hashes or casebook["source_model_fingerprints"]!=hashes:
        raise ValueError("Source SHA mismatch between R6.10 and R6.17")
    if mesh["source_F3_one_way_shear_unsafe"]!=True or mesh["engineering_approval"]!=False:
        raise ValueError("F3 adverse source report or engineering HOLD changed")
    graph=canonical_topology(model,control)
    if set(graph["unsupported_shell_ids"])!=set(mesh["unrestrained_shell_source_ids"]):
        raise ValueError("R6.17 excluded shells do not match original R6.10")
    proximity=unsupported_diagnostics(model,graph)
    near=contact_audit(model,graph["unsupported_shell_ids"])
    cases=gravity_reaction_audit(casebook,graph)
    report={"schema":SCHEMA,"governing_ULS_SLS_input_SHA256":hashes,
       "model_definition":"ORIGINAL_ETABS21_SOURCE_IDENTITY_GRAPH_NO_GENERATED_ANALYSIS_MESH",
       "node_key_semantics":"story:pointID exactly; XYZ overlap alone never merges source joints",
       "geometry_tolerance_mm":TOL_MM,
       "counts":{"source_points_catalogued":len(model["points_xyz_local_mm"]),
         "source_frame_objects":len(graph["frames"]),"source_shell_objects":len(graph["shells"]),
         "canonical_source_graph_nodes":len(graph["nodes"]),"canonical_source_graph_edges":len(graph["edges"]),
         "original_source_fixed_base_point_ids":len(graph["declared_support_ids"]),
         "used_in_current_coarse_FE_fixed_base_nodes":len(graph["connected_support_node_keys"]),
         "declared_fixed_base_ids_without_frame_shell_graph_node":len(graph["unmatched_declared_support_ids"]),
         "source_components":len(graph["components"]),
         "components_with_original_fixed_base_path":sum(c["has_declared_base_reachability"] for c in graph["components"]),
         "source_graph_connected_shells":len(graph["connected_shell_ids"]),
         "original_unanchored_shells_excluded":len(graph["unsupported_shell_ids"]),
         "independently_solved_bounded_gravity_cases":len(cases),
         "signed_individual_base_reactions":sum(len(c["signed_support_reactions"]) for c in cases)},
       "canonical_nodes":list(sorted(graph["nodes"].values(),key=lambda x:x["key"])),
       "canonical_original_frames":graph["frames"],
       "canonical_original_shells":graph["shells"],
       "source_topological_edges":graph["edges"],
       "source_components":graph["components"],
       "original_fixed_base_ids":graph["declared_support_ids"],
       "coarse_FE_original_base_id_nodes":graph["connected_support_node_keys"],
       "original_source_base_ids_not_bound_to_coarse_FE":graph["unmatched_declared_support_ids"],
       "individual_twelve_unanchored_shell_investigations":proximity,
       "source_corner_contact_candidate_audit":near,
       "coarse_trial_signed_gravity_support_reactions":cases,
       "research_case_sign_convention":"positive Rz upward, applied gravity downward; OpenSees 6DOF nodeReaction signed",
       "source_shell_admission_rule":"original ID adjacency reaching user-selected fixed base, not verified force-path connectivity",
       "source_graph_shells_accepted_as_actual_vertical_support":False,
       "native_ETABS21_generated_joints_or_releases_verified":False,
       "no_source_unsupported_shell_was_added_to_solver":True,
       "no_new_fixed_restraints_or_beam_shell_ties_created":True,
       "full_ETABS21_3D_model_reconstructed_and_validated":False,
       "coarse_2x2_shell_mesh_original_ETABS_8x8_equivalent":False,
       "source_vertical_reactions_physically_verified":False,
       "equilibrium_of_research_gravity_cases_verified":True,
       "final_design_member_or_foundation_reactions_approved":False,
       "R6P16_engineering_readiness_held":True,
       "F3_one_way_shear_unsafe":True,
       "engineering_approval":False}
    c=report["counts"]
    if (c["source_frame_objects"],c["source_shell_objects"],c["source_components"],
        c["components_with_original_fixed_base_path"],c["source_graph_connected_shells"],
        c["original_unanchored_shells_excluded"],c["original_source_fixed_base_point_ids"],
        c["used_in_current_coarse_FE_fixed_base_nodes"],
        c["independently_solved_bounded_gravity_cases"],c["signed_individual_base_reactions"])!=(
        165,115,5,2,103,12,27,21,8,168):
        raise ValueError("Canonical R6.17 source and supported research case invariants changed")
    return report

def export(model=None,control=None,mesh=None,casebook=None):
    d=build(model=model,control=control,mesh=mesh,casebook=casebook)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(d,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf8")
    receipt={"schema":"jp.structural.r6p17.model_reaction_receipt.v0.1",
      "source_SHA256":d["governing_ULS_SLS_input_SHA256"],
      "canonical_graph_and_reactions_SHA256":sha256(OUT.read_bytes()).hexdigest(),
      "counts":d["counts"],"no_original_unsupported_shell_promoted":True,
      "source_native_ETABS21_reactions_verified":False,
      "coarse_research_force_equilibrium_verified":True,
      "F3_one_way_shear_unsafe":True,"engineering_approval":False}
    RECEIPT.parent.mkdir(parents=True,exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf8")
    return d,receipt
if __name__=="__main__":
    a,b=export()
    print("R6P17_CANONICAL_SOURCE_GRAPH_12_SHELL_HOLD",json.dumps(a["counts"],sort_keys=True))
    print("R6P17_RESEARCH_EIGHT_GRAVITY_CASES_168_SIGNED_SUPPORT_REACTIONS_F3_UNSAFE")
