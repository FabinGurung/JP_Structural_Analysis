"""R5 bounded source-defined area/line geometry -> conservative nodal gravity + mass.

This is NOT a shell, tributary solver, distributed beam FEM action, wall stiffness
model, in-plane diaphragm, automatic self-weight or code live-load selector.
All pressures, participation factors, node shares and geometry are explicit.
A uniform line/area gravity load's resultant is preserved; member-end moments
for *true distributed loading* require dedicated element-load integration later.
"""
from __future__ import annotations
from collections.abc import Mapping, Sequence
import hashlib
import json
import math

from jp_structural.solvers.native.load_mass_assembly import (
    allocate_loads_to_nodes, LoadAssemblyError
)

class GeometryLoadError(ValueError):
    """Invalid or unverifiable source geometry or load provenance."""

def _id(value, field):
    if not isinstance(value,str) or not value.strip():
        raise GeometryLoadError(field+" must be a nonempty source ID")
    return value

def _positive(value, field, *, zero=False):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise GeometryLoadError(field+" must be finite numeric")
    if value<0 if zero else value<=0:
        raise GeometryLoadError(field+" must be "+("nonnegative" if zero else "positive"))
    return float(value)

def _point(node):
    try:
        xyz=tuple(_positive(node[k],k,zero=True) if False else float(node[k]) for k in ("x","y","z"))
    except (KeyError,TypeError,ValueError,OverflowError) as e:
        raise GeometryLoadError("node x/y/z required") from e
    if any(not math.isfinite(x) for x in xyz):
        raise GeometryLoadError("nonfinite model geometry")
    return xyz

def _cross(a,b,c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])

def _segments_intersect(a,b,c,d):
    eps=1e-10
    oa,ob,oc,od=_cross(a,b,c),_cross(a,b,d),_cross(c,d,a),_cross(c,d,b)
    if (oa>eps and ob < -eps or oa < -eps and ob>eps) and (
         oc>eps and od < -eps or oc < -eps and od>eps):return True
    def on_line(p,q,r):
        return abs(_cross(p,q,r))<=eps and min(p[0],q[0])-eps<=r[0]<=max(p[0],q[0])+eps and min(p[1],q[1])-eps<=r[1]<=max(p[1],q[1])+eps
    return any((on_line(a,b,c),on_line(a,b,d),on_line(c,d,a),on_line(c,d,b)))

def polygon_area(points):
    if len(points)<3 or len(points)>100:
        raise GeometryLoadError("panel requires 3..100 ordered boundary nodes")
    if any(math.dist(points[i],points[(i+1)%len(points)])<=1e-8 for i in range(len(points))):
        raise GeometryLoadError("collapsed panel edge")
    for i in range(len(points)):
        for j in range(i+1,len(points)):
            if i==j or j==(i+1)%len(points) or i==(j+1)%len(points):
                continue
            if _segments_intersect(points[i],points[(i+1)%len(points)],
                                   points[j],points[(j+1)%len(points)]):
                raise GeometryLoadError("self-intersecting panel boundary")
    signed=math.fsum(points[i][0]*points[(i+1)%len(points)][1]-
                     points[(i+1)%len(points)][0]*points[i][1]
                     for i in range(len(points)))/2
    if not math.isfinite(signed) or abs(signed)<1e-8:
        raise GeometryLoadError("zero/invalid panel horizontal area")
    return abs(signed)

def _shares(rows,allowed,key):
    if not isinstance(rows,list) or not rows:
        raise GeometryLoadError(key+": explicit nodal load shares required")
    seen=set(); result=[]
    for x in rows:
        if not isinstance(x,Mapping):raise GeometryLoadError(key+": share object required")
        nid=_id(x.get("node_id"),"share.node_id")
        if nid in seen or nid not in allowed:raise GeometryLoadError(key+": duplicate or unknown/out-of-region node")
        seen.add(nid)
        fraction=_positive(x.get("fraction"),"fraction",zero=True)
        if fraction>1:raise GeometryLoadError(key+": fraction over one")
        result.append({"node_id":nid,"fraction":fraction})
    if not math.isclose(math.fsum(x["fraction"] for x in result),1.,rel_tol=1e-10,abs_tol=1e-10):
        raise GeometryLoadError(key+": load shares must total exactly one")
    return result

