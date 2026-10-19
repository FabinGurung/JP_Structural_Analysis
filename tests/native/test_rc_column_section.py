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


# Independent, published SP16 Table A data transcribed from Table 4.1 of
# NRCMEC CE502PC RCC course notes p.10, not generated from the implementation.
# Full SP16 interaction charts are not available as numerical QA fixtures yet.
from jp_structural.solvers.native.rc_column_section import (
    _steel_stress, uniaxial_pm_curve, SP16_STEEL_KNOTS,
)

@pytest.mark.parametrize("fy,eps,expected", [
    (415, 0.00163, 306.7), (415, 0.00192, 324.8),
    (415, 0.00241, 342.8), (415, 0.00276, 351.8),
    (415, 0.00380, 360.9), (500, 0.00195, 369.6),
    (500, 0.00226, 391.3), (500, 0.00277, 413.0),
    (500, 0.00312, 423.9), (500, 0.00417, 434.8),
])
def test_sp16_table_a_steel_knots_against_independent_published_values(fy,eps,expected):
    assert _steel_stress(eps, fy) == pytest.approx(expected, abs=0.10)
    assert _steel_stress(-eps, fy) == pytest.approx(-expected, abs=0.10)

@pytest.mark.parametrize("fy", [415, 500])
def test_steel_curve_elastic_continuous_monotone_odd_symmetric(fy):
    fyd=fy/1.15
    limit=0.8*fyd/200000
    assert _steel_stress(limit,fy)==pytest.approx(0.8*fyd,rel=1e-12)
    assert _steel_stress(limit-1e-10,fy)==pytest.approx(.8*fyd-.00002,abs=.00001)
    assert _steel_stress(.1,fy)==pytest.approx(fyd,rel=1e-12)
    e=[i*.00001 for i in range(701)]
    f=[_steel_stress(v,fy) for v in e]
    assert all(a<=b+1e-9 for a,b in zip(f,f[1:]))
    assert all(_steel_stress(-v,fy)==pytest.approx(-_steel_stress(v,fy)) for v in e)

@pytest.mark.parametrize("fy", [415,500])
def test_interpolated_steel_law_is_not_premature_ideal_plastic_plateau(fy):
    # This was the previous regression bug: a bilinear 0.87fy stress cap
    # reached as early as epsilon~0.0018/0.0022.
    fyd=fy/1.15
    stress=_steel_stress(.0025,fy)
    assert stress < fyd
    assert stress > .90*fyd

def test_pm_four_faces_recover_target_points_and_signs():
    cases=[]
    for axis in ("X","Y"):
        for face in ("START","END"):
            curve=uniaxial_pm_curve(**BASIS,axis=axis,compression_face=face,
                source_id="SYNTHETIC_PM_TABLE_A",points=33,
                target_axial_kN=1200)
            assert curve["status"].endswith("SP16_CHART_HOLD")
            assert len(curve["points"])>=34
            assert not curve["engineering_approval"]
            assert not curve["independently_SP16_benchmarked"]
            assert all(math.isfinite(p["axial_kN"]) and
                       math.isfinite(p["signed_moment_kNm"])
                       for p in curve["points"])
            target=curve["target_equilibrium"]
            assert abs(target["axial_kN"]-1200)<1e-5
            assert target["target_equilibrium"]
            cases.append(curve)
    assert cases[0]["target_equilibrium"]["signed_moment_kNm"]==pytest.approx(
        -cases[1]["target_equilibrium"]["signed_moment_kNm"],rel=1e-8)
    assert cases[2]["target_equilibrium"]["signed_moment_kNm"]==pytest.approx(
        -cases[3]["target_equilibrium"]["signed_moment_kNm"],rel=1e-8)
    assert any(p["axial_kN"]<0 for p in cases[0]["points"])
    assert any(p["axial_kN"]>1200 for p in cases[0]["points"])

def test_pm_curve_axis_rotation_invariance_on_transposed_bar_layout():
    swapped=[{"x_mm":bar["y_mm"],"y_mm":bar["x_mm"],
              "area_mm2":bar["area_mm2"]} for bar in BARS]
    a=uniaxial_pm_curve(**BASIS,axis="X",compression_face="START",
        source_id="SYNTHETIC",points=33)
    b=uniaxial_pm_curve(width_mm=500,depth_mm=400,fck_MPa=25,fy_MPa=415,
        bars=swapped,axis="Y",compression_face="START",
        source_id="SYNTHETIC",points=33)
    assert len(a["points"])==len(b["points"])
    for lhs,rhs in zip(a["points"],b["points"]):
        assert lhs["axial_kN"]==pytest.approx(rhs["axial_kN"],rel=1e-10)
        assert lhs["signed_moment_kNm"]==pytest.approx(
            rhs["signed_moment_kNm"],rel=1e-10)

@pytest.mark.parametrize("bad", [
    {"points":0}, {"points":300}, {"points":True},
    {"source_id":""},{"bars":BARS[:2]},
    {"target_axial_kN":100000},
])
def test_pm_curve_bad_inputs_fail_closed(bad):
    args=dict(**BASIS,axis="X",compression_face="START",
              source_id="SYNTHETIC",points=33)
    args.update(bad)
    with pytest.raises(ColumnSectionError):
        uniaxial_pm_curve(**args)


@pytest.mark.parametrize("axial_fraction,chart31_normalized_m,k_reference", [
    (0.25, 0.081575, 0.676601),
    (0.44, 0.028979, 1.161766),
])
def test_sp16_chart31_related_independent_hand_calculation_examples(
    axial_fraction,chart31_normalized_m,k_reference
):
    """External SP16 Chart31 reconstruction examples (Desai, SEFI, Jan 2005).

    A 400 x 500 mm M20 Fe415 section; d'/D=.05; p/fck=.02 (p=.4%).
    Two opposite reinforcement rows, two 200-mm2 bars in each row.
    Compare normalized moment and neutral-axis depth with independently
    published hand-calculated examples associated with Chart31; do not claim
    that the original BIS chart was digitally verified.

    https://www.sefindia.org/forum/viewtopic.php?t=1979
    """
    b,D,fck=400,500,20
    bars=[{"x_mm":x,"y_mm":y,"area_mm2":200}
          for x in (50,350) for y in (25,475)]
    target=axial_fraction*fck*b*D/1000
    result=uniaxial_capacity_at_axial_load(width_mm=b,depth_mm=D,fck_MPa=fck,
        fy_MPa=415,bars=bars,target_axial_kN=target,axis="X",
        compression_face="START",source_id="SEFI_DESAI_2005_SP16_CHART31_EXAMPLE",
        integration_slices=1024)
    normalized=result["moment_capacity_kNm"]*1e6/(fck*b*D**2)
    k=result["section_resultants"]["neutral_axis_depth_mm"]/D
    assert normalized==pytest.approx(chart31_normalized_m,rel=.007)
    assert k==pytest.approx(k_reference,rel=.005)
    assert result["independently_SP16_benchmarked"] is False
    assert result["engineering_approval"] is False
