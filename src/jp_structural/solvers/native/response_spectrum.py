"""Response-spectrum post-processing helpers validated against SEIS-01.

Only global base-shear scaling and orthogonal SRSS combination are included.
No eigensolution, modal extraction, spectrum interpolation, within-direction
CQC, or full dynamic solver is implemented here.
"""
from __future__ import annotations

import math
from typing import Iterable, Mapping


def global_scale_factor(design_base_shear: float, minimum_dynamic_base_shear: float) -> float:
    if minimum_dynamic_base_shear <= 0:
        raise ValueError("minimum_dynamic_base_shear must be positive")
    return float(design_base_shear) / float(minimum_dynamic_base_shear)


def scale_response(response: Mapping[str, float], factor: float) -> dict[str, float]:
    return {key: float(value) * float(factor) for key, value in response.items()}


def srss(components: Iterable[float]) -> float:
    return math.sqrt(sum(float(value) ** 2 for value in components))


def principal_direction_scaling(inputs: Mapping[str, object]) -> dict[str, object]:
    factor = global_scale_factor(float(inputs["design_base_shear_kips"]), float(inputs["minimum_dynamic_base_shear_kips"]))
    return {
        "scale_factor": factor,
        "scaled_major": scale_response(inputs["unscaled_major"], factor),
        "scaled_minor": scale_response(inputs["unscaled_minor"], factor),
    }
