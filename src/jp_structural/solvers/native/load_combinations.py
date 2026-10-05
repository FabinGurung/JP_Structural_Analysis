"""Deterministic load-combination enumeration validated against LC-01."""
from __future__ import annotations

from itertools import product
from typing import Any, Mapping


def lambda_for_usage(usage: str) -> float:
    return 0.6 if usage.strip().lower() in {"storage", "storage facility", "storage facilities"} else 0.3


def _pm(base: float, term: float) -> list[float]:
    return sorted([base - term, base + term])


def _nested_pm(base: float, a: float, b: float) -> list[float]:
    return sorted(base + sign_a * a + sign_b * b for sign_a, sign_b in product((-1, 1), repeat=2))


def generate_load_combinations(inputs: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Generate the limited NBC 105 combination family covered by LC-01.

    The numeric regression inputs used in validation are derived test data; this
    function does not imply a complete structural-response or design engine.
    """
    DL = float(inputs["DL"])
    LL = float(inputs["LL"])
    Ex = float(inputs["Ex"])
    Ey = float(inputs["Ey"])
    E = float(inputs.get("E_parallel", Ex))
    Z = float(inputs["Z"])
    Sso = float(inputs.get("Sso", 0.0))
    lam = float(inputs.get("lambda", lambda_for_usage(str(inputs.get("usage", "other")))))
    additional_type = str(inputs.get("additional_load_type", "")).lower()
    S_lsm = 1.2 * Sso if additional_type == "snow" else float(inputs.get("S_LSM", 0.0))
    S_wsm = Sso if additional_type == "snow" else float(inputs.get("S_WSM", 0.0))
    vertical_coefficient = 1.1 + 2 * Z / 3

    return {
        "lsm_parallel": {
            "1_2DL_plus_1_5LL": 1.2 * DL + 1.5 * LL,
            "1_2DL_plus_0_5LL_plus_S": 1.2 * DL + 0.5 * LL + S_lsm,
            "DL_plus_lambdaLL_pm_E": _pm(DL + lam * LL, E),
            "0_9DL_pm_E": _pm(0.9 * DL, E),
        },
        "lsm_nonparallel": {
            "DL_plus_lambdaLL_pm_Ex_pm_0_3Ey": _nested_pm(DL + lam * LL, Ex, 0.3 * Ey),
            "DL_plus_lambdaLL_pm_Ey_pm_0_3Ex": _nested_pm(DL + lam * LL, Ey, 0.3 * Ex),
            "0_9DL_pm_Ex_pm_0_3Ey": _nested_pm(0.9 * DL, Ex, 0.3 * Ey),
            "0_9DL_pm_Ey_pm_0_3Ex": _nested_pm(0.9 * DL, Ey, 0.3 * Ex),
        },
        "vertical_seismic": {
            "coefficient_on_DL": vertical_coefficient,
            "combination_pm_E": _pm(vertical_coefficient * DL + lam * LL, E),
        },
        "working_stress": {
            "DL_plus_LL": DL + LL,
            "DL_plus_LL_plus_S": DL + LL + S_wsm,
            "DL_plus_lambdaLL_pm_0_7E": _pm(DL + lam * LL, 0.7 * E),
            "0_7DL_pm_0_7E": _pm(0.7 * DL, 0.7 * E),
        },
    }
