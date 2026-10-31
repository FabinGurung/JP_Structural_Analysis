"""R5.4 explicitly one-way, simply-supported rectangular panel -> edge beam UDL.

A bounded *source-declared* tributary model, not a slab shell FEM or inferred
two-way slab distribution. For a uniformly pressured rectangular panel spanning
between opposite edge beams, each beam takes pressure * transverse_span / 2,
as a native horizontal-beam uniform element load. The allocation conserves
Fz AND first moments about global X/Y. The original audited load/mass registry
is reused untouched; only its GRAVITY application changes, not seismic mass.
"""
from __future__ import annotations
import hashlib
import json
import math
from collections.abc import Mapping

from jp_structural.solvers.native.geometry_load_intake import (
    assemble_geometry_source_loads,GeometryLoadError,
)

class PanelRoutingError(ValueError):
    pass

def _id(x,field):
    if not isinstance(x,str) or not x.strip():
        raise PanelRoutingError(field+" requires nonempty string")
    return x

def _num(x,field):
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x):
        raise PanelRoutingError(field+" requires finite numeric")
    return float(x)

def _point(n):
    return tuple(_num(n[k],"node."+k) for k in ("x","y","z"))

def _near(a,b):
    return math.isclose(a,b,abs_tol=1e-8,rel_tol=0)

def _corner_tuple(points):
    xx=[p[0] for p in points];yy=[p[1] for p in points]
    xlo,xhi=min(xx),max(xx);ylo,yhi=min(yy),max(yy)
    if not (xhi-xlo>1e-8 and yhi-ylo>1e-8):
        raise PanelRoutingError("rectangular panel requires nonzero two-dimensional span")
    expected={(xlo,ylo),(xhi,ylo),(xhi,yhi),(xlo,yhi)}
    got={(x,y) for x,y,_ in points}
    if len(points)!=4 or len(got)!=4 or got!=expected:
        raise PanelRoutingError("only source-declared axis-aligned four-corner rectangle supported")
    if max(p[2] for p in points)-min(p[2] for p in points)>1e-8:
        raise PanelRoutingError("only horizontal panels supported")
    return xlo,xhi,ylo,yhi

def _beam(model_nodes,frame,member_id):
    if member_id not in frame:raise PanelRoutingError("unknown edge beam")
    row=frame[member_id]
    if row.get("member_type")!="BEAM":
        raise PanelRoutingError("tributary recipient must be explicit BEAM")
    if any(row.get(k) is not None for k in ("local_axis_vector","local_axis_angle","orientation")):
        raise PanelRoutingError("custom local axis needs separate beam load mapper")
    a,b=_point(model_nodes[row["i_node"]]),_point(model_nodes[row["j_node"]])
    if not _near(a[2],b[2]):raise PanelRoutingError("inclined receiving beam unsupported")
    span=math.dist(a,b)
    if span<=1e-8:raise PanelRoutingError("receiving beam length invalid")
    return a,b,span

