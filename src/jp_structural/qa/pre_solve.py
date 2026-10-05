"""Fail-closed pre-solve QA for the evolving canonical model."""
from __future__ import annotations
import math
from collections import Counter
from typing import Any

def _f(code,status,message,**context): return {"code":code,"status":status,"message":message,"context":context}
def run_pre_solve_qa(model: dict[str,Any], *, near_node_tol: float=1e-6) -> dict[str,Any]:
    findings=[]; units=model.get("units") or {}
    for key in ("force","length"):
        if not units.get(key): findings.append(_f("UNITS_MISSING","FAIL",f"Missing {key} unit",field=key))
    nodes=model.get("nodes",[]); node_ids=[str(n.get("id")) for n in nodes]
    for nid,count in Counter(node_ids).items():
        if count>1: findings.append(_f("DUPLICATE_NODE_ID","FAIL","Duplicate node ID",node_id=nid,count=count))
    coords={}
    for n in nodes:
        nid=str(n.get("id"))
        try: xyz=tuple(float(n[k]) for k in ("x","y","z"))
        except Exception: findings.append(_f("INVALID_NODE_COORDINATE","FAIL","Node coordinates incomplete/non-numeric",node_id=nid)); continue
        if not all(math.isfinite(v) for v in xyz): findings.append(_f("INVALID_NODE_COORDINATE","FAIL","Node coordinate non-finite",node_id=nid)); continue
        coords[nid]=xyz
    cids=list(coords); tol2=near_node_tol**2
    for i,a in enumerate(cids):
        for b in cids[i+1:]:
            d2=sum((p-q)**2 for p,q in zip(coords[a],coords[b]))
            if d2==0: findings.append(_f("COINCIDENT_NODES","WARNING","Distinct node IDs share coordinates",node_a=a,node_b=b))
            elif d2<=tol2: findings.append(_f("NEAR_DUPLICATE_NODES","WARNING","Nodes are within tolerance",node_a=a,node_b=b,distance=math.sqrt(d2)))
    materials={str(m.get("id") or m.get("name")):m for m in model.get("materials",[])}
    sections={str(s.get("id") or s.get("name")):s for s in model.get("sections",model.get("frame_sections",[]))}
    used=set()
    for member in model.get("frames",model.get("frame_members",[])):
        mid=str(member.get("id")); ni=str(member.get("i_node") or member.get("i")); nj=str(member.get("j_node") or member.get("j"))
        if ni not in coords or nj not in coords: findings.append(_f("MEMBER_NODE_REFERENCE","FAIL","Member references missing node",member_id=mid,i_node=ni,j_node=nj)); continue
        used.update((ni,nj))
        if ni==nj or math.dist(coords[ni],coords[nj])<=near_node_tol: findings.append(_f("ZERO_LENGTH_MEMBER","FAIL","Member length zero/near-zero",member_id=mid))
        sec=member.get("section") or member.get("section_id")
        if sec and str(sec) not in sections: findings.append(_f("MISSING_SECTION","FAIL","Member references missing section",member_id=mid,section=sec))
    for sid,s in sections.items():
        mat=s.get("material") or s.get("material_id")
        if mat and str(mat) not in materials: findings.append(_f("MISSING_MATERIAL","FAIL","Section references missing material",section_id=sid,material=mat))
    for nid in sorted(set(coords)-used): findings.append(_f("ORPHAN_NODE","WARNING","Node not referenced by frame member",node_id=nid))
    patterns={str(p.get("id") or p.get("name")) for p in model.get("load_patterns",[])}
    for item in (model.get("mass_source") or {}).get("load_factors",[]):
        pat=str(item.get("pattern") or item.get("load_pattern_id"))
        if patterns and pat not in patterns: findings.append(_f("MASS_PATTERN_REFERENCE","FAIL","Mass source references missing load pattern",pattern=pat))
    if not model.get("design_basis"): findings.append(_f("DESIGN_BASIS_UNRESOLVED","UNRESOLVED","Design basis/code edition not normalized"))
    order={"PASS":0,"WARNING":1,"UNRESOLVED":2,"FAIL":3}; worst=max((order[x["status"]] for x in findings),default=0); status=next(k for k,v in order.items() if v==worst)
    return {"status":status,"blocking":status in {"FAIL","UNRESOLVED"},"summary":{s:sum(x["status"]==s for x in findings) for s in order},"findings":findings}
