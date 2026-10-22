#!/usr/bin/env python3
"""Gate14: matched two-level, source-bay ShellMITC4 sensitivity (NOT a floor model).

The F-G/1-2 source sample bay is HYPOTHETICALLY repeated at elevated levels
1 and 2. Each level has a real 2x2 ShellMITC4 mesh with beam-line-compatible
mid-edge nodes. This is a computational repeat, NOT evidence of slab extent
or actual storey assignment. All three alternatives preserve the same 165
original member segments, applied gravity, assumed wall beam line loads,
signed seismic resultants and G10 mass ledger. Original ETABS mass and F3
one-way shear failure remain unresolved; no engineering acceptance.
"""
import argparse
import json
import math
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.run_g15_open_3d import source,section,SAMPLE,validate
from scripts.build_g15_gate10_assumptions import build as gate10
from scripts.build_g15_gate11_torsion_proxy import centroid
from scripts.run_g15_gate12_diaphragm_fe import floor_nodal_lateral
from jp_structural.solvers.native.nbc105_2025_esm import equivalent_static_floor_forces

PATCH_LEVELS=(1,2)
SHELL_THICKNESS_M=.125
SOURCE_PANEL_DEAD_KPA=5.13
SOURCE_MAIN_WALL_KN_M=9.24
WALL_LEVELS=(1,2)
MODES=("FRAME_POINT_PATCH_2F","SHELLMITC4_PATCH_2F","FULL_RIGID_MPC_REFERENCE_2F")
COMPONENTS=["Ni","Vyi","Vzi","Ti","Myi","Mzi","Nj","Vyj","Vzj","Tj","Myj","Mzj"]

def build_plan():
    original=source()
    study=gate10()
    reg=json.loads((ROOT/"registry/g15-gate09-panel-mass-source.v0.1.json").read_text())
    cols=original["column_positions_mm"]
    xy={p[0]:(p[1]/1000.,p[2]/1000.) for p in cols}
    fx,fy=xy["F1"];gx,gy=xy["G1"];tx,ty=xy["F2"]
    assert math.isclose(gx-fx,4.965,abs_tol=1e-8)
    assert math.isclose(ty-fy,3.6,abs_tol=1e-8)
    assert math.isclose(gy,fy)
    xmid=(fx+gx)/2.;ymid=(fy+ty)/2.
    extra={
        "G2":(gx,ty),"FG1_M":(xmid,fy),"GG2_M":(gx,ymid),
        "FG2_M":(xmid,ty),"FF2_M":(fx,ymid),"BAY_CENTER":(xmid,ymid)
    }
    patch=["F1","FG1_M","G1","FF2_M","BAY_CENTER","GG2_M","F2","FG2_M","G2"]
    for q in extra:
        assert q not in xy
    xy.update(extra)
    quads=[
        ("F1","FG1_M","BAY_CENTER","FF2_M"),
        ("FG1_M","G1","GG2_M","BAY_CENTER"),
        ("FF2_M","BAY_CENTER","FG2_M","F2"),
        ("BAY_CENTER","GG2_M","G2","FG2_M")]
    for ids in quads:
        ps=[xy[i] for i in ids]
        twice=sum(ps[i][0]*ps[(i+1)%4][1]-ps[(i+1)%4][0]*ps[i][1] for i in range(4))
        assert twice>0
    area=(gx-fx)*(ty-fy)
    assert abs(area-17.874)<1e-8
    main=study["wall_candidates"]["edges"]
    assert len(main)==7
    assert all(p["source_verified_wall"] is False for p in main)
    assert abs(reg["source_wall_assembly"]["reported_main_wall_kN_m"]-SOURCE_MAIN_WALL_KN_M)<1e-8
    return original,study,xy,extra,quads,area,main

