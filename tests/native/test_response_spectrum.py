from jp_structural.solvers.native.response_spectrum import principal_direction_scaling, srss


def test_seis01_derived_microbenchmark_exact():
    scaled = principal_direction_scaling({
        "design_base_shear_kips": 300,
        "minimum_dynamic_base_shear_kips": 75,
        "unscaled_major": {"V_kips": 75, "M_ft_kips": 4000},
        "unscaled_minor": {"V_kips": 80, "M_ft_kips": 4500},
    })
    assert scaled["scale_factor"] == 4.0
    assert scaled["scaled_major"] == {"V_kips": 300.0, "M_ft_kips": 16000.0}
    assert scaled["scaled_minor"] == {"V_kips": 320.0, "M_ft_kips": 18000.0}
    assert srss([120, 50]) == 130.0
    assert srss([9, 12]) == 15.0
