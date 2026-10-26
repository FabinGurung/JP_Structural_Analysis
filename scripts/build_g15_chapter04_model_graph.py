#!/usr/bin/env python3
"""Chapter 4: reproducible source-to-trial OpenSees object and load identity graph.

An index of a hypothetical source-derived model, NOT reconstructed ETABS object
IDs or authenticated member, shell, wall, foundation and mass assignments.
The signed response is freshly solved in OpenSeesPy by Gate21.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_g15_gate21_report import calculate, PDF_ID, PDF_SHA, get_inputs
from scripts.run_g15_open_3d import source

SCHEMA = "jp.structural.g15.chapter04.source_model_load_graph.v0.1"
STATUSES = {"VERIFIED_SOURCE", "SOURCE_REPORTED_UNVERIFIED", "DERIVED",
            "ASSUMED", "MISSING", "CONFLICT", "NOT_APPLICABLE"}
GATE20 = ROOT / "registry/g15-gate20-source-crosswalk.v0.1.json"
RATE_FILE = ROOT / "registry/g15-chapter02-load-facts.v0.1.json"
GRID_FILE = ROOT / "site/data/g15-working-grid.public.v0.1.json"

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build():
    grid = source()
    gate = read_json(GATE20)
    rates = read_json(RATE_FILE)
    assert gate["source_report_sha256"] == rates["original_pdf_sha256"] == PDF_SHA
    assert gate["source_F3_status"] == "NOT SAFE IN ONE WAY SHEAR"
    assert len(gate["gates"]) == 15 and all(not x["accepted"] for x in gate["gates"])
    assert rates["geometry_source"]["actual_area_polygon_ids_recovered"] is False
    assert rates["geometry_source"]["actual_wall_segment_ids_recovered"] is False
    assert grid["safety"]["engineering_approval"] is False
    assert grid["hypothetical_beam_edge_indices"] == [30, 31]

    solved, signed = calculate()  # REAL OpenSees FE solve and signed numerical checks
    request, _ = get_inputs()
    assert solved["counts"]["members"] == 165 and solved["counts"]["nodes"] == 92
    assert solved["case_count"] == 5 and len(signed) == 825
    assert solved["model_ETABS_source_verified"] is False
    assert solved["engineering_approval"] is False and solved["F3_verdict"] == "NOT SAFE IN ONE WAY SHEAR"
    assert request == solved["inputs"]
    cols = grid["column_positions_mm"]
    levels = grid["floor_levels_mm"]
    edges = grid["beam_edges"]
    positions = {r[0]: r for r in cols}
    nodes = []
    for index, (label, x, y, sec) in enumerate(cols):
        for level, z in enumerate(levels):
            nodes.append({
                "id": f"N-{label}-L{level}", "solver_tag": 100 * index + level + 1,
                "grid": label, "storey": level,
                "xyz_m": [x / 1000, y / 1000, z / 1000],
                "section_at_grid": sec, "source_observation_id": "SRC-PLAN-GRID",
                "original_ETABS_joint_id": None, "status": "DERIVED",
                "engineering_accepted": False
            })
    node_by_id = {n["id"]: n for n in nodes}
    elements = []
    tag = 0
    for label, x, y, sec in cols:
        for level in range(1, 4):
            tag += 1
            elements.append({
                "id": f"COL-{label}-L{level-1}-{level}", "solver_tag": tag,
                "type": "COLUMN", "grid": label, "storey": level,
                "node_i": f"N-{label}-L{level-1}",
                "node_j": f"N-{label}-L{level}",
                "section_id": sec, "material_id": "M20-TRIAL",
                "source_observation_id": "SRC-PLAN-GRID",
                "original_ETABS_frame_id": None, "status": "DERIVED",
                "connection_status": "ASSUMED", "engineering_accepted": False
            })
    for idx, (a, b) in enumerate(edges):
        for level in range(1, 4):
            tag += 1
            connector = idx in grid["hypothetical_beam_edge_indices"]
            elements.append({
                "id": f"BEAM-{a}-{b}-L{level}", "solver_tag": tag,
                "type": "BEAM", "grid": a + ":" + b, "storey": level,
                "node_i": f"N-{a}-L{level}", "node_j": f"N-{b}-L{level}",
                "section_id": "BEAM", "material_id": "M20-TRIAL",
                "source_observation_id": "SRC-INFERRED-EDGES",
                "original_ETABS_frame_id": None, "status": "ASSUMED" if connector else "DERIVED",
                "connection_status": "UNVERIFIED_CONNECTOR" if connector else "INFERRED_PLAN_EDGE",
                "engineering_accepted": False
            })
    assert len(nodes) == 92 and len(node_by_id) == 92
    assert len(elements) == 165 and len({e["id"] for e in elements}) == 165
    assert [e["solver_tag"] for e in elements] == list(range(1, 166))
    assert len([e for e in elements if e["connection_status"] == "UNVERIFIED_CONNECTOR"]) == 6
    for e in elements:
        assert e["node_i"] in node_by_id and e["node_j"] in node_by_id
        assert e["node_i"] != e["node_j"] and e["status"] in STATUSES
        for n in ("node_i", "node_j"):
            assert all(math.isfinite(x) for x in node_by_id[e[n]]["xyz_m"])
    action_ids = {row["member"] for row in signed}
    assert action_ids == {e["id"] for e in elements}

    supports = [{
        "id": "FIXITY-TRIAL-" + label, "node_id": f"N-{label}-L0",
        "restrained_dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"],
        "translation_stiffness_kN_m": None, "rotation_stiffness_kNm_rad": None,
        "soil_mechanism": "UNKNOWN", "source_basis": "Numerical solver default, not original foundation detail",
        "status": "ASSUMED", "engineering_accepted": False
    } for label, *_ in cols]
    assert len(supports) == 23

    cases = ["GRAVITY", "EQ_PLUS_X", "EQ_MINUS_X", "EQ_PLUS_Y", "EQ_MINUS_Y"]
    assert [c["name"] for c in solved["cases"]] == cases
    seismic = solved["ESM"]["floor"]
    loads = []
    for case in cases:
        for level in range(1, 4):
            f = seismic[level-1]
            per_node_gravity = request["floor_weights_kN"][level-1] / len(cols)
            per_node_lateral = f["Fi_kN"] / len(cols)
            for label, *_ in cols:
                vec = ([0., 0., -per_node_gravity] if case == "GRAVITY"
                       else [(1 if case == "EQ_PLUS_X" else -1) * per_node_lateral, 0., 0.]
                       if case.endswith("_X")
                       else [0., (1 if case == "EQ_PLUS_Y" else -1) * per_node_lateral, 0.])
                loads.append({
                    "id": f"TRIAL-{case}-{label}-L{level}",
                    "pattern_id": case, "solver_case_id": case,
                    "target_node_id": f"N-{label}-L{level}",
                    "force_xyz_kN": vec, "distribution": "EQUAL_PER_GRID_POSITION",
                    "source_observation_id": "SRC-CONDITIONAL-MASS",
                    "status": "ASSUMED",
                    "included_in_seismic_mass": None,
                    "physical_load_assignment_accepted": False
                })
    assert len(loads) == 5 * 3 * 23
    case_loads = []
    for name, record in zip(cases, solved["cases"]):
        c = [r for r in loads if r["pattern_id"] == name]
        actual = [sum(r["force_xyz_kN"][j] for r in c) for j in range(3)]
        reaction = record["reactions_kN_xyz"]
        residual = max(abs(actual[j] + reaction[j]) for j in range(3))
        assert residual < 0.001
        assert record["force_residual_kN"] < 0.001
        assert record["moment_residual_kNm"] < 0.001
        case_loads.append({
            "id": name, "assignment_count": len(c),
            "sum_applied_force_xyz_kN": actual,
            "sum_opensees_reactions_xyz_kN": reaction,
            "force_residual_kN": residual,
            "moment_residual_kNm": record["moment_residual_kNm"],
            "signed_member_end_records": len([v for v in signed if v["case"] == name]),
            "source_assignment_verified": False
        })
    reported = [{
        "id": row["id"], "description": row.get("label", row.get("space", "")),
        "unit": "kN/m" if "printed_kN_m" in row else "kN/m2",
        "reported_value": row.get("printed_kN_m", row.get("value_kN_m2")),
        "section": "2.6.3" if "printed_kN_m" in row else "2.6.2",
        "physical_object_id": None, "status": "SOURCE_REPORTED_UNVERIFIED",
        "assigned_to_solver": False
    } for row in rates["reported_line_rates"] + rates["reported_live_load_rates"]]
    assert len(reported) == 8
    assert all(r["physical_object_id"] is None and not r["assigned_to_solver"] for r in reported)

    return {
        "schema": SCHEMA,
        "project_id": "G15-ORIGINAL-REPORT-RECONSTRUCTION",
        "model_version": "G15-PROVISIONAL-165-V01",
        "source_documents": [{"id": "SRC-ORIGINAL-PDF", "drive_file_id": PDF_ID,
          "sha256": PDF_SHA, "status": "SOURCE_REPORTED_UNVERIFIED",
          "scope": "Original Chapter 4 §4.1 Fig 9, §4.2 Figs 10-11; object IDs absent"},
          {"id": "SRC-PLAN-GRID", "document_id": "SRC-ORIGINAL-PDF",
           "scope": "Original source plans and column schedule; de-identified derived grid",
           "status": "DERIVED"},
          {"id": "SRC-INFERRED-EDGES", "document_id": "SRC-ORIGINAL-PDF",
           "scope": "32 trial plan beam edges, 2 explicitly hypothetical, replicated on 3 levels",
           "status": "ASSUMED"},
          {"id": "SRC-CONDITIONAL-MASS", "document_id": "SRC-ORIGINAL-PDF",
           "scope": "Conditional story weights; distributed equally, NOT actual element loads",
           "status": "ASSUMED"}],
        "input_hashes": {"grid_SHA256": sha256(GRID_FILE),
                         "chapter02_load_facts_SHA256": sha256(RATE_FILE),
                         "gate20_crosswalk_SHA256": sha256(GATE20)},
        "coordinate_units": "metres",
        "force_units": "kN",
        "nodes": nodes, "elements": elements, "supports": supports,
        "trial_nodal_loads": loads, "solved_cases": case_loads,
        "unassigned_source_report_load_rates": reported,
        "counts": {"nodes": 92, "members": 165, "supports": 23,
                   "source_unverified_connectors": 6, "trial_load_assignments": len(loads),
                   "open_sees_signed_member_case_records": len(signed),
                   "authenticated_original_frame_ids": 0,
                   "authenticated_original_area_ids": 0,
                   "authenticated_original_wall_segment_ids": 0,
                   "source_gate20_open": 15},
        "conditional_seismic_weight_kN": solved["ESM"]["W_kN"],
        "original_ETABS_reported_seismic_weight_kN": solved["ESM"]["W_reported_ETABS_kN"],
        "case_type": "OPENSEES_5_CASE_LINEAR_ELASTIC_TRIAL",
        "actual_selfweight_assembled": False,
        "actual_live_floor_finish_loads_mapped": False,
        "actual_wall_line_loads_mapped": False,
        "actual_seismic_mass_assembled": False,
        "supports_authenticated": False,
        "original_ETABS_model_authenticated": False,
        "engineering_approval": False,
        "original_F3_one_way_shear": "NOT SAFE IN ONE WAY SHEAR"
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    data = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("CHAPTER4_OPENSEES_SOURCE_TO_TRIAL_GRAPH_PASS",
          data["counts"]["members"], data["counts"]["trial_load_assignments"],
          "ORIGINAL_F3_HOLD")

if __name__ == "__main__":
    main()
