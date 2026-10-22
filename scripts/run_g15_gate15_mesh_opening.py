#!/usr/bin/env python3
"""Gate15: OpenSees mesh-refinement and hypothetical aperture study.

The only source-backed geometry is the dimensional sample bay F-G/1-2.
The sample is hypothetically repeated on levels 1 and 2 as in Gate14.
Compare compatible 2x2 and 4x4 real ShellMITC4 meshes, then 4x4 with
a hypothetical central 50% span-width by 50% span-height opening.
The opening reduces modelled patch gravity and conditionally subtracts
its 5.13 kPa equivalent from the pre-existing G10 trial floor weights.
This mass delta is NOT source verification: the inclusion of the patch
in that earlier mass ledger has not been established.
P-Delta, NBC drift, physical floor diaphragm, real walls and F3 design
acceptance remain open. CI numerical success is not engineering approval.
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
MODES=("MESH_2X2_FULL","MESH_4X4_FULL","MESH_4X4_CENTER_VOID")
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


def mesh_for(mode, source_xy):
    """Return consistently oriented quads and beam-edge nodes for one sample bay.

    The opening is an explicit purely hypothetical middle 2x2 cells of a
    4x4 grid, 25% of area; avoid even creating its disconnected center node.
    """
    if mode not in MODES:
        raise ValueError("unknown mesh scenario")
    n=2 if mode=="MESH_2X2_FULL" else 4
    opening=mode=="MESH_4X4_CENTER_VOID"
    a=source_xy["F1"];b=source_xy["G1"];c=source_xy["F2"]
    corners={(0,0):"F1",(n,0):"G1",(0,n):"F2",(n,n):"G2"}
    def ident(i,j):
        return corners.get((i,j),f"BAY_{i}_{j}_N{n}")
    positions={}
    for j in range(n+1):
        for i in range(n+1):
            if opening and i==n//2 and j==n//2:continue
            name=ident(i,j)
            positions[name]=(a[0]+(b[0]-a[0])*i/n,
                             a[1]+(c[1]-a[1])*j/n)
    quads=[]
    for j in range(n):
        for i in range(n):
            if opening and i in (1,2) and j in (1,2):
                continue
            names=(ident(i,j),ident(i+1,j),ident(i+1,j+1),ident(i,j+1))
            assert len(set(names))==4
            assert all(x in positions for x in names)
            ps=[positions[x] for x in names]
            twice=sum(ps[k][0]*ps[(k+1)%4][1]-
                       ps[(k+1)%4][0]*ps[k][1] for k in range(4))
            assert twice>0, ("shell normal reversed",mode,names)
            quads.append(names)
    extra={k:v for k,v in positions.items() if k not in ("F1","G1","F2")}
    area=(b[0]-a[0])*(c[1]-a[1])
    active_area=len(quads)*area/(n*n)
    assert math.isclose(area,17.874,abs_tol=1e-8)
    assert len(quads)==(12 if opening else n*n)
    assert math.isclose(active_area/area,.75 if opening else 1.,abs_tol=1e-12)
    assert len(extra)==(6 if n==2 else 21 if opening else 22)
    boundary={name for name,(x,y) in extra.items()
              if (math.isclose(x,a[0],abs_tol=1e-8) or
                  math.isclose(x,b[0],abs_tol=1e-8) or
                  math.isclose(y,a[1],abs_tol=1e-8) or
                  math.isclose(y,c[1],abs_tol=1e-8))}
    assert len(boundary)==(5 if n==2 else 13)
    return {"n":n,"opening":opening,"quads":quads,"extra":extra,
            "active_area_per_level_m2":active_area,
            "full_panel_area_m2":area,"boundary":boundary,
            "source_location_verified":False}

def solve(stiffness="ULS",summary_only=True):
    import openseespy.opensees as ops
    old,study,plan_xy,_,_,patch_area,walls=build_plan()
    mass=next(x for x in study["model_cases"] if x["id"]=="G10_EDGE_COMM")
    base_req=dict(SAMPLE)
    base_req["stiffness"]=stiffness
    base_req["floor_weights_kN"]=mass["floor_weights_kN"]
    columns=old["column_positions_mm"]
    base_ids={p[0]:i*100+1 for i,p in enumerate(columns)}
    level_heights=[z/1000 for z in old["floor_levels_mm"]]
    elastic=base_req["concrete_E_MPa"]*1000.
    shear=elastic/2.4
    beam_crack,column_crack={"GROSS":(1.,1.),"SLS":(.70,.90),"ULS":(.35,.70)}[stiffness]
    mass_polys=study["footprints"]["assumed_per_floor"]
    centers=[centroid(q["scaled_convex_hull_outline_xy_m"]) for q in mass_polys]
    plan=[plan_xy[p[0]] for p in columns]
    lx=max(x for x,y in plan)-min(x for x,y in plan)
    ly=max(y for x,y in plan)-min(y for x,y in plan)
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
        mesh=mesh_for(mode,plan_xy)
        xy={q[0]:plan_xy[q[0]] for q in columns}
        extra=mesh["extra"]
        xy.update(extra)
        quads=mesh["quads"]
        req=dict(base_req)
        # This is an optional *conditional* floor-mass deduction, not a
        # verified correction to ETABS or source G10 mass definitions.
        aperture_dead_kN=(patch_area-mesh["active_area_per_level_m2"])*SOURCE_PANEL_DEAD_KPA
        req["floor_weights_kN"]=[
            mass["floor_weights_kN"][i]-(aperture_dead_kN if i+1 in PATCH_LEVELS else 0.)
            for i in range(3)]
        assert all(v>0 for v in req["floor_weights_kN"])
        req=validate(req)
        esm=equivalent_static_floor_forces(floor_weights_kN=req["floor_weights_kN"],
           floor_heights_m=level_heights[1:],period_seconds=req["T_seconds"],
           design_coefficient=req["C_design"])
        nid={(p[0],k):base_ids[p[0]]+k for p in columns for k in range(4)}
        for i,n in enumerate(extra):
            for level in PATCH_LEVELS:
                nid[(n,level)]=3000+100*level+i
        for case,axis,sign,ecc_sign in specs:
            ops.wipe();ops.model("basic","-ndm",3,"-ndf",6)
            for name,xx,yy,_ in columns:
                for lev,z in enumerate(level_heights):
                    ops.node(nid[(name,lev)],xx/1000.,yy/1000.,z)
                    if lev==0:ops.fix(nid[(name,0)],1,1,1,1,1,1)
            for level in PATCH_LEVELS:
                for name,(xx,yy) in extra.items():
                    ops.node(nid[(name,level)],xx,yy,level_heights[level])
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
                            if name not in mesh["boundary"]:continue
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
            assert len(frame)==(177 if mesh["n"]==2 else 193), (len(frame),mode,case)
            shell=[]
            ops.nDMaterial("ElasticIsotropic",30,elastic,.2)
            ops.section("PlateFiber",31,30,SHELL_THICKNESS_M)
            for level in PATCH_LEVELS:
                for q in quads:
                    tag+=1
                    ops.element("ShellMITC4",tag,*[nid[(n,level)] for n in q],31)
                    shell.append(tag)
            assert len(shell)==len(quads)*len(PATCH_LEVELS)
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
                    # Consistent nodal area load on ACTIVE mesh cells only.
                    # No element body gravity. Missing aperture area is NOT loaded.
                    for q in quads:
                        patch=-SOURCE_PANEL_DEAD_KPA*(patch_area/mesh["n"]**2)/4
                        for label in q:add_node_load(label,level,0.,0.,patch)
                for w in walls:
                    start,end=w["between"]
                    for floor in WALL_LEVELS:
                        for et,length,u,v in per_origin[(start,end,floor)]:
                            ops.eleLoad("-ele",et,"-type","-beamUniform",0.,-SOURCE_MAIN_WALL_KN_M,0.)
                            x,y=xy[u];xx,yy=xy[v]
                            applied.append(((x+xx)/2,(y+yy)/2,level_heights[floor],
                                 0.,0.,-SOURCE_MAIN_WALL_KN_M*length))
            ops.constraints("Plain")
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
                "measured_panel_transverse_load_kN":
                    SOURCE_PANEL_DEAD_KPA*mesh["active_area_per_level_m2"]*len(PATCH_LEVELS)
                    if case=="GRAVITY" else 0.,
                "mesh_subdivisions_per_side":mesh["n"],
                "mesh_active_area_per_level_m2":mesh["active_area_per_level_m2"],
                "mesh_opening_hypothesis":mesh["opening"],
                "conditional_seismic_floor_weights_kN":req["floor_weights_kN"],
                "seismic_weight_deduction_per_assumed_opening_floor_kN":aperture_dead_kN,
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
        coarse,fine,opening=[r[k] for k in MODES]
        diff=abs(coarse["roof_horizontal_displacement_mm"]-fine["roof_horizontal_displacement_mm"])
        denom=max(abs(fine["roof_horizontal_displacement_mm"]),1e-12)
        comparisons.append({
          "case":case,
          "coarse_roof_mm":coarse["roof_horizontal_displacement_mm"],
          "fine_roof_mm":fine["roof_horizontal_displacement_mm"],
          "opening_roof_mm":opening["roof_horizontal_displacement_mm"],
          "coarse_max_chord":coarse["max_elastic_column_story_chord_ratio"],
          "fine_max_chord":fine["max_elastic_column_story_chord_ratio"],
          "opening_max_chord":opening["max_elastic_column_story_chord_ratio"],
          "mesh_2x2_to_4x4_roof_relative_difference_pct":100*diff/denom,
          "coarse_signed_end_moment_kNm":coarse["governing_signed_end_moment_kNm"],
          "fine_signed_end_moment_kNm":fine["governing_signed_end_moment_kNm"],
          "opening_signed_end_moment_kNm":opening["governing_signed_end_moment_kNm"],
          "opening_and_mass_effect_not_isolated":True,
          "refinement_convergence_verified":False})
    return {
      "schema":"jp.structural.g15.gate15.mesh_opening_source_bay.v0.1",
      "source_report_bay":"F_G_GRID_1_2_SAMPLE_SLAB_PAGE_55",
      "source_grid_3d_beam_column_segments":165,
      "source_grid_column_positions":23,
      "assumed_panel_levels":list(PATCH_LEVELS),
      "source_panel_actual_storey_verified":False,
      "models": [
         {"mode":mode,"mesh_n":mesh_for(mode,plan_xy)["n"],
          "opening":mesh_for(mode,plan_xy)["opening"],
          "active_shells":len(mesh_for(mode,plan_xy)["quads"])*len(PATCH_LEVELS),
          "active_area_two_levels_m2":2*mesh_for(mode,plan_xy)["active_area_per_level_m2"],
          "gravity_patch_two_levels_kN":2*mesh_for(mode,plan_xy)["active_area_per_level_m2"]*SOURCE_PANEL_DEAD_KPA}
         for mode in MODES],
      "source_reported_panel_area_m2":patch_area,
      "source_reported_slab_dead_kPa":SOURCE_PANEL_DEAD_KPA,
      "assumed_opening_area_m2_per_level":patch_area*.25,
      "assumed_opening_fraction_of_panel":.25,
      "estimated_conditional_mass_deduction_both_floors_kN":2*patch_area*.25*SOURCE_PANEL_DEAD_KPA,
      "trial_mass_without_aperture_kN":sum(mass["floor_weights_kN"]),
      "trial_mass_with_aperture_kN":sum(mass["floor_weights_kN"])-2*patch_area*.25*SOURCE_PANEL_DEAD_KPA,
      "reported_source_ETABS_seismic_weight_kN":study["source_seismic_W_kN"],
      "source_mass_gap_still_unresolved":True,
      "opening_mass_reduction_only_if_existing_source_mass_included_full_patch":True,
      "opening_geometry_and_structural_trim_verified":False,
      "floor_source_diaphragm_verified":False,
      "wall_locations_verified":False,
      "uniform_beam_wall_line_load_sum_kN":source_wall_W,
      "opening_edge_trim_reinforcement_verified":False,
      "alternative_roof_terrace_geometry_verified":False,
      "full_floor_slab_geometry_verified":False,
      "mesh_convergence_verified":False,
      "mass_source_reconciled":False,
      "P_delta_included":False,
      "engineering_approval":False,
      "source_F3_one_way_shear":"NOT SAFE IN ONE WAY SHEAR",
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
    print("GATE15_MESH_2X2_VS_4X4_AND_HYPOTHETICAL_APERTURE_HOLD",len(d["cases"]))

if __name__=="__main__":main()
