"""Elementary source-parameterized material and section arithmetic (m, MPa).

These are NOT adopted code clauses or independently certified RC design.
No material grade or coefficient is silently selected from a precedent report.
"""
from __future__ import annotations

import math

class MaterialInputError(ValueError):
    """Invalid physical or numerical source input."""


def _pos(value: object, field: str) -> float:
    if isinstance(value, bool):
        raise MaterialInputError(f"{field}: boolean not permitted")
    try:
        x = float(value)
    except (ValueError, TypeError) as exc:
        raise MaterialInputError(f"{field}: not numerical") from exc
    if not math.isfinite(x) or x <= 0:
        raise MaterialInputError(f"{field}: must be finite and positive")
    return x


def rectangular_section(width_m: float, depth_m: float) -> dict:
    """b along local x, h along local y; Ixx=b*h³/12, Iyy=h*b³/12."""
    b, h = _pos(width_m, "width_m"), _pos(depth_m, "depth_m")
    try:
        a, ix, iy = b*h, b*h**3/12, h*b**3/12
    except OverflowError as exc:
        raise MaterialInputError("section calculation overflow") from exc
    if not all(math.isfinite(x) and x > 0 for x in (a, ix, iy)):
        raise MaterialInputError("section overflow")
    return {"formula_id": "JP-MAT-RECT-001", "area_m2": a,
            "Ixx_m4": ix, "Iyy_m4": iy}


def isotropic_shear_modulus(youngs_modulus_MPa: float, poisson_ratio: float) -> dict:
    """G=E/[2(1+nu)], elastic isotropic assumption."""
    E = _pos(youngs_modulus_MPa, "youngs_modulus_MPa")
    if isinstance(poisson_ratio, bool):
        raise MaterialInputError("invalid poisson_ratio")
    try:
        nu = float(poisson_ratio)
    except (ValueError, TypeError) as exc:
        raise MaterialInputError("invalid poisson_ratio") from exc
    if not math.isfinite(nu) or not 0 <= nu < .5:
        raise MaterialInputError("poisson_ratio outside [0, .5)")
    return {"formula_id": "JP-MAT-G-002", "shear_modulus_MPa": E/(2*(1+nu))}


def concrete_modulus_sqrt_model(fck_MPa: float, coefficient_MPa_per_sqrt_MPa: float) -> dict:
    """E=k*sqrt(fck). k MUST be supplied from separately verified code basis."""
    fck, k = _pos(fck_MPa, "fck_MPa"), _pos(coefficient_MPa_per_sqrt_MPa, "coefficient")
    E = k*math.sqrt(fck)
    if not math.isfinite(E):
        raise MaterialInputError("concrete modulus overflow")
    return {"formula_id": "JP-MAT-EC-003", "elastic_modulus_MPa": E}
