"""R6.23 independent source-to-multistorey OpenSees FE numerical regression.

All fixture geometry and materials are synthetic; no actual building QA.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import subprocess
import sys

import pytest

from r6p23.engine import (
    build, digest, solve_case, topology, validate, StructuralHold
)
from r6p23.runner import (
    reference_fixture, emit, verify, PREFIX, ROOT
)


@pytest.fixture(scope="module")
def example():
    return reference_fixture()


@pytest.fixture(scope="module")
def top(example):
    return topology(example)


@pytest.fixture(scope="module")
def result(example):
    return build(example)


def test_true_two_storey_shared_node_topology_and_removed_slab_opening(top):
    assert top["shell_count"] == 31
    assert top["beam_segment_count"] == 32
    assert top["column_segment_count"] == 8
    assert len(top["supports"]) == 4
    assert top["floor_areas_m2"] == {"1": 16.0, "2": 15.0}
    assert top["removed_opening_cells"] == {"1": [], "2": [[1, 1]]}
    assert top["all_shell_nodes_connected_to_base"] is True
    assert top["coordinate_proximity_ties_used"] is False
    assert (2, 1, 1) in top["active"]
    assert not any((c["floor"], c["i"], c["j"]) == (2, 1, 1)
                   for c in top["shell_cells"])
    assert all(all(node in top["active"] for node in p["corners"])
               for p in top["shell_cells"])
    for beam in top["beams"]:
        assert beam["a"] in top["active"] and beam["b"] in top["active"]
    for col in top["columns"]:
        assert col["a"] in top["active"] and col["b"] in top["active"]


def test_independent_manual_source_volume_takeoff(result):
    g = result["source_ledger"]["gravity_totals_kN"]
    # 31 square meters × (0.12×25+1.5) kPa = 139.5kN
    # 2x16m perimeter downstand .30×(.45-.12)×25 = 79.2kN
    # 8x3m columns .4×.4×25 = 96kN
    # wall: (2.5×4-1)×.15×18 = 24.3kN
    # DL 139.5+79.2+96+24.3 = 339kN, live 31×2 = 62kN
    assert g["SHELL_DL"] == pytest.approx(139.5)
    assert g["FRAME_DL"] == pytest.approx(199.5)
    assert g["DL"] == pytest.approx(339.0)
    assert g["LL"] == pytest.approx(62.0)
    components = result["source_ledger"]["components"]
    assert sum(x["weight_kN"] for x in components if x["kind"] == "WALL") == pytest.approx(24.3)
    assert sum(x["weight_kN"] for x in components if x["kind"] == "BEAM_DOWNSTAND") == pytest.approx(79.2)
    assert sum(x["weight_kN"] for x in components if x["kind"] == "COLUMN_AXIAL") == pytest.approx(96.0)
    assert sum(x["weight_kN"] for x in components if x["kind"] == "SLAB_PLUS_FINISH") == pytest.approx(139.5)


def test_real_shell_to_biaxial_beam_loadpath_with_no_assumed_tributary_split(result):
    for mode in ("FLEXIBLE_SHELL", "RIGID_INPLANE_MPC"):
        raw = result["solutions"][mode]
        assert raw["SHELL_DL"]["counts"] == {
            "analysis_nodes": 54,
            "shell_elements": 31,
            "beam_segments": 32,
            "column_segments": 8,
            "base_supports": 4,
        }
        assert raw["SHELL_DL"]["gravity_resultants"]["Fz_kN"] == pytest.approx(139.5)
        assert raw["FRAME_DL"]["gravity_resultants"]["Fz_kN"] == pytest.approx(199.5)
        assert raw["DL"]["gravity_resultants"]["Fz_kN"] == pytest.approx(339.0)
        assert raw["LL"]["gravity_resultants"]["Fz_kN"] == pytest.approx(62.0)
        assert raw["HX"]["gravity_resultants"]["Fx_kN"] == pytest.approx(10)
        assert raw["SHELL_DL"]["shell_to_beam_directional_vz_abs_sum"]["X"] > 1e-4
        assert raw["SHELL_DL"]["shell_to_beam_directional_vz_abs_sum"]["Y"] > 1e-4
        assert all(r["force_moment_balance_pass"] for r in raw.values())
        assert all(r["max_equilibrium_residual"] < 1e-3 for r in raw.values())
        assert raw["SHELL_DL"]["floor_max_vertical_displacement_m"]["2"] > 0
        assert set(raw["DL"]["support_reactions"]) == {
            "L0:X0:Y0", "L0:X0:Y4", "L0:X4:Y0", "L0:X4:Y4"
        }


def test_diaphagm_rigid_xyrz_kinematics_without_inventing_vertical_fixity(result):
    row = result["solutions"]["RIGID_INPLANE_MPC"]["HX"]
    assert row["rigid_inplane_MPC_residual_m"] < 1e-7
    other = result["solutions"]["FLEXIBLE_SHELL"]["HX"]
    assert other["rigid_inplane_MPC_residual_m"] is None
    assert row["floor_max_vertical_displacement_m"]["1"] >= 0
    assert other["force_moment_balance_pass"]
    assert result["in_plane_diaphagm_choice_source_required"]
    assert result["site_specific_seismic_modal_design_complete"] is False


def test_source_signed_load_algebra_same_model_frame_actions(result):
    for mode in result["modes"]:
        raw = result["solutions"][mode]
        cmb = result["signed_combinations"][mode]
        for member in raw["DL"]["signed_frame_end_actions"]:
            for end in ("I", "J"):
                for component in ("N", "Vy", "Vz", "T", "My", "Mz"):
                    g = raw["DL"]["signed_frame_end_actions"][member][end][component]
                    q = raw["LL"]["signed_frame_end_actions"][member][end][component]
                    x = raw["HX"]["signed_frame_end_actions"][member][end][component]
                    for cid, sign in (("U_PLUS", 1), ("U_MINUS", -1)):
                        value = cmb[cid]["signed_member_end_actions"][member][end][component]
                        assert value == pytest.approx(1.2*g + 1.5*q + sign*x, abs=1e-7)
        assert all(not c["NBC_code_completeness_verified"] for c in cmb.values())


def test_opening_change_recomputes_physical_shell_volume_without_doublecount(example):
    full = deepcopy(example)
    full["floors"][1]["opening_cells"] = []
    src = build(full, modes=("FLEXIBLE_SHELL",))
    assert src["topology"]["shell_count"] == 32
    assert src["topology"]["floor_areas_m2"]["2"] == pytest.approx(16)
    assert src["source_ledger"]["gravity_totals_kN"]["DL"] == pytest.approx(343.5)
    assert src["source_ledger"]["gravity_totals_kN"]["LL"] == pytest.approx(64.0)
    assert src["solutions"]["FLEXIBLE_SHELL"]["DL"]["force_moment_balance_pass"]


@pytest.mark.parametrize("edit, reason", [
    (lambda x: x["floors"][1].update(opening_cells=[[0, 0]]), "internal"),
    (lambda x: x["floors"][1].update(opening_cells=[[1, 1], [1, 1]]), "duplicated"),
    (lambda x: x["floors"][1].update(thickness_m=.50), "downstand"),
    (lambda x: x["floors"][0].update(level_index=2), "ordered"),
    (lambda x: x["floors"][0].update(imposed_kPa=-1), "nonnegative"),
    (lambda x: x["walls"][0].update(opening_area_m2=100), "openings"),
    (lambda x: x["walls"][0].update(edge="Y_OTHER"), "real floor"),
    (lambda x: x["concrete"].update(E_kN_m2=0), "positive"),
    (lambda x: x["x_grid_m"].update if False else x["x_grid_m"].__setitem__(2, 1), "ascending"),
    (lambda x: x["lateral_cases"][0].update(grid_i=99), "real floor grid"),
    (lambda x: x["combinations"][0]["factors"].update(ETABS=9), "unsupported"),
])
def test_unsupported_geometry_or_made_up_source_is_a_hold(example, edit, reason):
    spec = deepcopy(example)
    edit(spec)
    with pytest.raises(StructuralHold, match=reason):
        validate(spec)


def test_original_F3_and_professional_restrictions_unchanged(result):
    assert result["engineering_approval"] is False
    assert result["construction_release_authorised"] is False
    assert result["historical_F3_unsafe_status_retained"] is True
    assert result["soil_foundation_member_capacity_design_complete"] is False
    assert result["two_way_shell_plate_behavior"] == "REAL_ELASTIC_SHELLMITC4_NO_TRIBUTARY_SPLIT"
    assert result["classification"] == "SYNTHETIC_REFERENCE"


def test_source_checksum_and_output_bytes_deterministic(tmp_path, result, example):
    a = tmp_path/"a"
    b = tmp_path/"b"
    ma = emit(result, a)
    mb = emit(result, b)
    assert verify(a) == ma == mb
    assert result["source_SHA256"] == digest(example)
    for name in ma["files"]:
        assert (a/name).read_bytes() == (b/name).read_bytes()
    html_body = (a/(PREFIX+".html")).read_text()
    assert "339.000" in html_body and "62.000" in html_body
    assert "ENGINEERING HOLD" in html_body
    assert "ShellMITC4" in html_body
    assert "opening" in html_body.lower()


def test_mutated_html_csv_json_refused(tmp_path, result):
    emit(result, tmp_path)
    f = tmp_path/(PREFIX+".html")
    f.write_text(f.read_text()+"UNVERIFIED")
    with pytest.raises(StructuralHold, match="Tampered"):
        verify(tmp_path)
    emit(result, tmp_path)
    f = tmp_path/(PREFIX+".json")
    f.write_text(f.read_text().replace('"engineering_approval": false',
                                       '"engineering_approval": true', 1))
    with pytest.raises(StructuralHold, match="Tampered"):
        verify(tmp_path)


def test_public_synthetic_cli_runs_r6p23_end_to_end(tmp_path):
    d = tmp_path/"generated"
    p = subprocess.run([
        sys.executable, "-m", "r6p23.runner", "--reference",
        "--output-dir", str(d)
    ], cwd=ROOT, capture_output=True, text=True, check=True)
    a = json.loads(p.stdout)
    assert a["shell_elements"] == 31
    assert a["dead_kN"] == pytest.approx(339)
    assert a["live_kN"] == pytest.approx(62)
    assert a["report_generated"] and not a["engineering_approval"]
    verify(d)


def test_custom_user_input_can_never_be_exported_to_public_checkout(example, tmp_path):
    path = tmp_path/"input.json"
    path.write_text(json.dumps(example), encoding="utf-8")
    p = subprocess.run([
        sys.executable, "-m", "r6p23.runner", "--input", str(path),
        "--output-dir", str(ROOT/"build/r6p23-private-bad")
    ], cwd=ROOT, capture_output=True, text=True)
    assert p.returncode != 0
    assert "outside public repository" in p.stderr