def _load_rows(model, load_items):
    if not isinstance(model,Mapping) or model.get("units")!={"force":"kN","length":"m","time":"s","mass":"kN*s^2/m"}:
        raise GeometryLoadError("canonical model kN/m/s/mass units required")
    if any(model.get(k) for k in ("joint_loads","frame_loads","area_loads","load_patterns","load_cases","load_combinations","mass_source","nodal_masses","shell_elements","end_releases","rigid_offsets","diaphragms")):
        raise GeometryLoadError("existing loads/mass/shell/diaphragm or offsets unsupported: double counting")
    nodes=model.get("nodes")
    if not isinstance(nodes,list) or not nodes:raise GeometryLoadError("canonical source nodes required")
    nd={}
    for n in nodes:
        if not isinstance(n,Mapping):raise GeometryLoadError("node object required")
        nid=_id(n.get("id"),"node.id")
        if nid in nd:raise GeometryLoadError("duplicate node ID")
        _id(n.get("storey_id"),"node.storey_id")
        nd[nid]=n
        _point(n)
    members=model.get("frame_members",[])
    member_map={}
    for m in members:
        mid=_id(m.get("id"),"frame.id")
        if mid in member_map:raise GeometryLoadError("duplicate member ID")
        if m.get("i_node") not in nd or m.get("j_node") not in nd:
            raise GeometryLoadError("member references unknown node")
        member_map[mid]=m
    if not isinstance(load_items,list) or not load_items or len(load_items)>10000:
        raise GeometryLoadError("bounded nonempty source load objects required")
    sourcekeys=set(); ids=set();rows=[];audit=[]
    for item in load_items:
        if not isinstance(item,Mapping):raise GeometryLoadError("load object required")
        cid=_id(item.get("id"),"load.id")
        key=_id(item.get("source_key"),"load.source_key")
        category=_id(item.get("load_category"),"load.load_category")
        case=_id(item.get("case_id"),"load.case_id")
        evidence=_id(item.get("provenance"),"load.provenance")
        if cid in ids or key in sourcekeys:
            raise GeometryLoadError("duplicate load ID or source key")
        ids.add(cid);sourcekeys.add(key)
        f=_positive(item.get("participation_factor"),"participation_factor",zero=True)
        if f>1:raise GeometryLoadError("participation factor above 1")
        kind=item.get("type")
        if kind=="UNIFORM_PANEL_PRESSURE":
            boundary=item.get("boundary_node_ids")
            if not isinstance(boundary,list) or len(set(boundary))!=len(boundary) or any(n not in nd for n in boundary):
                raise GeometryLoadError("unknown or repeated panel boundary node")
            xyz=[_point(nd[n]) for n in boundary]
            if max(p[2] for p in xyz)-min(p[2] for p in xyz)>1e-8:
                raise GeometryLoadError("panel is not horizontal and coplanar")
            if len({nd[n]["storey_id"] for n in boundary})!=1:
                raise GeometryLoadError("panel boundary must belong to same floor")
            area=polygon_area([(x,y) for x,y,_ in xyz])
            intensity=_positive(item.get("pressure_kPa"),"panel pressure")
            total=area*intensity
            share=_shares(item.get("node_shares"),set(boundary),cid)
            geometry={"horizontal_area_m2":area,"pressure_kPa":intensity,"boundary_node_ids":boundary}
        elif kind=="UNIFORM_FRAME_LINE_LOAD":
            mid=_id(item.get("member_id"),"member_id")
            if mid not in member_map:raise GeometryLoadError("line source member not found")
            member=member_map[mid]
            end_ids=(member["i_node"],member["j_node"])
            a,b=_point(nd[end_ids[0]]),_point(nd[end_ids[1]])
            if abs(a[2]-b[2])>1e-8:
                raise GeometryLoadError("vertical/sloped member line gravity source unsupported")
            length=math.dist(a,b)
            if length<=1e-8:raise GeometryLoadError("line length invalid")
            intensity=_positive(item.get("intensity_kN_m"),"line intensity")
            total=length*intensity
            share=_shares(item.get("node_shares"),set(end_ids),cid)
            if set(x["node_id"] for x in share)!=set(end_ids) or any(
                 not math.isclose(x["fraction"],0.5,rel_tol=0,abs_tol=1e-10) for x in share):
                raise GeometryLoadError("uniform line load lumping requires equal 50/50 member ends")
            geometry={"member_id":mid,"length_m":length,"intensity_kN_m":intensity,
                      "equivalent_lumping":"HALF_TO_EACH_END_DOES_NOT_PRESERVE_DISTRIBUTED_MEMBER_MOMENTS"}
        else:
            raise GeometryLoadError("unsupported source load geometry type")
        comp={"id":cid,"source_key":key,"load_category":category,
              "downward_load_kN":total,"participation_factor":f,
              "node_shares":share}
        rows.append((case,comp))
        audit.append({"id":cid,"source_key":key,"load_case_id":case,"kind":kind,
                      "category":category,"gravity_weight_kN":total,
                      "seismic_eligible_weight_kN":f*total,"geometry":geometry,
                      "source_provenance":evidence,"node_shares":share})
    return nd,rows,audit

