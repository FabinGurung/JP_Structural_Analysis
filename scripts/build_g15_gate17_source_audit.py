#!/usr/bin/env python3
"""Gate17 source-evidence and seismic-mass discrepancy audit, no ETABS fabrication.

Source observations transcribed with PDF text line anchors in registry.
Absolute mass values are not source decomposition unless ETABS original
mass-source and individual area, line, and member objects are available.
A total match cannot establish a valid mass-source model.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
from scripts.build_g15_gate10_assumptions import build as gate10

ROOT=Path(__file__).resolve().parents[1]
REG=ROOT/"registry/g15-gate17-source-observations.v0.1.json"
G09=ROOT/"registry/g15-gate09-panel-mass-source.v0.1.json"
G16=ROOT/"registry/g15-gate16-drawing-mass-review.v0.1.json"

def build():
    src=json.loads(REG.read_text(encoding="utf-8"))
    r09=json.loads(G09.read_text(encoding="utf-8"))
    r16=json.loads(G16.read_text(encoding="utf-8"))
    study=gate10()
    assert src["basis"]["sha256"]==r09["source_pdf_sha256"]==r16["source_pdf_sha256"]
    records={q["id"]:q for q in src["observations"]}
    assert len(records)==len(src["observations"])==11
    e=records["G17-M01"]["reported_ETABS_seismic_weight_kN"]
    baseline=r09["report_mass"]["gate08_reconstructed_weight_kN"]
    comm=next(c for c in study["model_cases"] if c["id"]=="G10_EDGE_COMM")
    trial=comm["trial_seismic_weight_kN"]
    assert abs(e-6831.9109)<1e-7 and trial>baseline
    # Gate08 report-subtotals rounded to 3 d.p. each, so maintain the
    # numerical baseline canonical total, not their rounded sum.
    sub=r09["report_mass"]
    source_components=[
      {"id":"MEMBER_SELF_WEIGHT_G08","kN":sub["gate08_member_self_weight_kN"],"class":"INFERRED_GATE08"},
      {"id":"FLOOR_DEAD_G08","kN":sub["gate08_floor_added_dead_kN"],"class":"INFERRED_GATE08"},
      {"id":"LIVE_SEISMIC_SHARE_G08","kN":sub["gate08_seismic_live_share_kN"],"class":"INFERRED_GATE08"},
      {"id":"WALLS_CONDITIONAL_G08","kN":sub["gate08_conditional_wall_load_kN"],"class":"INFERRED_GATE08"}
    ]
    sum_rounded=math.fsum(x["kN"] for x in source_components)
    round_error=baseline-sum_rounded
    assert abs(round_error)<.001
    w20=records["G17-M03"]["reported_concrete_density_kN_m3"]
    w25=records["G17-M02"]["reported_RCC_density_kN_m3"]
    thickness=records["G17-S01"]["reported_thickness_mm"]/1000.
    reported_dead=records["G17-S01"]["reported_selfweight_kPa"]
    implied=thickness*w25
    assert math.isclose(implied,3.125,abs_tol=1e-10)
    assert math.isclose(reported_dead,round(implied,2),abs_tol=1e-10)
    source_modal=records["G17-D01"]
    assert source_modal["table_mode5_cumulative_UX"]>=.9
    assert source_modal["table_mode5_cumulative_UY"]>=.9
    assert source_modal["table_mode6_cumulative_RZ"]>=.9
    assert source_modal["reported_corresponding_period_sec"]!=source_modal["table_first_mode_period_sec"]
    no_source=src["source_file_manifest"]["source_ETABS_binary_or_e2k_confirmed"] is False
    assert no_source and all(not g["ready"] for g in src["decision_gates"])
    outstanding=[
      {"id":"GAP_G08","reference":"GATE08_CONDITIONAL",
       "reported_ETABS_kN":e,"trial_kN":baseline,
       "unexplained_kN":e-baseline,"percent_reported":100*(e-baseline)/e,
       "source_verified_reconciliation":False},
      {"id":"GAP_G10","reference":"G10_EDGE_COMM_HYPOTHESIS",
       "reported_ETABS_kN":e,"trial_kN":trial,
       "unexplained_kN":e-trial,"percent_reported":100*(e-trial)/e,
       "source_verified_reconciliation":False}
    ]
    assert all(g["unexplained_kN"]>0 and not g["source_verified_reconciliation"] for g in outstanding)
    return {
      "schema":"jp.structural.g15.gate17.source_mass_conflict_ledger.v0.1",
      "source_pdf_sha256":src["basis"]["sha256"],
      "source_original_google_drive_id":src["basis"]["source_id"],
      "audit_fact_count":len(records),
      "drawing_and_load_provenance_is_report_only":True,
      "all_original_source_observations_preserved":True,
      "report_seismic_weight_kN":e,
      "gap_scenarios":outstanding,
      "gate08_components_rounded_kN":source_components,
      "gate08_subtotal_rounding_residual_kN":round_error,
      "slab_125mm_25kN_m3_implied_selfweight_kPa":implied,
      "slab_report_rounded_selfweight_kPa":reported_dead,
      "slab_125mm_20kN_m3_counterfactual_selfweight_kPa":thickness*w20,
      "sample_uses_25_unit_weight_consistently":True,
      "whole_building_concrete_density_reconciled":False,
      "slab_thickness_120mm_vs_125mm_reconciled":False,
      "source_ground_occupancy_consistent_with_residential_summary":False,
      "table_first_modal_period_seconds":source_modal["table_first_mode_period_sec"],
      "narrative_claim_period_seconds":source_modal["reported_corresponding_period_sec"],
      "first_mode_vs_report_period_consistent":False,
      "mode5_horizontal_90pct_reached":True,
      "mode6_rotational_90pct_reached":True,
      "modal_screen_source_wording_resolved":False,
      "original_ETABS_e2k_for_this_building_found":False,
      "next_required_source_artifacts":[
        "original ETABS .edb/.e2k and Tables -> Model Definition -> Area and Load Assignments",
        "Mass Source load patterns, element mass settings, floor story weight export",
        "source structural DXF with slab boundaries and opening/terrace polygons",
        "actual site geotechnical assumptions and recalculated failing footing F3"
      ],
      "decision_gates":src["decision_gates"],
      "engineering_approval":False,
      "source_mass_reconciled":False,
      "full_floor_shell_verified":False,
      "F3_status":"NOT SAFE IN ONE WAY SHEAR",
      "roadmap_stage":"P0_SOURCE_RECONCILIATION_AND_ENGINEERING_VALIDATION",
      "roadmap":[
        {"id":"R0","label":"Governed source inventory and auditable discrepancy ledger","state":"GATE17_NUMERICAL_AUDIT_COMPLETE"},
        {"id":"R1","label":"Original ETABS/CAD object-level geometry and mass-source mapping","state":"BLOCKED_SOURCE"},
        {"id":"R2","label":"Native full-floor shell/wall load path and source-weight reconciliation","state":"BLOCKED_ON_R1"},
        {"id":"R3","label":"Signed NBC105 ULS/SLS/P-delta/drift and F3 redesign verification","state":"BLOCKED_ON_R2_AND_DESIGN_INPUTS"},
        {"id":"R4","label":"Approved project SAR and reusable report/template freeze","state":"DEFERRED_ENGINEERING_SIGNOFF"}
      ]
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    d=build()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(d,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("GATE17_SOURCE_MASS_AUDIT_NOT_DESIGN_APPROVAL",d["audit_fact_count"],d["gap_scenarios"][0]["unexplained_kN"])

if __name__=="__main__": main()
