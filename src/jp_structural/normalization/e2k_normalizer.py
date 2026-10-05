#!/usr/bin/env python3
"""Normalize structural meaning from ETABS .e2k without solving it.

The normalizer expands story-based ETABS assignments into explicit 3D node,
frame and area instances. Ambiguous source semantics are preserved, not guessed.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

Q = r'"((?:[^"]|"")*)"'

def qs(line: str) -> list[str]:
    return [x.replace('""','"') for x in re.findall(Q,line)]

def qafter(key: str, line: str):
    m=re.search(rf'\b{re.escape(key)}\s+{Q}',line)
    return m.group(1).replace('""','"') if m else None

def nafter(key: str,line: str):
    m=re.search(rf'\b{re.escape(key)}\s+([-+0-9.eE]+)',line)
    if not m: return None
    try: return float(m.group(1))
    except ValueError: return None

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
    return h.hexdigest()

def split_sections(text:str):
    out={}; cur=None
    for raw in text.splitlines():
        if raw.startswith("$"):
            cur=raw[1:].strip(); out.setdefault(cur,[])
        elif cur is not None:
            out[cur].append(raw)
    return out

def normalize(path:Path):
    raw=path.read_bytes()
    text=raw.decode("utf-8",errors="replace")
    sec=split_sections(text)
    nb=lambda n:[x.strip() for x in sec.get(n,[]) if x.strip()]
    warnings=[]

    topdown=[]
    for line in nb("STORIES - IN SEQUENCE FROM TOP"):
        q=qs(line)
        if q: topdown.append({"name":q[0],"height":nafter("HEIGHT",line),"elevation":nafter("ELEV",line)})
    bottom=list(reversed(topdown))
    elevations={}; z=None
    for s in bottom:
        if s["elevation"] is not None: z=s["elevation"]
        elif z is not None: z += s["height"] or 0.0
        else: raise ValueError("Cannot establish base story elevation.")
        elevations[s["name"]]=z
    bottom_names=[s["name"] for s in bottom]
    lower={n:(bottom_names[i-1] if i else None) for i,n in enumerate(bottom_names)}

    points={}
    for line in nb("POINT COORDINATES"):
        q=qs(line)
        rest=line.split('"',2)[-1]
        vals=[float(x) for x in re.findall(r'[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?',rest)]
        if q and len(vals)>=2: points[q[0]]=(vals[0],vals[1])


    materials={}
    for line in nb("MATERIAL PROPERTIES"):
        q=qs(line)
        if not q or not line.startswith("MATERIAL "): continue
        m=materials.setdefault(q[0],{"name":q[0]})
        for k,out in [("TYPE","type"),("GRADE","grade")]:
            v=qafter(k,line)
            if v is not None: m[out]=v
        for k,out in [("WEIGHTPERVOLUME","weight_per_volume"),("E","E"),("U","poisson"),
                      ("A","thermal_alpha"),("FC","fc"),("FY","fy"),("FU","fu")]:
            v=nafter(k,line)
            if v is not None: m[out]=v

    frame_sections={}
    for line in nb("FRAME SECTIONS"):
        q=qs(line)
        if not q or not line.startswith("FRAMESECTION "): continue
        s=frame_sections.setdefault(q[0],{"name":q[0]})
        for k,out in [("MATERIAL","material"),("SHAPE","shape")]:
            v=qafter(k,line)
            if v is not None: s[out]=v
        for k,out in [("D","depth"),("B","width"),("I2MOD","i2_modifier"),("I3MOD","i3_modifier"),
                      ("AMOD","area_modifier"),("JMOD","torsion_modifier")]:
            v=nafter(k,line)
            if v is not None: s[out]=v

    slab_properties={}
    for line in nb("SLAB PROPERTIES"):
        q=qs(line)
        if not q or not line.startswith("SHELLPROP "): continue
        s=slab_properties.setdefault(q[0],{"name":q[0]})
        for k,out in [("MATERIAL","material"),("MODELINGTYPE","modeling_type"),("SLABTYPE","slab_type"),
                      ("PROPTYPE","property_type")]:
            v=qafter(k,line)
            if v is not None: s[out]=v
        v=nafter("SLABTHICKNESS",line)
        if v is not None: s["thickness"]=v

    load_patterns=[]
    for line in nb("LOAD PATTERNS"):
        if line.startswith("LOADPATTERN "):
            q=qs(line)
            load_patterns.append({"name":q[0] if q else None,"type":qafter("TYPE",line),
                                  "self_weight":nafter("SELFWEIGHT",line)})

    point_assign={}
    for line in nb("POINT ASSIGNS"):
        q=qs(line)
        if len(q)>=2:
            point_assign[(q[0],q[1])]={"diaphragm":qafter("DIAPH",line),
                "restraint":qafter("RESTRAINT",line),"user_joint":qafter("USERJOINT",line)}

    line_conn={}
    for line in nb("LINE CONNECTIVITIES"):
        q=qs(line); m=re.search(r'^\s*LINE\s+'+Q+r'\s+(\w+)',line)
        if len(q)>=3 and m:
            line_conn[q[0]]={"source_id":q[0],"type":m.group(2),"i":q[1],"j":q[2],"raw":line}

    area_conn={}
    for line in nb("AREA CONNECTIVITIES"):
        q=qs(line); m=re.search(r'^\s*AREA\s+'+Q+r'\s+(\w+)\s+(\d+)',line)
        if q and m:
            n=int(m.group(3)); pids=q[1:1+n]
            spans=list(re.finditer(Q,line))
            tail=line[spans[n].end():].strip() if len(spans)>n else ""
            area_conn[q[0]]={"source_id":q[0],"type":m.group(2),"points":pids,
                             "connectivity_tail":tail,"raw":line}
            if any(t not in {"0","0.0"} for t in tail.split()):
                warnings.append({"code":"NONZERO_AREA_CONNECTIVITY_TAIL",
                    "source_id":q[0],"tail":tail,"severity":"hold_for_translator"})

    nodes={}
    def node(pid,story,reason):
        if pid not in points:
            warnings.append({"code":"MISSING_POINT_COORD","point":pid,"story":story,"reason":reason}); return None
        if story not in elevations:
            warnings.append({"code":"UNKNOWN_STORY","point":pid,"story":story,"reason":reason}); return None
        key=f"{story}::{pid}"
        if key not in nodes:
            a=point_assign.get((pid,story),{})
            nodes[key]={"id":key,"source_point_id":pid,"story":story,
                "x":points[pid][0],"y":points[pid][1],"z":elevations[story],
                "diaphragm":a.get("diaphragm"),"restraint":a.get("restraint"),
                "user_joint":a.get("user_joint")}
        return key

    for pid,story in point_assign: node(pid,story,"point_assignment")

    line_assign=[]; assigned_lines=set()
    for line in nb("LINE ASSIGNS"):
        q=qs(line)
        if len(q)>=2:
            a={"source_id":q[0],"story":q[1],"section":qafter("SECTION",line),"raw":line}
            line_assign.append(a); assigned_lines.add((q[0],q[1]))
    frames=[]
    for a in line_assign:
        c=line_conn.get(a["source_id"])
        if not c:
            warnings.append({"code":"MISSING_LINE_CONNECTIVITY","source_id":a["source_id"],"story":a["story"]}); continue
        if c["type"]=="COLUMN":
            below=lower.get(a["story"])
            if below is None:
                warnings.append({"code":"COLUMN_WITHOUT_LOWER_STORY","source_id":a["source_id"],"story":a["story"]}); continue
            ni=node(c["i"],a["story"],"column_top")
            nj=node(c["j"],below,"column_bottom")
        else:
            ni=node(c["i"],a["story"],"line_i")
            nj=node(c["j"],a["story"],"line_j")
        frames.append({"id":f'{a["story"]}::{a["source_id"]}',"source_id":a["source_id"],
            "story":a["story"],"type":c["type"],"i_node":ni,"j_node":nj,"section":a["section"]})

    area_assign=[]; assigned_areas=set()
    for line in nb("AREA ASSIGNS"):
        q=qs(line)
        if len(q)>=2:
            a={"source_id":q[0],"story":q[1],"section":qafter("SECTION",line),
               "diaphragm":qafter("DIAPH",line),"add_restraint":qafter("ADDRESTRAINT",line),"raw":line}
            area_assign.append(a); assigned_areas.add((q[0],q[1]))
    areas=[]
    for a in area_assign:
        c=area_conn.get(a["source_id"])
        if not c:
            warnings.append({"code":"MISSING_AREA_CONNECTIVITY","source_id":a["source_id"],"story":a["story"]}); continue
        nn=[node(pid,a["story"],"area") for pid in c["points"]]
        areas.append({"id":f'{a["story"]}::{a["source_id"]}',"source_id":a["source_id"],
            "story":a["story"],"type":c["type"],"nodes":nn,"section":a["section"],
            "diaphragm":a["diaphragm"],"add_restraint":a["add_restraint"],
            "connectivity_tail":c["connectivity_tail"]})

    def load_record(line,area=False):
        q=qs(line); rec={"source_id":q[0] if q else None,"story":q[1] if len(q)>1 else None,
            "type":qafter("TYPE",line),"direction":qafter("DIR",line),"load_pattern":qafter("LC",line),
            "fval":nafter("FVAL",line),"fstart":nafter("FSTART",line),"fend":nafter("FEND",line),
            "rdstart":nafter("RDSTART",line),"rdend":nafter("RDEND",line),"raw":line}
        key=(rec["source_id"],rec["story"])
        if (area and key not in assigned_areas) or ((not area) and key not in assigned_lines):
            warnings.append({"code":"LOAD_REFERENCES_UNASSIGNED_OBJECT","area":area,
                "source_id":rec["source_id"],"story":rec["story"]})
        return rec
    frame_loads=[load_record(x,False) for x in nb("FRAME OBJECT LOADS") if x.startswith("LINELOAD ")]
    area_loads=[load_record(x,True) for x in nb("SHELL OBJECT LOADS") if x.startswith("AREALOAD ")]

    mass_lines=nb("MASS SOURCE")
    mass={"definition":next((x for x in mass_lines if x.startswith("MASSSOURCE  ")),None),"load_factors":[]}
    for x in mass_lines:
        if x.startswith("MASSSOURCELOAD"):
            q=qs(x); nums=re.findall(r'([-+0-9.eE]+)\s*$',x)
            if len(q)>=2 and nums: mass["load_factors"].append({"pattern":q[1],"factor":float(nums[-1])})

    load_cases=[]
    for x in nb("LOAD CASES"):
        if x.startswith("LOADCASE ") and " TYPE " in f" {x} ":
            q=qs(x); load_cases.append({"name":q[0] if q else None,"type":qafter("TYPE",x),
                "modal_case":qafter("MODALCASE",x),"raw":x})
    combos=[]
    for x in nb("LOAD COMBINATIONS"):
        if x.startswith("COMBO ") and " TYPE " in f" {x} ":
            q=qs(x)
            if q and q[0] not in combos: combos.append(q[0])

    fatal=[w for w in warnings if w["code"] in {"MISSING_POINT_COORD","UNKNOWN_STORY",
        "MISSING_LINE_CONNECTIVITY","MISSING_AREA_CONNECTIVITY","COLUMN_WITHOUT_LOWER_STORY",
        "LOAD_REFERENCES_UNASSIGNED_OBJECT"}]
    counts={"nodes":len(nodes),"frames":len(frames),
        "columns":sum(f["type"]=="COLUMN" for f in frames),
        "beams":sum(f["type"]=="BEAM" for f in frames),
        "non_section_lines":sum(f["type"]=="LINE" for f in frames),
        "areas":len(areas),"frame_loads":len(frame_loads),"area_loads":len(area_loads)}
    return {"schema":"jp_structural.normalized_model.legacy_e2k.v0.1",
        "source":{"filename":path.name,"size_bytes":len(raw),"sha256":sha256(path)},
        "units":{"force":"N","length":"mm","temperature":"C"},
        "stories":[{"name":n,"elevation":elevations[n]} for n in bottom_names],
        "materials":list(materials.values()),"frame_sections":list(frame_sections.values()),
        "slab_properties":list(slab_properties.values()),"load_patterns":load_patterns,
        "nodes":list(nodes.values()),"frames":frames,"areas":areas,
        "frame_loads":frame_loads,"area_loads":area_loads,"mass_source":mass,
        "load_cases":load_cases,"load_combinations":combos,
        "qa":{"status":"PASS_REFERENCE_INTEGRITY" if not fatal else "FAIL_REFERENCE_INTEGRITY",
              "counts":counts,"fatal_issue_count":len(fatal),"warnings":warnings}}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("e2k",type=Path); ap.add_argument("-o","--output",type=Path)
    a=ap.parse_args(); d=normalize(a.e2k); payload=json.dumps(d,indent=2,ensure_ascii=False)+"\n"
    if a.output: a.output.write_text(payload,encoding="utf-8")
    else: print(payload,end="")
if __name__=="__main__": main()
