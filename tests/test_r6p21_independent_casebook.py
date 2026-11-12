"""R6.21 regression: genuine OpenSees solve -> code prechecks -> source-labelled SAR.

Synthetic inputs only. Assertions do not constitute real building certification.
"""
from __future__ import annotations

from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from jp_structural.reporting.independent_casebook import (
    SCHEMA, IndependentSARInputError, build, emit, render_html,
    validate_input, verify_bundle
)
from scripts.build_r6p21_independent_sar import reference_fixture, run, ROOT


@pytest.fixture(scope="module")
def reference_result():
    payload = reference_fixture()
    contract = json.loads((ROOT / "registry/report-template-contract.v0.2.json").read_text())
    coverage = json.loads((ROOT / "registry/report-calculation-coverage.v0.1.json").read_text())
    return build(payload, contract=contract, coverage=coverage)


def test_parameterized_opensees_static_cases_are_genuinely_solved_and_balanced(reference_result):
    result = reference_result
    assert result["schema"] == SCHEMA
    assert result["analysis_mode"] == "FIRST_PARTY_OPENSEES_ELASTIC_STATIC_3D_FRAMES"
    assert not result["native_ETABS_output_required"]
    assert result["counts"]["analysis_cases"] == 2
    assert result["counts"]["signed_combinations"] == 2
    assert result["counts"]["frame_members"] == 4
    assert result["counts"]["signed_end_rows"] == 32
    assert result["max_six_component_equilibrium_residual"] < 1e-5
    assert all(x["global_equilibrium_pass"]
               for x in result["signed_analysis"]["raw_cases"])
    assert result["signed_input_sha256"] == result[
        "bounded_design_checks"]["source_action_digest"]
    assert len(result["signed_results_sha256"]) == 64
    assert not result["engineering_approval"]
    assert not result["construction_release_authorised"]


def test_all_signed_member_end_actions_are_from_same_case_and_sum_before_enveloping(reference_result):
    result = reference_result
    rows = {(r["kind"], r["case_id"], r["member_id"], r["end"]): r
            for r in result["signed_end_rows"]}
    assert len(rows) == 32
    for member in ("BM1", "BM2", "COL1", "COL2"):
        for end in ("I", "J"):
            g = rows[("RAW", "G", member, end)]
            hx = rows[("RAW", "HX", member, end)]
            for component in ("N", "Vy", "Vz", "T", "My", "Mz"):
                assert rows[("COMBINATION", "U_PLUS", member, end)][component] == pytest.approx(
                    1.2 * g[component] + 1.2 * hx[component], abs=1e-6)
                assert rows[("COMBINATION", "U_MINUS", member, end)][component] == pytest.approx(
                    1.2 * g[component] - 1.2 * hx[component], abs=1e-6)


def test_project_report_reports_only_screened_members_and_never_implies_complete_design(reference_result):
    result = reference_result
    assert result["counts"]["beams_screened"] == 1
    assert result["counts"]["columns_screened"] == 1
    assert result["counts"]["joints_screened"] == 1
    assert result["unassessed_members"] == {
        "beams": ["BM2"], "columns": ["COL2"]
    }
    assert result["module_status"]["M04"] == "BOUNDED_FE"
    assert all(result["module_status"][key] == "BOUNDED_RC"
               for key in ("M08", "M09", "M10"))
    assert all(result["module_status"][key] == "NOT_EVALUATED"
               for key in ("M02", "M03", "M05", "M06", "M07", "M11",
                           "M12", "M13", "M14", "M15", "M16", "S18"))
    assert [x["id"] for x in result["chapters"]] == [
        "01", "02", "03", "04", "05", "06", "07"
    ]
    assert not result["all_applicable_design_modules_complete"]
    assert not result["historical_F3_unsafe_flag_overridden"]
    assert result["input_source_references"][0]["source_type"] == "SYNTHETIC_TEST"


def test_genuine_rc_checks_and_model_provenance(reference_result):
    checks = reference_result["bounded_design_checks"]
    assert checks["beam_design"] and checks["column_design"] and checks["joint_design"]
    assert [r["member_id"] for r in checks["beam_design"]] == ["BM1"]
    assert [r["member_id"] for r in checks["column_design"]] == ["COL1"]
    assert [r["joint_node_id"] for r in checks["joint_design"]] == ["T1"]
    assert all(not r["check"]["engineering_approval"] for r in checks["beam_design"])
    assert all(not scenario["check"]["engineering_approval"]
               for x in checks["column_design"] for scenario in x["scenarios"])
    assert not checks["engineering_approval"]


