import math
import pytest
from jp_structural.solvers.native.material_properties import (
    MaterialInputError, rectangular_section, isotropic_shear_modulus,
    concrete_modulus_sqrt_model,
)


def test_rectangular_area_inertias_and_axis_swap():
    s = rectangular_section(.4, .3)
    assert s["area_m2"] == pytest.approx(.12)
    assert s["Ixx_m4"] == pytest.approx(.4 * .3**3 / 12)
    assert s["Iyy_m4"] == pytest.approx(.3 * .4**3 / 12)
    assert rectangular_section(.3, .4)["Ixx_m4"] == pytest.approx(s["Iyy_m4"])


def test_parameterized_modulus_is_not_code_verification():
    assert concrete_modulus_sqrt_model(20, 5000)["elastic_modulus_MPa"] == pytest.approx(22360.679775)
    assert isotropic_shear_modulus(20000, .2)["shear_modulus_MPa"] == pytest.approx(20000/2.4)


@pytest.mark.parametrize("call", [
    lambda: rectangular_section(0, .3),
    lambda: rectangular_section(True, .3),
    lambda: rectangular_section(math.nan, .3),
    lambda: rectangular_section(1e308, 1e308),
    lambda: isotropic_shear_modulus(20000, .5),
    lambda: isotropic_shear_modulus(20000, math.inf),
    lambda: concrete_modulus_sqrt_model(-20, 5000),
    lambda: concrete_modulus_sqrt_model(20, 0),
])
def test_bad_material_inputs_fail_closed(call):
    with pytest.raises(MaterialInputError):
        call()
