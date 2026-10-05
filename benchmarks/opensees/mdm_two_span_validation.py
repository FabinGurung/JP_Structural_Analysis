#!/usr/bin/env python3
"""Validate the thesis SAMPLE_MDM_001 beam independently with OpenSeesPy.

This script intentionally does not mutate thesis data. It reads the approved
public demo dataset, recreates the two-span continuous beam in OpenSeesPy,
and writes a machine-readable comparison report.

The source MDM member-end moments use a clockwise-positive member-end
convention. OpenSees elasticBeamColumn local end moments are converted to that
convention before comparison.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
from pathlib import Path
from typing import Any

import openseespy.opensees as ops


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = ROOT / "examples" / "sanitized" / "mdm_two_span" / "website_demo_data.json"
DEFAULT_REPORT_PATH = ROOT / "benchmarks" / "opensees" / "results" / "mdm_two_span_validation.json"
PROJECT_CODE = "SAMPLE_MDM_001"
ABS_TOL = 1.0e-6


def nearly_equal(actual: float, expected: float, tol: float = ABS_TOL) -> bool:
    return math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=tol)


def load_source() -> dict[str, Any]:
    with SOURCE_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def validate_source_shape(data: dict[str, Any]) -> None:
    project = data.get("project", {})
    if project.get("project_code") != PROJECT_CODE:
        raise ValueError(f"Expected project_code={PROJECT_CODE!r}, got {project.get('project_code')!r}")

    members = data.get("member_summary", [])
    labels = [row.get("member_label") for row in members]
    if labels != ["AB", "BC"]:
        raise ValueError(f"Expected member_summary labels ['AB', 'BC']; got {labels!r}")

    model_members = data.get("structural_model", {}).get("members", [])
    if [row.get("member_label") for row in model_members] != ["AB", "BC"]:
        raise ValueError("structural_model.members does not match the expected AB/BC sample")


def aggregate_stored_reactions(data: dict[str, Any]) -> dict[str, float]:
    reactions: dict[str, float] = {}
    for row in data["member_summary"]:
        near_joint = row["near_joint_label"]
        far_joint = row["far_joint_label"]
        reactions[near_joint] = reactions.get(near_joint, 0.0) + float(row["near_reaction"])
        reactions[far_joint] = reactions.get(far_joint, 0.0) + float(row["far_reaction"])
    return reactions


def build_and_run_opensees(data: dict[str, Any]) -> dict[str, Any]:
    shared = {row["element_label"]: row for row in data["shared_dimensions"]}
    model_members = {row["member_label"]: row for row in data["structural_model"]["members"]}

    node_x = {
        "A": float(shared["AB"]["start_x"]),
        "B": float(shared["AB"]["end_x"]),
        "C": float(shared["BC"]["end_x"]),
    }
    node_tag = {"A": 1, "B": 2, "C": 3}

    # Use a reference E only to split the authoritative EI value into E and Iz.
    # Bending response depends on EI; no axial load is applied in this validation.
    e_ref = 25_000_000.0  # kN/m^2
    area_ref = 1.0        # m^2

    ops.wipe()
    ops.model("basic", "-ndm", 2, "-ndf", 3)

    for label in ("A", "B", "C"):
        ops.node(node_tag[label], node_x[label], 0.0)

    # A and C fixed. B is the intermediate continuous support: vertical
    # translation restrained, rotation free. Horizontal translation is left
    # free because the adjacent beam axial stiffness provides compatibility.
    ops.fix(node_tag["A"], 1, 1, 1)
    ops.fix(node_tag["B"], 0, 1, 0)
    ops.fix(node_tag["C"], 1, 1, 1)

    ops.geomTransf("Linear", 1)

    element_tag = {"AB": 1, "BC": 2}
    connectivity = {"AB": ("A", "B"), "BC": ("B", "C")}

    for label in ("AB", "BC"):
        ei = float(model_members[label]["flexural_rigidity_ei"])
        iz = ei / e_ref
        i, j = connectivity[label]
        ops.element(
            "elasticBeamColumn",
            element_tag[label],
            node_tag[i],
            node_tag[j],
            area_ref,
            e_ref,
            iz,
            1,
        )

    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)
    for label in ("AB", "BC"):
        udl = float(model_members[label]["udl"])
        if abs(udl) > ABS_TOL:
            # Source UDL values are stored as positive downward magnitudes.
            ops.eleLoad("-ele", element_tag[label], "-type", "-beamUniform", -udl)

    ops.system("BandGeneral")
    ops.numberer("Plain")
    ops.constraints("Plain")
    ops.integrator("LoadControl", 1.0)
    ops.algorithm("Linear")
    ops.analysis("Static")

    analyze_code = int(ops.analyze(1))
    if analyze_code != 0:
        raise RuntimeError(f"OpenSees static analysis failed with code {analyze_code}")

    ops.reactions()

    support_reactions_y = {
        label: float(ops.nodeReaction(node_tag[label], 2))
        for label in ("A", "B", "C")
    }

    member_end_moments: dict[str, dict[str, float]] = {}
    raw_local_forces: dict[str, list[float]] = {}
    for label in ("AB", "BC"):
        local = [float(v) for v in ops.eleResponse(element_tag[label], "localForce")]
        if len(local) < 6:
            raise RuntimeError(f"Unexpected localForce vector for {label}: {local!r}")
        raw_local_forces[label] = local
        # Convert OpenSees nodal-action sign to the clockwise-positive MDM
        # member-end convention used by website_demo_data.json.
        member_end_moments[label] = {
            "near_final_moment": -local[2],
            "far_final_moment": -local[5],
        }

    return {
        "analysis_return_code": analyze_code,
        "node_displacements": {
            label: [float(v) for v in ops.nodeDisp(node_tag[label])]
            for label in ("A", "B", "C")
        },
        "support_reactions_y": support_reactions_y,
        "member_end_moments_mdm_sign": member_end_moments,
        "raw_element_local_force_vectors": raw_local_forces,
        "opensees_version": str(ops.version()),
        "openseespy_package_version": importlib.metadata.version("openseespy"),
    }


def compare(data: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    stored_members = {row["member_label"]: row for row in data["member_summary"]}
    stored_reactions = aggregate_stored_reactions(data)

    moment_checks: list[dict[str, Any]] = []
    for member in ("AB", "BC"):
        for field in ("near_final_moment", "far_final_moment"):
            expected = float(stored_members[member][field])
            actual = float(result["member_end_moments_mdm_sign"][member][field])
            moment_checks.append(
                {
                    "member": member,
                    "quantity": field,
                    "stored_mdm": expected,
                    "opensees": actual,
                    "difference": actual - expected,
                    "pass": nearly_equal(actual, expected),
                }
            )

    reaction_checks: list[dict[str, Any]] = []
    for joint in ("A", "B", "C"):
        expected = float(stored_reactions[joint])
        actual = float(result["support_reactions_y"][joint])
        reaction_checks.append(
            {
                "joint": joint,
                "quantity": "vertical_reaction",
                "stored_mdm": expected,
                "opensees": actual,
                "difference": actual - expected,
                "pass": nearly_equal(actual, expected),
            }
        )

    total_downward_load = sum(
        float(row["udl"]) * float(row["length"])
        for row in data["structural_model"]["members"]
    )
    total_opensees_reaction = sum(float(v) for v in result["support_reactions_y"].values())
    total_stored_reaction = sum(float(v) for v in stored_reactions.values())

    equilibrium = {
        "total_downward_load_kN": total_downward_load,
        "total_opensees_vertical_reaction_kN": total_opensees_reaction,
        "total_stored_vertical_reaction_kN": total_stored_reaction,
        "opensees_global_equilibrium_pass": nearly_equal(total_opensees_reaction, total_downward_load),
        "stored_global_equilibrium_pass": nearly_equal(total_stored_reaction, total_downward_load),
    }

    moment_pass = all(row["pass"] for row in moment_checks)
    reaction_pass = all(row["pass"] for row in reaction_checks)

    if moment_pass and reaction_pass:
        status = "PASS"
    elif moment_pass and not reaction_pass:
        status = "FAIL_REACTION_DATA_RECONCILIATION"
    else:
        status = "FAIL_MODEL_OR_DATA_RECONCILIATION"

    return {
        "status": status,
        "moment_checks_pass": moment_pass,
        "reaction_checks_pass": reaction_pass,
        "moment_checks": moment_checks,
        "reaction_checks": reaction_checks,
        "equilibrium": equilibrium,
        "note": (
            "The source dataset is not modified by this validator. A reaction mismatch is retained "
            "as evidence requiring reconciliation against the governed thesis authority."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a non-zero exit code when any comparison fails.",
    )
    args = parser.parse_args()

    data = load_source()
    validate_source_shape(data)
    opensees_result = build_and_run_opensees(data)
    comparison = compare(data, opensees_result)

    report = {
        "validator": "OpenSeesPy independent validation of thesis SAMPLE_MDM_001",
        "source": str(SOURCE_PATH.relative_to(ROOT)),
        "project_code": PROJECT_CODE,
        "source_mutated": False,
        "solver": {
            "name": "OpenSeesPy",
            "package_version": opensees_result["openseespy_package_version"],
            "engine_version": opensees_result["opensees_version"],
            "analysis_type": "2D linear elastic static",
            "element_type": "elasticBeamColumn",
        },
        "model_interpretation": {
            "A": "fixed support",
            "B": "continuous intermediate support: vertical restrained, rotation free",
            "C": "fixed support",
            "load": "AB UDL applied downward; BC unloaded",
            "sign_conversion": "OpenSees local end moments negated to match source clockwise-positive MDM member-end convention",
        },
        "opensees_result": {
            "analysis_return_code": opensees_result["analysis_return_code"],
            "node_displacements": opensees_result["node_displacements"],
            "support_reactions_y": opensees_result["support_reactions_y"],
            "member_end_moments_mdm_sign": opensees_result["member_end_moments_mdm_sign"],
            "raw_element_local_force_vectors": opensees_result["raw_element_local_force_vectors"],
        },
        "comparison": comparison,
    }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2))
    if args.strict and comparison["status"] != "PASS":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
