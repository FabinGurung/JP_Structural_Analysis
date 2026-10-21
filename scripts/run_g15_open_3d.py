"""Public-source G15 3D elastic frame solver: OpenSeesPy, 165 members.

23 supplied positions; 3 vertical segments per position; 32 assumed beams at
each of three levels. Public engineering source is explicitly NOT as-built.
Code: NBC 105:2025 static force distribution (coefficients user-supplied,
not independently site-verified). Uses 6 DOF per node and signed 12-component
local member actions. No physical slab shells, walls, diaphragms, accidental
torsion, P-Delta or footing redesign. ALL runs carry engineering HOLD.
"""
import argparse
import json
import math
import os
from pathlib import Path
from jp_structural.solvers.native.nbc105_2025_esm import equivalent_static_floor_forces

ROOT=Path(__file__).resolve().parents[1]
MODEL=ROOT/"site/data/g15-working-grid.public.v0.1.json"
SAMPLE={
  "schema":"jp.structural.g15.open3d.request.v1",
  "beam_width_mm":304.8,"concrete_E_MPa":22360.6798,
  "stiffness":"ULS","bridges":True,
  "floor_weights_kN":[2050.,2050.,1959.877983371731],
  "C_design":.131,"T_seconds":.493
}
ALLOWED=set(SAMPLE)
LIMITS={
  "beam_width_mm":(200,650),"concrete_E_MPa":(10000,50000),
  "C_design":(.01,.5),"T_seconds":(.1,3.0),
}
def numeric(v,name,lo,hi):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not lo<=v<=hi:
        raise ValueError(f"{name} outside allowed finite range {lo}..{hi}")
    return float(v)
def validate(p):
    if not isinstance(p,dict) or set(p)!=ALLOWED or p.get("schema")!=SAMPLE["schema"]:
        raise ValueError("Unsupported request keys/schema")
    out={"schema":SAMPLE["schema"]}
    for k,(lo,hi) in LIMITS.items():
        out[k]=numeric(p[k],k,lo,hi)
    if p["stiffness"] not in ("ULS","SLS","GROSS"):
        raise ValueError("Invalid stiffness state")
    if not isinstance(p["bridges"],bool):
        raise ValueError("bridges must be boolean")
    w=p["floor_weights_kN"]
    if not isinstance(w,list) or len(w)!=3:
        raise ValueError("Exactly three floor seismic weights required")
    out.update({"stiffness":p["stiffness"],"bridges":p["bridges"],
         "floor_weights_kN":[numeric(x,"floor_weight_kN",20,10000) for x in w]})
    return out

def parse_issue(path):
    event=json.loads(Path(path).read_text(encoding="utf-8"))
    issue=event["issue"]
    if issue.get("user",{}).get("login") not in ("FabinGurung","Kaksaveksaka"):
        raise ValueError("Unapproved GitHub Actions submitter; fork to run your own")
    if not str(issue.get("title","")).startswith("[JP G15 3D]"):
        raise ValueError("Not a configured G15 3D run")
    body=issue.get("body","")
    if len(body)>3200 or not body.startswith("JP_G15_3D_RUN_V1\n"):
        raise ValueError("Bad public request format")
    line=body.splitlines()[1]
    if len(line)>1200:raise ValueError("Request too large")
    return validate(json.loads(line))

def source():
    model=json.loads(MODEL.read_text(encoding="utf-8"))
    assert model["schema"]=="jp.structural.g15.public_working_grid.v0.1"
    assert len(model["column_positions_mm"])==23
    assert len(model["beam_edges"])==32
    assert model["hypothetical_beam_edge_indices"]==[30,31]
    assert model["safety"]["engineering_approval"] is False
    return model

def section(section_id,sections,width):
    s=sections[section_id]
    if s["shape"]=="circle":
        d=s["diameter"]/1000.
        a=math.pi*d*d/4;iy=iz=math.pi*d**4/64.;j=2*iy
    else:
        b=(width if section_id=="BEAM" else s["width"])/1000.
        h=s["depth"]/1000.
        a=b*h;iy=h*b**3/12;iz=b*h**3/12
        bigger,smaller=max(b,h),min(b,h)
        j=bigger*smaller**3*(1/3-.21*smaller/bigger*(1-smaller**4/(12*bigger**4)))
    return a,iy,iz,j

