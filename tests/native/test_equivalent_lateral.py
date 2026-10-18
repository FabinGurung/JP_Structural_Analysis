import math
import pytest
from jp_structural.solvers.native.equivalent_lateral import (
    ExplicitSeismicInputError, empirical_period, period_distribution_exponent,
    report_coefficient_arithmetic, vertical_force_distribution
)

def test_fictional_equilibrium():
    out=vertical_force_distribution([
        {'id':'L1','seismic_weight':100,'height_above_base':3},
        {'id':'L2','seismic_weight':200,'height_above_base':6}],100,1)
    assert math.isclose(out[0]['lateral_force'],20)
    assert math.isclose(out[1]['lateral_force'],80)

def test_fictional_period():
    assert math.isclose(empirical_period(16,.1,.5,1.5),.6)
    assert period_distribution_exponent(1.5,.5,2.5,1,2)==1.5
    assert period_distribution_exponent(.2,.5,2.5,1,2)==1

def test_fictional_coefficients():
    c=report_coefficient_arithmetic(2,.3,1,4,1.5,1.25,.2)
    assert math.isclose(c['elastic_spectral_factor'],.6)
    assert math.isclose(c['uls_coefficient'],.1)
    assert math.isclose(c['sls_coefficient'],.096)

def test_invalid_inputs_fail_closed():
    with pytest.raises(ExplicitSeismicInputError):
        vertical_force_distribution([
            {'id':'L1','seismic_weight':100,'height_above_base':3},
            {'id':'L1','seismic_weight':200,'height_above_base':6}],100,1)
    with pytest.raises(ExplicitSeismicInputError):
        vertical_force_distribution([{'id':'L1','seismic_weight':math.nan,'height_above_base':3}],100,1)
    with pytest.raises(ExplicitSeismicInputError):
        report_coefficient_arithmetic(2,.3,1,4,0,1.25,.2)