def transfer_one_way_panels(*,model:dict,loads:list,routes:list,gravity_m_s2:float)->dict:
    """Derive and audit gravity beam loads and keep source-defined seismic mass.

    routes: [{panel_source_id, span_direction:"X"|"Y",
              edge_beam_member_ids:[beam_min,beam_max],
              transfer_model:"ONE_WAY_SIMPLY_SUPPORTED"}].
    span_direction is the one-way *span* (between support beams); receiving
    beams run perpendicular to span_direction. Structural slab stiffness,
    reinforcement and actual two-way action are not modeled.
    """
    audit=assemble_geometry_source_loads(model=model,loads=loads,gravity_m_s2=gravity_m_s2)
    if not isinstance(routes,list) or not routes:raise PanelRoutingError("explicit nonempty one-way routes required")
    nd={n["id"]:n for n in model["nodes"]}
    members={m["id"]:m for m in model["frame_members"]}
    if len(nd)!=len(model["nodes"]) or len(members)!=len(model["frame_members"]):
        raise PanelRoutingError("duplicate canonical geometry identities")
    load_by_id={r["id"]:r for r in loads}
    source_by_id={x["id"]:x for x in audit["source_case_components"]}
    panel_ids={x["id"] for x in audit["source_case_components"]
               if x["kind"]=="UNIFORM_PANEL_PRESSURE"}
    route_ids=set()
    element_sources=[]
    allocations=[]
    origin=[]  # each raw physical source exists once, including wall loads
    for route in routes:
        if not isinstance(route,Mapping) or set(route)!={
                "panel_source_id","span_direction","edge_beam_member_ids","transfer_model"}:
            raise PanelRoutingError("route schema missing/unsupported")
        rid=_id(route["panel_source_id"],"panel_source_id")
        if rid in route_ids or rid not in panel_ids:
            raise PanelRoutingError("duplicate/unknown routed panel load")
        route_ids.add(rid)
        if route["transfer_model"]!="ONE_WAY_SIMPLY_SUPPORTED":
            raise PanelRoutingError("unverified slab load transfer model")
        direction=route["span_direction"]
        if direction not in ("X","Y"):
            raise PanelRoutingError("explicit X/Y one-way span direction required")
        bs=route["edge_beam_member_ids"]
        if not isinstance(bs,list) or len(bs)!=2 or len(set(bs))!=2:
            raise PanelRoutingError("two distinct opposite edge beam IDs required")
        source=load_by_id[rid]
        geometry=source_by_id[rid]["geometry"]
        corners=geometry["boundary_node_ids"]
        points=[_point(nd[k]) for k in corners]
        x0,x1,y0,y1=_corner_tuple(points)
        area=(x1-x0)*(y1-y0)
        if not _near(geometry["horizontal_area_m2"],area):
            raise PanelRoutingError("routed rectangle differs from audited source polygon")
        support_len=(y1-y0 if direction=="X" else x1-x0)
        beam_len=(x1-x0 if direction=="X" else y1-y0)
        minedge,maxedge=(x0,x1) if direction=="X" else (y0,y1)
        centroid=((x0+x1)/2,(y0+y1)/2,(points[0][2]))
        source_resultant=source_by_id[rid]["gravity_weight_kN"]
        pressure=geometry["pressure_kPa"]
        if not math.isclose(pressure*area,source_resultant,rel_tol=1e-10,abs_tol=1e-8):
            raise PanelRoutingError("source pressure area disagreement")
        distributed=[]
        for index,mid in enumerate(bs):
            _id(mid,"edge_beam_member_id")
            a,b,L=_beam(nd,members,mid)
            along=[a[0],b[0]] if direction=="Y" else [a[1],b[1]]
            other=[a[1],b[1]] if direction=="Y" else [a[0],b[0]]
            far=(y0,y1) if direction=="X" else (x0,x1)
            if (not all(_near(v,far[index]) for v in other) or
                not _near(min(along),minedge) or
                not _near(max(along),maxedge) or
                not _near(L,beam_len) or
                not _near(a[2],centroid[2])):
                raise PanelRoutingError("edge beam must coincide with corresponding opposite full panel side")
            tributary_width=support_len/2
            w=pressure*tributary_width
            resultant=w*L
            entry={
                 "id":rid+"__TRIB__"+mid,
                 "source_key":source["source_key"]+"::TRIB::"+mid,
                 "member_id":mid,
                 "downward_kN_per_m":w,
                 "case_id":source["case_id"],
                 "source_panel_id":rid,
                 "area_tributary_m2":L*tributary_width,
                 "downward_resultant_kN":resultant,
                 "line_centroid_xyz_m":[(a[i]+b[i])/2 for i in range(3)],
                 "source_pressure_kPa":pressure,
                 "source_provenance":source["provenance"],
            }
            distributed.append(entry)
            element_sources.append(entry)
        total=math.fsum(x["downward_resultant_kN"] for x in distributed)
        if not _near(total,source_resultant):
            raise PanelRoutingError("panel load lost or duplicated during tributary transfer")
        for axis in (0,1):
            actual=math.fsum(x["downward_resultant_kN"]*x["line_centroid_xyz_m"][axis]
                             for x in distributed)
            target=source_resultant*centroid[axis]
            if not math.isclose(actual,target,rel_tol=1e-10,abs_tol=1e-7):
                raise PanelRoutingError("routed panel first moment not conserved")
        allocations.append({
             "panel_source_id":rid,"transfer_model":"ONE_WAY_SIMPLY_SUPPORTED",
             "span_direction":direction,
             "support_spacing_m":support_len,
             "loaded_beam_length_m":beam_len,
             "source_panel_area_m2":area,
             "source_total_kN":source_resultant,
             "panel_centroid_xyz_m":list(centroid),
             "support_beam_ids":bs,
             "beam_loads":distributed,
             "gravity_force_and_plan_first_moments_conserved":True,
             "shell_FEM_or_two_way_distribution_evaluated":False,
        })
    if route_ids!=panel_ids:
        raise PanelRoutingError("all source panel pressure cases require one explicit route")
    for source in audit["source_case_components"]:
        origin.append((source["id"],source["gravity_weight_kN"]))
        if source["kind"]=="UNIFORM_PANEL_PRESSURE":
            continue
        if source["kind"]!="UNIFORM_FRAME_LINE_LOAD":
            raise PanelRoutingError("source type not implemented as member load")
        geometry=source["geometry"]
        mid=geometry["member_id"]
        a,b,L=_beam(nd,members,mid)
        if not math.isclose(L,geometry["length_m"],rel_tol=1e-10,abs_tol=1e-8):
            raise PanelRoutingError("source wall/member span differs")
        element_sources.append({
           "id":source["id"],"source_key":source["source_key"],
           "member_id":mid,"downward_kN_per_m":geometry["intensity_kN_m"],
           "case_id":source["load_case_id"],"source_panel_id":None,
           "area_tributary_m2":None,
           "downward_resultant_kN":source["gravity_weight_kN"],
           "line_centroid_xyz_m":[(a[i]+b[i])/2 for i in range(3)],
           "source_pressure_kPa":None,
           "source_provenance":load_by_id[source["id"]]["provenance"]})
    if len({x["id"] for x in element_sources})!=len(element_sources) or len({
        x["source_key"] for x in element_sources})!=len(element_sources):
        raise PanelRoutingError("member load output IDs/physical source keys not unique")
    sum_element=math.fsum(x["downward_resultant_kN"] for x in element_sources)
    source_total=audit["audited_assembly"]["total_gravity_load_kN"]
    if not math.isclose(sum_element,source_total,rel_tol=1e-10,abs_tol=1e-7):
        raise PanelRoutingError("global member load force not conservative")
    source_gravity={s["id"]:s["gravity_weight_kN"] for s in audit["source_case_components"]}
    assigned={name:0. for name in source_gravity}
    for x in element_sources:
        name=x["source_panel_id"] or x["id"]
        if name not in assigned:raise PanelRoutingError("member load without authoritative source")
        assigned[name]+=x["downward_resultant_kN"]
    for k,val in source_gravity.items():
        if not math.isclose(val,assigned[k],rel_tol=1e-10,abs_tol=1e-8):
            raise PanelRoutingError("individual source conservation failed")
    cases={}
    for x in element_sources:
        cases.setdefault(x["case_id"],[]).append({
            "id":x["id"],"source_key":x["source_key"],
            "member_id":x["member_id"],
            "downward_kN_per_m":x["downward_kN_per_m"]})
    report={
       "schema":"jp.structural.r5.one_way_panel_beam_routes.v0.1",
       "source_model_id":model["model_id"],
       "source_model_SHA256":audit["model_sha256"],
       "source_assembly":audit["audited_assembly"],
       "source_total_gravity_kN":source_total,
       "source_seismic_weight_kN":audit["audited_assembly"]["total_seismic_weight_kN"],
       "panel_source_count":len(panel_ids),"panel_route_count":len(allocations),
       "panel_edge_element_load_count":sum(len(x["beam_loads"]) for x in allocations),
       "source_wall_element_count":len(element_sources)-sum(len(x["beam_loads"]) for x in allocations),
       "total_native_element_gravity_kN":sum_element,
       "panel_routes":allocations,"member_element_load_sources":element_sources,
       "native_element_loads_by_case":{k:v for k,v in sorted(cases.items())},
       "each_physical_source_conserved":True,"global_gravity_force_conserved":True,
       "gravity_plan_first_moments_conserved":True,
       "seismic_mass_assumptions_reused_unchanged":True,
       "panel_shell_stiffness_modeled":False,
       "actual_building_accepted":False,"engineering_approval":False,
       "limitations":["Only axis-aligned rectangular horizontal panels and two opposing full-edge beams.",
         "ONE_WAY_SIMPLY_SUPPORTED transfer is user-selected and is not determined from panel aspect ratio, stiffness, openings or two-way action.",
         "Seismic mass nodal allocation remains the original independently audited source assumption; it is not recalculated from gravity support reactions.",
         "Distributed member loading uses the existing 3D elastic frame solver, not a shell/plate element."],
    }
    report["source_route_input_SHA256"]=hashlib.sha256(json.dumps({
         "model":model,"loads":loads,"routes":routes,"gravity":gravity_m_s2},
         sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    return report
