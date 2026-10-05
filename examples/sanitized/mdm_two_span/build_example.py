#!/usr/bin/env python3
"""Build the first public sanitized analysis + SAR package."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from jp_structural.model.ids import stable_id
from jp_structural.qa.pre_solve import run_pre_solve_qa

ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/"examples"/"sanitized"/"mdm_two_span"/"website_demo_data.json"
BENCHMARK=ROOT/"benchmarks"/"opensees"/"mdm_two_span_validation.py"


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def git_value(*args: str, fallback: str) -> str:
    try:
        return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()
    except Exception:
        return fallback


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,default=ROOT/"build"/"mdm_two_span")
    args=ap.parse_args()
    out=args.output
    out.mkdir(parents=True,exist_ok=True)

    source=json.loads(SOURCE.read_text(encoding="utf-8"))
    source_hash=sha256(SOURCE)
    project_id=stable_id("PRJ",source["project"]["project_code"])
    model_id=stable_id("MDL",source_hash)
    run_id=stable_id("ANR",model_id+":opensees-2d")
    result_id=stable_id("RES",run_id)
    validation_id=stable_id("VAL",run_id+":source-comparison")

    benchmark_path=out/"benchmark_result.json"
    subprocess.run([sys.executable,str(BENCHMARK),"--report",str(benchmark_path)],cwd=ROOT,check=True,capture_output=True,text=True)
    benchmark=json.loads(benchmark_path.read_text(encoding="utf-8"))

    inv={"schema_version":"0.1","files":[{
        "file_id":stable_id("SRC",source_hash),
        "original_filename":SOURCE.name,
        "file_type":"application/json",
        "size_bytes":SOURCE.stat().st_size,
        "sha256":source_hash,
        "source_origin":"migrated sanitized R&D benchmark",
        "received_date":"2026-10-05",
        "authority_role":"sanitized regression source",
        "classification":"sanitized",
        "parser":"json",
        "parser_version":"stdlib",
        "ingestion_status":"INVENTORIED"
    }]}
    dump(out/"source_inventory.json",inv)

    points={"A":0.0,"B":6.0,"C":12.0}
    nodes=[]
    node_ids={}
    for label,x in points.items():
        nid=stable_id("NOD",source["project"]["project_code"]+":"+label)
        node_ids[label]=nid
        nodes.append({"id":nid,"label":label,"x":x,"y":0.0,"z":0.0})
    mat_id=stable_id("MAT","reference-E-split")
    sec_id=stable_id("SEC","source-EI-reference")
    members=[]
    for row in source["structural_model"]["members"]:
        mid=stable_id("MEM",source["project"]["project_code"]+":"+row["member_label"])
        i,j=tuple(row["member_label"])
        members.append({
            "id":mid,"label":row["member_label"],"i_node":node_ids[i],"j_node":node_ids[j],
            "section_id":sec_id,"flexural_rigidity_ei":row["flexural_rigidity_ei"],
            "flexural_rigidity_unit":row["ei_unit"]
        })
    lp_id=stable_id("LP","DEAD-LIKE-UDL")
    lc_id=stable_id("LC","SANITIZED-STATIC")
    model={
        "schema_version":"0.1","model_id":model_id,
        "project":{"project_id":project_id,"project_code":source["project"]["project_code"],"project_name":source["project"]["project_name"]},
        "units":{"force":"kN","length":"m","temperature":None,"mass":None},
        "design_basis":{"status":"UNRESOLVED","note":"Sanitized mathematical benchmark; no governing building-code edition is asserted."},
        "source_references":[{"source_file_id":inv["files"][0]["file_id"],"source_record":"structural_model/member_summary","extraction_method":"deterministic JSON mapping","verification_status":"SANITIZED_SOURCE"}],
        "storeys":[],
        "nodes":nodes,
        "frame_members":members,
        "shell_elements":[],
        "materials":[{"id":mat_id,"label":"Reference elastic material","status":"ANALYSIS_REFERENCE_ONLY","E_kN_per_m2":25000000.0}],
        "sections":[{"id":sec_id,"label":"EI-preserving reference section","material_id":mat_id,"status":"ANALYSIS_REFERENCE_ONLY","area_m2":1.0}],
        "supports":[{"node_id":node_ids["A"],"type":"fixed"},{"node_id":node_ids["B"],"type":"vertical restraint / rotationally free"},{"node_id":node_ids["C"],"type":"fixed"}],
        "constraints":[],"diaphragms":[],"end_releases":[],"rigid_offsets":[],"stiffness_modifiers":[],
        "load_patterns":[{"id":lp_id,"label":"AB UDL"}],
        "load_cases":[{"id":lc_id,"label":"Linear static"}],
        "load_combinations":[],
        "mass_source":None,"joint_loads":[],
        "frame_loads":[{"member_label":"AB","load_pattern_id":lp_id,"type":"uniform","magnitude":10.0,"unit":"kN/m"}],
        "area_loads":[],"response_spectra":[],"analysis_cases":[]
    }
    dump(out/"normalized_model.json",model)
    model_qa=run_pre_solve_qa({
        "units":model["units"],"design_basis":model["design_basis"],"nodes":model["nodes"],
        "materials":model["materials"],"sections":model["sections"],"frame_members":model["frame_members"],
        "load_patterns":model["load_patterns"],"mass_source":{}
    })
    dump(out/"model_qa.json",model_qa)

    config={
        "schema_version":"0.1","analysis_run_id":run_id,"model_id":model_id,"model_sha256":sha256(out/"normalized_model.json"),
        "solver":{"name":"OpenSeesPy","version":benchmark["solver"]["package_version"],"engine_version":benchmark["solver"]["engine_version"],"adapter_version":"migrated-mdm-two-span-v0.1"},
        "unit_system":{"force":"kN","length":"m"},
        "cases":[{"case_id":lc_id,"analysis_type":"2D linear elastic static"}],
        "tolerances":{"absolute":1e-6},
        "options":{"element_type":"elasticBeamColumn","source_mutated":False}
    }
    dump(out/"analysis_config.json",config)

    analysis={
        "schema_version":"0.1","result_set_id":result_id,"analysis_run_id":run_id,"model_id":model_id,
        "solver":config["solver"],"units":{"reaction":"kN","moment":"kN m","displacement":"m"},
        "case_results":[{
            "case_id":lc_id,
            "analysis_return_code":benchmark["opensees_result"]["analysis_return_code"],
            "node_displacements":benchmark["opensees_result"]["node_displacements"],
            "support_reactions_y":benchmark["opensees_result"]["support_reactions_y"],
            "member_end_moments":benchmark["opensees_result"]["member_end_moments_mdm_sign"]
        }],
        "provenance":{"source_file_id":inv["files"][0]["file_id"],"source_sha256":source_hash,"benchmark_script":"benchmarks/opensees/mdm_two_span_validation.py"}
    }
    dump(out/"analysis_results.json",analysis)

    comparisons=[]
    for row in benchmark["comparison"]["moment_checks"]:
        a=float(row["stored_mdm"]); b=float(row["opensees"]); diff=b-a
        comparisons.append({"benchmark_id":"MDM-TWO-SPAN","quantity":row["quantity"],"location":row["member"],"load_case":lc_id,
            "engine_A":"governed sanitized source","value_A":a,"engine_B":"OpenSeesPy","value_B":b,
            "absolute_difference":abs(diff),"relative_difference_percent":None if a==0 else abs(diff/a)*100.0,
            "tolerance":1e-6,"status":"PASS" if row["pass"] else "FAIL","explanation":"Direct source-to-OpenSees member-end moment comparison."})
    for row in benchmark["comparison"]["reaction_checks"]:
        a=float(row["stored_mdm"]); b=float(row["opensees"]); diff=b-a
        comparisons.append({"benchmark_id":"MDM-TWO-SPAN","quantity":row["quantity"],"location":row["joint"],"load_case":lc_id,
            "engine_A":"governed sanitized source","value_A":a,"engine_B":"OpenSeesPy","value_B":b,
            "absolute_difference":abs(diff),"relative_difference_percent":None if a==0 else abs(diff/a)*100.0,
            "tolerance":1e-6,"status":"PASS" if row["pass"] else "FAIL","explanation":"Reaction discrepancy is deliberately preserved for reconciliation."})
    validation={"schema_version":"0.1","validation_run_id":validation_id,"status":"FAIL","comparisons":comparisons,
        "equilibrium":benchmark["comparison"]["equilibrium"],
        "professional_state":"ENGINEER_REVIEW_REQUIRED",
        "note":"Moment checks and OpenSees global equilibrium pass; stored support reactions do not reconcile with OpenSees and remain unresolved."}
    dump(out/"validation_results.json",validation)

    assumptions=[{"id":"ASM-001","status":"DISCLOSED","text":"A reference E and area are used only to split authoritative EI for the OpenSees beam formulation; no axial load is applied in this benchmark."}]
    conflicts=[{"id":"CON-001","status":"UNRESOLVED","quantity":"support reactions","source":"sanitized source dataset","comparison":"OpenSeesPy","detail":"A/B/C reaction distribution differs although both systems sum to the same 60 kN total vertical load."}]
    unresolved=[{"id":"UNR-001","status":"UNRESOLVED","topic":"reaction distribution","blocks":"NUMERICAL_VALIDATION_PASS"},
                {"id":"UNR-002","status":"UNRESOLVED","topic":"governing design code edition","blocks":"professional design/code-check claims"}]
    dump(out/"assumption_register.json",assumptions)
    dump(out/"conflict_register.json",conflicts)
    dump(out/"unresolved_items.json",unresolved)

    moments=benchmark["comparison"]["moment_checks"]
    reactions=benchmark["comparison"]["reaction_checks"]
    def rows(items):
        return "".join(f"<tr><td>{html.escape(str(x.get('member',x.get('joint'))))}</td><td>{html.escape(x['quantity'])}</td><td>{x['stored_mdm']:.6g}</td><td>{x['opensees']:.6g}</td><td>{'PASS' if x['pass'] else 'FAIL'}</td></tr>" for x in items)
    sar=f"""<!doctype html><html><head><meta charset="utf-8"><title>Sanitized Structural Analysis Report</title>