def assemble_geometry_source_loads(*,model:dict,loads:list,gravity_m_s2:float)->dict:
    nd,by_case,audit=_load_rows(model,loads)
    gravity=_positive(gravity_m_s2,"gravity_m_s2")
    # Explicit source nodes, including every source load receiver, go to the
    # existing audited allocator. No automatic geometric tributaries invented.
    receiver={x["node_id"] for _,comp in by_case for x in comp["node_shares"]}
    source_nodes=[{"node_id":n,"storey_id":nd[n]["storey_id"],
                   "x_m":_point(nd[n])[0],"y_m":_point(nd[n])[1],"z_m":_point(nd[n])[2]}
                  for n in sorted(receiver)]
    components=[comp for _,comp in by_case]
    try:
        assembly=allocate_loads_to_nodes(source_nodes,components,gravity)
    except LoadAssemblyError as e:
        raise GeometryLoadError(str(e)) from e
    cases={}
    for case,comp in by_case:
        part=cases.setdefault(case,{})
        for share in comp["node_shares"]:
            nid=share["node_id"]
            part[nid]=part.get(nid,0.)+comp["downward_load_kN"]*share["fraction"]
    check=math.fsum(math.fsum(nodes.values()) for nodes in cases.values())
    if not math.isclose(check,assembly["total_gravity_load_kN"],rel_tol=1e-10,abs_tol=1e-8):
        raise GeometryLoadError("load-case decomposition not conservative")
    return {"schema":"jp.structural.r5.geometry_load_assembly.v0.1",
      "case_id":_id(model.get("model_id"),"model_id"),
      "model_sha256":hashlib.sha256(json.dumps(model,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest(),
      "source_case_components":audit,"source_component_count":len(audit),
      "load_case_nodal_gravity_kN":{k:[{"node_id":nid,"downward_load_kN":v}
          for nid,v in sorted(nodes.items()) if v>0] for k,nodes in sorted(cases.items())},
      "audited_assembly":assembly,
      "case_total_vertical_kN":{case:math.fsum(v.values()) for case,v in sorted(cases.items())},
      "gravity_force_conservative":True,"seismic_mass_conservative":True,
      "derived_distributed_member_end_force_diagrams":False,
      "geometry_is_a_loaded_region_not_shell_FE":True,
      "load_participation_and_nodal_shares_user_source_supplied":True,
      "engineering_approval":False}