def test_deterministic_input_source_lineage_not_magic_etabs_matching(reference_result):
    payload = reference_fixture()
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    assert reference_result["input_sha256"] == hashlib.sha256(data.encode()).hexdigest()
    assert reference_result["classification"] == "SYNTHETIC_REFERENCE"
    assert "ETABS" not in reference_result["analysis_mode"]
    assert reference_result["project_geometry_and_loads_approved"] is False


def test_public_synthetic_casebook_files_are_hashed_and_reproducible(tmp_path, reference_result):
    path1 = tmp_path / "run1"
    path2 = tmp_path / "run2"
    one = emit(reference_result, path1)
    two = emit(reference_result, path2)
    assert one == two == verify_bundle(path1)
    assert set(one["files"]) == {
        "independent-sar.json",
        "independent-sar.html",
        "independent-sar-member-ends.csv",
    }
    for filename in one["files"]:
        assert (path1 / filename).read_bytes() == (path2 / filename).read_bytes()
    rows = list(csv.DictReader((path1 / "independent-sar-member-ends.csv").open()))
    assert len(rows) == 32
    html = (path1 / "independent-sar.html").read_text()
    assert "Chapter 05" in html and "Chapter 06" in html
    assert "NOT ENGINEERING APPROVED" in html
    assert "Unassessed beam members" in html and "BM2" in html
    assert "Unassessed column members" in html and "COL2" in html
    assert "F3 adverse finding" in html


def test_hash_readback_rejects_tampered_csv_and_missing_members(tmp_path, reference_result):
    dest = tmp_path / "case"
    emit(reference_result, dest)
    csv_path = dest / "independent-sar-member-ends.csv"
    csv_path.write_text(csv_path.read_text() + "FORGED\n")
    with pytest.raises(IndependentSARInputError, match="SHA256 mismatch"):
        verify_bundle(dest)
    emit(reference_result, dest)
    json_path = dest / "independent-sar.json"
    payload = json.loads(json_path.read_text())
    payload["counts"]["signed_end_rows"] = 33
    json_path.write_text(json.dumps(payload))
    with pytest.raises(IndependentSARInputError, match="SHA256 mismatch"):
        verify_bundle(dest)


def test_fail_closed_against_source_identity_overclaim_and_missing_parameters():
    base = reference_fixture()
    for modify in (
        lambda p: p["provenance"].pop("geometry"),
        lambda p: p["provenance"].update({"loads": ""}),
        lambda p: p.update({"classification": "ENGINEER_APPROVED"}),
        lambda p: p.update({"engineering_approval": True}),
        lambda p: p["model"].update({"source_references": []}),
        lambda p: p["design_bindings"].pop("columns"),
        lambda p: p["code_references"].clear(),
        lambda p: p.update({"case_id": "../../attack"}),
    ):
        case = deepcopy(base)
        modify(case)
        with pytest.raises(IndependentSARInputError):
            validate_input(case)


def test_source_derived_input_does_not_require_etabs_but_must_remain_private(tmp_path):
    case = reference_fixture()
    case["classification"] = "PROJECT_SOURCE_DERIVED_UNVERIFIED"
    with pytest.raises(IndependentSARInputError, match="synthetic source registry"):
        validate_input(case)
    case["model"]["source_references"] = [{
        "id": "REDACTED_SOURCE_DRAWING_ID",
        "source_type": "ARCHITECTURAL_DRAWING"
    }]
    validate_input(case)
    # Unvalidated source models may be calculated privately but never written
    # into the public GitHub checkout, even under a build/ or site/ path.
    with pytest.raises(ValueError, match="outside public repository"):
        run(case, ROOT / "build" / "r6p21-project-sensitive")
    report, _ = run(case, tmp_path / "private-output")
    assert report["classification"] == "PROJECT_SOURCE_DERIVED_UNVERIFIED"
    assert not report["engineering_approval"]
    assert not report["all_applicable_design_modules_complete"]


def test_cli_reference_reruns_real_fe_and_outputs_a_verifiable_artifact(tmp_path):
    out = tmp_path / "cli"
    process = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_r6p21_independent_sar.py"),
         "--reference", "--output-dir", str(out)],
        cwd=ROOT, text=True, capture_output=True, check=True
    )
    details = json.loads(process.stdout)
    assert details["frame_members"] == 4
    assert details["signed_end_rows"] == 32
    assert details["engineering_approval"] is False
    assert verify_bundle(out)["case_id"] == "SYNTHETIC-D2-FRAME-001"
