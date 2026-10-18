import math
import pytest
from jp_structural.solvers.native.rc_beam_strength import (
    RCBeamInputError, rectangular_singly_reinforced_flexure,
    required_singly_reinforced_steel_area, vertical_stirrup_shear_check,
)


def _f(**kwargs):
    args=dict(width_mm=230,effective_depth_mm=450,overall_depth_mm=500,
              fck_MPa=20,fy_MPa=500,tension_steel_area_mm2=2*math.pi*16**2/4,
              factored_moment_kNm=60)
    args.update(kwargs)
    return rectangular_singly_reinforced_flexure(**args)


def test_independent_force_block_moment_and_equilibrium():
    result=_f()
    Ast=2*math.pi*16**2/4
    xu=.87*500*Ast/(.36*20*230)
    C=.36*20*230*xu
    T=.87*500*Ast
    mu=T*(450-.42*xu)/1e6
    assert C==pytest.approx(T)
    assert result["neutral_axis_xu_mm"]==pytest.approx(xu)
    assert result["nominal_design_moment_capacity_kNm"]==pytest.approx(mu)
    assert result["status"]=="BOUNDED_FLEXURE_PRECHECK_PASS"
    assert result["engineering_approval"] is False


def test_over_reinforced_or_insufficient_flexure_must_fail():
    over=_f(tension_steel_area_mm2=3500, factored_moment_kNm=0)
    assert over["status"]=="FAIL"
    assert over["nominal_design_moment_capacity_kNm"] is None
    weak=_f(factored_moment_kNm=120)
    assert weak["status"]=="FAIL"
    assert weak["checks"]["flexural_capacity_vs_demand"] is False
    under_min=_f(tension_steel_area_mm2=1)
    assert under_min["status"]=="FAIL"


def test_required_area_inverse_and_capacity_limit():
    args=dict(width_mm=230,effective_depth_mm=450,overall_depth_mm=500,
              fck_MPa=20,fy_MPa=500)
    req=required_singly_reinforced_steel_area(**args,factored_moment_kNm=62)
    assert req["status"]=="CANDIDATE_AREA_ONLY_NOT_BAR_DESIGN"
    provided=rectangular_singly_reinforced_flexure(**args,
             tension_steel_area_mm2=req["required_Ast_mm2"],factored_moment_kNm=62)
    assert provided["status"]=="BOUNDED_FLEXURE_PRECHECK_PASS"
    assert provided["nominal_design_moment_capacity_kNm"]==pytest.approx(62,rel=1e-10)
    assert required_singly_reinforced_steel_area(**args,factored_moment_kNm=9999)["status"].startswith("FAIL")


def _s(**kwargs):
    args=dict(width_mm=230,effective_depth_mm=450,fck_MPa=20,
              factored_shear_kN=90,table19_concrete_shear_strength_MPa=.48,
              table19_lookup_source_id="SYNTHETIC-TABLE19-CANDIDATE",
              stirrup_fy_MPa=415,stirrup_legs=2,stirrup_diameter_mm=8,
              provided_spacing_mm=125)
    args.update(kwargs)
    return vertical_stirrup_shear_check(**args)


def test_shear_units_and_checks_but_always_hold_table19():
    r=_s()
    av=2*math.pi*8**2/4
    vc=.48*230*450/1000
    vs=.87*415*av*450/125/1000
    assert r["concrete_shear_contribution_kN"]==pytest.approx(vc)
    assert r["stirrup_shear_capacity_kN"]==pytest.approx(vs)
    assert r["stirrup_shear_demand_kN"]==pytest.approx(90-vc)
    assert r["status"]=="HOLD_TABLE19_NUMERIC_LOOKUP"
    assert all(r["checks"].values())
    assert r["engineering_approval"] is False


def test_shear_physical_failures_cannot_be_adopted():
    for row in (
        _s(factored_shear_kN=400),
        _s(provided_spacing_mm=350),
        _s(stirrup_diameter_mm=6,provided_spacing_mm=300),
    ):
        assert row["status"]=="FAIL"


@pytest.mark.parametrize("call",[
    lambda:_f(width_mm=0),
    lambda:_f(fck_MPa=27.58),
    lambda:_f(fy_MPa=550),
    lambda:_f(effective_depth_mm=500),
    lambda:_f(tension_steel_area_mm2=float("inf")),
    lambda:_f(factored_moment_kNm=-2),
    lambda:_s(stirrup_fy_MPa=500),
    lambda:_s(table19_concrete_shear_strength_MPa=3.5),
    lambda:_s(table19_lookup_source_id=""),
    lambda:_s(stirrup_legs=True),
    lambda:_s(provided_spacing_mm=float("nan")),
])
def test_unsupported_rc_input_fail_closed(call):
    with pytest.raises(RCBeamInputError): call()
