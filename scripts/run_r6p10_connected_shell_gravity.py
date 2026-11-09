#!/usr/bin/env python3
"""R6.10 research-only source-connected ShellMITC4 gravity and ESM trial.

Full original shell/source records: 115 (12 lack native-source support path).
Numerical pilot: 103 connected shell surfaces meshed 2x2, all 165 native
sectioned beams/columns, source role stiffness, actual fixed supports and
available rigid diaphragm source point constraints. This is a NON-CONFORMING
COARSE TRIAGE MESH, NOT ETABS automatic 8x8 meshing or full building design.
No artificial fixities, no unapproved mass source, no engineer approval.

A solved case is published only with finite 12-component member forces and
global equilibrium. Unverified shell load transfers / joint compatibility,
source selfweight and partial span formulations are explicitly labelled.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from scripts.build_r6p10_source_shell_mesh import build as source_audit, shape_at_xy, mesh_point, triangle_area_xy, triangle_area_3d
from scripts.run_r6p9_source_frame_gravity import controls, section_props
from scripts.build_r6p8_native_source_catalogue import build as native_model

OUT=ROOT/"site/data/r6p10-source-connected-shell-trial.json"
MANIFEST=ROOT/"site/reports/r6p10-source-connected-shell-trial-manifest.json"

def rig(role="ULS",resolution=2):
    if resolution not in (1,2,4):
        raise ValueError("This bounded research solver has only 1, 2 and 4 trial refinements")
    source=source_audit()
    native,registry=controls()
    ctrl=registry["roles"][role]
    import openseespy.opensees as ops
    ops.wipe()
    ops.model("basic","-ndm",3,"-ndf",6)
    by_xyz={}
    positions={}
    def node(p):
        key=tuple(round(float(z),3) for z in p)
        if key not in by_xyz:
            tag=len(by_xyz)+1
            by_xyz[key]=tag
            positions[tag]=key
            ops.node(tag,*key)
        return by_xyz[key]
    frametags={}
    frameids={}
    for m in native["members"]:
        if m["kind"] not in ("BEAM","COLUMN"):continue
        a=node(m["start_xyz_mm"]);b=node(m["end_xyz_mm"])
        if a==b:raise ValueError("Original source frame has zero length")
        frameids[m["key"]]=(a,b,m)
    source_panels={p["key"]:p for p in source["all_shell_parameters"] if p["source_supported_by_frame_shell_topology"]}
    if len(source_panels)!=103 or len(frameids)!=165:
        raise ValueError("Source supported-component count drift")
    cells={};surf_keys={}
    for key,p in source_panels.items():
        corners=p["corners_xyz_mm"];grid={}
        for i in range(resolution+1):
            for j in range(resolution+1):
                grid[i,j]=node(mesh_point(corners,i/resolution,j/resolution))
        span=[]
        for i in range(resolution):
            for j in range(resolution):
                corners4=[grid[i,j],grid[i+1,j],grid[i+1,j+1],grid[i,j+1]]
                xyz4=[positions[q] for q in corners4]
                signed=sum(xyz4[k][0]*xyz4[(k+1)%4][1]-xyz4[(k+1)%4][0]*xyz4[k][1] for k in range(4))
                if abs(signed)<1e-3:
                    raise ValueError("Unresolved zero-area source shell mesh quad "+key)
                if signed<0:
                    corners4=[corners4[0],corners4[3],corners4[2],corners4[1]]
                    xyz4=[positions[q] for q in corners4]
                proj=(triangle_area_xy(*xyz4[:3])+triangle_area_xy(xyz4[0],xyz4[2],xyz4[3]))
                true=(triangle_area_3d(*xyz4[:3])+triangle_area_3d(xyz4[0],xyz4[2],xyz4[3]))
                span.append({"nodes":corners4,"xyz":xyz4,"projection_mm2":proj,"true_area_mm2":true})
        cells[key]=span
        surf_keys[key]=grid

    source_points=native["points_xyz_local_mm"]
    diaphragm_assignments=[]
    masters={}
    for item in source["rigid_diaphragm_source_assignments"]:
        story=item["story"];pidlist=item["source_point_ids"]
        slave=[]
        for pid in pidlist:
            xyz=source_points[pid]
            point=(xyz[0],xyz[1],xyz[2]+native["floor_elevations_mm"][story])
            key=tuple(round(float(z),3) for z in point)
            if key in by_xyz:slave.append(by_xyz[key])
        if not slave:continue
        xs=[positions[t][0] for t in slave];ys=[positions[t][1] for t in slave]
        floorZ=native["floor_elevations_mm"][story]
        # Diaphragm master is a non-structural kinematic reference, not a support.
        master=len(by_xyz)+len(masters)+10000
        ops.node(master,sum(xs)/len(xs),sum(ys)/len(ys),floorZ)
        ops.fix(master,0,0,1,1,1,0)
        masters[story]=master
        ops.rigidDiaphragm(3,master,*sorted(set(slave)))
        diaphragm_assignments.append({"source_story":story,
             "original_source_point_assignments":len(pidlist),
             "slaves_with_structural_or_connected_shell_nodes":len(set(slave)),
             "withheld_due_to_unconnected_original_shells":len(pidlist)-len(set(slave))})
    if set(masters)!={"GF","FF","TF"}:
        raise ValueError("Original three diaphragms could not be mapped")

    original_supports=set(ctrl["supports"])
    support_tags=set()
    for pid in original_supports:
        xyz=source_points[pid]
        key=tuple(round(float(z),3) for z in xyz)
        if key in by_xyz:
            tag=by_xyz[key]
            ops.fix(tag,1,1,1,1,1,1)
            support_tags.add(tag)
    if len(support_tags)!=27:
        raise ValueError("Original 27 supports not represented by verified source nodes")

    ops.geomTransf("Linear",1,0,0,1)
    ops.geomTransf("Linear",2,0,1,0)
    tag=0
    for key,(u,v,m) in sorted(frameids.items()):
        sec=native["frame_sections"][m["section"]]
        material=ctrl["material_elasticity"][sec["material"]]
        mod=ctrl["frame_modifiers"].get(m["section"],{})
        A,E,G,J,Iy,Iz=section_props(sec,material,mod)
        tag+=1
        ops.element("elasticBeamColumn",tag,u,v,A,E,G,J,Iy,Iz,1 if m["kind"]=="BEAM" else 2)
        frametags[key]=tag
    sections={}
    for m in source_panels.values():
        section_key=m["source_section_canonical"]
        if section_key in sections:continue
        shell=native["shell_sections"][m["source_section"]]
        material=ctrl["material_elasticity"][shell["material"]]
        t=float(shell["thickness_mm"])
        sec_tag=100+len(sections)
        ops.section("ElasticMembranePlateSection",sec_tag,float(material["E_N_mm2"]),
                    float(material["nu"]),t,0.0)
        sections[section_key]=sec_tag
    shelltags={}
    for key,pan in sorted(source_panels.items()):
        secid=sections[pan["source_section_canonical"]]
        shelltags[key]=[]
        for cell in cells[key]:
            tag+=1
            ops.element("ShellMITC4",tag,*cell["nodes"],secid)
            shelltags[key].append(tag)

    return {"ops":ops,"ctrl":ctrl,"native":native,"source":source,"frames":frameids,
       "frametags":frametags,"shelltags":shelltags,"cells":cells,"positions":positions,
       "supports":support_tags,"diaphragms":diaphragm_assignments,"masters":masters,
       "tag_count":tag,"resolution":resolution}

def add_gravity_loads(r,case):
    ops=r["ops"];native=r["native"];source=r["source"]
    nodes=defaultdict(float)
    input_N=0.;deferred_N=0.
    source_areas={p["key"]:p for p in source["all_shell_parameters"]}
    for m in native["members"]:
        if m["kind"] not in ("BEAM","COLUMN") or m["key"] not in r["frametags"]:continue
        key=m["key"];tag=r["frametags"][key]
        a,b,_=r["frames"][key]
        xyz0,xyz1=m["start_xyz_mm"],m["end_xyz_mm"]
        length=math.dist(xyz0,xyz1)
        if case=="Dead":
            area=m["section_area_mm2"]
            gamma=native["materials"][m["material"]]["unit_weight_N_mm3"]
            w=area*gamma # N/mm
            dz=(xyz1[2]-xyz0[2])/length
            transverse=math.sqrt(max(0,1-dz*dz))
            ops.eleLoad("-ele",tag,"-type","-beamUniform",0.0,-w*transverse,-w*dz)
            input_N+=w*length
        if case=="WALL LOAD":
            for load in m["applied_loads"]:
                if load["pattern"]!="WALL LOAD":continue
                if load["method"]=="U":
                    w=load["working"]["w_N_per_mm"]
                    dz=(xyz1[2]-xyz0[2])/length
                    ops.eleLoad("-ele",tag,"-type","-beamUniform",0.0,-w*math.sqrt(max(0,1-dz*dz)),-w*dz)
                    input_N+=load["raw_integrated_kN"]*1000
                elif load["method"]=="T":
                    # A conservative source-resultant and 1st-moment preserving
                    # endpoint approximation; not beam consistent fixed-end
                    # moments, not source ETABS shear/moment distribution.
                    a0=load["working"]["start_fraction"]
                    b0=load["working"]["end_fraction"]
                    xi=(a0+b0)/2
                    P=load["raw_integrated_kN"]*1000
                    nodes[a]-=P*(1-xi);nodes[b]-=P*xi
                    input_N+=P
                else:raise ValueError("Unsupported source member load")
    for key,pan in source_areas.items():
        if key not in r["cells"]:continue
        shell=native["shell_sections"][pan["source_section"]]
        gamma=native["materials"][shell["material"]]["unit_weight_N_mm3"]
        for cell in r["cells"][key]:
            applied=0.
            if case=="Dead":
                applied=cell["true_area_mm2"]*pan["source_thickness_mm"]*gamma
            if case in ("Live","FLOOR FINISH"):
                q=sum(v["working"]["q_N_per_mm2"] for v in pan["source_applied_loads"]
                    if v["pattern"]==case)
                applied=q*cell["projection_mm2"]
            if applied:
                for n in cell["nodes"]:nodes[n]-=applied/4
                input_N+=applied
    if case=="WALL LOAD":
        lines=[m for m in native["members"] if m["kind"]=="LINE"]
        for m in lines:
            for load in m["applied_loads"]:
                if load["pattern"]!="WALL LOAD":continue
                a=m["start_xyz_mm"];b=m["end_xyz_mm"]
                total=load["raw_integrated_kN"]*1000
                for j in range(48):
                    t=(j+.5)/48
                    pos=[a[k]+(b[k]-a[k])*t for k in range(3)]
                    candidates=[]
                    for pan in source_areas.values():
                        if pan["story"]!=m["storey"] or pan["kind"]!="FLOOR" or pan["key"] not in r["cells"]:
                            continue
                        q=shape_at_xy(pan["corners_xyz_mm"],pos)
                        if q is None:continue
                        z=sum(q[i]*pan["corners_xyz_mm"][i][2] for i in range(4))
                        if abs(z-pos[2])>1e-3:continue
                        candidates.append(pan)
                    if not candidates:
                        raise ValueError("Original LINE wall has no vertically supported native shell at "+m["key"])
                    for pan in candidates:
                        eligible=[(cell,shape_at_xy(cell["xyz"],pos)) for cell in r["cells"][pan["key"]]]
                        eligible=[(c,s) for c,s in eligible if s is not None]
                        if not eligible:raise ValueError("Nonconforming source cell missing LINE wall point")
                        cell,w=eligible[0]
                        for nid,pct in zip(cell["nodes"],w):
                            nodes[nid]-=total/48/len(candidates)*pct
                input_N+=total
    for key,val in nodes.items():
        if val:ops.load(key,0.,0.,val,0.,0.,0.)
    return {"case":case,"total_applied_downward_N":input_N,
            "nodal_source_load_points":len(nodes),
            "unverified_TRAPF_represented_as_endpoints":case=="WALL LOAD",
            "unsectioned_LINE_source_transfer_interpolated":case=="WALL LOAD",
            "lost_load_N":deferred_N}

def solve(role="ULS",case="Dead",resolution=2):
    if case not in ("Dead","Live","WALL LOAD","FLOOR FINISH"):
        raise ValueError("Not one of the original explicitly assigned gravity patterns")
    r=rig(role,resolution)
    ops=r["ops"]
    ops.timeSeries("Linear",1)
    ops.pattern("Plain",1,1)
    application=add_gravity_loads(r,case)
    ops.constraints("Transformation")
    ops.numberer("RCM")
    ops.system("UmfPack")
    ops.test("NormDispIncr",1.e-7,50)
    ops.algorithm("Linear")
    ops.integrator("LoadControl",1.)
    ops.analysis("Static")
    if ops.analyze(1)!=0:raise RuntimeError("Native connected shell + diaphragm case failed; do not publish member actions")
    ops.reactions()
    reactions=[0.,0.,0.]
    for tag in r["supports"]:
        value=ops.nodeReaction(tag)
        for i in range(3):reactions[i]+=float(value[i])
    error=abs(reactions[2]-application["total_applied_downward_N"])
    if error>max(.05,application["total_applied_downward_N"]*3e-5):
        raise RuntimeError("Applied gravity vs reaction not balanced: "+str(error))
    end={}
    for key,tag in r["frametags"].items():
        vals=ops.eleResponse(tag,"localForce")
        if len(vals)!=12 or any(not math.isfinite(float(z)) for z in vals):
            raise RuntimeError("Signed native action not finite "+key)
        end[key]=[round(float(z)/1000 if i in (0,1,2,6,7,8) else float(z)/1e6,5)
                  for i,z in enumerate(vals)]
    record={
      "role":role,"source_case":case,
      "status":"INDEPENDENT_RESEARCH_CONNECTED_SHELL_FRAME_GRAVITY_NOT_FULL_SOURCE",
      "all_source_shells_registered":115,
      "vertically_supported_shells_numerically_included":103,
      "original_unsupported_shells_numerically_excluded":12,
      "original_frame_elements_included":len(r["frames"]),
      "coarse_numerical_shell_elements":sum(len(c) for c in r["cells"].values()),
      "coarse_refinement":resolution,
      "shell_mesh_faithfully_reproduces_ETABS_8x8":False,
      "source_diaph_points":201,
      "connected_rigid_diaphragm_constraints":r["diaphragms"],
      "source_selfweight_section_proxy_only":case=="Dead",
      "source_transferred_LOAD_LINE_point_weights_proxy":case=="WALL LOAD",
      "applied_gravity":application,
      "sum_native_fixed_base_reactions_N":reactions,
      "vertical_equilibrium_residual_N":error,
      "signed_member_end_actions_bounded":end,
      "full_building_analysis":False,
      "design_load_combination":False,
      "professional_engineer_approved":False,
      "F3_one_way_shear_unsafe":True}
    ops.wipe()
    return record

def write(role="ULS",case="Dead",resolution=2):
    x=solve(role,case,resolution)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+"\n")
    rec={"schema":"jp.structural.r6p10.research_shell_trial.v0.1",
      "role":role,"case":case,"source_uls_sls_registered":True,
      "numerical_result_sha256":hashlib.sha256(OUT.read_bytes()).hexdigest(),
      "source_shell_objects":115,"connected_source_shells_solved":103,
      "original_ETABS21_full_analysis":False,
      "independently_solved_full_gravity_and_seismic_combinations":False,
      "engineering_approval":False,"F3_one_way_shear_unsafe":True}
    MANIFEST.parent.mkdir(parents=True,exist_ok=True)
    MANIFEST.write_text(json.dumps(rec,indent=2,sort_keys=True)+"\n")
    return x

if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("--role",choices=["ULS","SLS"],default="ULS")
    cli.add_argument("--case",choices=["Dead","Live","WALL LOAD","FLOOR FINISH"],default="Dead")
    cli.add_argument("--resolution",type=int,choices=[1,2,4],default=2)
    args=cli.parse_args()
    r=write(args.role,args.case,args.resolution)
    print("R6P10_SOURCE_CONNECTED_SHELL_GRAVITY_BOUNDED",r["role"],r["source_case"],
      r["vertical_equilibrium_residual_N"])
