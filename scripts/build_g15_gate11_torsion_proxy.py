#!/usr/bin/env python3
"""Gate11 trial rigid-diaphragm accidental-torsion screen, NOT a 3D FE replacement.

A floor mass centroid is derived from SOURCE CAPTION AREA-FITTED convex hull,
NOT from as-built floor polygons. A floor stiffness centroid is an independent
cantilever-column K=12EI/h^3 proxy, NOT an ETABS diaphragm/result. Signed floor
forces are balanced through 23 elastic node springs for X/Y and ±5% eccentricity.
"""
import argparse
import json
import math
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.build_g15_gate10_assumptions import build as gate10

ROOT=Path(__file__).resolve().parents[1]
GRID=ROOT/"site/data/g15-working-grid.public.v0.1.json"
STORY_HEIGHT_M=3.048
ELASTIC_E_KN_M2=22360.6798*1000.
C_DESIGN=.131
T_SECONDS=.493
ACCIDENTAL=.05

def centroid(vertices):
    area2=0.;cx=0.;cy=0.
    for i,(x,y) in enumerate(vertices):
        X,Y=vertices[(i+1)%len(vertices)]
        z=x*Y-X*y
        area2+=z;cx+=(x+X)*z;cy+=(y+Y)*z
    assert abs(area2)>1
    return cx/(3*area2),cy/(3*area2)

def inertia(s):
    if s["shape"]=="circle":
        D=s["diameter"]/1000.
        I=math.pi*D**4/64.
        return I,I
    b=s["width"]/1000.;d=s["depth"]/1000.
    return b*d**3/12., d*b**3/12.

