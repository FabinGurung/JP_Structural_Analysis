#!/usr/bin/env python3
"""Gate12: actual 165-element OpenSees 3D frame under flexible vs rigid-floor MPC.

Both alternatives use identical SOURCE-GRID NODES, section stiffness, signed
equivalent static floor forces, and exactly the same equivalent nodal forcing.
Rigid trial constrains (Ux,Uy,Rz) per floor using OpenSees rigidDiaphragm(3)
at the AREA-FITTED assumed slab polygon centroid. Flexible frame has no MPC.
No shell slab, physical wall, floor mass extraction, P-Delta, seismic code
drift acceptance, actual model verification, or engineering acceptance.
"""
from __future__ import annotations
import argparse
import json
import math
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.run_g15_open_3d import source, section, validate, SAMPLE
from scripts.build_g15_gate10_assumptions import build as gate10
from scripts.build_g15_gate11_torsion_proxy import centroid
from jp_structural.solvers.native.nbc105_2025_esm import equivalent_static_floor_forces

COMPONENTS=["Ni","Vyi","Vzi","Ti","Myi","Mzi","Nj","Vyj","Vzj","Tj","Myj","Mzj"]
ACC=.05
CASE_ID="G10_EDGE_COMM"

def floor_nodal_lateral(axis,signed_force,pts,load_xy,ecc):
    """Exact resultant force and Mz at (load_xy+signed eccentricity).

    Same distribution is imposed in unconstrained and rigid-constrained model;
    no automatic 1/23 load centroid drift is concealed.
    """
    n=len(pts)
    mx=sum(q[0] for q in pts)/n
    my=sum(q[1] for q in pts)/n
    if axis=="X":
        denom=sum((y-my)**2 for x,y in pts)
        assert denom>0
        factor=signed_force*(load_xy[1]+ecc-my)/denom
        result=[(signed_force/n+factor*(y-my),0.) for x,y in pts]
        force=sum(x for x,_ in result)
        moment=-sum(y*x for (x,y),(fx,_) in zip(pts,result) for x in [fx])
        target=-signed_force*(load_xy[1]+ecc)
        assert math.isclose(force,signed_force,abs_tol=1e-8)
    elif axis=="Y":
        denom=sum((x-mx)**2 for x,y in pts)
        assert denom>0
        factor=signed_force*(load_xy[0]+ecc-mx)/denom
        result=[(0.,signed_force/n+factor*(x-mx)) for x,y in pts]
        force=sum(y for _,y in result)
        moment=sum(x*fy for (x,y),(_,fy) in zip(pts,result))
        target=signed_force*(load_xy[0]+ecc)
        assert math.isclose(force,signed_force,abs_tol=1e-8)
    else: raise ValueError("Unknown axis")
    assert math.isclose(moment,target,abs_tol=1e-7)
    return result

