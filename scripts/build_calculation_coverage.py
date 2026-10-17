#!/usr/bin/env python3
"""Deterministic build/check of public-safe calculation coverage projection."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "registry/report-calculation-coverage.v0.1.json"
OUTPUT = ROOT / "site/data/report-calculation-coverage.v0.1.json"
VALID = {"IMPLEMENTED_BOUNDED", "PARTIAL", "DRAFT_UNVALIDATED", "MISSING"}


def run(check: bool = False) -> bool:
    obj = json.loads(SOURCE.read_text(encoding="utf-8"))
    if obj.get("schema") != "jp.structural.calculation_coverage.v0.1":
        raise ValueError("Unknown coverage schema")
    requirements = obj["requirements"]
    expected = {f"M{x:02d}" for x in range(1, 17)} | {"S17", "S18"}
    actual = [x["id"] for x in requirements]
    if len(actual) != len(expected) or set(actual) != expected:
        raise ValueError("Exactly M01-M16 and S17-S18 are required")
    for row in requirements:
        if row["status"] not in VALID or not row["validation_gate"]:
            raise ValueError("Unrecognized status or missing validation gate")
        for path in row["implemented_paths"]:
            if not path.startswith("src/jp_structural/") or not (ROOT / path).is_file():
                raise ValueError(f"Implementation path missing: {path}")
    # Readable JSON is the canonical source. Projection changes only when it changes.
    result = json.dumps(obj, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    if check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != result:
            raise ValueError("Coverage projection out of sync; rerun builder")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(result, encoding="utf-8")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    run(args.check)
    print("COVERAGE_PROJECTION_PASS")
