#!/usr/bin/env python3
"""Reusable structural report and submission contract engine v0.1.

This stage implements reproducible load arithmetic, source provenance and QA
fail-closed semantics. It DOES NOT implement complete engineering design.
"""
from __future__ import annotations
import argparse,json,math,hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"registry/sap-template-engine.v0.1.json"
REQUIRED={"project_id","revision","site","occupancy","code_edition","inputs","load_cases"}
SUPPORTED={"dead_area_kN_m2","live_area_kN_m2","slab_thickness_m","concrete_density_kN_m3","area_m2","factor"}
class InputError(ValueError):pass

def finite_pos(value,key,allow_zero=False):
    if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value):
        raise InputError(f"{key} must be a finite numeric value")
    if value<0 if allow_zero else value<=0: raise InputError(f"{key} must be positive")
    return float(value)

def assess(data):
    contract=json.loads(CONTRACT.read_text(encoding="utf8"))
    if not isinstance(data,dict):raise InputError("case must be an object")
    missing=REQUIRED-set(data)
    if missing:raise InputError("missing "+",".join(sorted(missing)))
    for k in ["project_id","revision","site","occupancy","code_edition"]:
        if not isinstance(data[k],str) or not data[k].strip():raise InputError(k+" required")
    if data["code_edition"] not in {"NBC 105:2025","NBC 105:2020"}:
        raise InputError("unregistered seismic code edition")
    if not isinstance(data["inputs"],dict) or not data["inputs"]:
        raise InputError("inputs object required")
    x=data["inputs"]
    if set(x)!=SUPPORTED:raise InputError(f"unexpected/missing numeric inputs: {sorted(set(x)^SUPPORTED)}")
    v={k:finite_pos(x[k],k,k in ("dead_area_kN_m2","live_area_kN_m2")) for k in SUPPORTED}
    if not isinstance(data["load_cases"],list) or not data["load_cases"]:
        raise InputError("nonempty load_cases required")
    seen=set()
    for case in data["load_cases"]:
        if not isinstance(case,dict) or set(case)!={"id","type","combination_factors","source"}:
            raise InputError("load case must have id/type/combination_factors/source")
        if case["id"] in seen or not isinstance(case["id"],str) or not case["id"]:
            raise InputError("load case ids must be unique and nonblank")
        seen.add(case["id"])
        if case["type"] not in ("REFERENCE_GRAVITY","REFERENCE_COMBINATION"):
            raise InputError("unsupported load type; never silently run seismic")
        if not isinstance(case["source"],str) or not case["source"].strip():
            raise InputError("load case provenance required")
        if not isinstance(case["combination_factors"],dict) or set(case["combination_factors"])!={"dead","live"}:
            raise InputError("explicit dead/live factors required")
        for k,f in case["combination_factors"].items():
            finite_pos(f,k,True)
    if not isinstance(data.get("source_custody"),dict):
        raise InputError("source_custody must describe source and its verification")
    source=data["source_custody"]
    if not isinstance(source.get("id"),str) or not source["id"]:
        raise InputError("source custody identity required")
    if not isinstance(source.get("verified"),bool):raise InputError("source verified must be boolean")
    if not isinstance(data.get("engineer_review"),dict) or not isinstance(data["engineer_review"].get("signed"),bool):
        raise InputError("independent engineer signed status required")
    dead_slab=v["slab_thickness_m"]*v["concrete_density_kN_m3"]
    dead_total=dead_slab+v["dead_area_kN_m2"]
    live=v["live_area_kN_m2"]
    records=[]
    for case in data["load_cases"]:
        f=case["combination_factors"]
        q=dead_total*f["dead"]+live*f["live"]
        records.append({"id":case["id"],"type":case["type"],"source":case["source"],"factors":f,
         "pressure_kPa":q,"total_vertical_force_kN":q*v["area_m2"],
         "is_code_approved_combination":False,"is_signed_FE_result":False})
    req_modules=["source_model_identity","global_geometry","material_strength","dead_live_loads",
                 "diaphragm_mass_source","seismic_actions","signed_FE_equilibrium",
                 "member_strength_checks","serviceability","soil_foundation",
                 "independent_review","drawings"]
    implemented={"dead_live_loads":True}
    checks=[{"id":x,"implemented":implemented.get(x,False),
             "result":"REFERENCE_CALCULATED_NOT_CERTIFIED" if implemented.get(x,False) else "NOT_IMPLEMENTED",
             "design_pass":False} for x in req_modules]
    ready=source["verified"] and data["engineer_review"]["signed"] and all(x["design_pass"] for x in checks)
    assert not ready and all(not x["design_pass"] for x in checks)
    return {"schema":"jp.structural.sap.template_case_result.v0.1",
      "contract_schema":contract["schema"],"project_id":data["project_id"],
      "revision":data["revision"],"code_edition":data["code_edition"],
      "source_custody":source,"reference_only":True,
      "calculations":{"slab_selfweight_kPa":dead_slab,
        "additional_dead_area_kPa":v["dead_area_kN_m2"],"dead_area_total_kPa":dead_total,
        "imposed_area_kPa":live,"tributary_area_m2":v["area_m2"],"cases":records},
      "chapter_coverage":[{"chapter":c["chapter"],"title":c["title"],
        "template_defined":True,"design_or_analysis_complete":False} for c in contract["chapters"]],
      "required_design_modules":checks,
      "approval":{"engineer_signed":data["engineer_review"]["signed"],
        "submission_ready":False,"analysis_verified":False,"design_approved":False},
      "trace":{"contract_sha256":hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
       "case_sha256":hashlib.sha256(json.dumps(data,sort_keys=True,separators=(",",":")).encode()).hexdigest()},
      "limitations":["AREA_GRAVITY_ARITHMETIC_ONLY","NOT_A_FULL_OPEN_SEES_RUN","NOT_CODE_FACTOR_VALIDATION",
       "NOT_MEMBER_OR_FOOTING_DESIGN","SITE_SPECIFIC_GEOTECH_NOT_VALIDATED",
       "INDEPENDENT_ENGINEER_AND_LOCAL_PERMIT_PROCESS_REQUIRED"]}

