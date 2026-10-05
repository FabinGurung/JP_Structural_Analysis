from jp_structural.solvers.native.load_combinations import generate_load_combinations


def test_lc01_regression_exact():
    got = generate_load_combinations({"DL": 100, "LL": 50, "Ex": 20, "Ey": 10, "E_parallel": 20, "Z": 0.30, "Sso": 10, "additional_load_type": "snow", "usage": "other"})
    assert got["lsm_parallel"]["1_2DL_plus_1_5LL"] == 195.0
    assert got["lsm_parallel"]["DL_plus_lambdaLL_pm_E"] == [95.0, 135.0]
    assert got["lsm_nonparallel"]["DL_plus_lambdaLL_pm_Ex_pm_0_3Ey"] == [92.0, 98.0, 132.0, 138.0]
    assert got["vertical_seismic"]["coefficient_on_DL"] == 1.3
    assert got["vertical_seismic"]["combination_pm_E"] == [125.0, 165.0]
    assert got["working_stress"]["DL_plus_LL_plus_S"] == 160.0