def solve(request):
    import openseespy.opensees as ops
    p=validate(request);m=source();cols=m["column_positions_mm"]
    coords={c[0]:(c[1]/1000,c[2]/1000,c[3]) for c in cols}
    nodes={}
    for idx,c in enumerate(cols):
        for level in range(4):
            nodes[(c[0],level)]=100*idx+level+1
    count=23*3+len(m["beam_edges"][:(32 if p["bridges"] else 30)])*3
    if p["bridges"] and count!=165:raise ValueError("Source member count unexpectedly changed")
    stiffness={"ULS":(.35,.70),"SLS":(.70,.90),"GROSS":(1.,1.)}[p["stiffness"]]
    h=[z/1000 for z in m["floor_levels_mm"][1:]]
    esm=equivalent_static_floor_forces(
       floor_weights_kN=p["floor_weights_kN"],floor_heights_m=h,
       period_seconds=p["T_seconds"],design_coefficient=p["C_design"])
    elastic=p["concrete_E_MPa"]*1000; shear=elastic/2.4
    out=[]
    for label,axis,sign in [
        ("GRAVITY","Z",-1),("EQ_PLUS_X","X",1),("EQ_MINUS_X","X",-1),
        ("EQ_PLUS_Y","Y",1),("EQ_MINUS_Y","Y",-1)]:
        ops.wipe()
        ops.model("basic","-ndm",3,"-ndf",6)
        for c in cols:
            x,y,_=coords[c[0]]
            for level,z in enumerate(m["floor_levels_mm"]):
                nid=nodes[(c[0],level)]
                ops.node(nid,x,y,z/1000)
                if level==0:ops.fix(nid,1,1,1,1,1,1)
        ops.geomTransf("Linear",1,1,0,0) # column axis +Z; local ref +X
        ops.geomTransf("Linear",2,0,0,1) # horizontal beam ref +Z
        elements=[];tag=0
        for c in cols:
            name,_,_,sec=c
            a,iy,iz,j=section(sec,m["section_definitions_mm"],p["beam_width_mm"])
            for level in range(1,4):
                tag+=1
                ops.element("elasticBeamColumn",tag,nodes[(name,level-1)],nodes[(name,level)],
                            a,elastic,shear,j,iy*stiffness[1],iz*stiffness[1],1)
                elements.append((tag,f"COL-{name}-L{level-1}-{level}"))
        edges=m["beam_edges"] if p["bridges"] else m["beam_edges"][:30]
        a,iy,iz,j=section("BEAM",m["section_definitions_mm"],p["beam_width_mm"])
        for edge in edges:
            for level in range(1,4):
                tag+=1
                ops.element("elasticBeamColumn",tag,nodes[(edge[0],level)],nodes[(edge[1],level)],
                            a,elastic,shear,j,iy*stiffness[0],iz*stiffness[0],2)
                elements.append((tag,f"BEAM-{edge[0]}-{edge[1]}-L{level}"))
        ops.timeSeries("Linear",1);ops.pattern("Plain",1,1)
        for level in range(1,4):
            for c in cols:
                nid=nodes[(c[0],level)]
                weight=p["floor_weights_kN"][level-1]/len(cols)
                lateral=sign*esm["floor_forces_kN"][level-1]/len(cols)
                if label=="GRAVITY":ops.load(nid,0,0,-weight,0,0,0)
                elif axis=="X":ops.load(nid,lateral,0,0,0,0,0)
                else:ops.load(nid,0,lateral,0,0,0,0)
        ops.constraints("Plain");ops.numberer("RCM");ops.system("UmfPack")
        ops.test("NormUnbalance",1e-7,8)
        ops.algorithm("Linear");ops.integrator("LoadControl",1)
        ops.analysis("Static")
        if ops.analyze(1)!=0:raise RuntimeError(f"3D solve failed: {label}")
        disp=[]
        for level in range(1,4):
            for c in cols:
                disp.append({"node":c[0],"level":level,"ux_mm":ops.nodeDisp(nodes[(c[0],level)],1)*1000,
                       "uy_mm":ops.nodeDisp(nodes[(c[0],level)],2)*1000})
        forces=[]
        for etag,ename in elements:
            vec=list(map(float,ops.eleResponse(etag,"localForce")))
            if len(vec)!=12 or not all(math.isfinite(v) for v in vec):
                raise RuntimeError("Nonfinite or incomplete signed local action")
            forces.append({"id":ename,"local_components":["Ni","Vyi","Vzi","Ti","Myi","Mzi","Nj","Vyj","Vzj","Tj","Myj","Mzj"],"signed":vec})
        ops.reactions()
        total=[sum(ops.nodeReaction(nodes[(c[0],0)],j) for c in cols) for j in (1,2,3)]
        target=([0,0,sum(p["floor_weights_kN"])] if label=="GRAVITY"
                else [-sign*esm["base_shear_kN"] if axis=="X" else 0,
                      -sign*esm["base_shear_kN"] if axis=="Y" else 0,0])
        residual=max(abs(total[j]-target[j]) for j in range(3))
        if residual>1e-3:raise RuntimeError(f"Global equilibrium mismatch {label}: {residual}")
        maxroof=max((abs(x["ux_mm"])+abs(x["uy_mm"])) for x in disp if x["level"]==3)
        out.append({"case":label,"reaction_kN_xyz":total,"equilibrium_residual_kN":residual,
                    "max_roof_horizontal_displacement_mm":maxroof,
                    "node_displacements":disp,
                    "member_signed_local_end_forces":forces})
        ops.wipe()
    return {"schema":"jp.structural.g15.open3d.result.v1","request":p,
            "model":"REAL_SOURCE_DERIVED_3D_HYPOTHESIS",
            "model_counts":{"column_positions":23,"nodes":92,"members":count,"column_segments":69,
                  "beam_segments":count-69},"esm":esm,"cases":out,
            "analysis_type":"LINEAR_ELASTIC_3D_FRAME_SINGLE_DIRECTION_STATIC_CASES",
            "diaphragm_included":False,"accidental_torsion_included":False,
            "floor_load_allocation":"EQUAL_PER_GRID_POSITION_ASSUMPTION",
            "slab_wall_load_paths_verified":False,
            "foundation_F3_one_way_shear":"NOT SAFE IN ONE WAY SHEAR",
            "seismic_mass_reconciled":False,
            "engineering_approval":False,"report_accepted":False}

def main():
    parser=argparse.ArgumentParser()
    arg=parser.add_mutually_exclusive_group(required=True)
    arg.add_argument("--sample",action="store_true")
    arg.add_argument("--event",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    req=SAMPLE if args.sample else parse_issue(args.event)
    res=solve(req)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(res,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("PUBLIC_G15_3D_5_CASES_SIGNED_EQUILIBRIUM_PASS_DESIGN_HOLD",
       len(res["cases"]),res["model_counts"]["members"])
if __name__=="__main__":main()