def solve(request=None,case_id=CASE_ID,summary_only=False):
    import openseespy.opensees as ops
    if request is None:request=dict(SAMPLE)
    p=validate(request)
    model=source()
    assumptions=gate10()
    mass_case=next((c for c in assumptions["model_cases"] if c["id"]==case_id),None)
    if mass_case is None:raise ValueError("Unsupported assumption case")
    # Floor loads are user-editable in the source OpenSees contract; the
    # named Gate10 case is provenance ONLY unless explicitly passed in.
    assert len(p["floor_weights_kN"])==3
    cols=model["column_positions_mm"]
    assert len(cols)==23
    coords={c[0]:(c[1]/1000,c[2]/1000,c[3]) for c in cols}
    plan=[coords[c[0]][:2] for c in cols]
    names=[c[0] for c in cols]
    nodes={(c[0],lev):100*idx+lev+1 for idx,c in enumerate(cols) for lev in range(4)}
    levels=[z/1000 for z in model["floor_levels_mm"]]
    floor_areas=assumptions["footprints"]["assumed_per_floor"]
    floor_cms=[centroid(q["scaled_convex_hull_outline_xy_m"]) for q in floor_areas]
    xs=[v[0] for v in plan];ys=[v[1] for v in plan]
    lx=max(xs)-min(xs);ly=max(ys)-min(ys)
    esm=equivalent_static_floor_forces(floor_weights_kN=p["floor_weights_kN"],
      floor_heights_m=levels[1:],period_seconds=p["T_seconds"],
      design_coefficient=p["C_design"])
    widths={"ULS":(.35,.70),"SLS":(.70,.90),"GROSS":(1.,1.)}[p["stiffness"]]
    e=p["concrete_E_MPa"]*1000.
    g=e/2.4
    edges=model["beam_edges"][:32 if p["bridges"] else 30]
    count=69+3*len(edges)
    assert count in (159,165)
    specs=[("GRAVITY",None,0,0)]
    for axis in ("X","Y"):
        for sign in (1,-1):
            for eccentricity_sign in (1,-1):
                specs.append((f"EQ_{axis}_{'POS' if sign==1 else 'NEG'}_E{('POS' if eccentricity_sign==1 else 'NEG')}",
                   axis,sign,eccentricity_sign))
    assert len(specs)==9
    cases=[]
    signed_for_superposition={}
    for boundary in ("FLEXIBLE","RIGID_MPC_TRIAL"):
        for name,axis,sign,esgn in specs:
            ops.wipe()
            ops.model("basic","-ndm",3,"-ndf",6)
            for c in cols:
                x,y,_=coords[c[0]]
                for level,z in enumerate(levels):
                    n=nodes[(c[0],level)]
                    ops.node(n,x,y,z)
                    if level==0:ops.fix(n,1,1,1,1,1,1)
            if boundary=="RIGID_MPC_TRIAL":
                for level,cm in enumerate(floor_cms,1):
                    master=5000+level
                    ops.node(master,cm[0],cm[1],levels[level])
                    # Only Ux,Uy and Rz may act as master DOFs.
                    ops.fix(master,0,0,1,1,1,0)
                    slaves=[nodes[(c[0],level)] for c in cols]
                    ops.rigidDiaphragm(3,master,*slaves)
            ops.geomTransf("Linear",1,1,0,0)
            ops.geomTransf("Linear",2,0,0,1)
            elements=[];tag=0
            for c in cols:
                label,_,_,sec=c
                a,iy,iz,j=section(sec,model["section_definitions_mm"],p["beam_width_mm"])
                for level in range(1,4):
                    tag+=1
                    ops.element("elasticBeamColumn",tag,nodes[(label,level-1)],nodes[(label,level)],
                                a,e,g,j,iy*widths[1],iz*widths[1],1)
                    elements.append((tag,f"COL-{label}-L{level-1}-{level}"))
            a,iy,iz,j=section("BEAM",model["section_definitions_mm"],p["beam_width_mm"])
            for begin,end in edges:
                for level in range(1,4):
                    tag+=1
                    ops.element("elasticBeamColumn",tag,nodes[(begin,level)],nodes[(end,level)],
                                a,e,g,j,iy*widths[0],iz*widths[0],2)
                    elements.append((tag,f"BEAM-{begin}-{end}-L{level}"))
            assert len(elements)==count
            ops.timeSeries("Linear",1)
            ops.pattern("Plain",1,1)
            application=[]
            for floor in range(1,4):
                height=levels[floor]
                Fi=esm["floor_forces_kN"][floor-1]*sign
                cm=floor_cms[floor-1]
                ecc=(esgn*ACC*(ly if axis=="X" else lx)) if axis else 0.
                nodals=floor_nodal_lateral(axis,Fi,plan,cm,ecc) if axis else [(0.,0.)]*len(cols)
                for i,c in enumerate(cols):
                    fx,fy=nodals[i]
                    fz=-p["floor_weights_kN"][floor-1]/len(cols) if name=="GRAVITY" else 0.
                    ops.load(nodes[(c[0],floor)],fx,fy,fz,0.,0.,0.)
                    application.append((coords[c[0]][0],coords[c[0]][1],height,fx,fy,fz))
            ops.constraints("Transformation" if boundary=="RIGID_MPC_TRIAL" else "Plain")
            ops.numberer("RCM");ops.system("UmfPack")
            ops.test("NormUnbalance",1e-7,10)
            ops.algorithm("Linear")
            ops.integrator("LoadControl",1.)
            ops.analysis("Static")
            if ops.analyze(1)!=0:
                ops.wipe()
                raise RuntimeError("OpenSees failed "+boundary+" "+name)
            disp={}
            for floor in range(1,4):
                for label in names:
                    n=nodes[(label,floor)]
                    disp[(label,floor)]=(float(ops.nodeDisp(n,1)),float(ops.nodeDisp(n,2)))
            node_by_grid=[]
            for floor in range(1,4):
                for label in names:
                    dx,dy=disp[(label,floor)]
                    node_by_grid.append({"grid":label,"floor":floor,"ux_mm":1000*dx,"uy_mm":1000*dy})
            floor_drifts=[]
            for floor in range(1,4):
                step=[]
                for label in names:
                    now=disp[(label,floor)]
                    prev=disp.get((label,floor-1),(0.,0.))
                    step.append(math.hypot(now[0]-prev[0],now[1]-prev[1]))
                floor_drifts.append({
                    "floor":floor,
                    "max_elastic_node_to_node_story_chord_mm":1000*max(step),
                    "max_elastic_story_chord_ratio":max(step)/(levels[floor]-levels[floor-1])
                })
            max_roof=max(math.hypot(*disp[(label,3)])*1000 for label in names)
            signed=[]
            for t,label in elements:
                force=list(map(float,ops.eleResponse(t,"localForce")))
                if len(force)!=12 or not all(math.isfinite(v) for v in force):
                    ops.wipe();raise RuntimeError("Invalid signed element local forces")
                signed.append({"id":label,"components":COMPONENTS,"signed":force})
            governing=max(signed,key=lambda v:max(abs(v["signed"][j]) for j in (4,5,10,11)))
            governing_component=max((4,5,10,11),key=lambda j:abs(governing["signed"][j]))
            ops.reactions()
            base_force=[sum(ops.nodeReaction(nodes[(c[0],0)],j) for c in cols) for j in (1,2,3)]
            applied_force=[sum(x[i] for x in application) for i in (3,4,5)]
            force_res=max(abs(x+y) for x,y in zip(applied_force,base_force))
            support_m=[0.,0.,0.]
            for c in cols:
                x,y,_=coords[c[0]]
                n=nodes[(c[0],0)]
                rx,ry,rz=[ops.nodeReaction(n,j) for j in (1,2,3)]
                mx,my,mz=[ops.nodeReaction(n,j) for j in (4,5,6)]
                support_m[0]+=y*rz+mx
                support_m[1]+=-x*rz+my
                support_m[2]+=x*ry-y*rx+mz
            applied_m=[0.,0.,0.]
            for x,y,z,fx,fy,fz in application:
                applied_m[0]+=y*fz-z*fy
                applied_m[1]+=z*fx-x*fz
                applied_m[2]+=x*fy-y*fx
            moment_res=max(abs(x+y) for x,y in zip(applied_m,support_m))
            if force_res>=.001 or moment_res>=.001:
                ops.wipe()
                raise RuntimeError(f"Failed full vector equilibrium {boundary}:{name} {force_res} kN / {moment_res} kNm")
            if boundary=="RIGID_MPC_TRIAL":
                # Rigid in-plane body motion must be recovered at every floor.
                for floor in range(1,4):
                    cm=floor_cms[floor-1]
                    master=5000+floor
                    ux=ops.nodeDisp(master,1);uy=ops.nodeDisp(master,2);rz=ops.nodeDisp(master,6)
                    for label in names:
                        xx,yy,_=coords[label]
                        dx,dy=disp[(label,floor)]
                        if abs(dx-(ux-rz*(yy-cm[1])))>2e-5 or abs(dy-(uy+rz*(xx-cm[0])))>2e-5:
                            ops.wipe();raise RuntimeError("Rigid master-slave kinematic integrity failure")
            record={
                "case":name,"boundary":boundary,"members":count,
                "signed_applied_force_kN_xyz":applied_force,
                "signed_applied_global_moment_kNm_xyz":applied_m,
                "reaction_force_kN_xyz":base_force,
                "max_force_equilibrium_residual_kN":force_res,
                "max_moment_equilibrium_residual_kNm":moment_res,
                "floor_drifts":floor_drifts,
                "max_elastic_roof_horizontal_vector_mm":max_roof,
                "max_elastic_story_chord_ratio":max(x["max_elastic_story_chord_ratio"] for x in floor_drifts),
                "governing_absolute_member_end_moment_kNm":abs(governing["signed"][governing_component]),
                "governing_member":governing["id"],
                "governing_local_component":COMPONENTS[governing_component],
                "governing_signed_local_component_kNm":governing["signed"][governing_component],
                "governing_signed_local_12_actions":governing["signed"],
                "node_displacements":node_by_grid,
                "local_signed_member_action_count":len(signed),
                "floor_weight_application":"EQUAL_GRAVITY_NODAL; EQUIVALENT_LATERAL_FORCE_PLUS_NODAL_TORSION_COUPLE",
                "accidental_eccentricity_fraction":ACC if axis else 0,
                "applied_accidental_eccentricity_sign":esgn if axis else 0,
                "reaction_equilibrium_verified":True
            }
            signed_for_superposition[(boundary,name)]=signed
            if not summary_only:record["full_local_member_signed_actions"]=signed
            cases.append(record)
            ops.wipe()
    comparison=[]
    for i,(_,axis,sign,esgn) in enumerate(specs):
        a=cases[i]
        b=cases[i+len(specs)]
        assert a["case"]==b["case"]
        comparison.append({
           "case":a["case"],"signed_axis":axis or "GRAVITY",
           "sign":sign,"eccentricity_sign":esgn,
           "flexible_roof_mm":a["max_elastic_roof_horizontal_vector_mm"],
           "rigid_roof_mm":b["max_elastic_roof_horizontal_vector_mm"],
           "flexible_max_story_chord_ratio":a["max_elastic_story_chord_ratio"],
           "rigid_max_story_chord_ratio":b["max_elastic_story_chord_ratio"],
           "flexible_governing_end_moment_kNm":a["governing_absolute_member_end_moment_kNm"],
           "rigid_governing_end_moment_kNm":b["governing_absolute_member_end_moment_kNm"],
           "force_equilibrium_both":a["reaction_equilibrium_verified"] and b["reaction_equilibrium_verified"]
        })
    # Explicitly assumed factors for sensitivity, NOT accepted NBC design
    # combinations. Within each boundary, ALL 165 signed component vectors
    # are superimposed before selecting a controlling member. Never combine
    # absolute moments, envelope maxima, or independent governing members.
    combos=[]
    for boundary in ("FLEXIBLE","RIGID_MPC_TRIAL"):
        g=signed_for_superposition[(boundary,"GRAVITY")]
        for gravity_factor,tag in ((1.2,"G1P2_PLUS_EQ"),(.9,"G0P9_PLUS_EQ")):
            for name,axis,sign,esgn in specs[1:]:
                eq=signed_for_superposition[(boundary,name)]
                full=[]
                for gv,ev in zip(g,eq):
                    assert gv["id"]==ev["id"]
                    v=[gravity_factor*x+y for x,y in zip(gv["signed"],ev["signed"])]
                    full.append({"id":gv["id"],"components":COMPONENTS,"signed":v})
                top=max(full,key=lambda x:max(abs(x["signed"][j]) for j in (4,5,10,11)))
                idx=max((4,5,10,11),key=lambda j:abs(top["signed"][j]))
                comb={
                  "boundary":boundary,"seismic_case":name,
                  "trial_combination":tag,
                  "gravity_factor_assumed":gravity_factor,"seismic_factor_assumed":1.,
                  "signed_member_action_count":len(full),
                  "governing_member":top["id"],"governing_local_component":COMPONENTS[idx],
                  "governing_signed_end_moment_kNm":top["signed"][idx],
                  "governing_moment_abs_kNm":abs(top["signed"][idx]),
                  "not_a_confirmed_code_combination":True
                }
                if not summary_only:
                    comb["full_local_member_signed_actions"]=full
                combos.append(comb)
    assert len(combos)==32
    return {
      "schema":"jp.structural.g15.gate12.diaphragm_openSees_comparison.v0.1",
      "run_kind":"SAME_SOURCE_FRAME_ALTERNATIVE_MPC_LINEAR_STATIC_FE",
      "request":p,"source_grid_members":count,"source_columns":23,
      "model_levels":4,"source_case_id":case_id,
      "assumed_floor_cm_xy_m":floor_cms,
      "assumed_envelope_xy_m":[lx,ly],
      "site_or_building_source_mass_verified":False,
      "assumed_floor_polygon_physical":False,"actual_slab_shell_elements":False,
      "structural_wall_members_in_model":False,
      "flexible_boundary":"CONNECTED_BEAM_COLUMN_FRAME_NO_MPC",
      "rigid_boundary":"OPENSEES_RIGIDDIAPHRAGM_PERP_3_3DOF_MPC",
      "true_seismic_response_spectrum_included":False,
      "accidental_eccentricity_physical":"SIGNED_EQUIVALENT_NODAL_FORCE_COUPLES",
      "interstorey_measure":"MAX_PLAN_COLUMN_ELASTIC_CHORD_OVER_STORY_HEIGHT",
      "displacement_limit_compliance_verified":False,
      "signed_combinations_implemented":"32_PROVISIONAL_LINEAR_SUPERPOSITION_TRIALS_NOT_CODE_ACCEPTED",
      "trial_factors_need_NBC_SOURCE_COMBINATION_VERIFICATION":True,
      "P_delta_and_foundation_check_included":False,
      "source_F3_one_way_shear":"NOT SAFE IN ONE WAY SHEAR",
      "seismic_mass_reconciled":False,"engineering_approval":False,
      "cases":cases,"comparisons":comparison,"trial_signed_combinations":combos
    }