def build(case_id="G10_EDGE_COMM",stiffness="ULS"):
    assert stiffness in ("GROSS","ULS","SLS")
    g=gate10()
    model=json.loads(GRID.read_text(encoding="utf-8"))
    chosen=next((x for x in g["model_cases"] if x["id"]==case_id),None)
    if chosen is None:raise ValueError("unknown Gate10 case")
    sections=model["section_definitions_mm"]
    factor={"GROSS":1.,"ULS":.70,"SLS":.90}[stiffness]
    pts=[]
    for name,mmx,mmy,kind in model["column_positions_mm"]:
        iy,iz=inertia(sections[kind])
        Kx=12*ELASTIC_E_KN_M2*iz*factor/STORY_HEIGHT_M**3
        Ky=12*ELASTIC_E_KN_M2*iy*factor/STORY_HEIGHT_M**3
        pts.append({"id":name,"x":mmx/1000.,"y":mmy/1000.,"Kx":Kx,"Ky":Ky})
    sumx=sum(x["Kx"] for x in pts);sumy=sum(x["Ky"] for x in pts)
    crx=sum(x["Ky"]*x["x"] for x in pts)/sumy
    cry=sum(x["Kx"]*x["y"] for x in pts)/sumx
    ktheta=sum(x["Ky"]*(x["x"]-crx)**2+x["Kx"]*(x["y"]-cry)**2 for x in pts)
    assert ktheta>0
    # Envelope dimensions derive from 0–21m x and 0–12.53m y SOURCE grid
    xs=[x["x"] for x in pts];ys=[x["y"] for x in pts]
    lx=max(xs)-min(xs);ly=max(ys)-min(ys)
    assert abs(lx-21)<1e-6 and abs(ly-12.53)<1e-6
    h=[3.048,6.096,9.144]
    weights=chosen["floor_weights_kN"]
    V=C_DESIGN*sum(weights)
    denom=sum(a*b for a,b in zip(weights,h))
    Fi=[V*a*b/denom for a,b in zip(weights,h)]
    cases=[]
    for axis in ["X","Y"]:
        for lateral in [-1,1]:
            for offset in [-1,1]:
                floors=[]
                for i,outline in enumerate(g["footprints"]["assumed_per_floor"]):
                    cmx,cmy=centroid(outline["scaled_convex_hull_outline_xy_m"])
                    signed_force=lateral*Fi[i]
                    # ±5% of perpendicular source-grid plan dimension
                    ecc=ACCIDENTAL*(ly if axis=="X" else lx)*offset
                    ex=cmx-crx+(ecc if axis=="Y" else 0.)
                    ey=cmy-cry+(ecc if axis=="X" else 0.)
                    M=(-ey*signed_force if axis=="X" else ex*signed_force)
                    theta=M/ktheta
                    Fx=signed_force if axis=="X" else 0.
                    Fy=signed_force if axis=="Y" else 0.
                    reactions=[]
                    for p in pts:
                        dx=p["x"]-crx;dy=p["y"]-cry
                        rx=(p["Kx"]/sumx)*Fx-p["Kx"]*dy*theta
                        ry=(p["Ky"]/sumy)*Fy+p["Ky"]*dx*theta
                        reactions.append({"column_grid":p["id"],
                           "signed_floor_shear_X_kN":rx,
                           "signed_floor_shear_Y_kN":ry,
                           "assumed_wall_shear_kN":0,
                           "story_lateral_disp_X_mm":1000*((Fx/sumx)-dy*theta),
                           "story_lateral_disp_Y_mm":1000*((Fy/sumy)+dx*theta)})
                    sx=sum(a["signed_floor_shear_X_kN"] for a in reactions)
                    sy=sum(a["signed_floor_shear_Y_kN"] for a in reactions)
                    sm=sum((p["x"]-crx)*r["signed_floor_shear_Y_kN"]-
                           (p["y"]-cry)*r["signed_floor_shear_X_kN"]
                           for p,r in zip(pts,reactions))
                    assert max(abs(sx-Fx),abs(sy-Fy),abs(sm-M))<1e-7
                    floors.append({
                        "floor":i+1,"height_m":h[i],
                        "assumed_mass_centroid_xy_m":[cmx,cmy],
                        "assumed_stiffness_centroid_xy_m":[crx,cry],
                        "accidental_eccentricity_m":ecc,
                        "signed_applied_floor_force_kN":signed_force,
                        "signed_torsional_demand_about_stiffness_center_kNm":M,
                        "rotation_radians":theta,
                        "max_assumed_lateral_displacement_mm":max(
                           math.hypot(r["story_lateral_disp_X_mm"],r["story_lateral_disp_Y_mm"])
                           for r in reactions),
                        "sum_column_X_kN":sx,"sum_column_Y_kN":sy,
                        "sum_column_torsion_kNm":sm,
                        "force_and_moment_equilibrium_verified":True,
                        "column_force_distribution":reactions})
                cases.append({"axis":axis,"lateral_sign":lateral,
                   "accidental_offset_sign":offset,"floors":floors,
                   "max_trial_story_displacement_mm":max(x["max_assumed_lateral_displacement_mm"] for x in floors),
                   "max_abs_torsional_kNm":max(abs(x["signed_torsional_demand_about_stiffness_center_kNm"]) for x in floors)})
    assert len(cases)==8 and all(len(x["floors"])==3 for x in cases)
    return {
       "schema":"jp.structural.g15.gate11.rigid_diaphragm_proxy.v0.1",
       "source_mass_case_id":case_id,
       "stiffness_state":stiffness,
       "boundary_assumption":"INDEPENDENT_STORY_CANTILEVER_COLUMNS_NO_BEAM_CONTINUITY",
       "diaphragm_assumption":"RIGID_IN_PLANE_ABSTRACT_MPC_SCREEN_NOT_FLOOR_SHELL",
       "accidental_eccentricity_fraction":ACCIDENTAL,
       "source_grid_span_xy_m":[lx,ly],
       "floor_base_shear_kN":V,
       "source_floor_weight_kN":weights,
       "source_floor_force_kN":Fi,
       "center_of_rigidity_proxy_xy_m":[crx,cry],
       "K_torsion_kNm_per_rad":ktheta,
       "cases":cases,
       "footprints_and_real_wall_placements_verified":False,
       "actual_story_drift_accepted":False,
       "P_delta_checked":False,
       "mass_source_reconciled":False,
       "foundation_F3_source":"NOT SAFE IN ONE WAY SHEAR",
       "engineering_approval":False
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--case",default="G10_EDGE_COMM")
    p.add_argument("--stiffness",default="ULS")
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    result=build(args.case,args.stiffness)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("G15_GATE11_ECCENTRICITY_AND_RIGID_PROXY_SCREEN_PASS_NOT_APPROVED",len(result["cases"]),
          round(result["floor_base_shear_kN"],5))
if __name__=="__main__":main()
