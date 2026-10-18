"""M09 strain-compatibility numerical equilibrium and failure regression gates.

These tests do NOT assert Fig23A exact cold-worked steel equivalence or
engineering acceptance; they independently spot-check Fig22 concrete block.
"""
import math

import pytest

from jp_structural.solvers.native.rc_column_section import (
    ColumnSectionError, section_resultants, uniaxial_capacity_at_axial_load,
    biaxial_interaction_from_bars,
)


BARS = [
    {"x_mm": x, "y_mm": y, "area_mm2": 490.874}
    for x, y in ((50, 50), (200, 50), (350, 50),
                 (50, 450), (200, 450), (350, 450),
                 (50, 250), (350, 250))
]
BASIS = dict(width_mm=400, depth_mm=500, fck_MPa=25, fy_MPa=415, bars=BARS)


def test_plain_concrete_integral_matches_independent_is456_fig22_stress_block():
    # Analytic block: 0.36 fck*b*xu located 0.42*xu from compressed face.
    # Numeric 0.446-fck parabolic/rectangular integration should agree closely.
    b, depth, fck, xu = 300, 400, 25, 200
    result = section_resultants(width_mm=b, depth_mm=depth, fck_MPa=fck,
        fy_MPa=415, bars=[], axis="X", compression_face="START",
        neutral_axis_depth_mm=xu, integration_slices=2048)
    p_analytic_kN = .36 * fck * b * xu / 1000
    m_analytic_kNm = p_analytic_kN * (depth / 2 - .42 * xu) / 1000
    assert result["axial_kN"] == pytest.approx(p_analytic_kN, rel=.008)
    assert result["moment_about_selected_axis_kNm"] == pytest.approx(
        m_analytic_kNm, rel=.012)
    assert result["steel_net_axial_kN"] == 0


@pytest.mark.parametrize("axis", ["X", "Y"])
def test_root_solver_recovers_axial_equilibrium_both_faces(axis):
    a = uniaxial_capacity_at_axial_load(**BASIS, target_axial_kN=1200,
        axis=axis, compression_face="START", source_id="SYNTHETIC_8D25")
    b = uniaxial_capacity_at_axial_load(**BASIS, target_axial_kN=1200,
        axis=axis, compression_face="END", source_id="SYNTHETIC_8D25")
    assert abs(a["axial_equilibrium_residual_kN"]) < 1.e-5
    assert a["moment_capacity_kNm"] > 0
    assert a["moment_capacity_kNm"] == pytest.approx(
        b["moment_capacity_kNm"], rel=1.e-8)
    assert a["section_resultants"]["axial_kN"] == pytest.approx(1200, abs=1.e-5)
    assert a["engineering_approval"] is False
    assert "HOLD" in a["status"]


def test_biaxial_integration_consumes_actual_generated_section_capacities():
    data = dict(**BASIS, Pu_kN=1200, Mux_kNm=80, Muy_kNm=40,
        clear_height_mm=2600, effective_length_x_mm=2800,
        effective_length_y_mm=2800, source_id="SYNTHETIC_8D25")
    result = biaxial_interaction_from_bars(**data)
    assert len(result["face_capacities"]) == 4
    assert result["uniaxial_capacity_solver_implemented"] is True
    assert result["legacy_interaction"]["uniaxial_capacity_source_id"].startswith(
        "JP-M09-FIBER-SECTION")
    assert result["legacy_interaction"]["interaction_utilization"] > 0
    assert result["status"] != "FAIL"
    assert not result["code_check_complete"]
    assert not result["engineering_approval"]


def test_unsafe_biaxial_case_fails_even_with_numerically_generated_strength():
    result = biaxial_interaction_from_bars(
        **BASIS, Pu_kN=1200, Mux_kNm=100_000, Muy_kNm=100_000,
        clear_height_mm=2600, effective_length_x_mm=2800,
        effective_length_y_mm=2800, source_id="SYNTHETIC_OVERLOAD")
    assert result["status"] == "FAIL"
    assert result["legacy_interaction"]["interaction_utilization"] > 1


@pytest.mark.parametrize("corruption", [
    {"bars": BARS[:3]},
    {"bars": BARS + [{"x_mm": 400, "y_mm": 30, "area_mm2": 400}]},
    {"bars": BARS + [{"x_mm": 30, "y_mm": 20, "area_mm2": 40000}]},
    {"source_id": ""},
    {"target_axial_kN": 100_000},
])
def test_invalid_or_unattainable_section_inputs_fail_closed(corruption):
    args = dict(**BASIS, target_axial_kN=1200, axis="X",
                compression_face="START", source_id="SYNTHETIC")
    args.update(corruption)
    with pytest.raises(ColumnSectionError):
        uniaxial_capacity_at_axial_load(**args)


def test_bars_are_net_of_displaced_concrete_for_compression():
    c = section_resultants(**BASIS, axis="X", compression_face="START",
        neutral_axis_depth_mm=2000, integration_slices=512)
    assert math.isfinite(c["steel_net_axial_kN"])
    assert c["concrete_axial_kN"] > 0
    assert c["axial_kN"] == pytest.approx(
        c["concrete_axial_kN"] + c["steel_net_axial_kN"], rel=1.e-12)
