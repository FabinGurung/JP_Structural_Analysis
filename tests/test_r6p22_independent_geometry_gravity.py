"""R6.22 independent geometry -> material loads -> OpenSees -> SAR QA.

All reference quantities and runs are synthetic, never a building approval.
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

from jp_structural.solvers.native.r6p22_geometry_gravity import (
    derive_sources, GeometryGravityHold
)
from jp_structural.reporting.r6p22_pipeline import (
    build, emit, verify, PREFIX
)
from scripts.build_r6p22_independent_geometry_sar import (
    reference_fixture, run, CONTRACT, COVERAGE, ROOT
)


@pytest.fixture(scope="module")
def spec():
    return reference_fixture()


@pytest.fixture(scope="module")
def report(spec):
    return build(
        spec,
        contract=json.loads(CONTRACT.read_text(encoding="utf-8")),
        coverage=json.loads(COVERAGE.read_text(encoding="utf-8"))
    )


def test_independent_source_volumes_and_gravity_manual_reference(spec):
    src = derive_sources(spec)
    total = src["gravity_totals"]
    # 12m² roof slab: 0.12*25=3kPa -> 36kN
    # Finish: 1.5kPa *12 = 18kN
    # Imposed: 2kPa *12 = 24kN
    # Masonry with 1.5m² opening: (2.8*4-1.5)*0.15*18 = 26.19kN
    # Beams: 14m total *0.3*0.45*25 = 47.25kN
    # Four columns: 4*3*.4*.5*25 = 60kN
    assert total["noncolumn_source_gravity_kN"] == pytest.approx(151.44)
    assert total["plumb_column_self_weight_kN"] == pytest.approx(60.0)
    assert total["total_source_gravity_kN"] == pytest.approx(211.44)
    assert total["seismic_eligible_weight_kN"] == pytest.approx(194.64)
    assert src["graph"]["all_source_nodes_reach_declared_base"] is True
    assert src["graph"]["beam_count"] == 4
    assert src["graph"]["column_count"] == 4
    assert src["graph"]["base_support_count"] == 4
    assert src["source_force_conservation_pass"] is True
    assert src["gravity_plan_first_moment_balance_pass"] is True
    assert len(src["routing"]["panel_routes"]) == 3
    assert len(src["routing"]["member_element_load_sources"]) == 11
    assert len(src["column_source_ledger"]) == 4
    assert src["seismic_masses_bound_to_dynamic_FE"] is False


def test_each_panel_routes_to_actual_full_edge_beam_in_correct_direction(spec):
    src = derive_sources(spec)
    byid = {x["panel_source_id"]: x for x in src["routing"]["panel_routes"]}
    slab = byid["ROOF-SLAB::SLAB-SELFWEIGHT"]
    assert slab["source_panel_area_m2"] == pytest.approx(12)
    assert slab["source_total_kN"] == pytest.approx(36)
    assert slab["support_beam_ids"] == ["BM1", "BM3"]
    assert slab["support_spacing_m"] == pytest.approx(3)
    assert len(slab["beam_loads"]) == 2
    for x in slab["beam_loads"]:
        assert x["downward_kN_per_m"] == pytest.approx(4.5)
        assert x["area_tributary_m2"] == pytest.approx(6.0)
        assert x["downward_resultant_kN"] == pytest.approx(18)
    wall = next(x for x in src["routing"]["member_element_load_sources"]
                if x["id"] == "WALL-BM1::MASONRY")
    assert wall["member_id"] == "BM1"
    assert wall["downward_kN_per_m"] == pytest.approx(26.19/4)


def test_column_weight_is_lumped_to_true_end_node_ids_and_flags_axial_limits(spec):
    src = derive_sources(spec)
    loads = src["column_gravity_node_loads"]
    assert len(loads) == 8
    assert all(x == pytest.approx(7.5) for x in loads.values())
    assert all(not x["local_column_axial_force_distribution_exact"]
               for x in src["column_source_ledger"])
    assert src["column_axial_force_diagram_selfweight_exact"] is False
    assert sum(loads.values()) == pytest.approx(60.0)


def test_real_opensees_solved_from_geometry_with_signed_member_actions(report):
    assert report["no_ETABS_calculation_or_export_required"]
    assert report["actual_native_frame_gravity_kN"] == pytest.approx(211.44)
    assert report["gravity_force_balance_pass"]
    assert report["gravity_plan_moment_balance_pass"]
    fe = report["casebook"]
    assert fe["counts"]["frame_members"] == 8
    assert fe["counts"]["analysis_cases"] == 3
    assert fe["counts"]["signed_combinations"] == 2
    assert fe["counts"]["signed_end_rows"] == 80
    assert fe["max_six_component_equilibrium_residual"] < 1e-5
    bycase = {x["case_id"]: x for x in fe["signed_analysis"]["raw_cases"]}
    assert set(bycase) == {"DL", "LL", "HX"}
    assert sum(x["downward_resultant_kN"] for x in
               bycase["DL"]["uniform_beam_loads"]) == pytest.approx(127.44)
    assert sum(-x["Fz_kN"] for x in
               bycase["DL"]["nodal_loads"]) == pytest.approx(60)
    assert sum(x["downward_resultant_kN"] for x in
               bycase["LL"]["uniform_beam_loads"]) == pytest.approx(24)
    assert all(x["global_equilibrium_pass"] for x in bycase.values())
    assert fe["bounded_design_checks"]["source_action_digest"] == fe["signed_input_sha256"]
    assert fe["counts"]["beams_screened"] == 1
    assert fe["counts"]["columns_screened"] == 1
    assert fe["counts"]["joints_screened"] == 1
    assert not report["engineering_approval"]
    assert not fe["construction_release_authorised"]


def test_rebar_beam_joint_and_original_F3_remain_explicitly_bounded(report):
    assert report["casebook"]["unassessed_members"]["beams"] == [
        "BM2", "BM3", "BM4"]
    assert report["casebook"]["unassessed_members"]["columns"] == [
        "COL2", "COL3", "COL4"]
    assert len(report["casebook"]["bounded_design_summary"]) == 3
    assert report["casebook"]["historical_F3_unsafe_flag_overridden"] is False
    assert not report["casebook"]["all_applicable_design_modules_complete"]
    assert report["physical_diaphragm_and_shell_stiffness"] == "NOT_MODELLED"
    assert report["column_weight_effect_on_member_axial_diagrams"] == (
        "HALF_NODAL_EQUIVALENT_APPROXIMATION"
    )


def test_physical_quantity_change_changes_true_source_load_not_hardcoded(spec):
    s = deepcopy(spec)
    s["panels"][0]["thickness_m"] = 0.15
    out = derive_sources(s)
    assert out["gravity_totals"]["total_source_gravity_kN"] == pytest.approx(220.44)
    s = deepcopy(spec)
    s["walls"][0]["opening_area_m2"] = 2.5
    out = derive_sources(s)
    assert out["gravity_totals"]["total_source_gravity_kN"] == pytest.approx(208.74)
    s = deepcopy(spec)
    s["physical_materials"][0]["unit_weight_kN_m3"] = 24
    out = derive_sources(s)
    # Vol of slab 1.44m³ + beams 1.89m³ + columns 2.4m³ = 5.73m³
    assert out["gravity_totals"]["total_source_gravity_kN"] == pytest.approx(211.44-5.73)


@pytest.mark.parametrize("mutate,pattern", [
    (lambda p: p["panels"][0].update(span_direction="TWO_WAY"), "one-way"),
    (lambda p: p["panels"][0].update(edge_beam_member_ids=["BM2", "BM4"]), "opposite full panel"),
    (lambda p: p["panels"][0].update(boundary_node_ids=["R1","R2","R3","R3"]), "four distinct"),
    (lambda p: p["panels"][0].update(thickness_m=-0.12), "thickness"),
    (lambda p: p["physical_materials"][0].update(unit_weight_kN_m3=0), "unit_weight"),
    (lambda p: p["walls"][0].update(opening_area_m2=20), "openings"),
    (lambda p: p["walls"][0].update(material_id="UNKNOWN"), "wall material"),
    (lambda p: p.update(include_frame_self_weight=False), "self-weight"),
    (lambda p: p["model"].update(supports=[]), "support"),
    (lambda p: p["model"]["nodes"][2].update(x=0, y=0, z=0), "coincident"),
])
def test_unsubstantiated_connectivity_material_support_or_slab_action_stays_hold(
    spec, mutate, pattern
):
    case = deepcopy(spec)
    mutate(case)
    with pytest.raises(GeometryGravityHold, match=pattern):
        derive_sources(case)


def test_overlapping_slab_source_cannot_double_count(spec):
    s = deepcopy(spec)
    s["panels"].append(deepcopy(s["panels"][0]))
    s["panels"][1]["id"] = "ROOF-SLAB-DUPLICATE"
    with pytest.raises(GeometryGravityHold, match="overlapping"):
        derive_sources(s)


def test_hanging_mid_beam_node_is_not_implicitly_connected(spec):
    s = deepcopy(spec)
    s["model"]["nodes"].append({
        "id": "HANGING", "storey_id": "ROOF", "x": 2., "y": 0., "z": 3.
    })
    with pytest.raises(GeometryGravityHold, match="hanging node"):
        derive_sources(s)


def test_topologically_unanchored_component_must_be_explicitly_resolved(spec):
    s = deepcopy(spec)
    s["model"]["nodes"] += [
        {"id": "FLOAT-1", "storey_id": "ROOF", "x": 10., "y": 10., "z": 4.},
        {"id": "FLOAT-2", "storey_id": "ROOF", "x": 12., "y": 10., "z": 4.}]
    s["model"]["frame_members"].append({
        "id": "FLOAT-BM", "member_type": "BEAM",
        "i_node": "FLOAT-1", "j_node": "FLOAT-2", "section_id": "BEAM-S"
    })
    with pytest.raises(GeometryGravityHold, match="cannot reach"):
        derive_sources(s)


def test_bundle_hashes_html_csv_and_member_actions_are_read_back(tmp_path, report):
    emit(report, tmp_path)
    m = verify(tmp_path)
    assert m["engineering_approval"] is False
    assert len(m["files_sha256"]) == 4
    for name, digest in m["files_sha256"].items():
        assert hashlib.sha256((tmp_path / name).read_bytes()).hexdigest() == digest
    routes = list(csv.DictReader((tmp_path/(PREFIX+"-routes.csv")).open()))
    assert len(routes) == 11
    body = (tmp_path/(PREFIX+".html")).read_text()
    assert "211.44000" in body
    assert "One-way slab" in body
    assert "casebook/independent-sar.html" in body
    fe = json.loads((tmp_path/"casebook/independent-sar.json").read_text())
    assert fe["counts"]["signed_end_rows"] == 80
    assert "M09" in (tmp_path/"casebook/independent-sar.html").read_text()
    assert fe["engineering_approval"] is False


def test_tampered_geometry_report_or_child_manifest_fails(tmp_path, report):
    emit(report, tmp_path)
    p = tmp_path/(PREFIX+"-routes.csv")
    p.write_text(p.read_text()+"fake,load\n")
    with pytest.raises(GeometryGravityHold, match="SHA mismatch"):
        verify(tmp_path)
    emit(report, tmp_path)
    q = tmp_path/"casebook/independent-sar.json"
    q.write_text(q.read_text()+"FALSIFIED")
    with pytest.raises(Exception, match="SHA256 mismatch"):
        verify(tmp_path)


def test_private_source_input_and_output_restrictions_and_no_etabs(spec,tmp_path):
    case = deepcopy(spec)
    case["classification"] = "PROJECT_SOURCE_DERIVED_UNVERIFIED"
    case["model"]["source_references"] = [
        {"id": "PRIVATE_DRAWING_RECEIPT_REDACTED", "source_type": "ARCHITECTURAL_DRAWING"}
    ]
    with pytest.raises(ValueError, match="outside public repository"):
        run(case, ROOT/"build/r6p22-unsafe-private")
    report = run(case, tmp_path/"restricted-output")
    assert report["casebook"]["classification"] == "PROJECT_SOURCE_DERIVED_UNVERIFIED"
    assert not report["engineering_approval"]
    assert verify(tmp_path/"restricted-output")["case_id"] == spec["case_id"]


def test_cli_reference_recomputes_without_etabs_and_prints_result(tmp_path):
    folder = tmp_path/"generated"
    o = subprocess.run([
        sys.executable, str(ROOT/"scripts/build_r6p22_independent_geometry_sar.py"),
        "--reference", "--output-dir", str(folder)
    ], cwd=ROOT, capture_output=True, text=True, check=True)
    report = json.loads(o.stdout)
    assert report["source_gravity_kN"] == pytest.approx(211.44)
    assert report["applied_FE_gravity_kN"] == pytest.approx(211.44)
    assert report["signed_end_rows"] == 80
    assert verify(folder)["engineering_approval"] is False

def test_custom_source_cli_cannot_write_to_public_checkout_even_if_labelled_synthetic(spec, tmp_path):
    input_file = tmp_path / "synthetic-but-custom.json"
    input_file.write_text(json.dumps(spec), encoding="utf-8")
    run_cli = subprocess.run([
        sys.executable, str(ROOT/"scripts/build_r6p22_independent_geometry_sar.py"),
        "--input", str(input_file), "--output-dir", str(ROOT/"build/r6p22-untrusted-output")
    ], cwd=ROOT, capture_output=True, text=True)
    assert run_cli.returncode != 0
    assert "outside public checkout" in run_cli.stderr