def parse_issue_event(event_path):
    data=json.loads(Path(event_path).read_text(encoding="utf-8"))
    issue=data.get("issue",{})
    if issue.get("user",{}).get("login") not in ("FabinGurung","Kaksaveksaka"):
        raise ValueError("Unapproved GitHub Actions submitter")
    if not str(issue.get("title","")).startswith("[JP G15 G12]"):
        raise ValueError("Not a governed Gate12 request")
    raw=issue.get("body","")
    if not isinstance(raw,str) or len(raw)>2000 or not raw.startswith("JP_G15_GATE12_RUN_V1\\n"):
        raise ValueError("Gate12 request schema missing")
    line=raw.splitlines()[1]
    if len(line)>600:raise ValueError("Gate12 source selection too large")
    params=json.loads(line)
    if not isinstance(params,dict) or set(params)!= {"gate10_case","stiffness"}:
        raise ValueError("Unsupported Gate12 request fields")
    allowed={x["id"] for x in gate10()["model_cases"]}
    if params["gate10_case"] not in allowed or params["stiffness"] not in ("ULS","SLS","GROSS"):
        raise ValueError("Unknown Gate12 source or stiffness")
    return params

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--output",type=Path,required=True)
    a.add_argument("--event",type=Path)
    a.add_argument("--summary-only",action="store_true")
    a.add_argument("--gate10-case",default=CASE_ID)
    a.add_argument("--stiffness",default="ULS",choices=["ULS","SLS","GROSS"])
    opt=a.parse_args()
    if opt.event:
        submitted=parse_issue_event(opt.event)
        opt.gate10_case=submitted["gate10_case"]
        opt.stiffness=submitted["stiffness"]
    d=gate10()
    match=next(x for x in d["model_cases"] if x["id"]==opt.gate10_case)
    p=dict(SAMPLE)
    p["floor_weights_kN"]=match["floor_weights_kN"]
    p["stiffness"]=opt.stiffness
    out=solve(p,opt.gate10_case,summary_only=opt.summary_only)
    opt.output.parent.mkdir(parents=True,exist_ok=True)
    opt.output.write_text(json.dumps(out,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("G15_GATE12_SAME_165_MEMBER_FRAME_FLEXIBLE_RIGID_18_FE_CASES_EQUILIBRIUM_PASS_ENGINEERING_HOLD",
          len(out["cases"]),len(out["comparisons"]),opt.output)

if __name__=="__main__":main()
