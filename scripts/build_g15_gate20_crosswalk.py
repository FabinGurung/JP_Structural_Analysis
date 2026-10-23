#!/usr/bin/env python3
"""G15 Gate20 source-to-model and F3 discrepancy ledger.

Proof obligations, dependency order and quantitative source conflicts are
computed, not declared complete. Existing Gate17/18/19 evidence stays source
truth; missing original ETABS / geotechnical data never becomes a PASS.
"""
from __future__ import annotations
import argparse,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_g15_gate18_mass_f3 import build as g18
from scripts.screen_g15_gate19_e2k import build as g19
from scripts.reconcile_f3_source import build as f3

REG=ROOT/"registry/g15-gate20-source-crosswalk.v0.1.json"
SOURCE=ROOT/"registry/g15-gate17-source-observations.v0.1.json"

def build():
    c=json.loads(REG.read_text(encoding="utf-8"))
    src=json.loads(SOURCE.read_text(encoding="utf-8"))
    prev=g18()
    etabs=g19()
    footing=f3()
    assert c["source_report_sha256"]==src["basis"]["sha256"]==prev["source_report_sha256"]
    assert c["source_F3_status"]==prev["f3_source_explicit_verdict"]==footing["source_extraction"]["source_f3_one_way_shear_flag"]
    assert etabs["status"]=="BLOCKED_ORIGINAL_ETABS_MODEL_NOT_FOUND"
    assert len(c["gates"])==15
    obs={x["id"] for x in src["observations"]}
    ids={x["id"] for x in c["gates"]}
    assert len(ids)==len(c["gates"]) and len(obs)==11
    for g in c["gates"]:
        assert g["source_observation_ids"] and all(s in obs for s in g["source_observation_ids"])
        assert g["evidence_needed"] and g["acceptance_test"] and g["required_by_role"]
        assert all(p in ids and p!=g["id"] for p in g["depends_on"])
        assert not (g["evidence_received"] or g["source_provider_readback"]
                    or g["independent_review_passed"] or g["accepted"])
    # Dependency graph is checked for cycles, so the acceptance path can be
    # executed in order without self-supporting source assumptions.
    graph={x["id"]:x["depends_on"] for x in c["gates"]}
    def walk(n,seen):
        assert n not in seen,"Cyclic evidence dependency"
        for p in graph[n]:walk(p,seen|{n})
    for x in graph:walk(x,set())
    # F3: original worksheet's 194.22 kPa is based on 571kN without
    # selfweight, while source includes separate 600kN service total.
    raw=footing["source_extraction"]
    B,L=raw["source_footing_size_mm"]
    area_m2=B*L/1e6
    P=raw["source_axial_kN"]
    Ps=raw["source_axial_with_selfweight_kN"]
    q=raw["source_factored_upward_pressure_kPa"]
    factor=1.5
    q571=factor*P/area_m2
    q600=factor*Ps/area_m2
    qs=Ps/area_m2
    assert math.isclose(q571,q,abs_tol=.005)
    assert q600>q571 and math.isclose(qs,600/4.41,abs_tol=1e-9)
    sheet=json.loads((ROOT/"registry/g15-gate18-report-mass-f3-source.v0.1.json").read_text())
    depth_src=sheet["f3_source"]["sheet_effective_depth_d_mm"]
    d_reconstructed=prev["f3_prior_reconstruction_assumed_depth_mm"]
    D=raw["source_overall_thickness_mm"]
    assert 0<d_reconstructed<depth_src<D
    assert sheet["f3_source"]["sheet_one_way_nominal_shear_rounded_MPa"]==sheet["f3_source"]["sheet_one_way_permissible_shear_rounded_MPa"]
    source_governing_fail=c["source_F3_status"]
    domains=sorted({x["domain"] for x in c["gates"]})
    summary={}
    for name in domains:
        rows=[x for x in c["gates"] if x["domain"]==name]
        summary[name]={"total":len(rows),"accepted":sum(bool(x["accepted"]) for x in rows)}
    return {
        "schema":"jp.structural.g15.gate20.crosswalk_F3_reconciliation.v0.1",
        "source_report_sha256":c["source_report_sha256"],
        "source_original_drive_id":c["original_report_drive_id"],
        "source_gate_registry":"registry/g15-gate20-source-crosswalk.v0.1.json",
        "current_phase":"P0_SOURCE_TO_MODEL_RECONCILIATION",
        "gates":c["gates"],
        "gate_count":len(c["gates"]),
        "accepted_gate_count":sum(x["accepted"] for x in c["gates"]),
        "domain_counts":summary,
        "topological_dependencies_acyclic":True,
        "reported_ETABS_W_kN":prev["source_report_ETABS_seismic_W_kN"],
        "source_three_storey_mass_arithmetic_identity":prev["source_aggregate_mass_arithmetic_consistent_given_kg_and_standard_g"],
        "native_ETABS_mass_unit_and_source_definition_verified":False,
        "component_mass_reconciliation_complete":False,
        "trial_G08_mass_gap_kN":prev["older_trial_composition_gap_remains_unresolved"]["G08_vs_source_difference_kN"],
        "trial_G10_mass_gap_kN":prev["older_trial_composition_gap_remains_unresolved"]["G10_vs_source_difference_kN"],
        "f3":{"source_verdict":source_governing_fail,
          "source_footer_summary_was_not_safe":True,
          "foundation_plan_area_m2":area_m2,
          "source_ultimate_pressure_printed_kPa":q,
          "reconstructed_printed_q_from_1p5_times_571_kPa":q571,
          "alternative_1p5_times_600_kPa":q600,
          "factored_pressure_difference_kPa":q600-q571,
          "source_service_with_selfweight_pressure_kPa":qs,
          "reported_allowable_soil_kPa_not_geotechnically_verified":raw["source_claimed_SBC_kPa"],
          "source_sheet_effective_depth_mm":depth_src,
          "previous_trial_effective_depth_mm":d_reconstructed,
          "discrepancy_mm":depth_src-d_reconstructed,
          "source_nominal_and_allowable_shear_stresses_displayed_equal_only_after_rounding":True,
          "load_components_verified":False,
          "soil_bearing_settlement_verified":False,
          "source_f3_design_accepted":False,
          "F3_redesign_verified":False},
        "upstream_native_ETABS_model_found":False,
        "source_engineering_signoff":False,
        "engineering_approval":False
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();data=build()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(data,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("G15_GATE20_SOURCE_CROSSWALK_AND_F3_FAIL_HOLD",data["gate_count"],data["accepted_gate_count"])

if __name__=="__main__":main()
