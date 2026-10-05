from jp_structural.solvers.native.mdm import solve_moment_distribution


def test_mdm01_regression_with_governed_source_precision():
    initial = {
        "AB": 1.3333333333333333, "BA": -1.3333333333333333,
        "BC": 4.444444444444445, "CB": -2.2222222222222223,
        "CD": 6.666666666666667, "DC": -6.666666666666667,
        "BE": 0.0, "EB": 0.0, "CF": 5.0, "FC": -5.0,
        "DG": 0.0, "GD": 0.0,
    }
    result = solve_moment_distribution(
        initial_end_moments=initial,
        joint_ends={"D": ["DC", "DG"], "C": ["CB", "CD", "CF"], "B": ["BA", "BC", "BE"]},
        distribution_factors={"BA": 0.428, "BC": 0.286, "BE": 0.286, "CB": 0.276, "CD": 0.414, "CF": 0.31, "DC": 0.5, "DG": 0.5},
        joint_order=["D", "C", "B"],
        cycles=3,
        zero_carryover_from=["CF"],
        pre_adjustments=[{"end": "FC", "delta": 5.0, "far_end": "CF", "far_delta": 2.5}],
    )
    expected = {
        "AB": 1.087, "BA": -1.826, "BC": 2.157, "CB": -6.302,
        "CD": 3.197, "DC": -4.797, "BE": -0.329, "EB": -0.165,
        "CF": 3.105, "FC": 0.0, "DG": 4.798, "GD": 2.4,
    }
    assert max(abs(result["end_moments"][k] - v) for k, v in expected.items()) <= 0.01
    assert max(abs(v) for v in result["joint_residuals"].values()) <= 0.01


def test_mdm02_exact_core_solution():
    result = solve_moment_distribution(
        initial_end_moments={"AB": 0.0, "BA": -10.0, "BC": 0.0, "CB": 0.0, "BD": 5.0, "DB": -5.0},
        joint_ends={"B": ["BA", "BC", "BD"]},
        distribution_factors={"BA": 0.0, "BC": 0.5, "BD": 0.5},
        joint_order=["B"],
        cycles=1,
        zero_carryover_from=["BA"],
    )
    expected = {"BA": -10.0, "BC": 2.5, "CB": 1.25, "BD": 7.5, "DB": -3.75}
    for key, value in expected.items():
        assert abs(result["end_moments"][key] - value) < 1e-12
    assert abs(result["joint_residuals"]["B"]) < 1e-12
