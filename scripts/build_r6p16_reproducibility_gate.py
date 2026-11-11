#!/usr/bin/env python3
"""R6.16 cross-layer report reproducibility acceptance audit.

Answers three DIFFERENT questions:
(a) Does the first-party Python/OpenSees stack execute bounded reports?
(b) Is that run source-equivalent to the governing ETABS21 ULS/SLS input pair?
(c) Can it independently reproduce and approve ALL historical-report design?
Never infer (b) or (c) from (a), green software CI, or the printed PDF.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_r6p15_incomplete_edge_audit import build as r615_build

COVERAGE=ROOT/"registry/report-calculation-coverage.v0.1.json"
GOVERNING=ROOT/"registry/r6p5_etabs21_governing_pair.v0.1.json"
HISTORICAL=ROOT/"registry/r6p6_reported_structural_results.v0.1.json"
GATE21=ROOT/"site/reports/g15-gate21-report.v0.1.json"
OUT=ROOT/"site/data/r6p16-report-reproducibility-readiness.json"
RECEIPT=ROOT/"site/reports/r6p16-report-reproducibility-receipt.json"
SCHEMA="jp.structural.r6p16.report_engine_reproduction_readiness.v0.1"
STATUSES=("IMPLEMENTED_BOUNDED","PARTIAL","DRAFT_UNVALIDATED","MISSING")
PRIORITIES=("P0","P1","P2")
BLOCKERS=(
 ("B01","P0","Native source analysis geometry and physical support paths",
  "One authoritative canonical 3D model: generate compatible shell/frame joints, exact source releases/offsets, diaphragm and footings; resolve 12 original unanchored shells with authenticated drawings, never automatic snapping.",
  "Source model mapping + 6-DOF free-body, signed reactions, mesh convergence, no conditional source support accepted as a verified one."),
 ("B02","P0","Material, gravity loads, mass and actual site evidence",
  "Reconstruct physical concrete and steel densities, wall/slab/finishes/occupancy and authentic mass source; reconcile gravitational force and mass by object/story without forcing historic 6831.9109 kN match.",
  "Original-grounded mass and applied load ledger with sample third-party calculation and nonduplicated shell/frame transfers."),
 ("B03","P0","ULS/SLS and governing seismic numerical envelope",
  "Build both source stiffness cases with actual spectrum/site/soil conditions, eccentricity and torsion, MRSM/ELF scaling, P-Delta, wind where governing and full signed design combinations.",
  "Independent code-controlled, edition-cited modal/force/drift/equilibrium comparisons plus sensitivity, member and foundation envelopes."),
 ("B04","P0","Reinforced-concrete member and foundation designs",
  "Complete beams, biaxial columns, ductile joints, one/two-way slabs, stairs, isolated/combined footing shear/punching and reinforcement/anchorage, including adverse F3 redesign.",
  "Explicit pass/fail with code edition, source dimensions and actual accepted design forces; F3 fail cannot be overridden by assumed alternatives."),
 ("B05","P0","Independent benchmark and qualified engineering review",
  "Compare critical members, frames, slabs and reactions with independent hand solutions and alternative FE models; resolve contradictory historical PDF assertions; independent engineer reviews assumptions.",
  "Qualified check evidence, risk registers and signed engineering acceptance before construction."),
 ("B06","P1","Complete version-controlled report and Drive workflow",
  "Publish a complete chapter-by-chapter computational report with input and model/solver hashes, drawings, detail schedules and controlled PDF exports. Keep Drive as private evidence authority and add governed fingerprint-based import when approved.",
  "One-click validated rerun tied to exact approved input revision, per-figure/calculation provenance, prior-release diffs and no sensitive public data."),
)

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def sha(path):
    return sha256(Path(path).read_bytes()).hexdigest()

def get_gate21(gate21=None):
    if gate21 is not None:return gate21
    if GATE21.is_file():return read_json(GATE21)
    from scripts.build_g15_gate21_report import calculate
    return calculate()[0]

def build(r615=None,coverage=None,governing=None,historical=None,gate21=None):
    covered=read_json(COVERAGE) if coverage is None else coverage
    model=read_json(GOVERNING) if governing is None else governing
    history=read_json(HISTORICAL) if historical is None else historical
    edge=r615_build() if r615 is None else r615
    g21=get_gate21(gate21)
    if covered["schema"]!="jp.structural.calculation_coverage.v0.1":
        raise ValueError("Coverage version or scope changed")
    req=covered["requirements"]
    counts=dict(sorted(Counter(m["status"] for m in req).items()))
    if (len(req)!=18 or set(counts)!=set(STATUSES) or
        counts!={"DRAFT_UNVALIDATED":1,"IMPLEMENTED_BOUNDED":2,"MISSING":4,"PARTIAL":11}):
        raise ValueError("Unreviewed change to report engine coverage registry")
    if len({m["id"] for m in req})!=18:
        raise ValueError("Duplicate report module identifier")
    for m in req:
        if m["status"] not in STATUSES or m["priority"] not in PRIORITIES or not m.get("validation_gate"):
            raise ValueError("Unsupported or ungrounded report module status")
    pair={role:model["model_pair"][role]["sha256"] for role in ("ULS","SLS")}
    if pair!=edge["governing_ULS_SLS_input_SHA256"]:
        raise ValueError("R6.15 model revision differs from registered ETABS21 ULS/SLS source")
    if (not model["decision"]["selected_model_takes_precedence_over_report_for_future_RECONCILIATION"]
        or model["admission_gates"]["native_ETABS_solution_and_mass_per_story_tables_reproduced"]
        or model["admission_gates"]["engineering_approval"]
        or model["admission_gates"]["F3_one_way_shear_safe"]):
        raise ValueError("Source acceptance illegally promoted or historic F3 cleared")
    if (history["source"]["report_sha256"]!="f122904444a2e2f75230d9d4e41da0093d050da25c6e8140c86d466b7e37cc52"
        or history["source"]["model_current"]!="USER_CONFIRMED_ETABS21_ULS_SLS_PAIR"
        or history["foundation"]["report_status"]!="NOT SAFE IN ONE WAY SHEAR"
        or history["foundation"]["acceptance"]):
        raise ValueError("Historical report identity or foundation result changed")
    if history["readiness"]["new_ETABS21_solution_executed"] or history["readiness"]["professional_engineering_approval"]:
        raise ValueError("Historical results silently reclassified as current verified solution")
    if (edge["coverage"]["slabs_examined"]!=77 or edge["coverage"]["source_edges_examined"]!=308
        or edge["baseline"]["shells"]!=115 or edge["baseline"]["source_graph_connected"]!=103
        or edge["baseline"]["source_graph_unanchored"]!=12 or edge["baseline"]["r614_complete_four_edge_shells"]!=25
        or edge["engineering_approval"] or not edge["twelve_unsupported_shells_still_excluded"]
        or edge["member_design_loads_modified"] or not edge["F3_one_way_shear_unsafe"]):
        raise ValueError("R6.15 original source fidelity or engineering HOLD failed")
    if (g21["schema"]!="jp.structural.g15.gate21.open_reproducible_sar.v0.1"
        or g21["case_count"]!=5 or g21["signed_end_action_count"]!=825
        or g21["counts"]["members"]!=165 or g21["model_ETABS_source_verified"]
        or g21["real_slab_and_wall_assignments_verified"]
        or g21["member_rebar_design_performed"] or g21["p_delta_performed"]
        or g21["engineering_approval"] or g21["F3_verdict"]!="NOT SAFE IN ONE WAY SHEAR"):
        raise ValueError("Original Gate21 numerical example overclaimed physical analysis or safety")
    # This is deliberately not a percentage of a building's verification.
    modules=[{"id":x["id"],"name":x["title"],"status":x["status"],
              "priority":x["priority"],
              "remaining_scope":x.get("remaining_scope",""),
              "validation_gate":x["validation_gate"],
              "engineered_design_approved":False} for x in req]
    stages=[
        {"id":"S01","title":"Version-frozen original input evidence",
            "state":"SOURCE_FILE_REGISTERED_NOT_NATIVE_SOLVER_VERIFIED",
            "evidence":"Governed Drive ULS/SLS E2K names/sizes/hashes, not live fetched in GitHub Pages",
            "original_model_equivalence":False},
        {"id":"S02","title":"First-party bounded solver and reporting",
            "state":"EXECUTABLE_REPRODUCIBLE_BOUNDED",
            "evidence":"OpenSees Gate21 5 independently solved assumed cases, 165 members, 825 signed end-action rows",
            "original_model_equivalence":False},
        {"id":"S03","title":"Source shell and gravity research",
            "state":"SOURCE_GEOMETRY_AND_BOUNDED_NUMERIC_TRIAL_ONLY",
            "evidence":"R6.10 103/115 source shells admitted to coarse conditional FE, 12 excluded",
            "original_model_equivalence":False},
        {"id":"S04","title":"Historical document arithmetic",
            "state":"REPORT_CLAIM_ARITHMETIC_CHECKS_ONLY",
            "evidence":"R6.12 arithmetic cross-check and historical source values; not exact ETABS21 reproduced analysis",
            "original_model_equivalence":False},
        {"id":"S05","title":"Perimeter and tributary reconciliation",
            "state":"GEOMETRIC_HYPOTHESES_ONLY",
            "evidence":"R6.14 25 rectangular geometric candidates; R6.15 77 withheld slabs/308 source edges",
            "original_model_equivalence":False},
        {"id":"S06","title":"Whole building seismic and RCC design",
            "state":"INCOMPLETE_DESIGN_HOLD",
            "evidence":"Incomplete source masses, actual stiffness/reactions, combined actions and member/footing design",
            "original_model_equivalence":False},
        {"id":"S07","title":"Complete report equivalent to approved historical engineer report",
            "state":"NOT_REPRODUCED_OR_APPROVED",
            "evidence":"Historical PDF contains ETABS20 and ETABS21 mixed references, selected native model result parity absent",
            "original_model_equivalence":False}
    ]
    needs=[{"id":a,"priority":b,"title":c,"missing":d,"completion_evidence":e}
           for a,b,c,d,e in BLOCKERS]
    return {"schema":SCHEMA,
        "source_scope":{"governing_ULS_SLS_SHA256":pair,
            "input_authority":"User-selected ETABS21 E2K pair in original restricted Google Drive",
            "raw_private_E2K_checked_into_public_github":False,
            "governing_model_last_verified_Google_Drive_metadata_in_this_audit":False,
            "published_pipeline":"Pinned GitHub source snapshot / de-identified derived data, not continuous Google Drive API ingestion",
            "source_drift_detection_against_drive_at_each_build":False,
            "historical_pdf_SHA256":history["source"]["report_sha256"],
            "historical_pdf_is_original_current_model_solution":False},
        "reproduction":{
            "first_party_bounded_engine_solutions_executable":True,
            "Gate21_assumption_frame_solved_cases":5,
            "Gate21_assumption_frame_member_end_action_rows":825,
            "Gate21_reference_frame_members":165,
            "R610_original_source_shells":115,
            "R610_source_shells_in_bounded_coarse_solver":103,
            "R610_source_shells_excluded":12,
            "R615_reviewed_missing_perimeter_slabs":77,
            "R615_original_edges_inspected":308,
            "R614_provisional_four_beam_slabs":25,
            "full_governing_ETABS21_model_equivalent":False,
            "all_historical_report_results_recomputed":False,
            "complete_project_code_based_RCC_design_approved":False,
            "signed_original_support_reactions_obtained":False,
            "engineering_approval":False,
            "F3_one_way_shear_unsafe":True},
        "coverage_registry_version":covered["version"],
        "module_coverage_status_counts":counts,
        "module_coverage_is_sufficient_for_full_project_report":False,
        "module_coverage_snapshot_must_be_revalidated_for_latest_work":True,
        "module_count":len(req),"modules":modules,
        "reproducibility_stages":stages,
        "critical_gates":needs,
        "engineering_acceptance":"NOT ACCEPTED",
        "never_replace_missing_source_reactions_with_zeros":True,
        "public_pages_are_not_live_gdrive_editors":True,
        "F3_one_way_shear_unsafe":True,
        "twelve_unsupported_shells_excluded":True,
        "engineering_approval":False}

def export(r615=None,coverage=None,governing=None,historical=None,gate21=None):
    d=build(r615=r615,coverage=coverage,governing=governing,historical=historical,gate21=gate21)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(d,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf8")
    receipt={"schema":"jp.structural.r6p16.reproducibility_receipt.v0.1",
        "source_coverage_SHA256":sha(COVERAGE),"governing_source_SHA256":sha(GOVERNING),
        "historical_registry_SHA256":sha(HISTORICAL),
        "record":d["schema"],"body_sha256":sha(OUT),
        "modules":d["module_count"],"safe_construction_design":False,
        "F3_one_way_shear_unsafe":True,"engineering_approval":False}
    RECEIPT.parent.mkdir(parents=True,exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf8")
    return d,receipt

if __name__=="__main__":
    d,proof=export()
    print("R6P16_BOUND_ENGINE_YES_COMPLETE_ETABS_REPRODUCTION_NO",
        json.dumps(d["module_coverage_status_counts"],sort_keys=True))
    print("R6P16_QA_REPORT_FINGERPRINT",proof["body_sha256"])
