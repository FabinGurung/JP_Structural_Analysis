#!/usr/bin/env python3
"""Execute the independent OpenSees/Python SAR pipeline on a case JSON or reference.

No native ETABS export required. The built-in reference is synthetic; real
private source inputs/output MUST stay outside this public checkout.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from jp_structural.reporting.independent_casebook import (
    INPUT_SCHEMA, build, emit, verify_bundle
)
from jp_structural.solvers.opensees.synthetic_d2_example import case_fixture

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "registry/report-template-contract.v0.2.json"
COVERAGE = ROOT / "registry/report-calculation-coverage.v0.1.json"


def reference_fixture() -> dict:
    model, cases, combos, beams, columns, joints = case_fixture()
    return {
        "schema": INPUT_SCHEMA,
        "case_id": "SYNTHETIC-D2-FRAME-001",
        "classification": "SYNTHETIC_REFERENCE",
        "provenance": {
            "geometry": "SYNTHETIC_D2_GEOMETRY_NO_CLIENT_SOURCE",
            "materials": "SYNTHETIC_D2_E25GPA_REFERENCE",
            "supports": "SYNTHETIC_D2_TWO_FIXED_ENDS",
            "loads": "SYNTHETIC_D2_G_AND_HX_NODAL_LOADS",
            "reinforcement": "SYNTHETIC_D2_8D25_AND_HINGE_ASSUMPTIONS",
            "design_code": "NBC105_2025_AND_IS456_2000_CALCULATION_REFERENCE"
        },
        "model": model,
        "cases": cases,
        "combinations": combos,
        "design_bindings": {
            "beams": beams, "columns": columns, "joints": joints
        },
        "code_references": [
            {"id": "NBC105_2025",
             "url": "https://ebps.kathmandu.gov.np/UploadFiles/NBC_105_2025_Sesmic_Design.pdf"},
            {"id": "IS456_2000",
             "url": "https://wriddodoti.gov.np/uploads/blog/20230331071217_IS-456-with-all-ammendments.pdf"}
        ],
        "engineering_approval": False
    }


def _inside(path: Path, parent: Path) -> bool:
    return path.resolve() == parent.resolve() or parent.resolve() in path.resolve().parents


def run(input_payload: dict, output_dir: Path):
    if input_payload.get("classification") != "SYNTHETIC_REFERENCE":
        # No private client model/results may land in checkout, Pages, repo
        # reports, or public GitHub Actions artifact paths.
        if _inside(output_dir, ROOT):
            raise ValueError("Real-source SAR output must be outside public repository")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    coverage = json.loads(COVERAGE.read_text(encoding="utf-8"))
    result = build(input_payload, contract=contract, coverage=coverage)
    manifest = emit(result, output_dir)
    verify_bundle(output_dir)
    return result, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--reference", action="store_true")
    source.add_argument("--input", type=Path, help="Private source-derived canonical case JSON")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.input:
        if _inside(args.input, ROOT):
            raise ValueError("Client source model must stay outside public repository")
        payload = json.loads(args.input.read_text(encoding="utf-8"))
    else:
        payload = reference_fixture()
    report, manifest = run(payload, args.output_dir)
    print(json.dumps({
        "case_id": report["case_id"],
        "mode": report["analysis_mode"],
        "source_class": report["classification"],
        "frame_members": report["counts"]["frame_members"],
        "signed_end_rows": report["counts"]["signed_end_rows"],
        "unassessed_members": report["unassessed_members"],
        "sha256_manifest": manifest["files"],
        "engineering_approval": report["engineering_approval"],
        "complete_building": report["all_applicable_design_modules_complete"]
    }, sort_keys=True))


if __name__ == "__main__":
    main()
