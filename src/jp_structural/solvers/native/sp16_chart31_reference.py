"""Primary SP16 Chart31 measured spot checks and explicit edition boundaries.

The original chart is a scanned graph (SP16:1980, printed p116, PDF p139).
Two approximate plotted ordinates are independently recorded, not calculated
by the section solver, and compared at their source-identified axial ratios.
These spots are NOT digitized full curves, nor 1978→2000 code equivalence.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
from jp_structural.solvers.native.rc_column_section import uniaxial_capacity_at_axial_load

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "registry" / "sp16_chart31_visual_samples.v0.1.json"


def _invariant(condition: bool, explanation: str) -> None:
    if not condition:
        raise ValueError("SP16_CHART31_SOURCE_QA_FAIL: " + explanation)


def build_chart31_comparison(fixture: dict | None = None) -> dict:
    d = fixture if fixture is not None else json.loads(FIXTURE.read_text(encoding="utf-8"))
    g = d["geometry_basis"]
    a = d["acceptance"]
    _invariant(d["schema"] == "jp.structural.sp16.chart31.visual_samples.v0.1", "schema")
    _invariant(d["original_pdf_sha256"] == "d2a6246a5dc7504568f4e55f310dd4be9d925fb1a8b04b6d7f5132c93f66c76e", "PDF digest")
    _invariant(d["physical_pdf_page"] == 139 and d["printed_page"] == 116 and d["chart_number"] == 31, "source location")
    _invariant(g["width_mm"] == 400 and g["depth_mm"] == 500 and
               g["fck_mpa"] == 20 and g["fy_mpa"] == 415 and
               g["d_prime_over_D"] == .05 and g["p_over_fck"] == .02, "geometry")
    _invariant(a["engineering_approval"] is False and
               a["full_chart_curves_digitized"] is False and
               a["IS456_1978_to_2000_clause_parity_verified"] is False, "source acceptance flags")
    _invariant(len(d["points"]) >= 2, "at least two original chart samples")
    width, depth, fck, fy = [g[k] for k in ("width_mm", "depth_mm", "fck_mpa", "fy_mpa")]
    cover = depth*g["d_prime_over_D"]
    # Equal reinforcement on opposite faces, exactly p=0.4% for fck=M20,
    # without claiming a client's real reinforcement layout.
    total_ast = (g["total_reinforcement_percentage"]/100) * width * depth
    bars = [
        {"x_mm": x, "y_mm": y, "area_mm2": total_ast/4}
        for x in (width*.125, width*.875) for y in (cover, depth-cover)
    ]
    check_ast = sum(x["area_mm2"] for x in bars)
    _invariant(math.isclose(100*check_ast/(width*depth), .4, abs_tol=1e-12), "bar distribution")
    results = []
    for row in d["points"]:
        axial_ratio = row["pu_over_fck_bD"]
        ref = row["chart_read_mu_over_fck_bD2"]
        tol = row["visual_read_absolute_tolerance"]
        _invariant(0 < axial_ratio < 1 and 0 < ref < .5 and .003 <= tol <= .02,
                   "chart coordinate/tolerance out of bounds")
        pu_kN = axial_ratio * fck * width * depth / 1000
        section = uniaxial_capacity_at_axial_load(
            width_mm=width, depth_mm=depth, fck_MPa=fck, fy_MPa=fy,
            bars=bars, target_axial_kN=pu_kN, axis="X", compression_face="START",
            source_id="SP16:1980_CHART31_" + row["point_id"], integration_slices=1024)
        numeric = section["moment_capacity_kNm"]*1e6/(fck*width*depth**2)
        error = abs(numeric-ref)
        passed = error <= tol
        results.append({
            "point_id": row["point_id"],
            "source_chart_coordinate": {
                "pu_over_fck_bD": axial_ratio,
                "mu_over_fck_bD2": ref,
                "approximate_image_pixel": row["source_pixel_estimate"],
            },
            "engine_mu_over_fck_bD2": numeric,
            "absolute_normalized_error": error,
            "visual_uncertainty_absolute_normalized_moment": tol,
            "independent_worked_example_mu_over_fck_bD2": row["independent_worked_example_mu_over_fck_bD2"],
            "independent_worked_example_error": abs(numeric-row["independent_worked_example_mu_over_fck_bD2"]),
            "source_page_pdf": 139,
            "spot_agreement": passed,
            "status": "COARSE_PRIMARY_CHART_SPOT_AGREEMENT" if passed else "CHART_DISAGREEMENT_REQUIRES_REVIEW",
        })
        _invariant(passed, row["point_id"]+" outside primary chart visual uncertainty")
    source_json=json.dumps(d,sort_keys=True,separators=(",",":"),allow_nan=False)
    return {
        "schema":"jp.structural.sp16.chart31.spot_comparison.v0.1",
        "original_sp16_pdf_sha256":d["original_pdf_sha256"],
        "figure":"Chart 31; SP16:1980; PDF physical page 139; printed page 116",
        "historical_code_basis":"IS456:1978",
        "current_engine_code_basis":"IS456:2000",
        "comparison_status":"TWO_COARSE_PRIMARY_CHART_SPOT_AGREEMENTS_EDITION_PARITY_HOLD",
        "visual_reference_method":d["digitization_method"],
        "uncertainty_description":d["sampling_uncertainty_note"],
        "source_fixture_sha256":hashlib.sha256(source_json.encode()).hexdigest(),
        "points":results,
        "all_sampled_points_agree":all(x["spot_agreement"] for x in results),
        "code_edition_reconciliation":{
            "concrete_stress_peak":"0.446*fck in historic section and current numerical kernel; numeric form aligned",
            "concrete_strain_max":"0.0035 in historic section and current numerical kernel; numeric form aligned",
            "steel_total_strain":"Fe415/Fe500 SP16 Table A 12 points independently regression-tested",
            "concrete_displaced_by_steel":"SP16 charts approximate displaced-concrete contribution with M20; numerical solver subtracts actual displaced-fiber concrete stress, so nonzero discrepancy is expected",
            "historic_ref":"SP16:1980 derives its charts from IS456:1978, not IS456:2000",
            "current_project_seismic_basis":"NBC105:2025 separate seismic actions/detailing, not validated by old SP16 charts",
            "full_edition_parity_verified":False,
            "engineering_approval":False
        },
        "full_sp16_chart31_curve_digitization_complete":False,
        "engineering_approval":False,
        "report_accepted":False,
    }
