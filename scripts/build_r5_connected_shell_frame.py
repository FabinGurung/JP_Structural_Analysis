#!/usr/bin/env python3
"""R5.5 physically CONNECTED synthetic horizontal ShellMITC4-to-frame reference.

The shell boundary vertices ARE the beam element vertices (beam subdivided
to the same mesh), and shell corners ARE the top of columns. Uniform area
pressure enters as conservative nodal work-equivalent quad Fz loads. This
calculates elastic shell/beam load paths and support reactions; it is NOT
a verified real building, true arbitrary polygon model, rigid diaphragm
constraint, nonlinear shell reinforcement, or NBC seismic compliance.

All dimensions, E, thickness, dead/live pressure and roof mass are explicitly
synthetic. No implicit selfweight; source mass is reused from original R5.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from jp_structural.solvers.native.geometry_load_intake import assemble_geometry_source_loads
from scripts.build_r5_generic_frame_case import DEFAULT
from scripts.build_structural_template_engine import CONTRACT,COVERAGE

SHELL_T_M=0.125
MESHES=(2,4,8)
PFX="r5-connected-shell"
SCHEMA="jp.structural.r5.connected_shell_frame_FE.v0.1"
AXES=("Fx_kN","Fy_kN","Fz_kN","Mx_kNm","My_kNm","Mz_kNm")
LOCAL=("N","Vy","Vz","T","My","Mz")

class ShellBridgeError(ValueError):
    pass

def sha(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def exact_reference(spec, thickness=SHELL_T_M):
    if not isinstance(spec,dict) or spec.get("schema")!="jp.structural.r5.input.v0.1" or spec.get("classification")!="SYNTHETIC_REFERENCE_NOT_A_BUILDING":
        raise ShellBridgeError("source fixture must be a governed synthetic reference")
    model=spec["model"]
    if spec.get("case_id")!=model.get("model_id"):raise ShellBridgeError("canonical case/model mismatch")
    if not (isinstance(thickness,(int,float)) and not isinstance(thickness,bool) and math.isfinite(thickness) and 0<thickness<0.5):
        raise ShellBridgeError("explicit finite positive bounded shell thickness required")
    audit=assemble_geometry_source_loads(model=model,loads=spec["source_loads"],gravity_m_s2=spec["gravity_m_s2"])
    nodes={n["id"]:n for n in model["nodes"]}
    member={m["id"]:m for m in model["frame_members"]}
    if len(nodes)!=8 or len(member)!=8 or set(member)!={*(f"BM{i}" for i in range(1,5)),*(f"COL{i}" for i in range(1,5))}:
        raise ShellBridgeError("R5.5 first increment supports exact four-column synthetic rectangular frame only")
    plan=[nodes[f"R{i}"] for i in range(1,5)]
    xx=[float(n["x"]) for n in plan];yy=[float(n["y"]) for n in plan];zz=[float(n["z"]) for n in plan]
    x0,x1=min(xx),max(xx);y0,y1=min(yy),max(yy)
    if len({(n["x"],n["y"]) for n in plan})!=4 or [
            (xx[i],yy[i]) for i in range(4)]!=[(x0,y0),(x1,y0),(x1,y1),(x0,y1)]:
        raise ShellBridgeError("roof source corners must form ordered axis-aligned rectangle")
    if x1-x0<=1e-5 or y1-y0<=1e-5 or max(zz)-min(zz)>1e-8:
        raise ShellBridgeError("nonzero span and horizontal roof required")
    for i in range(1,5):
        b=nodes[f"B{i}"];r=nodes[f"R{i}"]
        if b["x"]!=r["x"] or b["y"]!=r["y"] or float(b["z"])>=float(r["z"]):
            raise ShellBridgeError("corners must connect vertical column to base")
        m=member[f"COL{i}"]
        if (m["i_node"],m["j_node"])!=(f"B{i}",f"R{i}"):
            raise ShellBridgeError("column topology drifts from source")
    for i in range(1,5):
        m=member[f"BM{i}"]
        if (m["i_node"],m["j_node"])!=(f"R{i}",f"R{(i%4)+1}"):
            raise ShellBridgeError("beam ring topology incompatible with shell mesh")
    if model.get("diaphragms") or model.get("shell_elements") or model.get("nodal_masses") or model.get("mass_source"):
        raise ShellBridgeError("pre-existing shell/mass/diaphragm forbidden: double count")
    for source in audit["source_case_components"]:
        if source["kind"]=="UNIFORM_PANEL_PRESSURE" and source["geometry"]["boundary_node_ids"] not in (
             ["R1","R2","R3","R4"],["R4","R3","R2","R1"]):
            raise ShellBridgeError("different panel geometry requires separate mesh mapper")
        if source["kind"]=="UNIFORM_FRAME_LINE_LOAD" and source["geometry"]["member_id"] not in member:
            raise ShellBridgeError("source wall member missing")
    sections={s["id"]:s for s in model["sections"]}
    materials={m["id"]:m for m in model["materials"]}
    col=sections["COL-S"];beam=sections["BEAM-S"]
    if col["material_id"]!=beam["material_id"]:raise ShellBridgeError("single isotropic synthetic material required")
    mat=materials[col["material_id"]]
    E=float(mat["E"]);nu=float(mat["poisson"])
    if not(1e5<E<1e9 and 0<nu<.49):raise ShellBridgeError("invalid elastic modulus or Poisson ratio")
    def props(sec):
        b=float(sec["width"]);h=float(sec["depth"])
        if not (0<b<2 and 0<h<2):raise ShellBridgeError("section dimensions out of bounded synthetic range")
        A=b*h
        Iy=b*h**3/12;Iz=h*b**3/12
        # Explicit bounded Saint-Venant torsion approximation for solid rectangle:
        s,l=sorted((b,h))
        J=l*s**3*(1/3-0.21*s/l*(1-s**4/(12*l**4)))
        return A,Iy,Iz,J
    panel_area=(x1-x0)*(y1-y0)
    pressures={}
    for row in spec["source_loads"]:
        if row["type"]=="UNIFORM_PANEL_PRESSURE":
            cid=row["case_id"]
            pressures[cid]=pressures.get(cid,0.)+float(row["pressure_kPa"])
    walls=[]
    for row in spec["source_loads"]:
        if row["type"]=="UNIFORM_FRAME_LINE_LOAD":
            walls.append({"case_id":row["case_id"],"member_id":row["member_id"],"w":float(row["intensity_kN_m"]),
                          "source_key":row["source_key"]})
    # Preserve and validate the exact external horizontal load ledger; never
    # replace a changed synthetic input with invented hard-coded 10kN/corner.
    lateral_cases=spec.get("lateral_cases")
    if not isinstance(lateral_cases,list) or len(lateral_cases)!=1 or lateral_cases[0].get("case_id")!="HX":
        raise ShellBridgeError("one explicit source HX load case required")
    lateral_by_node={}
    for row in lateral_cases[0].get("nodal_loads",[]):
        nid=row.get("node_id")
        if nid not in {"R1","R2","R3","R4"} or nid in lateral_by_node:
            raise ShellBridgeError("lateral source must list unique physical roof corner nodes")
        keys={"node_id","Fx_kN","Fy_kN","Fz_kN","Mx_kNm","My_kNm","Mz_kNm"}
        if set(row)!=keys:
            raise ShellBridgeError("full signed lateral source components required")
        vals=[row[k] for k in ("Fx_kN","Fy_kN","Fz_kN","Mx_kNm","My_kNm","Mz_kNm")]
        if any(isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) for v in vals):
            raise ShellBridgeError("invalid signed horizontal force component")
        if any(vals[j]!=0 for j in (2,3,4,5)):
            raise ShellBridgeError("horizontal HX case must not contain vertical/couple gravity duplicates")
        lateral_by_node[nid]=vals
    if set(lateral_by_node)!={"R1","R2","R3","R4"}:
        raise ShellBridgeError("missing physical lateral roof corner source")
    source_by_case={}
    for rec in audit["source_case_components"]:
        cid=rec["load_case_id"]
        source_by_case[cid]=source_by_case.get(cid,0.)+rec["gravity_weight_kN"]
    if set(source_by_case)!={"DL","LL"}:
        raise ShellBridgeError("only explicit independently identified DL and LL loads supported")
    return {"model":model,"audit":audit,"corners":(x0,x1,y0,y1,zz[0]),
       "area_m2":panel_area,"pressure_by_case":pressures,"walls":walls,
       "E_kN_m2":E,"nu":nu,"shell_thickness_m":thickness,
       "column_section":props(col),"beam_section":props(beam),
       "lateral_source_by_node":lateral_by_node,
       "source_total_by_case_kN":source_by_case,
       "explicit_original_mass_SHA256":sha(audit["audited_assembly"])}

def solve_mesh(ref, n:int, case_id:str, *, diaphragm_mode="FLEXIBLE_SHELL", factors=None):
    """Retain one shell/frame topology across original raw and signed cases."""
    import openseespy.opensees as ops
    if n not in MESHES:raise ShellBridgeError("unsupported mesh size; validated 2,4,8")
    if diaphragm_mode not in ("FLEXIBLE_SHELL","RIGID_INPLANE_MPC"):
        raise ShellBridgeError("unknown diaphragm mode")
    if factors is None:
        if case_id not in ("DL","LL","HX"):raise ShellBridgeError("unknown raw source case")
        factors={case_id:1.}
    elif (case_id in ("DL","LL","HX") or not isinstance(factors,dict) or not factors
        or not set(factors)<={"DL","LL","HX"} or any(
            not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v)
            for v in factors.values())):
        raise ShellBridgeError("invalid signed combination source or factor")
    m=ref["model"]; x0,x1,y0,y1,z=ref["corners"]
    ops.wipe();ops.model("basic","-ndm",3,"-ndf",6)
    def tag(i,j):return 1000+i+(n+1)*j
    positions={}
    for j in range(n+1):
        for i in range(n+1):
            x=x0+(x1-x0)*i/n;y=y0+(y1-y0)*j/n
            positions[(i,j)]=(x,y,z)
            ops.node(tag(i,j),x,y,z)
    corner_ix=[(0,0),(n,0),(n,n),(0,n)]
    master_tag=None
    if diaphragm_mode=="RIGID_INPLANE_MPC":
        master_tag=9900
        xc=(x0+x1)/2;yc=(y0+y1)/2
        ops.node(master_tag,xc,yc,z)
        ops.fix(master_tag,0,0,1,1,1,0)
        ops.rigidDiaphragm(3,master_tag,*[tag(i,j)
            for j in range(n+1) for i in range(n+1)])
    base=[]
    for idx,(i,j) in enumerate(corner_ix,1):
        b=m["nodes"][idx-1]
        if b["id"]!=f"B{idx}":raise ShellBridgeError("base physical model order drift")
        ops.node(idx,b["x"],b["y"],b["z"])
        ops.fix(idx,1,1,1,1,1,1);base.append(idx)
    # A single shared node is used by ShellMITC4, perimeter beams and columns;
    # this is actual compatible 6DOF shell/beam kinematic connectivity.
    ops.geomTransf("Linear",1,1,0,0)   # vertical columns vecxz
    ops.geomTransf("Linear",2,0,0,1)   # horizontal frame beams vecxz
    E=ref["E_kN_m2"];nu=ref["nu"];G=E/(2*(1+nu))
    columns=[];beams=[];segment_register={k:[] for k in ("BM1","BM2","BM3","BM4")}
    A,Iy,Iz,J=ref["column_section"]
    for idx,corner in enumerate(corner_ix,1):
        e=idx
        ops.element("elasticBeamColumn",e,idx,tag(*corner),A,E,G,J,Iy,Iz,1)
        columns.append(e)
    A,Iy,Iz,J=ref["beam_section"]
    paths={
       "BM1":[(i,0) for i in range(n+1)],
       "BM2":[(n,j) for j in range(n+1)],
       "BM3":[(i,n) for i in range(n,-1,-1)],
       "BM4":[(0,j) for j in range(n,-1,-1)]}
    for k,path in paths.items():
        for index,(a,b) in enumerate(zip(path,path[1:])):
            e=10+len(beams)
            ops.element("elasticBeamColumn",e,tag(*a),tag(*b),A,E,G,J,Iy,Iz,2)
            beams.append(e);segment_register[k].append(e)
    ops.nDMaterial("ElasticIsotropic",100,E,nu)
    ops.section("PlateFiber",101,100,ref["shell_thickness_m"])
    shells=[];element_area=ref["area_m2"]/(n*n)
    for j in range(n):
        for i in range(n):
            e=300+j*n+i
            ops.element("ShellMITC4",e,tag(i,j),tag(i+1,j),
                        tag(i+1,j+1),tag(i,j+1),101)
            shells.append(e)
    assert len(shells)==n*n and len(beams)==4*n and len(columns)==4
    # Audited source seismic masses are for old physical R1...R4 and attach
    # only to corresponding connected shell/beam/column corner nodes.
    mass_nodes=ref["audit"]["audited_assembly"]["nodal_masses"]
    for row in mass_nodes:
        node=row["node_id"]
        if node not in ("R1","R2","R3","R4"):
            raise ShellBridgeError("R5 source mass node cannot be mapped to connected corner")
        ci=corner_ix[int(node[1])-1]
        ops.mass(tag(*ci),*[row[k] for k in ("mx","my","mz","mrx","mry","mrz")])
    ops.timeSeries("Linear",1);ops.pattern("Plain",1,1)
    external=[] # global {x,y,z, fx,fy,fz,mx,my,mz}; wall centroid exact
    def push(x,y,z,fx=0.,fy=0.,fz=0.,mx=0.,my=0.,mz=0.):
        external.append((x,y,z,fx,fy,fz,mx,my,mz))
    # Raw cases and signed combinations are loaded together into this
    # exact connected model. No independent action envelope substitution.
    for src in ("DL","LL"):
        factor=factors.get(src,0.)
        if factor==0:continue
        patch=-factor*ref["pressure_by_case"][src]*element_area/4
        for j in range(n):
            for i in range(n):
                for node in ((i,j),(i+1,j),(i+1,j+1),(i,j+1)):
                    ops.load(tag(*node),0.,0.,patch,0.,0.,0.)
                    x,y,zz=positions[node];push(x,y,zz,fz=patch)
        for wall in ref["walls"]:
            if wall["case_id"]!=src:continue
            k=wall["member_id"];w=factor*wall["w"]
            for e,(a,b) in zip(segment_register[k],zip(paths[k],paths[k][1:])):
                ops.eleLoad("-ele",e,"-type","-beamUniform",0.,-w,0.)
                p1=positions[a];p2=positions[b]
                L=math.dist(p1,p2)
                push(*[(p1[d]+p2[d])/2 for d in range(3)],fz=-w*L)
    if factors.get("HX",0.)!=0:
        for index,corner in enumerate(corner_ix,1):
            vals=ref["lateral_source_by_node"][f"R{index}"]
            fx,fy,fz,mx,my,mz=[v*factors["HX"] for v in vals]
            ops.load(tag(*corner),fx,fy,fz,mx,my,mz)
            x,y,zz=positions[corner]
            push(x,y,zz,fx,fy,fz,mx,my,mz)
    ops.constraints("Transformation" if master_tag is not None else "Plain")
    ops.numberer("RCM");ops.system("BandGeneral")
    ops.algorithm("Linear");ops.integrator("LoadControl",1.)
    ops.analysis("Static")
    if ops.analyze(1)!=0:raise ShellBridgeError(f"OpenSees elastic shell/frame failed {case_id}, mesh {n}")
    ops.reactions()
    reactions=[]
    for idx in base:
        reactions.append([float(ops.nodeReaction(idx,k)) for k in range(1,7)])
    total=[0.]*6
    def accumulate(x,y,z,fx,fy,fz,mx,my,mz):
        for k,v in enumerate((fx,fy,fz,mx+y*fz-z*fy,my+z*fx-x*fz,mz+x*fy-y*fx)):
            total[k]+=v
    for v in external:accumulate(*v)
    for idx,r in zip(base,reactions):
        b=m["nodes"][idx-1]
        accumulate(float(b["x"]),float(b["y"]),float(b["z"]),*r)
    max_res=max(abs(v) for v in total)
    if max_res>1e-4:raise ShellBridgeError(f"global six-component shell/frame balance failed {case_id}, n={n}: {total}")
    center=(n//2,n//2)
    center_w=float(ops.nodeDisp(tag(*center),3))
    if not math.isfinite(center_w):raise ShellBridgeError("invalid shell center displacement")
    corner_displacements={}
    for index,corner in enumerate(corner_ix,1):
        corner_displacements[f"R{index}"]={
           key:float(ops.nodeDisp(tag(*corner),dof))
           for key,dof in (("UX",1),("UY",2),("UZ",3),("RZ",6))}
    inplane_x=max(abs(float(ops.nodeDisp(tag(n,j),1))-
                      float(ops.nodeDisp(tag(0,j),1))) for j in range(n+1))
    inplane_y=max(abs(float(ops.nodeDisp(tag(i,n),2))-
                      float(ops.nodeDisp(tag(i,0),2))) for i in range(n+1))
    rigid_residual=None
    if master_tag is not None:
        umx=float(ops.nodeDisp(master_tag,1))
        umy=float(ops.nodeDisp(master_tag,2))
        mrz=float(ops.nodeDisp(master_tag,6))
        xc=(x0+x1)/2;yc=(y0+y1)/2
        rigid_residual=max(
            abs(float(ops.nodeDisp(tag(i,j),1))-
                (umx-(positions[(i,j)][1]-yc)*mrz))
            for j in range(n+1) for i in range(n+1))
        rigid_residual=max(rigid_residual,max(
            abs(float(ops.nodeDisp(tag(i,j),2))-
                (umy+(positions[(i,j)][0]-xc)*mrz))
            for j in range(n+1) for i in range(n+1)))
        if rigid_residual>1e-8 or inplane_x>1e-8 or inplane_y>1e-8:
            raise ShellBridgeError("MPC displacement compatibility failed")
    end_records={}
    for key,segments in segment_register.items():
        end_records[key]=[]
        for e in segments:
            f=ops.eleResponse(e,"localForce")
            if f is None or len(f)!=12 or not all(math.isfinite(float(v)) for v in f):
                raise ShellBridgeError("invalid native frame signed member action")
            end_records[key].append({"element_tag":e,"I":dict(zip(("N","Vy","Vz","T","My","Mz"),[float(x) for x in f[:6]])),
                                     "J":dict(zip(("N","Vy","Vz","T","My","Mz"),[float(x) for x in f[6:]]))})
    for idx,e in enumerate(columns,1):
        f=ops.eleResponse(e,"localForce")
        if f is None or len(f)!=12:raise ShellBridgeError("missing column force vector")
        end_records[f"COL{idx}"]=[{"element_tag":e,"I":dict(zip(LOCAL,[float(x) for x in f[:6]])),
                                  "J":dict(zip(LOCAL,[float(x) for x in f[6:]]))}]
    return {
       "case_id":case_id,"mesh_divisions":n,
       "diaphragm_mode":diaphragm_mode,
       "source_factors":{k:factors[k] for k in sorted(factors)},
       "master_tag":master_tag,
       "master_retained_dofs":"UX_UY_RZ" if master_tag is not None else None,
       "rigid_compatibility_residual_m":rigid_residual,
       "inplane_row_UX_difference_m":inplane_x,
       "inplane_col_UY_difference_m":inplane_y,
       "corner_displacements_m":corner_displacements,
       "shell_nodes":(n+1)**2,"shell_elements":n*n,
       "connected_boundary_beam_segments":len(beams),"columns":len(columns),
       "member_end_vector_count":2*(len(columns)+len(beams)),
       "applied_force_kN":[sum(v[3+k] for v in external) for k in range(3)],
       "applied_plan_force_resultant_Fz_kN":sum(v[5] for v in external),
       "support_reactions_Fz_kN":[r[2] for r in reactions],
       "support_reaction_total_Fz_kN":sum(r[2] for r in reactions),
       "global_force_moment_residual":dict(zip(AXES,total)),
       "global_equilibrium_pass":True,
       "center_shell_Uz_m":center_w,
       "signed_member_end_actions":end_records,
       "shell_to_beam_same_node_count":4*n,
       "shell_panel_load_directly_applied_at_interior_nodes":n>1 and any(factors.get(c,0.)!=0. for c in ("DL","LL")),
       "source_seismic_weight_kN":ref["audit"]["audited_assembly"]["total_seismic_weight_kN"],
       "engineering_approval":False,
    }

def build(spec=None):
    if spec is None:spec=json.loads(DEFAULT.read_text(encoding="utf8"))
    ref=exact_reference(spec)
    cases=[]
    for n in MESHES:
        for cid in ("DL","LL","HX"):
            cases.append(solve_mesh(ref,n,cid))
    if len(cases)!=9:raise ShellBridgeError("expected three mesh resolutions and three raw static cases")
    for r in cases:
        if not r["global_equilibrium_pass"]:raise ShellBridgeError("source model force equilibrium absent")
        if r["source_seismic_weight_kN"]!=ref["audit"]["audited_assembly"]["total_seismic_weight_kN"]:
            raise ShellBridgeError("seismic mass changed across mesh")
        if r["case_id"] in ("DL","LL"):
            expected=-ref["source_total_by_case_kN"][r["case_id"]]
            if not math.isclose(r["applied_force_kN"][2],expected,abs_tol=1e-7):
                raise ShellBridgeError("source gravity case not completely transferred")
        if r["case_id"]=="HX":
            expected_x=math.fsum(v[0] for v in ref["lateral_source_by_node"].values())
            expected_y=math.fsum(v[1] for v in ref["lateral_source_by_node"].values())
            if not (math.isclose(r["applied_force_kN"][0],expected_x,abs_tol=1e-7)
                  and math.isclose(r["applied_force_kN"][1],expected_y,abs_tol=1e-7)):
                raise ShellBridgeError("source explicit lateral forces mismatch")
    by_n={n:next(x for x in cases if x["mesh_divisions"]==n and x["case_id"]=="DL") for n in MESHES}
    center=[by_n[n]["center_shell_Uz_m"] for n in MESHES]
    if not all(v<0 for v in center):raise ShellBridgeError("gravity must move shell center down in all meshes")
    ref_disp=abs(center[-1])
    if ref_disp<=1e-14:raise ShellBridgeError("no shell flexibility response")
    differences=[abs(center[i+1]-center[i]) for i in (0,1)]
    if differences[1]>=differences[0]:
        raise ShellBridgeError("2/4/8 shell displacement does not show mesh refinement convergence")
    if differences[1]/ref_disp>0.20:
        raise ShellBridgeError("4-to-8 shell center displacement discrepancy >20%")
    contract=json.loads(CONTRACT.read_text(encoding="utf8"))
    coverage={r["id"]:r for r in json.loads(COVERAGE.read_text(encoding="utf8"))["requirements"]}
    scopes={"M02":"EXPLICIT_SHELL_AREA_PRESSURE_AND_AUDITED_GRAVITY_SEISMIC_MASS",
            "M04":"ACTUAL_CONNECTED_SHELLMITC4_FRAME_3D_STATIC_QUAD_MESH",
            "M08":"ELASTIC_MEMBER_IJ_SIGNED_ACTIONS_NOT_FULL_REINFORCEMENT_DESIGN",
            "M11":"SHELL_ELASTIC_DISPLACEMENT_MESH_REFINEMENT_NO_SLAB_STEEL",
            "S17":"INDEPENDENT_6DOF_FRAME_REACTIONS_AND_2_4_8_MESH_CONVERGENCE"}
    chapters=[{"id":ch["id"],"title":ch["title"],
              "modules":[{"id":mid,"title":coverage[mid]["title"],"status":scopes.get(mid,"NOT_EVALUATED_IN_CONNECTED_SHELL_RUN")}
                         for mid in ch["requirement_ids"]]} for ch in contract["chapters"]]
    if len(chapters)!=7 or {m["id"] for c in chapters for m in c["modules"]}!=set(coverage):
        raise ShellBridgeError("7 chapter/18-module report contract missing")
    return {
       "schema":SCHEMA,"case_id":spec["case_id"],
       "source_input_SHA256":sha(spec),
       "source_audited_mass_SHA256":ref["explicit_original_mass_SHA256"],
       "source_total_gravity_kN":ref["audit"]["audited_assembly"]["total_gravity_load_kN"],
       "source_seismic_weight_kN":ref["audit"]["audited_assembly"]["total_seismic_weight_kN"],
       "shell_material_E_kN_m2":ref["E_kN_m2"],"shell_poisson":ref["nu"],
       "shell_thickness_m":ref["shell_thickness_m"],"panel_area_m2":ref["area_m2"],
       "mesh_sizes":list(MESHES),"mesh_case_results":cases,
       "source_DL_expected_kN":104.,"source_LL_expected_kN":24.,
       "gravity_mesh_center_Uz_m":{str(n):by_n[n]["center_shell_Uz_m"] for n in MESHES},
       "convergence_abs_displacement_differences_m":differences,
       "convergence_improvement":differences[1]<differences[0],
       "shell_elements_actual_connected_frame":True,
       "shared_edge_beam_shell_nodes":True,
       "source_mass_conserved_across_mesh":True,
       "global_six_component_equilibrium_pass":True,
       "distinct_raw_static_cases_count":3,
       "signed_combo_executed_on_connected_shell":False,
       "physical_diaphragm_constraint_tested":False,
       "full_floor_shell_or_original_building":False,
       "shell_stiffness_material_assumed":True,
       "original_F3_failure":"NOT SAFE IN ONE WAY SHEAR",
       "engineering_approval":False,"permit_eligible":False,
       "chapters":chapters,
       "open_debt":[
        "Single synthetic rectangular bay and 3 raw linear static cases only; no arbitrary 3D building or complete original floor.",
        "Source-assumed E, shell thickness, no automatic selfweight, no slab reinforcement/capacity or plate crack model.",
        "No rigid diaphragm MPC versus flexible connected shell benchmark or modal eigen mass participation yet.",
        "Shell uniform pressure represented through consistent nodal external forces, with mesh-refined actual shell stiffness and beam connectivity.",
        "Full signed load combinations from this connected shell source and certified code combination basis remain future work.",
        "Original G+1.5 source 15 physical gates remain OPEN and original F3 remains NOT SAFE IN ONE WAY SHEAR.",
       ],
    }

def main():
    a=argparse.ArgumentParser();a.add_argument("--output-dir",type=Path,required=True);p=a.parse_args()
    p.output_dir.mkdir(parents=True,exist_ok=True)
    out=build()
    filename=p.output_dir/(PFX+".json")
    filename.write_text(json.dumps(out,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf8")
    (p.output_dir/(PFX+"-manifest.json")).write_text(json.dumps({
       "schema":"jp.structural.r5.connected_shell_manifest.v0.1",
       "input_SHA256":out["source_input_SHA256"],
       "files":{filename.name:hashlib.sha256(filename.read_bytes()).hexdigest()},
       "engineering_approval":False},sort_keys=True,indent=2)+"\n",encoding="utf8")
    print("R5P5_CONNECTED_SHELL",len(out["mesh_case_results"]),"FE_CASES","2_4_8_MESHES",
          "128_KN_GRAVITY_SOURCE","F3_UNSAFE_NOT_APPROVED")
if __name__=="__main__":main()
