"""Source-safe NBC 105:2025 bounded ESM numerical gate checks."""
import math
import pytest
from jp_structural.solvers.native.nbc105_2025_esm import (
    ESMInputError,period_exponent,design_coefficients,
    equivalent_static_floor_forces,signed_case_combination,bounded_story_drift,
)

@pytest.mark.parametrize("period,k",[(.25,1.),(.5,1.),(1.5,1.5),(2.5,2.),(3.,2.)])
def test_nbc2025_period_exponent(period,k):
    assert period_exponent(period)==pytest.approx(k)

def test_nbc2025_static_coefficients_are_from_explicit_design_factors():
    r=design_coefficients(elastic_horizontal_C=.7875,ductility_Rmu=4,
        overstrength_ULS=1.5,elastic_SLS_Cs=.1575,overstrength_SLS=1.25)
    assert r["ULS"]==pytest.approx(.13125)
    assert r["SLS"]==pytest.approx(.126)
    assert r["seismic_input_verification"].endswith("NOT_INDEPENDENTLY_VERIFIED")

def test_nbc2025_floor_distribution_recovers_base_shear_and_height_ratios():
    r=equivalent_static_floor_forces(floor_weights_kN=[400,450,350],
       floor_heights_m=[3,6,9],period_seconds=.4,design_coefficient=.13125)
    assert r["base_shear_kN"]==pytest.approx(157.5)
    assert sum(r["floor_forces_kN"])==pytest.approx(157.5)
    assert r["floor_forces_kN"][1]/r["floor_forces_kN"][0]==pytest.approx((450*6)/(400*3))
    assert r["engineering_approval"] is False
    assert not r["accidental_eccentricity_applied"]

def test_nbc2025_equivalent_floor_forces_change_period_exponent():
    a=equivalent_static_floor_forces(floor_weights_kN=[400,450,350],
        floor_heights_m=[3,6,9],period_seconds=.4,design_coefficient=.12)
    b=equivalent_static_floor_forces(floor_weights_kN=[400,450,350],
        floor_heights_m=[3,6,9],period_seconds=2.5,design_coefficient=.12)
    assert b["floor_forces_kN"][-1]>a["floor_forces_kN"][-1]
    assert sum(a["floor_forces_kN"])==pytest.approx(sum(b["floor_forces_kN"]))

def test_signed_force_superposition_never_adds_absolute_peaks():
    vals=signed_case_combination({"D":[120,8,-5],"EX":[80,-10,11]},
                                 {"D":1.2,"EX":-1.2})
    assert vals==pytest.approx([48,21.6,-19.2])

@pytest.mark.parametrize("kwargs",[
    {"floor_weights_kN":[1],"floor_heights_m":[3,2]},
    {"floor_weights_kN":[1,2],"floor_heights_m":[3,3]},
    {"floor_weights_kN":[1,-2],"floor_heights_m":[3,6]},
    {"floor_weights_kN":[1,2],"floor_heights_m":[3,float("nan")]},
])
def test_invalid_floor_aggregations_fail_closed(kwargs):
    with pytest.raises(ESMInputError):
        equivalent_static_floor_forces(period_seconds=.4,
                                      design_coefficient=.13,**kwargs)

@pytest.mark.parametrize("v",[-1,0,float("nan"),float("inf"),True])
def test_nonphysical_period_rejected(v):
    with pytest.raises(ESMInputError):
        period_exponent(v)

def test_nbc2025_uls_drift_uses_ductility_scaling_and_not_legacy_unscaled_pass():
    res=bounded_story_drift(elastic_interstory_delta_m=.02,
                           story_height_m=3.,limit_state="ULS",ductility_Rmu=4)
    assert res["calculated_design_drift_ratio"]==pytest.approx(.0266666666667)
    assert res["numerical_limit_exceeded"]
    assert not res["engineering_approval"]

def test_source_unverified_numerically_below_limit_is_hold():
    r=bounded_story_drift(elastic_interstory_delta_m=.008,
                story_height_m=3.,limit_state="SLS",ductility_Rmu=4)
    assert not r["numerical_limit_exceeded"]
    assert r["status"].endswith("EVIDENCE_HOLD")

def test_even_full_bounded_numeric_gate_is_not_professional_approval():
    r=bounded_story_drift(elastic_interstory_delta_m=.003,
          story_height_m=3.,limit_state="SLS",ductility_Rmu=4,
          source_model_stiffness_verified=True,
          accidental_eccentricity_verified=True,
          mass_and_geometry_verified=True)
    assert r["status"]=="BOUNDED_NUMERIC_PASS_SOURCE_GATES_RECORDED"
    assert r["engineering_approval"] is False

def test_uncertain_orthogonal_eccentricity_requires_hard_explicit_boolean():
    with pytest.raises(ESMInputError):
        bounded_story_drift(elastic_interstory_delta_m=.003,story_height_m=3.,
          limit_state="ULS",ductility_Rmu=4,accidental_eccentricity_verified="yes")

def test_unknown_source_case_and_duplicate_vectors_rejected():
    with pytest.raises(ESMInputError):
        signed_case_combination({"D":[1,2]},{"E":1.})
    with pytest.raises(ESMInputError):
        signed_case_combination({"D":[1,2],"E":[2]},{"D":1.,"E":1.})