def solve(stiffness="ULS",summary_only=True):
    import openseespy.opensees as ops
    old,study,xy,extra,quads,patch_area,walls=build_plan()
    mass=next(x for x in study["model_cases"] if x["id"]=="G10_EDGE_COMM")
    req=dict(SAMPLE);req["floor_weights_kN"]=mass["floor_weights_kN"]
    req["stiffness"]=stiffness
    req=validate(req)
    columns=old["column_positions_mm"]
    base_ids={p[0]:i*100+1 for i,p in enumerate(columns)}
    nid={(p[0],k):base_ids[p[0]]+k for p in columns for k in range(4)}
    extra_ids={(n,level):3000+100*level+i
               for level in PATCH_LEVELS for i,n in enumerate(extra)}
    for (n,level),tag in extra_ids.items():nid[(n,level)]=tag
    level_heights=[z/1000 for z in old["floor_levels_mm"]]
    elastic=req["concrete_E_MPa"]*1000.
    shear=elastic/2.4
    beam_crack,column_crack={"GROSS":(1.,1.),"SLS":(.70,.90),"ULS":(.35,.70)}[stiffness]
    mass_polys=study["footprints"]["assumed_per_floor"]
    centers=[centroid(q["scaled_convex_hull_outline_xy_m"]) for q in mass_polys]
    plan=[xy[p[0]] for p in columns]
    lx=max(x for x,y in plan)-min(x for x,y in plan)
    ly=max(y for x,y in plan)-min(y for x,y in plan)
    esm=equivalent_static_floor_forces(floor_weights_kN=req["floor_weights_kN"],
       floor_heights_m=level_heights[1:],period_seconds=req["T_seconds"],
       design_coefficient=req["C_design"])
    wall_length=sum(p["length_m"] for p in walls)
    source_wall_W=len(WALL_LEVELS)*wall_length*SOURCE_MAIN_WALL_KN_M
    expected_slab_W=patch_area*SOURCE_PANEL_DEAD_KPA
    assert source_wall_W>0 and expected_slab_W>0
    wall_edges={tuple(q["between"]) for q in walls}
    specs=[("GRAVITY",None,0,0)]
    for axis in ("X","Y"):
        for sign in (1,-1):
            for eccsign in (1,-1):
                specs.append((f"EQ_{axis}_{'POS' if sign>0 else 'NEG'}_E{'POS' if eccsign>0 else 'NEG'}",
                    axis,sign,eccsign))
    cases=[]
    for mode in MODES:
        for case,axis,sign,ecc_sign in specs:
            ops.wipe();ops.model("basic","-ndm",3,"-ndf",6)
            for name,xx,yy,_ in columns:
                for lev,z in enumerate(level_heights):
                    ops.node(nid[(name,lev)],xx/1000.,yy/1000.,z)
                    if lev==0:ops.fix(nid[(name,0)],1,1,1,1,1,1)
            for level in PATCH_LEVELS:
                for name,(xx,yy) in extra.items():
                    if name=="BAY_CENTER" and mode!="SHELLMITC4_PATCH_2F":continue
                    ops.node(nid[(name,level)],xx,yy,level_heights[level])
            if mode=="FULL_RIGID_MPC_REFERENCE_2F":
                for floor,center in enumerate(centers,1):
                    master=6000+floor
                    ops.node(master,center[0],center[1],level_heights[floor])
                    ops.fix(master,0,0,1,1,1,0)
                    members=[nid[(c[0],floor)] for c in columns]
                    if floor in PATCH_LEVELS:
                        members += [nid[(q,floor)] for q in extra if q!="BAY_CENTER"]
                    ops.rigidDiaphragm(3,master,*members)
            ops.geomTransf("Linear",1,1,0,0)
            ops.geomTransf("Linear",2,0,0,1)
            frame=[];per_origin={}
            tag=0
            for col in columns:
                name,_,_,kind=col
                a,iy,iz,j=section(kind,old["section_definitions_mm"],req["beam_width_mm"])
                for level in range(1,4):
                    tag+=1
                    ops.element("elasticBeamColumn",tag,nid[(name,level-1)],
                      nid[(name,level)],a,elastic,shear,j,iy*column_crack,iz*column_crack,1)
                    frame.append((tag,f"COL-{name}-L{level-1}-{level}"))
            a,iy,iz,j=section("BEAM",old["section_definitions_mm"],req["beam_width_mm"])
            for start,end in old["beam_edges"]:
                for level in range(1,4):
                    names=[start,end]
                    if level in PATCH_LEVELS:
                        x0,y0=xy[start];x1,y1=xy[end]
                        for name,(x,y) in extra.items():
                            if name=="BAY_CENTER":continue
                            if abs((x-x0)*(y1-y0)-(y-y0)*(x1-x0))>1e-7:continue
                            dot=(x-x0)*(x1-x0)+(y-y0)*(y1-y0)
                            Lsq=(x1-x0)**2+(y1-y0)**2
                            if dot>1e-7 and dot<Lsq-1e-7:names.insert(-1,name)
                        names=[start]+sorted(names[1:-1],key=lambda q:
                          ((xy[q][0]-x0)*(x1-x0)+(xy[q][1]-y0)*(y1-y0))/Lsq)+[end]
                    for u,v in zip(names,names[1:]):
                        tag+=1
                        ops.element("elasticBeamColumn",tag,nid[(u,level)],nid[(v,level)],
                                    a,elastic,shear,j,iy*beam_crack,iz*beam_crack,2)
                        frame.append((tag,f"BEAM-{start}-{end}-L{level}" + (f"-{u}-{v}" if len(names)>2 else "")))
                        per_origin.setdefault((start,end,level),[]).append((tag,math.dist(xy[u],xy[v]),u,v))
            assert len(frame)==177, (len(frame),mode,case)
            shell=[]
            if mode=="SHELLMITC4_PATCH_2F":
                ops.nDMaterial("ElasticIsotropic",30,elastic,.2)
                ops.section("PlateFiber",31,30,SHELL_THICKNESS_M)
                for level in PATCH_LEVELS:
                    for q in quads:
                        tag+=1
                        ops.element("ShellMITC4",tag,*[nid[(n,level)] for n in q],31)
                        shell.append(tag)
                assert len(shell)==4*len(PATCH_LEVELS)
            ops.timeSeries("Linear",1);ops.pattern("Plain",1,1)
            applied=[]
            def add_node_load(label,floor,fx,fy,fz):
                x,y=xy[label];z=level_heights[floor]
                ops.load(nid[(label,floor)],fx,fy,fz,0,0,0)
                applied.append((x,y,z,fx,fy,fz))
            for floor in range(1,4):
                f=sign*esm["floor_forces_kN"][floor-1]
                cm=centers[floor-1]
                ecc=ecc_sign*.05*(ly if axis=="X" else lx) if axis else 0.
                load=floor_nodal_lateral(axis,f,plan,cm,ecc) if axis else [(0.,0.)]*len(columns)
                for col,(fx,fy) in zip(columns,load):
                    add_node_load(col[0],floor,fx,fy,0.)
            if case=="GRAVITY":
                for level in PATCH_LEVELS:
                    if shell:
                        # Area load supplied as consistent nodal patch weight,
                        # including slab selfweight ONCE (no auto body weight).
                        for q in quads:
                            patch=-SOURCE_PANEL_DEAD_KPA*(patch_area/4)/4
                            for label in q:add_node_load(label,level,0.,0.,patch)
                    else:
                        # Matched frame/rigid corner tributary reference at
                        # BOTH assumed levels; total applied force identical.
                        for name in ("F1","G1","G2","F2"):
                            add_node_load(name,level,0.,0.,-expected_slab_W/4)
                for w in walls:
                    start,end=w["between"]
                    for floor in WALL_LEVELS:
                        for et,length,u,v in per_origin[(start,end,floor)]:
                            ops.eleLoad("-ele",et,"-type","-beamUniform",0.,-SOURCE_MAIN_WALL_KN_M,0.)
                            x,y=xy[u];xx,yy=xy[v]
                            applied.append(((x+xx)/2,(y+yy)/2,level_heights[floor],
                                 0.,0.,-SOURCE_MAIN_WALL_KN_M*length))
            ops.constraints("Transformation" if mode=="FULL_RIGID_MPC_REFERENCE_2F" else "Plain")
            ops.numberer("RCM");ops.system("UmfPack")
            ops.test("NormUnbalance",1e-7,10)
            ops.algorithm("Linear");ops.integrator("LoadControl",1)
            ops.analysis("Static")
            if ops.analyze(1)!=0:
                ops.wipe();raise RuntimeError("OpenSees failed "+mode+" "+case)
            loc=[]
            for t,label in frame:
                q=list(map(float,ops.eleResponse(t,"localForce")))
                if len(q)!=12 or not all(math.isfinite(v) for v in q):
                    raise ValueError("Bad frame end-action vector")
                loc.append({"id":label,"signed":q,"components":COMPONENTS})
            node_displacements={}
            floor_chords=[]
            for floor in range(1,4):
                dis={}
                for col in columns:
                    label=col[0]
                    dis[label]=(ops.nodeDisp(nid[(label,floor)],1),ops.nodeDisp(nid[(label,floor)],2))
                node_displacements[floor]=dis
                prev=node_displacements.get(floor-1,{})
                ratios=[math.dist(x,prev.get(label,(0.,0.)))/3.048 for label,x in dis.items()]
                floor_chords.append({"floor":floor,"max_elastic_column_chord_ratio":max(ratios)})
            roof=max(math.hypot(*q)*1000 for q in node_displacements[3].values())
            governing=max(loc,key=lambda x:max(abs(x["signed"][j]) for j in (4,5,10,11)))
            best=max((4,5,10,11),key=lambda j:abs(governing["signed"][j]))
            ops.reactions()
            reaction=[sum(ops.nodeReaction(nid[(c[0],0)],j) for c in columns) for j in (1,2,3)]
            applied_force=[sum(q[i] for q in applied) for i in (3,4,5)]
            f_res=max(abs(a+b) for a,b in zip(reaction,applied_force))
            moment_applied=[0.,0.,0.]
            for x,y,z,fx,fy,fz in applied:
                moment_applied[0]+=y*fz-z*fy
                moment_applied[1]+=z*fx-x*fz
                moment_applied[2]+=x*fy-y*fx
            moment_reaction=[0.,0.,0.]
            for c in columns:
                x,y=xy[c[0]]
                n=nid[(c[0],0)]
                rx,ry,rz=[ops.nodeReaction(n,j) for j in (1,2,3)]
                mx,my,mz=[ops.nodeReaction(n,j) for j in (4,5,6)]
                moment_reaction[0]+=y*rz+mx
                moment_reaction[1]+=-x*rz+my
                moment_reaction[2]+=x*ry-y*rx+mz
            m_res=max(abs(a+b) for a,b in zip(moment_applied,moment_reaction))
            if f_res>.001 or m_res>.001:
                ops.wipe()
                raise RuntimeError(f"Global equilibrium failed {mode}/{case}: {f_res:.5g} kN {m_res:.5g} kN.m")
            result={
                "mode":mode,"case":case,"source_physical_frame_members":165,
                "frame_elements_after_source_bay_mesh_subdivision":len(frame),
                "shell_mitc4_elements":len(shell),
                "measured_panel_transverse_load_kN":expected_slab_W*len(PATCH_LEVELS) if case=="GRAVITY" else 0.,
                "assumed_beam_wall_line_load_total_kN":source_wall_W if case=="GRAVITY" else 0.,
                "applied_force_kN_xyz":applied_force,"reaction_kN_xyz":reaction,
                "force_equilibrium_error_kN":f_res,"moment_equilibrium_error_kNm":m_res,
                "roof_horizontal_displacement_mm":roof,
                "max_elastic_column_story_chord_ratio":max(x["max_elastic_column_chord_ratio"] for x in floor_chords),
                "elastic_floor_chord_ratios":floor_chords,
                "governing_frame_segment":governing["id"],
                "governing_signed_end_moment_kNm":governing["signed"][best],
                "governing_signed_component":COMPONENTS[best],
                "frame_local_signed_action_count":len(loc),
                "force_and_moment_equilibrium_pass":True
            }
            if not summary_only:
                result["full_frame_local_signed_actions"]=loc
            cases.append(result)
            ops.wipe()
    assert len(cases)==27
    refs={}
    for case,_,_,_ in specs:
        refs[case]={r["mode"]:r for r in cases if r["case"]==case}
        assert len(refs[case])==3
    comparisons=[]
    for case,r in refs.items():
        a,b,c=[r[k] for k in MODES]
        comparisons.append({
          "case":case,
          "frame_roof_displacement_mm":a["roof_horizontal_displacement_mm"],
          "shell_roof_displacement_mm":b["roof_horizontal_displacement_mm"],
          "rigid_roof_displacement_mm":c["roof_horizontal_displacement_mm"],
          "frame_max_story_chord_ratio":a["max_elastic_column_story_chord_ratio"],
          "shell_max_story_chord_ratio":b["max_elastic_column_story_chord_ratio"],
          "rigid_max_story_chord_ratio":c["max_elastic_column_story_chord_ratio"],
          "frame_signed_governing_end_moment_kNm":a["governing_signed_end_moment_kNm"],
          "shell_signed_governing_end_moment_kNm":b["governing_signed_end_moment_kNm"],
          "rigid_signed_governing_end_moment_kNm":c["governing_signed_end_moment_kNm"]
        })
    return {
      "schema":"jp.structural.g15.gate14.multilevel_bay_shell_wall.v0.1",
      "source_report_bay":"F_G_GRID_1_2_SAMPLE_SLAB_PAGE_55",
      "chosen_assumed_panel_levels":list(PATCH_LEVELS),
      "source_panel_actual_storey_verified":False,
      "source_grid_3d_beam_column_segments":165,
      "subdivided_3d_frame_segments":177,
      "source_grid_column_positions":23,
      "real_shell_type":"OpenSees ShellMITC4 3D 6DOF",
      "shell_elements_across_assumed_levels":4*len(PATCH_LEVELS),
      "shell_panel_thickness_m":SHELL_THICKNESS_M,
      "patch_area_m2":patch_area,
      "patch_total_dead_kN":expected_slab_W*len(PATCH_LEVELS),
      "patch_total_area_m2":patch_area*len(PATCH_LEVELS),
      "source_bay_geometry_repeated_on_real_floor_verified":False,
      "shell_mesh_quads_per_assumed_floor":len(quads),
      "shell_mesh_normals_positive":True,
      "mass_ledger_scope":"G10_EDGE_COMM unchanged for all alternatives; these gravity patch loads are subsets of floor loading, not additions to seismic mass",
      "source_referenced_wall_rate_kN_m":SOURCE_MAIN_WALL_KN_M,
      "assumed_wall_edges_count":len(walls),
      "assumed_wall_length_per_level_m":wall_length,
      "assumed_wall_levels":list(WALL_LEVELS),
      "uniform_beam_wall_line_load_sum_kN":source_wall_W,
      "real_wall_locations_verified":False,
      "shells_represent_complete_building":False,
      "actual_slab_openings_verified":False,
      "shell_self_weight_automatically_applied":False,
      "mass_source_double_count_prevented":"GRAVITY_LOAD_PATCH_SEPARATE_FROM_LATERAL_G10_SEISMIC_WEIGHT_AND_NO_AUTO_ELEMENT_BODY_GRAVITY",
      "floor_seismic_weights_kN":req["floor_weights_kN"],
      "seismic_mass_reconciled":False,
      "P_delta_included":False,
      "site_specific_NBC_compliance":False,
      "true_floor_diaphragm_stiffness_verified":False,
      "source_F3_one_way_shear":"NOT SAFE IN ONE WAY SHEAR",
      "engineering_approval":False,
      "cases":cases,"comparisons":comparisons
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--stiffness",choices=("ULS","SLS","GROSS"),default="ULS")
    parser.add_argument("--full",action="store_true")
    a=parser.parse_args()
    d=solve(a.stiffness,summary_only=not a.full)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(d,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("GATE14_TWO_LEVEL_SHELLMITC4_7_ASSUMED_WALL_BEAMS_27_FE_CASES_HOLD",len(d["cases"]))

if __name__=="__main__":main()
