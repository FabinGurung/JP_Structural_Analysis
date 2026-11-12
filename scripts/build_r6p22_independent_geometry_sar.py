#!/usr/bin/env python3
"""R6.22: generate independent physical gravity/load paths and OpenSees casebook.

--reference uses fully synthetic 4-column roof geometry. No ETABS outputs.
For actual source models, private input and output MUST stay outside public Git.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from jp_structural.reporting.r6p22_pipeline import build, emit, verify
ROOT = Path(__file__).resolve().parents[1]


def _inside(path: Path, parent: Path) -> bool:
    target = path.resolve()
    base = parent.resolve()
    return target == base or base in target.parents

R5 = ROOT / "examples/sanitized/r5_generic_source_geometry_frame.v0.1.json"
CONTRACT = ROOT / "registry/report-template-contract.v0.2.json"
COVERAGE = ROOT / "registry/report-calculation-coverage.v0.1.json"


def reference_fixture() -> dict:
    """Known-volume roof, not any user's actual building dimensions/soil."""
    legacy = json.loads(R5.read_text(encoding="utf-8"))
    return {
        "schema": "jp.structural.r6p22.independent_geometry_input.v0.1",
        "case_id": legacy["model"]["model_id"],
        "classification": "SYNTHETIC_REFERENCE",
        "model": legacy["model"],
        "gravity_m_s2": 9.81,
        "include_frame_self_weight": True,
        "provenance": {
            "geometry": "SYNTHETIC_R5_FOUR_COLUMN_RECTANGLE_GEOMETRY",
            "materials": "REFERENCE_CONCRETE_25_AND_MASONRY_18_KN_M3",
            "supports": "SYNTHETIC_R5_FOUR_FIXED_BASES",
            "loads": "ASSUMED_SLAB_SELFWEIGHT_FINISH_IMPOSED_WALL",
            "reinforcement": "SYNTHETIC_R5_BEAM_HINGES_COLUMN_BARS_JOINT_STEEL",
            "design_code": "NBC105_2025_IS456_2000_REFERENCE_NOT_CODE_APPROVAL"
        },
        "physical_materials": [
            {"id": "CONC", "unit_weight_kN_m3": 25.0,
             "source_id": "SYNTHETIC_ASSUMED_CONCRETE_25"},
            {"id": "MASONRY", "unit_weight_kN_m3": 18.0,
             "source_id": "SYNTHETIC_ASSUMED_MASONRY_18"}
        ],
        "panels": [{
            "id": "ROOF-SLAB", "boundary_node_ids": ["R1", "R2", "R3", "R4"],
            "material_id": "CONC", "thickness_m": 0.12,
            "finish_kPa": 1.5, "imposed_kPa": 2.0,
            "live_mass_factor": 0.3, "span_direction": "Y",
            "edge_beam_member_ids": ["BM1", "BM3"],
            "source_id": "SYNTHETIC_RECTANGULAR_ROOF_ONEWAY_ASSUMPTION"
        }],
        "walls": [{
            "id": "WALL-BM1", "beam_member_id": "BM1",
            "material_id": "MASONRY", "height_m": 2.8,
            "thickness_m": 0.15, "opening_area_m2": 1.5,
            "source_id": "SYNTHETIC_R5_EDGE_WALL_WITH_OPENING"
        }],
        "additional_cases": legacy["lateral_cases"],
        "combinations": legacy["combinations"],
        "design_bindings": {
            "beams": legacy["design_bindings"]["beam"],
            "columns": legacy["design_bindings"]["column"],
            "joints": legacy["design_bindings"]["joint"]
        },
        "code_references": [
            {"id": "NBC105_2025", "url":
             "https://ebps.kathmandu.gov.np/UploadFiles/NBC_105_2025_Sesmic_Design.pdf"},
            {"id": "IS456_2000", "url":
             "https://wriddodoti.gov.np/uploads/blog/20230331071217_IS-456-with-all-ammendments.pdf"}
        ]
    }


def run(source: dict, folder: Path) -> dict:
    if source.get("classification") != "SYNTHETIC_REFERENCE":
        if _inside(folder, ROOT):
            raise ValueError("Project source-derived outputs must remain outside public repository")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    coverage = json.loads(COVERAGE.read_text(encoding="utf-8"))
    result = build(source, contract=contract, coverage=coverage)
    emit(result, folder)
    verify(folder)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--reference", action="store_true")
    group.add_argument("--input", type=Path, help="PRIVATE client model input outside repo")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.input:
        if _inside(args.input, ROOT):
            raise ValueError("Custom source input must not be committed to public checkout")
        if _inside(args.output_dir, ROOT):
            raise ValueError("Custom source output must remain outside public checkout")
        source = json.loads(args.input.read_text(encoding="utf-8"))
    else:
        source = reference_fixture()
    result = run(source, args.output_dir)
    print(json.dumps({
        "schema": result["schema"],
        "case_id": result["case_id"],
        "geometry_nodes": result["source_material_gravity"]["graph"]["node_count"],
        "frame_members": result["casebook"]["counts"]["frame_members"],
        "source_gravity_kN": result["source_material_gravity"]["gravity_totals"][
            "total_source_gravity_kN"],
        "applied_FE_gravity_kN": result["actual_native_frame_gravity_kN"],
        "signed_end_rows": result["casebook"]["counts"]["signed_end_rows"],
        "engineering_approval": False
    }, sort_keys=True))


if __name__ == "__main__":
    main()