def render_md(result):
    lines=["# Structural Analysis and Design Report — template case","",
      f"Case: {result['project_id']} · revision: {result['revision']}",
      f"Code reference: {result['code_edition']} (applicability not independently approved)","",
      "**REFERENCE CALCULATIONS ONLY — NOT A DESIGN OR BUILDING PERMIT REPORT**",""]
    for ch in result["chapter_coverage"]:
        lines += [f"## {int(ch['chapter'])}. {ch['title']}",
          "Template section defined; complete verified engineering outputs are NOT YET AVAILABLE.",""]
        if ch["chapter"]=="02":
            x=result["calculations"]
            lines.extend([f"Slab selfweight = {x['slab_selfweight_kPa']:.5f} kPa",
              f"Additional dead load = {x['additional_dead_area_kPa']:.5f} kPa",
              f"Total dead load = {x['dead_area_total_kPa']:.5f} kPa",
              f"Imposed load = {x['imposed_area_kPa']:.5f} kPa",""])
        if ch["chapter"]=="05":
            for r in result["calculations"]["cases"]:
                lines.append(f"- {r['id']} ({r['type']}): {r['pressure_kPa']:.5f} kPa; {r['total_vertical_force_kN']:.5f} kN. Not a verified FE or design result.")
            lines.append("")
    lines.extend(["## Submission gates — all engineering passes withheld",""])
    lines.extend("- "+r["id"]+": "+r["result"] for r in result["required_design_modules"])
    lines.extend(["","Submission ready: NO. Independent engineer must verify all governing inputs, calculations and drawings.",""])
    return "\n".join(lines)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--markdown",type=Path)
    a=p.parse_args()
    data=json.loads(a.input.read_text(encoding="utf8"))
    out=assess(data)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,indent=2,allow_nan=False)+"\n",encoding="utf8")
    if a.markdown:
        a.markdown.parent.mkdir(parents=True,exist_ok=True)
        a.markdown.write_text(render_md(out),encoding="utf8")
    print("SAP_TEMPLATE_V01_REFERENCE_GRAVITY_COMPUTED_FULL_ANALYSIS_NOT_COMPLETE_SUBMISSION_HOLD")
if __name__=="__main__":main()
