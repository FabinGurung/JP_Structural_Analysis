#!/usr/bin/env python3
"""R6.9 auditable ETABS21 -> OpenSees 3D FRAME-ONLY gravity bridge.

This is a deliberately BOUNDED independently solved case, not the building's
ETABS ULS/SLS structural solution: all original area shells, 201 diaphragm
point assignments, 30 wall loads attached to unsectioned lines, four partial
beam wall loads, beam loads on unsupported frame islands, source selfweight
and seismic design combinations remain OUT of this numerical subset.

Uses real immutable-source geometry, 27 original base restraints, material
elasticity, role-specific I2/I3/J modifiers, and 70 source UNIFF wall
loads on connected actual concrete beams. Produces signed 12-component
OpenSees local end actions ONLY if both convergence and reaction equilibrium
pass. Never fabricates or silently fills excluded load paths.

Analysis roles ULS and SLS refer solely to the source's respective
stiffness variants, not factored design load combinations.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter, defaultdict, deque
import hashlib
import json
import lzma
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_r6p8_native_source_catalogue import build as build_source
CONTROLS = ROOT / "registry/r6p9_etabs21_solver_controls.lzma.b64"
OUT = ROOT / "site/data/r6p9-etabs21-bounded-frame-solver.json"
MANIFEST = ROOT / "site/reports/r6p9-etabs21-bounded-frame-manifest.json"
UNCOMPRESSED_SHA256 = "c559311e7845863a4386b6b446dbc2ae0fd12ce11b2a5c7893320d1797862fcf"
SCHEMA = "jp.structural.r6p9.etabs21.source_solver_controls.v0.1"
LEVELS = {"Plinth level":0,"GF":3048,"FF":6096,"TF":9144}
BOUNDARY_STATUS = "SOURCE_FRAME_ONLY_OMITS_SHELL_DIAPHRAGM_AND_LOAD_TRANSFER"

class BridgeError(ValueError):
    pass

def controls():
    data=base64.b64decode("".join(CONTROLS.read_text(encoding="ascii").split()),validate=True)
    if len(data)>10000:raise BridgeError("Unexpected controls archive size")
    raw=lzma.decompress(data,format=lzma.FORMAT_XZ,memlimit=128*1024*1024)
    if hashlib.sha256(raw).hexdigest()!=UNCOMPRESSED_SHA256:
        raise BridgeError("Controls source SHA changed")
    a=json.loads(raw)
    if a.get("schema")!=SCHEMA or not a["status"]["F3_one_way_shear_unsafe"] or a["status"]["professional_approval"]:
        raise BridgeError("Source gate or F3 safety changed")
    model=build_source()
    for role in ("ULS","SLS"):
        r=a["roles"][role]
        if r["sha256"]!=model["source"]["source_ulssls_hashes"][("ULS","SLS").index(role)]:
            raise BridgeError("Live source SHA identity mismatch")
        if len(r["supports"])!=27 or len(set(r["supports"]))!=27:
            raise BridgeError("Restraints changed")
        if {k:len(v) for k,v in r["diaphragms"].items()}!={"GF:D1":67,"FF:D2":80,"TF:D3":54}:
            raise BridgeError("Diaphragm assignments changed")
        if len(r["mesh"])!=115 or len(r["combos"])!=11:
            raise BridgeError("Area mesh / load combinations changed")
        if r["analysis"]["PDELTA"]!=["METHOD","NONE"]:
            raise BridgeError("PDelta source changed")
        if r["mass"]["settings"]["INCLUDEELEMENTS"]!="No" or r["mass"]["settings"]["INCLUDELOADS"]!="Yes":
            raise BridgeError("Source seismic mass control changed")
        if r["mass"]["patterns"]!={"Dead":1.0,"Live":.3,"WALL LOAD":1.0,"FLOOR FINISH":1.0,"TANK":.6,"STAIRCASE LOAD":.3}:
            raise BridgeError("Mass pattern source changed")
        if r["seismic"]["EQX "+role]["SHEARCOEFF"] != (.131 if role=="ULS" else .126):
            raise BridgeError("Seismic coefficient source changed")
    if a["roles"]["ULS"]["supports"]!=a["roles"]["SLS"]["supports"] or a["roles"]["ULS"]["diaphragms"]!=a["roles"]["SLS"]["diaphragms"]:
        raise BridgeError("ULS/SLS point boundary maps no longer match")
    return model,a

def topology():
    model,a=controls()
    direct=[]
    edges=defaultdict(set)
    node_coords={}
    for m in model["members"]:
        if m["kind"] not in ("BEAM","COLUMN"):
            continue
        if m["kind"]=="COLUMN":
            lower={"GF":"Plinth level","FF":"GF","TF":"FF"}[m["storey"]]
            u=(m["point_ids"][0],lower)
            v=(m["point_ids"][1],m["storey"])
        else:
            u=(m["point_ids"][0],m["storey"])
            v=(m["point_ids"][1],m["storey"])
        for identity,coords in ((u,m["start_xyz_mm"]),(v,m["end_xyz_mm"])):
            position=tuple(float(z) for z in coords)
            if identity in node_coords and math.dist(node_coords[identity],position)>1e-6:
                raise BridgeError("Shared source point/story coordinate conflict: "+str(identity))
            node_coords[identity]=position
        if u==v:raise BridgeError("Zero-length frame node identity")
        edges[u].add(v);edges[v].add(u)
        direct.append((m,u,v))
    assert len(direct)==165
    seen=set()
    groups=[]
    support_ids=set(a["roles"]["ULS"]["supports"])
    for start in sorted(edges):
        if start in seen:continue
        q=deque([start]);seen.add(start);nodes=set()
        while q:
            key=q.popleft();nodes.add(key)
            for adj in edges[key]:
                if adj not in seen:seen.add(adj);q.append(adj)
        supports=sorted(k for k in nodes if k[1]=="Plinth level" and k[0] in support_ids)
        groups.append({"node_count":len(nodes),"fixed_source_base_nodes":len(supports),
                       "anchored":bool(supports),"node_keys":nodes})
    supported={k for c in groups if c["anchored"] for k in c["node_keys"]}
    solved=[(m,u,v) for m,u,v in direct if u in supported and v in supported]
    withheld=[(m,u,v) for m,u,v in direct if u not in supported or v not in supported]
    # 7 native frame-only connected components, 4 unsupported islands.
    if len(groups)!=7 or sum(not g["anchored"] for g in groups)!=4 or len(solved)!=161 or len(withheld)!=4:
        raise BridgeError("Source frame graph has changed, require topology review")
    if sum(len(g["node_keys"]) for g in groups if not g["anchored"])!=8:
        raise BridgeError("Source unsupported island coverage changed")
    eligible=[]
    deferred=[]
    for m,u,v in direct:
        for load in m["applied_loads"]:
            if load["pattern"]!="WALL LOAD":continue
            item={"key":m["key"],"load":load}
            if (u in supported and v in supported) and m["kind"]=="BEAM" and load["method"]=="U":
                eligible.append(item)
            else:deferred.append({**item,"reason":"TRAPF_OR_UNSUPPORTED_ISLAND"})
    lines=[(m,load) for m in model["members"] if m["kind"]=="LINE"
           for load in m["applied_loads"] if load["pattern"]=="WALL LOAD"]
    if len(eligible)!=70 or len(deferred)!=7 or len(lines)!=30:
        raise BridgeError("Wall-load coverage changed; do not silently approximate")
    total=sum(z["load"]["raw_integrated_kN"] for z in eligible)
    left_total=sum(z["load"]["raw_integrated_kN"] for z in deferred)+sum(z["raw_integrated_kN"] for _,z in lines)
    if not 0 < total < model["reconciled_source_applied_mass_eligible_loads_kN"]:
        raise BridgeError("Source wall loading reconciliation failed")
    baseline={
      "schema":"jp.structural.r6p9.native_frame_only_coverage.v0.1",
      "status":BOUNDARY_STATUS,
      "source":"USER_SELECTED_ETABS21_ULS_SLS_INPUTS",
      "model_solving_scope":"SOURCE_SUPPORT_CONNECTED_FRAME_ONLY_DIRECT_UNIFORM_WALL_LOAD",
      "native_points":127,"original_frame_elements":165,
      "original_lines_without_frame_stiffness":34,"original_shell_assignments":115,
      "source_fixed_base_point_assignments":27,
      "original_rigid_diaphragm_point_assignments":201,
      "frame_components":len(groups),
      "anchored_frame_components":sum(x["anchored"] for x in groups),
      "unanchored_islands":sum(not x["anchored"] for x in groups),
      "unsupported_island_nodes":8,
      "source_frame_elements_retained":len(solved),
      "source_frame_elements_withheld_without_support":len(withheld),
      "source_wall_load_records":107,
      "direct_uniform_wall_beam_loads_included":len(eligible),
      "direct_beam_wall_loads_deferred":len(deferred),
      "unsectioned_loaded_line_records_deferred":len(lines),
      "total_included_uniform_beam_wall_load_kN":round(total,6),
      "total_deferred_wall_load_kN":round(left_total,6),
      "all_source_direct_load_kN":model["reconciled_source_applied_mass_eligible_loads_kN"],
      "source_selfweight_excluded":True,
      "shell_floor_live_finish_loads_excluded":True,
      "rigid_diaphragm_source_assignments_not_yet_enforced":True,
      "source_partial_span_TRAPF_loads_not_solved":True,
      "accepted_full_model_analysis":False,
      "original_ETABS21_solver_result_verified":False,
      "F3_one_way_shear_unsafe":True,
      "engineering_approval":False,
      "member_force_scope_if_solved":"BOUNDED_WALL_LOAD_BASELINE_ONLY",
      "withheld_structural_member_keys":[m["key"] for m,_,_ in withheld],
      "withheld_load_keys":[x["key"] for x in deferred],
      "source_fingerprints":{"ULS":a["roles"]["ULS"]["sha256"],"SLS":a["roles"]["SLS"]["sha256"]},
      "stiffness_roles":{
         role:{name:ctrl["frame_modifiers"][name] for name in sorted(ctrl["frame_modifiers"])}
         for role,ctrl in a["roles"].items()},
      "source_analysis_controls":{"pdelta":"NONE","modal_eigen_max_modes":12,
             "diaphragms":sorted(a["roles"]["ULS"]["diaphragms"]),
             "load_combination_names":sorted(a["roles"]["ULS"]["combos"])}
    }
    return model,a,solved,node_coords,supported,eligible,baseline

def section_props(spec,elastic,mod):
    shape=spec["shape"]
    h=float(spec["depth_mm"])
    if shape=="Concrete Circle":
        d=h
        A=math.pi*d*d/4.
        Iy=Iz=math.pi*d**4/64
        J=math.pi*d**4/32
    elif shape=="Concrete Rectangular":
        b=float(spec["width_mm"])
        A=b*h
        # Assumed local-2 and local-3 orientation; exact ETABS local-axis
        # rotation, offsets, releases and section-specific torsion remain
        # subject to source-to-OpenSees transformation audit.
        Iy=h*b**3/12
        Iz=b*h**3/12
        narrow,wide=sorted((b,h))
        J=wide*narrow**3/3*(1-.63*(narrow/wide)+.052*(narrow/wide)**5)
    else:raise BridgeError("Unrecognized frame shape")
    E=float(elastic["E_N_mm2"]);nu=float(elastic["nu"])
    G=E/(2*(1+nu))
    return A,E,G,J*float(mod.get("JMOD",1.)),Iy*float(mod.get("I2MOD",1.)),Iz*float(mod.get("I3MOD",1.))

def solve(role, *, with_forces=True):
    if role not in ("ULS","SLS"):raise ValueError("Unknown role")
    import openseespy.opensees as ops
    model,regs,elements,xyz,anchored,eligible,coverage=topology()
    ctrl=regs["roles"][role]
    ops.wipe()
    ops.model("basic","-ndm",3,"-ndf",6)
    node_tags={key:i+1 for i,key in enumerate(sorted(anchored))}
    for key,tag in node_tags.items():
        ops.node(tag,*xyz[key])
        if key[1]=="Plinth level" and key[0] in set(ctrl["supports"]):
            ops.fix(tag,1,1,1,1,1,1)
    # Verify all source frame stiffnesses are material and role-specific.
    # Beam local xz reference is vertical; column xz is global Y.
    ops.geomTransf("Linear",1,0,0,1)
    ops.geomTransf("Linear",2,0,1,0)
    element_tags={}
    coords={}
    for it,(m,u,v) in enumerate(elements,1):
        mat=model["frame_sections"][m["section"]]
        spec=ctrl["material_elasticity"][mat["material"]]
        sec_mod=ctrl["frame_modifiers"].get(m["section"],{})
        A,E,G,J,Iy,Iz=section_props(mat,spec,sec_mod)
        geom=1 if m["kind"]=="BEAM" else 2
        ops.element("elasticBeamColumn",it,node_tags[u],node_tags[v],A,E,G,J,Iy,Iz,geom)
        element_tags[m["key"]]=it
        coords[m["key"]]=m
    ops.timeSeries("Linear",1)
    ops.pattern("Plain",1,1)
    # Uniform source loads only, exactly the 70 full-span BEAM entries that
    # have a verified frame-only support path. Sloping loads are projected
    # into local axial/transverse using the same xz ref (0,0,1).
    for rec in eligible:
        m=coords[rec["key"]]
        item=rec["load"]
        tag=element_tags[m["key"]]
        w=float(item["working"]["w_N_per_mm"])
        L=m["length_mm"]
        dz=m["end_xyz_mm"][2]-m["start_xyz_mm"][2]
        ratio=dz/L
        if not math.isfinite(ratio) or abs(ratio)>0.98:
            raise BridgeError("Beam axis nearly vertical: transformation requires source review")
        localz=-w*math.sqrt(max(0,1-ratio*ratio))
        localx=-w*ratio
        ops.eleLoad("-ele",tag,"-type","-beamUniform",0.0,localz,localx)
    ops.constraints("Plain")
    ops.numberer("RCM")
    ops.system("UmfPack")
    ops.test("NormDispIncr",1e-9,30)
    ops.algorithm("Linear")
    ops.integrator("LoadControl",1.0)
    ops.analysis("Static")
    if ops.analyze(1)!=0:
        raise BridgeError(role+" native-source frame-only gravity stiffness singular or solver failed")
    ops.reactions()
    reaction_nodes={}
    support_sum=[0.,0.,0.]
    for key,tag in node_tags.items():
        if key[1]!="Plinth level" or key[0] not in ctrl["supports"]:continue
        v=[float(x) for x in ops.nodeReaction(tag)[:3]]
        reaction_nodes[key[0]]=v
        for i in range(3):support_sum[i]+=v[i]
    expected=coverage["total_included_uniform_beam_wall_load_kN"]*1000
    error=abs(support_sum[2]-expected)
    if error>max(1e-3,abs(expected)*2e-5):
        raise BridgeError(f"Vertical reaction mismatch: Rz={support_sum[2]:.5f}N, F={expected:.5f}N")
    if abs(support_sum[0])>max(1e-3,abs(expected)*1e-5) or abs(support_sum[1])>max(1e-3,abs(expected)*1e-5):
        raise BridgeError("Horizontal gravity-only reaction not balanced")
    signed={}
    if with_forces:
        for key,tag in element_tags.items():
            v=ops.eleResponse(tag,"localForce")
            if len(v)!=12 or any(not math.isfinite(float(q)) for q in v):
                raise BridgeError("Invalid signed 12-component member end-force row: "+key)
            signed[key]=[round(float(q)/1000 if i in (0,1,2,6,7,8) else float(q)/1e6,6) for i,q in enumerate(v)]
    maximum=max((abs(float(x)) for tag in node_tags.values() for x in ops.nodeDisp(tag)[:3]),default=0)
    ops.wipe()
    return {
      "role":role,"status":"SOURCE_NATIVE_BOUNDED_GRAVITY_FRAME_NUMERICALLY_SOLVED",
      "model_not_full_etabs21":True,
      "applied_load_pattern":"WALL LOAD_DIRECT_UNIFORM_SUPPORTED_BEAMS_ONLY",
      "source_material_modifiers_role":role,
      "solved_elements":len(element_tags),
      "direct_assigned_uniform_loads":len(eligible),
      "applied_vertical_load_kN":round(expected/1000,6),
      "reconstructed_base_reaction_kN":[round(x/1000,6) for x in support_sum],
      "reaction_vertical_residual_N":round(error,6),
      "maximum_nodal_translation_mm":round(maximum,7),
      "signed_force_order":["Ni_kN","Vyi_kN","Vzi_kN","Ti_kNm","Myi_kNm","Mzi_kNm",
                            "Nj_kN","Vyj_kN","Vzj_kN","Tj_kNm","Myj_kNm","Mzj_kNm"],
      "actual_source_member_end_actions_bounded_only":signed,
      "support_vertical_reactions_kN":{key:round(v[2]/1000,6) for key,v in sorted(reaction_nodes.items())},
      "shell_force_transfer_included":False,
      "rigid_diaphragm_enforced":False,
      "original_ETABS21_result":False,
      "full_member_design_envelope":False,
      "F3_one_way_shear_unsafe":True,
      "engineering_approval":False
    }

def generate(run_solver=True, out=OUT):
    model,reg,elem,xyz,anchored,loads,coverage=topology()
    results={}
    if run_solver:
        for role in ("ULS","SLS"):
            results[role]=solve(role)
    else:
        for role in ("ULS","SLS"):
            results[role]={"role":role,"status":"SOURCE_MODEL_PREPARED_NOT_RUN",
                           "original_ETABS21_result":False,"engineering_approval":False}
    doc={"schema":"jp.structural.r6p9.bounded_source_openSees_results.v0.1",
         "coverage":coverage,"solver":"OpenSeesPy 3.8.0.0 3D linear elasticBeamColumn",
         "stiffness_note":"Source E and cracked section I modifiers; rectangular St Venant J is a stated approximation; no shell or diaphragm stiffness",
         "gravity_load_note":"Only supported full-span native BEAM wall loads applied; no element selfweight or shell dead/live loads",
         "roles":results,"professional_engineering_approval":False}
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(doc,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf8")
    receipt={"schema":"jp.structural.r6p9.bounded_source_openSees_manifest.v0.1",
             "result_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
             "source_control_sha256":UNCOMPRESSED_SHA256,
             "source_native_uls_sls_sha256":coverage["source_fingerprints"],
             "solved_cases":[k for k,v in results.items() if v["status"].endswith("NUMERICALLY_SOLVED")],
             "full_ETABS21_solver_replication":False,"engineering_approval":False,
             "F3_one_way_shear_unsafe":True}
    MANIFEST.parent.mkdir(parents=True,exist_ok=True)
    MANIFEST.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf8")
    return doc,receipt

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--prepare-only",action="store_true",
                        help="Source topology only; full numeric output requires OpenSees")
    args=parser.parse_args()
    doc,manifest=generate(run_solver=not args.prepare_only)
    print("R6P9_GOVERNING_SOURCE_BOUNDED_FRAME_GRAVITY",doc["coverage"]["direct_uniform_wall_beam_loads_included"],
          [(k,v["status"]) for k,v in doc["roles"].items()])
