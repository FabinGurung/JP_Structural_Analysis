#!/usr/bin/env python3
"""Lossless-first ETABS .e2k inventory extractor.

This module does not solve or mutate the source model. It inventories the E2K
vocabulary and extracts conservative facts required before DB normalization and
OpenSees translation.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
from typing import Any

_QUOTED = r'"((?:[^"]|"")*)"'

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def normalize_name(v: str) -> str:
    return re.sub(r"[^a-z0-9]+"," ",v.lower()).strip()

def split_sections(text: str) -> dict[str,list[str]]:
    sections={}; current=None
    for raw in text.splitlines():
        if raw.startswith("$"):
            current=raw[1:].strip(); sections.setdefault(current,[])
        elif current is not None:
            sections[current].append(raw)
    return sections

def nonblank(lines:list[str])->list[str]:
    return [x.strip() for x in lines if x.strip()]

def first_quoted(line:str)->str|None:
    m=re.search(_QUOTED,line)
    return m.group(1).replace('""','"') if m else None

def quoted_after(key:str,line:str)->str|None:
    m=re.search(rf"\b{re.escape(key)}\s+{_QUOTED}",line)
    return m.group(1).replace('""','"') if m else None

def number_after(key:str,line:str)->float|None:
    m=re.search(rf"\b{re.escape(key)}\s+([-+0-9.eE]+)",line)
    if not m: return None
    try: return float(m.group(1))
    except ValueError: return None

def inventory(path:Path)->dict[str,Any]:
    data=path.read_bytes()
    text=data.decode("utf-8",errors="replace")
    lines=text.splitlines()
    sections=split_sections(text)
    header=lines[0] if lines else ""
    program_line=next(iter(nonblank(sections.get("PROGRAM INFORMATION",[]))),"")
    controls=nonblank(sections.get("CONTROLS",[]))
    project_line=next(iter(nonblank(sections.get("PROJECT INFORMATION",[]))),"")
    units=[]
    for line in controls:
        if line.startswith("UNITS"):
            units=[x.replace('""','"') for x in re.findall(_QUOTED,line)]
            break

    stories=[]
    for line in nonblank(sections.get("STORIES - IN SEQUENCE FROM TOP",[])):
        if line.startswith("STORY "):
            stories.append({"name":first_quoted(line),"height":number_after("HEIGHT",line),
              "elevation":number_after("ELEV",line),"similar_to":quoted_after("SIMILARTO",line),
              "master_story":quoted_after("MASTERSTORY",line)})

    diaphragms=[first_quoted(x) for x in nonblank(sections.get("DIAPHRAGM NAMES",[])) if x.startswith("DIAPHRAGM ")]

    materials=[]; seen=set()
    for line in nonblank(sections.get("MATERIAL PROPERTIES",[])):
        if line.startswith("MATERIAL "):
            name=first_quoted(line)
            if name and name not in seen:
                seen.add(name); materials.append({"name":name,"type":quoted_after("TYPE",line),"grade":quoted_after("GRADE",line)})

    frames=[]; seen=set()
    for line in nonblank(sections.get("FRAME SECTIONS",[])):
        if line.startswith("FRAMESECTION "):
            name=first_quoted(line)
            if name and name not in seen:
                seen.add(name); frames.append({"name":name,"material":quoted_after("MATERIAL",line),
                  "shape":quoted_after("SHAPE",line),"depth":number_after("D",line),"width":number_after("B",line)})

    slabs=[]
    for line in nonblank(sections.get("SLAB PROPERTIES",[])):
        if line.startswith("SHELLPROP "):
            slabs.append({"name":first_quoted(line),"material":quoted_after("MATERIAL",line),
              "modeling_type":quoted_after("MODELINGTYPE",line),"slab_type":quoted_after("SLABTYPE",line),
              "thickness":number_after("SLABTHICKNESS",line)})

    patterns=[]; seismic=[]
    for line in nonblank(sections.get("LOAD PATTERNS",[])):
        if line.startswith("LOADPATTERN "):
            patterns.append({"name":first_quoted(line),"type":quoted_after("TYPE",line),"self_weight":number_after("SELFWEIGHT",line)})
        elif line.startswith("SEISMIC "):
            seismic.append({"name":first_quoted(line),"direction":quoted_after("DIR",line),
              "eccentricity":number_after("ECC",line),"top_story":quoted_after("TOPSTORY",line),
              "bottom_story":quoted_after("BOTTOMSTORY",line),"shear_coeff":number_after("SHEARCOEFF",line),
              "height_exponent":number_after("HEIGHTEXPONENT",line)})

    cases=[]
    for line in nonblank(sections.get("LOAD CASES",[])):
        if line.startswith("LOADCASE ") and " TYPE " in f" {line} ":
            cases.append({"name":first_quoted(line),"type":quoted_after("TYPE",line),"modal_case":quoted_after("MODALCASE",line)})

    combos=[]
    for line in nonblank(sections.get("LOAD COMBINATIONS",[])):
        if line.startswith("COMBO ") and " TYPE " in f" {line} ":
            name=first_quoted(line)
            if name and name not in combos: combos.append(name)

    functions=[]; seen=set()
    for line in nonblank(sections.get("FUNCTIONS",[])):
        if line.startswith("FUNCTION "):
            name=first_quoted(line)
            if name and name not in seen:
                seen.add(name); functions.append({"name":name,"type":quoted_after("FUNCTYPE",line),
                  "spectrum_type":quoted_after("SPECTYPE",line),"damping_ratio":number_after("DAMPRATIO",line)})

    model_name=quoted_after("MODELNAME",project_line)
    company=quoted_after("COMPANYNAME",project_line)
    title2=next((quoted_after("TITLE2",x) for x in controls if x.startswith("TITLE2")),None)
    source_norm=normalize_name(path.stem)
    warnings=[]
    for label,value in [("TITLE2",title2),("PROJECTINFO.MODELNAME",model_name)]:
        if value:
            vn=normalize_name(value)
            if vn and source_norm and vn not in source_norm and source_norm not in vn:
                warnings.append({"code":"SOURCE_INTERNAL_NAME_MISMATCH","field":label,
                  "source_filename":path.name,"internal_value":value,"severity":"warning"})
    opts=nonblank(sections.get("ANALYSIS OPTIONS",[]))
    if any("PDELTA" in x and 'METHOD "NONE"' in x for x in opts):
        warnings.append({"code":"PDELTA_DISABLED_IN_SOURCE","severity":"info"})
    mass=nonblank(sections.get("MASS SOURCE",[]))
    if any("MASSSOURCE " in x and 'INCLUDEELEMENTS "No"' in x for x in mass):
        warnings.append({"code":"MASS_SOURCE_EXCLUDES_DIRECT_ELEMENT_MASS","severity":"info"})

    return {
      "schema":"opensees_structural_report.e2k_inventory.v0.1",
      "source":{"filename":path.name,"size_bytes":len(data),"sha256":sha256_file(path),"header":header},
      "program":{"name":first_quoted(program_line),"version":quoted_after("VERSION",program_line),"units":units},
      "project_info":{"company_name":company,"model_name":model_name,"title2":title2},
      "counts":{"stories":len(stories),"point_coordinate_records":len(nonblank(sections.get("POINT COORDINATES",[]))),
        "line_connectivity_records":len(nonblank(sections.get("LINE CONNECTIVITIES",[]))),
        "area_connectivity_records":len(nonblank(sections.get("AREA CONNECTIVITIES",[]))),
        "load_patterns":len(patterns),"load_cases":len(cases),"load_combinations":len(combos)},
      "stories":stories,"diaphragms":[x for x in diaphragms if x],"materials":materials,
      "frame_sections":frames,"slab_properties":slabs,"load_patterns":patterns,
      "seismic_definitions":seismic,"load_cases":cases,"load_combinations":combos,
      "functions":functions,"section_record_counts":{k:len(nonblank(v)) for k,v in sections.items()},
      "warnings":warnings
    }

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("e2k",type=Path); ap.add_argument("-o","--output",type=Path)
    a=ap.parse_args(); payload=json.dumps(inventory(a.e2k),indent=2,ensure_ascii=False)+"\n"
    if a.output: a.output.write_text(payload,encoding="utf-8")
    else: print(payload,end="")
    return 0

if __name__=="__main__": raise SystemExit(main())
