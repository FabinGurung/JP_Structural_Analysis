"""R6.24 independent mesh/source and public readback QA (synthetic inputs)."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from r6p23.engine import build, digest, StructuralHold, topology, _load_book
from r6p23.runner import reference_fixture
from r6p23.convergence import SCHEMA, preflight, refine, screen
from r6p23.site_export import export, verify_export


@pytest.fixture(scope="module")
def original():
    return reference_fixture()


@pytest.fixture(scope="module")
def coarse_result(original):
    return build(original)


@pytest.fixture(scope="module")
def mesh(original, coarse_result):
    return screen(original, coarse_result)


def test_refined_geometry_has_same_two_floor_physics_and_fourfold_shells(original):
    fine = refine(original)
    assert fine["x_grid_m"] == [x*.5 for x in range(9)]
    assert fine["y_grid_m"] == [x*.5 for x in range(9)]
    assert fine["floors"][1]["opening_cells"] == [
        [2,2],[2,3],[3,2],[3,3]
    ]
    assert fine["lateral_cases"][0]["grid_i"] == 8
    assert fine["lateral_cases"][0]["grid_j"] == 8
    a,b=topology(original),topology(fine)
    assert a["shell_count"] == 31 and b["shell_count"] == 124
    assert a["beam_segment_count"] == 32 and b["beam_segment_count"] == 64
    assert a["column_segment_count"] == b["column_segment_count"] == 8
    assert a["floor_areas_m2"] == b["floor_areas_m2"]
    g0=_load_book(a)["expected_case_gravity_kN"]
    g1=_load_book(b)["expected_case_gravity_kN"]
    assert g0 == pytest.approx(g1)
    assert g0["DL"] == pytest.approx(339.)
    assert g0["LL"] == pytest.approx(62.)


def test_two_independent_meshes_execute_real_OpenSees_and_compare_matched_points(mesh):
    assert mesh["schema"] == SCHEMA
    assert mesh["coarse_mesh_shells"] == 31
    assert mesh["refined_mesh_shells"] == 124
    assert mesh["floor_area_preserved"] and mesh["opening_regions_preserved"]
    assert mesh["all_source_gravity_totals_preserved"]
    assert mesh["independent_FE_6axis_equilibrium"]
    assert {x["mode"] for x in mesh["comparisons"]} == {
        "FLEXIBLE_SHELL", "RIGID_INPLANE_MPC"
    }
    assert {x["case"] for x in mesh["comparisons"]} == {"DL","HX"}
    assert len(mesh["comparisons"]) == 4
    for x in mesh["comparisons"]:
        assert x["matched_original_nodes"] > 0
        assert len(x["base_reaction_differences"]) == 4
        assert x["max_response_difference_over_response_peak"] >= 0
        assert x["max_base_Fz_difference_over_total_vertical_action"] >= 0
        assert x["full_asymptotic_mesh_convergence_proven"] is False
        assert x["coarse_max_six_axis_equilibrium_residual"] >= 0
        assert x["refined_max_six_axis_equilibrium_residual"] >= 0
    assert mesh["full_asymptotic_mesh_convergence_proven"] is False
    assert mesh["engineering_approval"] is False


def test_preflight_never_promotes_synthetic_or_unverified_project_evidence(original):
    empty=preflight()
    assert not empty["etabs_native_mesh_or_calculation_required"]
    assert len(empty["physical_source_requirements"]) >= 6
    assert not empty["source_evidence_accepted"]
    synthetic=preflight(original)
    assert synthetic["input_source_sha256"] == digest(original)
    assert synthetic["status"] == "SYNTHETIC_NOT_REAL_PROJECT"
    private=deepcopy(original)
    private["classification"]="PROJECT_SOURCE_DERIVED_UNVERIFIED"
    evidence=preflight(private)
    assert evidence["status"] == "MODEL_PARSED_BUT_UNVERIFIED_PHYSICAL_SOURCE"
    assert not evidence["source_evidence_accepted"]
    assert evidence["historical_F3_one_way_shear_unsafe_retained"]


def test_unverifiable_geometry_source_cannot_refine_or_claim_approval(original):
    bad=deepcopy(original)
    bad["floors"][1]["opening_cells"]=[[0,0]]
    with pytest.raises(StructuralHold):
        refine(bad)
    with pytest.raises(StructuralHold):
        screen(bad)


def test_only_one_tested_refinement_factor_admitted(original):
    with pytest.raises(StructuralHold,match="only independently tested"):
        refine(original,factor=3)
    with pytest.raises(StructuralHold,match="only independently tested"):
        refine(original,factor=True)


def test_site_build_exports_real_solved_SAR_and_interactive_page(tmp_path):
    site=tmp_path/"site"
    site.mkdir()
    nav=('<nav><a href="index.html">Home</a>'
         '<a href="report.html">Report</a></nav>')
    (site/"index.html").write_text(nav+'<details class="section"></details>')
    (site/"more.html").write_text(nav)
    (site/"report.html").write_text(
        nav.replace('<a href="report.html">Report</a>',
                    '<a aria-current="page" href="report.html">Report</a>'))
    receipt=export(site)
    assert verify_export(site)==receipt
    assert receipt["navigation_pages_linked"] == 3
    for p in ("r6p23.html","r6p23.css","r6p23.js",
              "data/r6p23-preview.json",
              "data/r6p24-pages-receipt.json",
              "reports/r6p23-reference/r6p23-multifloor-shell.html",
              "reports/r6p23-reference/r6p23-multifloor-shell.json"):
        assert (site/p).is_file()
    data=json.loads((site/"data/r6p23-preview.json").read_text())
    assert data["source_SHA256"]==receipt["source_SHA256"]
    assert data["mesh_screen"]["refined_mesh_shells"] == 124
    assert data["mesh_screen"]["full_asymptotic_mesh_convergence_proven"] is False
    assert data["engineering_approval"] is False
    assert "NOT a complete engineering design" in (site/"r6p23.html").read_text()
    assert 'href="r6p23.html"' in (site/"index.html").read_text()
    assert "r6p23-independent-solver" in (site/"index.html").read_text()
    assert export(site)["navigation_pages_linked"] == 0
    verify_export(site)


def test_tampered_public_summary_report_rejected(tmp_path):
    site=tmp_path/"site"
    export(site)
    f=site/"r6p23.js"
    f.write_text(f.read_text()+"INJECTED",encoding="utf-8")
    with pytest.raises(StructuralHold,match="integrity failure"):
        verify_export(site)
    export(site)
    f=site/"reports/r6p23-reference/r6p23-multifloor-shell.json"
    f.write_text(f.read_text()+"TAMPER")
    with pytest.raises(StructuralHold):
        verify_export(site)
