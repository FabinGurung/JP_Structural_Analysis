#!/usr/bin/env python3
"""Chapter 5 original-source response audit + actual OpenSees signed end actions.

Every numerical action derives from a newly executed OpenSeesPy model via Gate21;
the original ETABS report is indexed separately and never reverse fitted to it.
End-resisting-force pairs are NOT certified member span diagrams or RC designs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_g15_gate21_report import PDF_SHA, PARTS, calculate
from scripts.run_g15_open_3d import solve, source
REGISTRY=ROOT/"registry/g15-chapter05-source-observations.v0.1.json"
GRID=ROOT/"site/data/g15-working-grid.public.v0.1.json"
SCHEMA="jp.structural.g15.chapter05.signed_numerical_source_comparison.v0.1"
CASES=("GRAVITY","EQ_PLUS_X","EQ_MINUS_X","EQ_PLUS_Y","EQ_MINUS_Y")
PART_TYPES={"axial":["Ni","Nj"],"shear_local_y":["Vyi","Vyj"],
  "shear_local_z":["Vzi","Vzj"],"bending_local_y":["Myi","Myj"],
  "bending_local_z":["Mzi","Mzj"],"torsion":["Ti","Tj"]}

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def numerical(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)

def build():
    observed=json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert observed["schema"]=="jp.structural.g15.chapter05.source_report_observations.v0.1"
    assert observed["original"]["sha256"]==PDF_SHA
    assert observed["source_F3_status"]=="NOT SAFE IN ONE WAY SHEAR"
    assert observed["physical_engineering_approval"] is False
    report, signed=calculate()  # REAL 5-case OpenSees solver, not source ETABS reactions
    # Independent same-input OpenSees call exposes node displacement records absent in Gate21 compact summary.
    numerical_model=solve(report["inputs"])
    assert report["model_ETABS_source_verified"] is False and report["engineering_approval"] is False
    assert len(signed)==825 and [c["name"] for c in report["cases"]]==list(CASES)
    assert [c["case"] for c in numerical_model["cases"]]==list(CASES)
    assert report["counts"]["members"]==165 and report["counts"]["nodes"]==92
    assert report["F3_verdict"]=="NOT SAFE IN ONE WAY SHEAR"
    for c in report["cases"]:
        assert c["force_residual_kN"]<.001 and c["moment_residual_kNm"]<.001
    known={c[0] for c in source()["column_positions_mm"]}
    member_ids=set()
    row_ids=set()
    end_actions=[]
    by_case=Counter()
    for record in signed:
        case,member=record["case"],record["member"]
        assert case in CASES and (case,member) not in row_ids
        assert all(numerical(record[p]) for p in PARTS)
        row_ids.add((case,member));member_ids.add(member);by_case[case]+=1
        end_actions.append({"id":case+"::"+member,"case_id":case,"member_id":member,
             "local_components":{part:float(record[part]) for part in PARTS},
             "scope":"ACTUAL_OPENSEES_SIGNED_ELEMENT_END_RESISTING_ACTIONS",
             "span_diagram_verified":False,"source_member_authenticated":False})
    assert len(member_ids)==165 and len(row_ids)==825
    assert all(by_case[c]==165 for c in CASES)
    for nc in numerical_model["cases"]:
        expected={x["id"]:x for x in nc["member_signed_local_end_forces"]}
        assert len(expected)==165 and set(expected)==member_ids
        for a in (x for x in end_actions if x["case_id"]==nc["case"]):
            # Separate OpenSees execution cannot silently disagree with Gate21.
            assert all(abs(a["local_components"][p]-expected[a["member_id"]]["signed"][j])<1e-7
                       for j,p in enumerate(PARTS))
    node_displacements=[]
    coords={x[0]:[x[1]/1000,x[2]/1000] for x in source()["column_positions_mm"]}
    for c in numerical_model["cases"]:
        assert len(c["node_displacements"])==69
        for x in c["node_displacements"]:
            assert x["node"] in known and x["level"] in (1,2,3)
            assert numerical(x["ux_mm"]) and numerical(x["uy_mm"])
            node_displacements.append({"case_id":c["case"],"node_id":f'N-{x["node"]}-L{x["level"]}',
              "grid":x["node"],"level":x["level"],"xy_m":coords[x["node"]],
              "ux_mm":float(x["ux_mm"]),"uy_mm":float(x["uy_mm"]),
              "source_displacement_authenticated":False})
    assert len(node_displacements)==345

    src_seismic=observed["original_auto_seismic"]
    for limit in ("ULS","SLS"):
        item=src_seismic[limit]
        computed=src_seismic["seismic_weight_kN"]*item["coefficient"]
        assert abs(computed-item["reported_base_shear_kN"])<.0001
    src_modes=observed["reported_modes"]
    assert src_modes["table"][0]["mode"]==1
    assert len(src_modes["table"])==6
    def crossing(name):
        return next((x["mode"] for x in src_modes["table"] if x[name]>=.9),None)
    assert (crossing("sum_UX"),crossing("sum_UY"),crossing("sum_RZ"))==(5,4,6)
    assert abs(src_modes["table"][0]["period_s"]-src_modes["narrative_period_s"])>.4
    original_claims={
      "auto_seismic_arithmetic":{
         name:{"printed_kN":src_seismic[name]["reported_base_shear_kN"],
           "recalculated_kN":src_seismic["seismic_weight_kN"]*src_seismic[name]["coefficient"],
           "difference_kN":src_seismic["seismic_weight_kN"]*src_seismic[name]["coefficient"]-
             src_seismic[name]["reported_base_shear_kN"]}
         for name in ("ULS","SLS")},
      "modal_90_percent_first_table_mode":{"UX":crossing("sum_UX"),"UY":crossing("sum_UY"),
        "RZ":crossing("sum_RZ")},
      "modal_period_source_conflict_s":{
        "first_reported_table_s":src_modes["table"][0]["period_s"],
        "surrounding_narrative_s":src_modes["narrative_period_s"],
        "difference_s":src_modes["table"][0]["period_s"]-src_modes["narrative_period_s"],
        "resolved":False},
      "source_physical_acceptance":False}
    report_cases=[]
    for c in report["cases"]:
        name=c["name"]
        rows=[r for r in end_actions if r["case_id"]==name]
        extrema={kind:max(({"member_id":r["member_id"],"component":p,
             "signed_value":r["local_components"][p],"unit":"kN" if kind.startswith(("axial","shear")) else "kN.m"}
             for r in rows for p in pair),key=lambda a:abs(a["signed_value"]))
             for kind,pair in PART_TYPES.items()}
        assert len(rows)==165 and all(numerical(a["signed_value"]) for a in extrema.values())
        report_cases.append({"id":name,"signed_end_action_records":len(rows),
          "roof_displacement_mm":c["roof_max_mm"],"story_chord_metrics":c["story_chord_metrics"],
          "reactions_kN_xyz":c["reactions_kN_xyz"],
          "force_residual_kN":c["force_residual_kN"],
          "moment_residual_kNm":c["moment_residual_kNm"],
          "absolute_signed_end_action_extrema":extrema,"verified_physical_case":False})
    assert len(report_cases)==5
    return {
      "schema":SCHEMA,"original_source_file_id":observed["original"]["file_id"],
      "original_source_SHA256":PDF_SHA,
      "original_source_section":"Original §5.1 to §5.15, preserving original narrative claims",
      "original_report_claims":original_claims,
      "original_observations":observed,
      "source_registry_SHA256":digest(REGISTRY),"grid_SHA256":digest(GRID),
      "chapter04_graph_reference":"data/g15-chapter04-model-graph.v0.1.json",
      "numerical_result_reference":"reports/g15-gate21-report.v0.1.json",
      "signed_end_action_csv_reference":"reports/g15-gate21-signed-member-actions.csv",
      "original_ETABS_model_authenticated":False,
      "numerical_engine":"OpenSeesPy elasticBeamColumn 3D",
      "numerical_scope":"5 independent static trial cases; no authenticated modal or spectrum model",
      "component_order":list(PARTS),"signed_pair_groups":PART_TYPES,
      "case_summaries":report_cases,"member_case_end_actions":end_actions,
      "trial_node_displacements":node_displacements,
      "counts":{"cases":5,"members_per_case":165,"signed_member_case_records":825,
          "components_per_record":12,"trial_displacement_records":345,"source_gates_open":15},
      "missing_source_checks":[
        "Native original ETABS model, object map, authentic member load diagram and model sign convention",
        "Verified floor mass and diaphragm stiffness for modal response",
        "Authentic response spectrum, accidental eccentricity, ULS/SLS combinations and P-Delta",
        "Project-specific drift, mass, soft-storey, torsion and section compliance",
        "Foundation F3 redesign and independently verified one-way shear"],
      "original_F3_one_way_shear":"NOT SAFE IN ONE WAY SHEAR",
      "project_specific_NBC_compliance_evaluated":False,
      "authentic_modal_analysis_performed":False,
      "authentic_member_span_diagrams_recovered":False,
      "original_report_claims_independently_verified":False,
      "engineering_approval":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    d=build()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(d,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("CHAPTER5_OPENSEES_SIGNED_825_CASE_MEMBERS_345_DISPLACEMENTS_SOURCE_GATE15_HOLD")

if __name__=="__main__":main()