<style>body{{font:15px system-ui,sans-serif;max-width:980px;margin:40px auto;padding:0 24px;line-height:1.5}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #999;padding:7px;text-align:left}}.warn{{border:2px solid #8a5a00;padding:12px}}code{{background:#eee;padding:2px 4px}}</style></head><body>
<h1>Structural Analysis Report — Sanitized Demonstration</h1>
<p><strong>Project:</strong> {html.escape(source['project']['project_name'])}<br><strong>Project ID:</strong> {project_id}<br><strong>Analysis run:</strong> {run_id}</p>
<div class="warn"><strong>ENGINEER_REVIEW_REQUIRED.</strong> This public sanitized benchmark is not a government approval, building certification, or code-compliance statement. The support-reaction distribution remains unreconciled.</div>
<h2>Structural system</h2><p>Two-span continuous beam A–B–C. Each span is 6 m. Source EI is 25,000 kN·m². AB carries 10 kN/m downward UDL; BC is unloaded.</p>
<h2>Analysis method</h2><p>OpenSeesPy {benchmark['solver']['package_version']} / OpenSees {benchmark['solver']['engine_version']}; 2D linear-elastic <code>elasticBeamColumn</code> model. Source data is not mutated.</p>
<h2>Member-end moment comparison</h2><table><tr><th>Member</th><th>Quantity</th><th>Source (kN·m)</th><th>OpenSees (kN·m)</th><th>Status</th></tr>{rows(moments)}</table>
<h2>Support reaction comparison</h2><table><tr><th>Joint</th><th>Quantity</th><th>Source (kN)</th><th>OpenSees (kN)</th><th>Status</th></tr>{rows(reactions)}</table>
<h2>Equilibrium</h2><p>Total applied downward load = {benchmark['comparison']['equilibrium']['total_downward_load_kN']:.6g} kN. Total OpenSees vertical reaction = {benchmark['comparison']['equilibrium']['total_opensees_vertical_reaction_kN']:.6g} kN. Global equilibrium: PASS.</p>
<h2>Validation</h2><p>Member-end moments: PASS. Support-reaction reconciliation: FAIL. Overall numerical validation: NOT PASSED. Required state: ENGINEER_REVIEW_REQUIRED.</p>
<h2>Assumptions / unresolved items</h2><ul><li>Reference E/area split preserves source EI for this bending benchmark.</li><li>Support reaction distribution discrepancy remains unresolved.</li><li>No governing building-code edition is asserted for this mathematical sanitized example.</li></ul>
<h2>Provenance</h2><p>Source SHA-256: <code>{source_hash}</code>. Model ID: <code>{model_id}</code>. Result set: <code>{result_id}</code>. Validation run: <code>{validation_id}</code>.</p>
</body></html>"""
    (out/"SAR.html").write_text(sar,encoding="utf-8")

    # Validate governed JSON contracts.
    for artifact,schema_name in [
        ("source_inventory.json","source-inventory.schema.json"),
        ("normalized_model.json","normalized-model.schema.json"),
        ("analysis_config.json","analysis-config.schema.json"),
        ("analysis_results.json","analysis-results.schema.json"),
        ("validation_results.json","validation-results.schema.json"),
    ]:
        schema=json.loads((ROOT/"schemas"/schema_name).read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(json.loads((out/artifact).read_text(encoding="utf-8")))

    git_commit=os.environ.get("GITHUB_SHA") or git_value("rev-parse","HEAD",fallback="0"*40)
    generated_at=git_value("show","-s","--format=%cI",git_commit,fallback="1970-01-01T00:00:00+00:00")
    output_names=["source_inventory.json","normalized_model.json","model_qa.json","analysis_config.json","analysis_results.json","validation_results.json","assumption_register.json","conflict_register.json","unresolved_items.json","SAR.html","benchmark_result.json"]
    manifest={"schema_version":"0.1","project_id":project_id,"model_id":model_id,"analysis_run_id":run_id,
        "git_commit":git_commit,"solver_versions":{"OpenSeesPy":benchmark["solver"]["package_version"],"OpenSees":benchmark["solver"]["engine_version"]},
        "input_hashes":{SOURCE.name:source_hash},"output_hashes":{name:sha256(out/name) for name in output_names},
        "generation_timestamp":generated_at,"validation_state":"ENGINEER_REVIEW_REQUIRED","unresolved_count":len(unresolved)}
    dump(out/"report_manifest.json",manifest)
    schema=json.loads((ROOT/"schemas"/"report-manifest.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(manifest)
    print(out)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
