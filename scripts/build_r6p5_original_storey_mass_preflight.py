#!/usr/bin/env python3
"""R6.5: source-reported storey mass against private *conditional* physical ledgers.

Gate18 confirms reported storey-table arithmetic only under inferred kilograms;
Gate08/R6.4 remains a PROVISIONAL physical hypothesis with 772.032917 kN gap.
Any optional owner-controlled component/mapping file is read privately and NEVER
serialized (including floor IDs, file paths, individual amounts or source hashes).
No matching arithmetic, receipt-like SHA or private-file presence grants project
source authentication, professional approval, NBC spectrum or MRSM scaling.
"""
from __future__ import annotations
import argparse
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_r6p4_physical_mass_intake import (  # noqa: E402
    SOURCE as R6P4_SOURCE, INTAKE, HEADERS, load_components, MassIntakeError
)

GATE18 = ROOT / "registry/g15-gate18-report-mass-f3-source.v0.1.json"
PREFIX = "r6p5-original-story-mass-private-preflight"
SCHEMA = "jp.structural.r6p5.original_storey_mass_preflight.v0.1"
SHA = re.compile(r"^[0-9a-f]{64}$")
REF = re.compile(r"^[A-Z0-9][A-Z0-9_-]{0,63}$")
SOURCE_STORIES = ("Story 1", "Story 2", "Story 3")
MAX_PRIVATE_STORY_DIFFERENCE_KN = Decimal("0.001")


def dec(value, key):
    try:
        v = Decimal(str(value))
    except (ValueError, TypeError, ArithmeticError) as exc:
        raise MassIntakeError(f"{key}: invalid decimal") from exc
    if isinstance(value, bool) or not v.is_finite():
        raise MassIntakeError(f"{key}: nonfinite decimal")
    return v


def source_benchmark(gate18=None, r6p4=None):
    gate18 = gate18 if gate18 is not None else json.loads(GATE18.read_text(encoding="utf8"))
    r6p4 = r6p4 if r6p4 is not None else json.loads(R6P4_SOURCE.read_text(encoding="utf8"))
    if gate18.get("schema") != "jp.structural.g15.gate18.source_mass_f3_provenance.v0.1":
        raise MassIntakeError("Gate18 source schema changed")
    if r6p4.get("schema") != "jp.structural.r6p4.mass_reconciliation_source.v0.1":
        raise MassIntakeError("R6.4 source schema changed")
    identity = gate18["source_pdf"]["sha256"]
    if not SHA.fullmatch(identity) or identity != r6p4["source_lineage"]["original_report_sha256"]:
        raise MassIntakeError("Gate18/R6.4 original report identity mismatch")
    table = gate18["source_mass_table"]
    if table.get("units_explicitly_printed") is not False or table.get("inferred_units_for_exact_match") != "kg":
        raise MassIntakeError("storey table units must remain an unverified kg inference")
    if table.get("units_inferred_not_ETABS_verified") is not True:
        raise MassIntakeError("Gate18 cannot claim native mass units verified")
    if gate18["f3_source"]["as_issued_one_way_shear_verdict"] != "NOT SAFE IN ONE WAY SHEAR":
        raise MassIntakeError("original F3 source failure must remain")
    if r6p4.get("original_physical_evidence_accepted") != 0 or r6p4.get("original_physical_evidence_total") != 15:
        raise MassIntakeError("original source evidence gates cannot close automatically")
    if r6p4.get("engineering_approval") is not False or r6p4.get("etabs_mass_authenticated") is not False:
        raise MassIntakeError("source mass authentication is not established")
    printed = table["reported_stories"]
    if len(printed) != 3 or tuple(p.get("storey") for p in printed) != SOURCE_STORIES:
        raise MassIntakeError("source printed story sequence changed")
    g = dec(table["g_m_s2_for_inference"], "standard gravity")
    if g != Decimal("9.80665"):
        raise MassIntakeError("source gravity conversion changed")
    mass_values = {p["storey"]: dec(p["printed_mass_value"], "printed storey mass") for p in printed}
    if any(v <= 0 for v in mass_values.values()):
        raise MassIntakeError("source story mass must be positive")
    expected = {k: v*g/Decimal("1000") for k,v in mass_values.items()}
    total = sum(expected.values(), Decimal(0))
    reported = dec(table["etabs_weight_kN"], "reported seismic weight")
    if reported != dec(r6p4["reported_original_ETABS_seismic_weight_kN"], "R6.4 reported weight"):
        raise MassIntakeError("Gate18 and R6.4 original weight differ")
    tolerance = Decimal(3)*Decimal("0.005")*g/Decimal("1000")+Decimal("0.00005")
    if abs(total-reported) > tolerance:
        raise MassIntakeError("reported story masses do not reproduce ETABS weight at source precision")
    if table["base_entry"]["included_in_report_automatic_seismic_weight_by_table_sum"] is not False:
        raise MassIntakeError("base printed entry inclusion cannot be inferred")
    scenario = r6p4["scenarios"]
    if len(scenario) != 2 or scenario[1]["id"] != "GATE08_WITH_HYPOTHETICAL_WALLS":
        raise MassIntakeError("Gate08 conditional sensitivity identity changed")
    conditional = dec(scenario[1]["seismic_weight_kN"], "hypothetical wall scenario")
    gap = reported-conditional
    if gap != Decimal("772.032917"):
        raise MassIntakeError("historical conditional gap cannot be silently revised")
    return expected, {
        "schema": SCHEMA,
        "scope": "SOURCE_REPORTED_KG_INFERENCE_AND_PRIVATE_CONDITIONAL_RECONCILIATION_ONLY",
        "reported_original_ETABS_weight_kN": float(reported),
        "conditional_story_table_total_kN": float(total),
        "story_table_vs_report_rounding_delta_kN": float(reported-total),
        "source_precision_bound_kN": float(tolerance),
        "source_story_count": 3,
        "source_mass_units_explicitly_printed": False,
        "source_reported_story_mass_arithmetic_consistent_if_kg": True,
        "native_original_ETABS_mass_source_export_authenticated": False,
        "gate08_hypothetical_wall_case_unexplained_kN": float(gap),
        "original_physical_evidence_accepted": 0,
        "original_physical_evidence_total": 15,
        "f3_source_verdict": "NOT SAFE IN ONE WAY SHEAR",
        "source_site_geotechnics_and_occupancy_approved": False,
        "real_original_mass_approved": False,
        "engineering_approval": False,
        "MRSM_scale_factor": None,
        "MRSM_scaling_executed": False,
    }


