#!/usr/bin/env python3
"""R6.8 deidentified ETABS21 source-member catalogue, NOT a solved design model.

Consumes an immutable LZMA-compressed, source-derived geometry/load snapshot
made by SHA256-verifying the original user-selected ETABS21 ULS+SLS pair.
Raw ETABS binaries and owner/client filename/path are never committed.
Computes each line length, section gross volume, line/shell load integral,
and explicitly approximate gravity source self-weight with unit evidence.
Do NOT mistake these local calculations for ETABS reactions, frame moments,
code compliance, as-built quantities or approved reinforcement.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter, defaultdict
import hashlib
import json
import lzma
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "registry/r6p8_etabs21_derived_source.lzma.b64"
REGISTRY = ROOT / "registry/r6p5_etabs21_governing_pair.v0.1.json"
OUT = ROOT / "site/data/r6p8-etabs21-source-member-catalogue.json"
REPORT = ROOT / "site/reports/r6p8-etabs21-member-catalogue-summary.json"
UNCOMPRESSED_SHA256 = "7c78e4537b85e2e6d5b9389501838fae71e9c8c6b507fc8ded4e79fe1afe693e"
SCHEMA = "jp.structural.r6p8.etabs21_governing_source_compact.v0.1"
STORIES = {"Plinth level": 0, "GF":3048,"FF":6096,"TF":9144}
PATTERNS = {"Dead":1.0,"Live":0.3,"WALL LOAD":1.0,"FLOOR FINISH":1.0,"TANK":0.6,"STAIRCASE LOAD":0.3}

class SourceError(ValueError):
    pass

def strict_number(v, msg):
    if isinstance(v, bool) or not isinstance(v,(int,float)) or not math.isfinite(v):
        raise SourceError("Nonfinite or invalid source number: "+msg)
    return float(v)

def source():
    source_file = base64.b64decode("".join(SEED.read_text(encoding="ascii").split()), validate=True)
    if len(source_file)>15000:
        raise SourceError("Compressed source size cap exceeded")
    raw=lzma.decompress(source_file, format=lzma.FORMAT_XZ, memlimit=128*1024*1024)
    if hashlib.sha256(raw).hexdigest()!=UNCOMPRESSED_SHA256:
        raise SourceError("Immutable source-derived snapshot changed")
    a=json.loads(raw)
    b=json.loads(REGISTRY.read_text(encoding="utf8"))
    if a["schema"]!=SCHEMA or a["status"]!={"current_ETABS21_source":True,"new_ETABS21_solver_executed":False,"engineering_approval":False,"F3_one_way_shear_unsafe":True,"raw_ETABS_files_in_repository":False}:
        raise SourceError("Bad ETABS21 source scope")
    if a["sha"] != [b["model_pair"][role]["sha256"] for role in ("ULS","SLS")]:
        raise SourceError("Source file identities differ from user-approved governing pair")
    if b["admission_gates"]["engineering_approval"] or b["admission_gates"]["native_ETABS_solution_and_mass_per_story_tables_reproduced"]:
        raise SourceError("Governance gates changed")
    if a["elevations_mm"]!=STORIES or a["factors"]!=PATTERNS:
        raise SourceError("Unexpected storeys or mass participation")
    if tuple(map(len,[a["points"],a["lines"],a["areas"],a["members"],a["shells"],a["loads"]]))!=(127,97,80,199,115,337):
        raise SourceError("Original model source record-count mismatch")
    if len(a["sections"])!=6 or len(a["shell_sections"])!=5:
        raise SourceError("Section count mismatch")
    if len({(x[0],x[1]) for x in a["members"]})!=199 or len({(x[0],x[1]) for x in a["shells"]})!=115:
        raise SourceError("Duplicate member or area identity")
    if a["points"]["20"][2]!=2456.94 or a["points"]["23"][:2]!=[0.0,0.0]:
        raise SourceError("Original out-of-plane source Z values dropped")
    return a

def polygon_area2d(vertices):
    return abs(sum(vertices[i][0]*vertices[(i+1)%len(vertices)][1]-
                   vertices[(i+1)%len(vertices)][0]*vertices[i][1]
                   for i in range(len(vertices)))/2)

def build():
    a=source()
    p=a["points"]
    entries=[]
    lookup={}
    for id,storey,section in a["members"]:
        if storey not in STORIES or id not in a["lines"]:
            raise SourceError("Invalid frame reference")
        kind,u,v=a["lines"][id]
        if kind not in ("COLUMN","BEAM","LINE") or u not in p or v not in p:
            raise SourceError("Invalid frame connectivity")
        uxyz,vxyz=p[u],p[v]
        if kind=="COLUMN":
            if u!=v or storey=="Plinth level":
                raise SourceError("Unexpected vertical member")
            length_mm=3048.0
            start=[uxyz[0],uxyz[1],STORIES[storey]-3048+uxyz[2]]
            finish=[vxyz[0],vxyz[1],STORIES[storey]+vxyz[2]]
        else:
            start=[uxyz[0],uxyz[1],STORIES[storey]+uxyz[2]]
            finish=[vxyz[0],vxyz[1],STORIES[storey]+vxyz[2]]
            length_mm=math.dist(start,finish)
        row={"key":storey+":"+id,"id":id,"storey":storey,"kind":kind,
             "point_ids":[u,v],"start_xyz_mm":start,"end_xyz_mm":finish,
             "section":section,"length_mm":round(length_mm,6),
             "applied_loads":[],"source_scope":"ETABS21_NATIVE_INPUT_ONLY"}
        if section!="NONE":
            sec=a["sections"].get(section)
            if not sec:raise SourceError("Undefined structural section")
            depth=strict_number(sec["depth_mm"],section)
            width=sec["width_mm"]
            if sec["shape"]=="Concrete Circle":
                area=math.pi*(depth**2)/4
            elif sec["shape"]=="Concrete Rectangular" and width is not None:
                area=depth*strict_number(width,section)
            else:raise SourceError("Unrecognized frame section")
            gross=area*length_mm/1e9
            gamma=a["materials"][sec["material"]]["unit_weight_N_mm3"]*1e6
            row.update({"section_shape":sec["shape"],"material":sec["material"],
                        "section_area_mm2":round(area,6),
                        "section_gross_volume_m3":round(gross,9),
                        "source_dead_selfweight_proxy_kN":round(gross*gamma,6),
                        "rebar_model_section":a["rebar"].get(section,{})})
        entries.append(row)
        lookup[(id,storey)]=row
    shells=[]
    shell_lookup={}
    for id,storey,section in a["shells"]:
        if id not in a["areas"] or storey not in STORIES:
            raise SourceError("Missing source shell")
        kind,*pointids=a["areas"][id]
        if len(pointids)<3 or any(q not in p for q in pointids):
            raise SourceError("Invalid shell polygon")
        vertices=[[p[q][0],p[q][1],p[q][2]+STORIES[storey]] for q in pointids]
        area=polygon_area2d(vertices)
        record={"key":storey+":"+id,"id":id,"storey":storey,"kind":kind,
                "point_ids":pointids,"vertices_xyz_mm":vertices,"section":section,
                "projected_area_mm2":round(area,6),
                "projected_area_is_true_3d_surface_area":False,
                "applied_loads":[],"source_scope":"ETABS21_NATIVE_INPUT_ONLY"}
        sec=a["shell_sections"].get(section)
        if not sec:raise SourceError("Unknown shell property")
        vol=area*sec["thickness_mm"]/1e9
        gamma=a["materials"][sec["material"]]["unit_weight_N_mm3"]*1e6
        record.update({"source_section_type":sec["type"],"thickness_mm":sec["thickness_mm"],
                       "material":sec["material"],
                       "plan_prism_volume_m3_proxy":round(vol,9),
                       "source_dead_selfweight_proxy_kN":round(vol*gamma,6)})
        shells.append(record)
        shell_lookup[(id,storey)]=record

    all_loads=[]
    for row in a["loads"]:
        kind,id,storey,pattern,method,*args=row
        target=lookup.get((id,storey)) if kind=="F" else shell_lookup.get((id,storey))
        if target is None or pattern not in PATTERNS:
            raise SourceError("Source-applied load missing target")
        if kind=="F":
            if target["kind"] not in ("BEAM","LINE"):raise SourceError("Frame gravity load target must be beam or explicit geometric LINE")
            length_mm=target["length_mm"]
            if method=="U" and len(args)==1:
                w=strict_number(args[0],id)
                total=w*length_mm/1000
                steps={"formula":"w × L ÷ 1000 = kN","w_N_per_mm":w,"L_mm":length_mm}
            elif method=="T" and len(args)==4:
                w0,w1,a0,a1=map(float,args)
                if not (0<=a0<a1<=1):raise SourceError("Bad load range")
                leff=length_mm*(a1-a0)
                total=(w0+w1)*.5*leff/1000
                steps={"formula":"(wstart + wend) / 2 × L × (end - start) ÷ 1000 = kN",
                       "wstart_N_per_mm":w0,"wend_N_per_mm":w1,
                       "start_fraction":a0,"end_fraction":a1,
                       "length_mm":length_mm}
            else:raise SourceError("Unknown member load type")
        elif kind=="S" and method=="U" and len(args)==1:
            q=strict_number(args[0],id)
            total=q*target["projected_area_mm2"]/1000
            steps={"formula":"q(N/mm²) × projected A(mm²) ÷ 1000 = kN",
                   "q_N_per_mm2":q,"projected_area_mm2":target["projected_area_mm2"]}
        else:raise SourceError("Unknown source load type")
        factor=PATTERNS[pattern]
        res={"target":target["key"],"pattern":pattern,"method":method,
             "raw_integrated_kN":round(total,6),
             "mass_participation_factor":factor,
             "mass_eligible_load_kN":round(total*factor,6),
             "working":steps}
        target["applied_loads"].append(res)
        all_loads.append(res)
    levels={}
    for storey in ("GF","FF","TF"):
        frames=[m for m in entries if m["storey"]==storey]
        shellrows=[s for s in shells if s["storey"]==storey]
        loads=[q for q in all_loads if q["target"].startswith(storey+":")]
        bypattern=defaultdict(float)
        for q in loads:bypattern[q["pattern"]]+=q["mass_eligible_load_kN"]
        levels[storey]={
            "source_structural_beam_count":sum(x["kind"]=="BEAM" for x in frames),
            "source_structural_column_count":sum(x["kind"]=="COLUMN" for x in frames),
            "source_unsectioned_line_count":sum(x["section"]=="NONE" for x in frames),
            "source_floor_shell_count":sum(x["kind"]=="FLOOR" for x in shellrows),
            "source_panel_count":sum(x["kind"]=="PANEL" for x in shellrows),
            "source_frame_gross_concrete_m3":round(sum(x.get("section_gross_volume_m3",0) for x in frames),6),
            "source_floor_projected_area_m2":round(sum(x["projected_area_mm2"] for x in shellrows if x["kind"]=="FLOOR")/1e6,6),
            "source_mass_eligible_applied_gravity_kN":round(sum(q["mass_eligible_load_kN"] for q in loads),6),
            "source_pattern_load_kN":{k:round(v,6) for k,v in sorted(bypattern.items())},
            "source_frame_dead_selfweight_proxy_kN":round(sum(x.get("source_dead_selfweight_proxy_kN",0) for x in frames),6),
            "source_shell_plan_prism_dead_selfweight_proxy_kN":round(sum(x.get("source_dead_selfweight_proxy_kN",0) for x in shellrows),6)}
    total=sum(x["source_mass_eligible_applied_gravity_kN"] for x in levels.values())
    if abs(total-3290.2187486)>0.02:
        raise SourceError("Original independently reconciled 3290 kN applied-load subtotal no longer matches")
    if (len(entries),len(shells),len(all_loads))!=(199,115,337):
        raise SourceError("Counts no longer match native source")
    sample=lookup[("B46","GF")]
    if sample["section"]!="beam 12*16" or not math.isclose(sample["length_mm"],4823,abs_tol=1e-6):
        raise SourceError("GF B46 original member source crosswalk mismatch")
    b46wall=sum(x["raw_integrated_kN"] for x in sample["applied_loads"] if x["pattern"]=="WALL LOAD")
    if not math.isclose(b46wall,44.61275,abs_tol=1e-5):
        raise SourceError("B46 source gravity wall load changed")
    if ("B19","GF") in lookup:
        raise SourceError("Historical GF B19 mismatch unexpectedly resolved")
    return {
      "schema":"jp.structural.r6p8.native_input_member_calculation_book.v0.1",
      "source":{"governing_etabs_major":21,"roles":["ULS","SLS"],
                "source_ulssls_hashes":a["sha"],"original_file_bytes_published":False,
                "same_native_uls_sls_geometry_and_applied_gravity_assignments":True,
                "historic_report_is_different_model_revision":True},
      "points_xyz_local_mm":a["points"],
      "grid_axes":{"X":{"A":0,"B":2985,"C":4900,"D":5485,"E":8748,"F":9723,"G":14688,"H":19500,"I":21000},
                   "Y":{"1":0,"2":3600,"3":6425,"4":7080,"5":10045,"6":10700,"7":12550}},
      "floor_elevations_mm":STORIES,
      "frame_sections":a["sections"],"shell_sections":a["shell_sections"],
      "source_model_rebar_section_input_not_approved_BBS":a["rebar"],
      "materials":a["materials"],"load_mass_participation_factors":PATTERNS,
      "members":entries,"shells":shells,"level_summary":levels,
      "reconciled_source_applied_mass_eligible_loads_kN":round(total,6),
      "historical_report_crosswalk":{
           "source_B46_GF":{"present":True,"same_historical_etabs_member_proven":False},
           "source_C24_TF":{"present":("C24","TF") in lookup,"same_historical_etabs_member_proven":False},
           "source_B19_GF":{"present":False,"cannot_transfer_report_forces":True}},
      "result_scope":{"actual_native_member_geometry":True,
                      "actual_native_applied_loads":True,
                      "source_based_gross_concrete_proxy_not_net_BOQ":True,
                      "source_based_selfweight_proxy_not_ETABS_solved_mass":True,
                      "new_ULS_SLS_ETABS_solver_run":False,
                      "complete_solved_member_end_forces":False,
                      "approved_rebar_cutting_schedules":False,
                      "engineering_approval":False,
                      "F3_one_way_shear_unsafe":True}}

def emit():
    out=build()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf8")
    summary={"schema":"jp.structural.r6p8.native_input_floor_comparison.v0.1",
             "levels":out["level_summary"],
             "overall_load_kN":out["reconciled_source_applied_mass_eligible_loads_kN"],
             "record_counts":{"points":len(out["points_xyz_local_mm"]),
                              "member_assignments":len(out["members"]),
                              "shell_assignments":len(out["shells"]),
                              "assigned_gravity_loads":sum(len(x["applied_loads"]) for x in out["members"]+out["shells"])},
             "catalogue_sha256":hashlib.sha256(OUT.read_bytes()).hexdigest(),
             "source_uls_sha256":out["source"]["source_ulssls_hashes"][0],
             "source_sls_sha256":out["source"]["source_ulssls_hashes"][1],
             "is_solver_result":False,"engineering_approval":False,
             "F3_one_way_shear_unsafe":True}
    REPORT.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf8")
    return out,summary

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",choices=["site"],default="site")
    p.parse_args()
    _,d=emit()
    print("R6P8_AUTHENTICATED_ETABS21_INPUT_CATALOGUE_NOT_SOLVED_MODEL",d["record_counts"],d["overall_load_kN"])