def private_conditional_comparison(components_path, mapping_path, expected):
    """Return ONLY non-sensitive Boolean/counts. Never disclose source rows."""
    # R6.4 already applies strict schema, SHA, eligibility and double-counting QA.
    summary = load_components(Path(components_path))
    if not summary["component_count"]:
        raise MassIntakeError("private physical mass components are missing")
    manifest = json.loads(Path(mapping_path).read_text(encoding="utf8"))
    if manifest.get("schema") != "jp.structural.r6p5.private_story_mapping.v0.1":
        raise MassIntakeError("private story mapping schema missing")
    if not SHA.fullmatch(str(manifest.get("original_native_ETABS_export_sha256", ""))):
        raise MassIntakeError("private ETABS export SHA missing")
    if not SHA.fullmatch(str(manifest.get("independent_floor_mapping_receipt_sha256", ""))):
        raise MassIntakeError("private floor mapping receipt SHA missing")
    if manifest.get("source_units_status") != "CONDITIONAL_KG_NOT_NATIVE_VERIFIED":
        raise MassIntakeError("printed story mass units still unverified")
    pairs = manifest.get("floor_bindings")
    if not isinstance(pairs, list) or len(pairs) != 3:
        raise MassIntakeError("exactly three floor bindings required")
    keys = [p.get("reported_story") for p in pairs]
    refs = [p.get("private_floor_ref") for p in pairs]
    if set(keys) != set(SOURCE_STORIES) or len(set(keys)) != 3:
        raise MassIntakeError("one-to-one source story mapping required")
    if any(not isinstance(x,str) or not REF.fullmatch(x) for x in refs) or len(set(refs))!=3:
        raise MassIntakeError("floor references must be unique, governed and non-sensitive")
    vals = {}
    with Path(components_path).open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != HEADERS:
            raise MassIntakeError("private ledger schema mismatch")
        for row in reader:
            amount = dec(row["quantity"], "quantity")*dec(row["unit_weight_kN_per_unit"], "unit load")*dec(row["seismic_participation_fraction"], "fraction")
            vals[row["floor_ref"]] = vals.get(row["floor_ref"],Decimal(0))+amount
    if set(vals) != set(refs):
        raise MassIntakeError("private floor ledger has missing or unmapped floors")
    match = all(abs(vals[ref]-expected[name])<=MAX_PRIVATE_STORY_DIFFERENCE_KN for name,ref in zip(keys,refs))
    return {
       "private_component_count": summary["component_count"],
       "private_floor_count": len(vals),
       "private_component_reviewed_row_count": summary["independently_reviewed_row_count"],
       "private_story_mapping_receipt_format_checked": True,
       "conditional_all_three_story_numeric_match": match,
       "private_row_and_per_story_values_publicly_released": False,
       "private_floor_ids_exported": False,
       "independently_authenticated_ETABS_export": False,
       "professional_review_authenticated": False,
       "actual_building_mass_accepted": False,
    }


def build(components_path=None, mapping_path=None):
    expected, result = source_benchmark()
    if (components_path is None) != (mapping_path is None):
        raise MassIntakeError("private components and private mapping must be provided together")
    if components_path is None:
        result["private_comparison"] = {
            "status": "HOLD_NO_AUTHENTICATED_NATIVE_ETABS_OR_PRIVATE_FLOOR_COMPONENTS",
            "conditional_all_three_story_numeric_match": None,
            "private_floor_ids_exported": False,
            "private_row_and_per_story_values_publicly_released": False,
            "actual_building_mass_accepted": False,
        }
    else:
        result["private_comparison"] = {
            "status": "CONDITIONAL_UNAUTHENTICATED_NUMERIC_AUDIT_NOT_APPROVAL",
            **private_conditional_comparison(components_path, mapping_path, expected)
        }
    return result


def emit(output, components_path=None, mapping_path=None):
    result=build(components_path, mapping_path)
    path=Path(output)
    path.parent.mkdir(parents=True,exist_ok=True)
    data=json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n"
    path.write_text(data,encoding="utf8")
    manifest={
        "schema": "jp.structural.r6p5.public_safe_report_manifest.v0.1",
        "json_sha256": hashlib.sha256(data.encode("utf8")).hexdigest(),
        "source_milestone": "R6.5",
        "private_source_rows_exported": False,
        "engineering_approval": False
    }
    mpath=path.with_name(path.stem+"-manifest.json")
    mpath.write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n",encoding="utf8")
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--private-components",type=Path)
    p.add_argument("--private-mapping",type=Path)
    args=p.parse_args()
    result=emit(args.output,args.private_components,args.private_mapping)
    print("R6P5_SOURCE_STORY_ARITHMETIC_PASS_PHYSICAL_COMPOSITION_HOLD",
          result["source_story_count"],"SOURCE_REPORTED_STORIES_NO_MRSM_SCALING")


if __name__=="__main__":
    main()
