"""Explicit elementary downward loads and seismic-mass arithmetic.

All magnitudes in kN and m; no assumptions about code participation
factors, actual wall locations or structural element compatibility.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence


class LoadInputError(ValueError):
    """A source quantity is missing, unphysical or numerically unsafe."""


def _num(value: object, field: str, zero_ok: bool = False) -> float:
    if isinstance(value, bool):
        raise LoadInputError(f"{field}: boolean invalid")
    try:
        x = float(value)
    except (ValueError, TypeError) as exc:
        raise LoadInputError(f"{field}: not numeric") from exc
    if not math.isfinite(x) or (x < 0 if zero_ok else x <= 0):
        raise LoadInputError(f"{field}: must be finite and {'nonnegative' if zero_ok else 'positive'}")
    return x


def _fraction(value: object, field: str) -> float:
    x = _num(value, field, True)
    if x > 1:
        raise LoadInputError(f"{field}: outside [0,1]")
    return x


def layered_area_dead_load(layers: Sequence[Mapping]) -> dict:
    """q=sum(t_i*gamma_i), kN/m². Layers require distinct source IDs."""
    if not isinstance(layers, (list, tuple)) or not layers:
        raise LoadInputError("nonempty layer list required")
    seen, parts = set(), []
    for layer in layers:
        if not isinstance(layer, Mapping):
            raise LoadInputError("invalid layer record")
        key = layer.get("id")
        if not isinstance(key, str) or not key.strip() or key in seen:
            raise LoadInputError("layer id missing or duplicated")
        seen.add(key)
        t = _num(layer.get("thickness_m"), "thickness_m")
        gamma = _num(layer.get("unit_weight_kN_m3"), "unit_weight_kN_m3")
        value = t*gamma
        if not math.isfinite(value):
            raise LoadInputError("area load overflow")
        parts.append({"id": key, "area_load_kN_m2": value})
    return {"formula_id": "JP-LOAD-LAYER-001",
            "area_load_kN_m2": math.fsum(p["area_load_kN_m2"] for p in parts),
            "layers": parts}


def wall_line_dead_load(unit_weight_kN_m3: float, gross_height_m: float,
                        opening_fraction: float, thickness_m: float,
                        height_deduction_m: float = 0) -> dict:
    """w=gamma*(H-d)*t*(1-o), kN/m; source locations NOT inferred."""
    gamma = _num(unit_weight_kN_m3, "unit_weight_kN_m3")
    H = _num(gross_height_m, "gross_height_m")
    o = _fraction(opening_fraction, "opening_fraction")
    t = _num(thickness_m, "thickness_m")
    d = _num(height_deduction_m, "height_deduction_m", True)
    if d >= H:
        raise LoadInputError("height_deduction_m must be less than H")
    w = gamma*(H-d)*t*(1-o)
    if not math.isfinite(w):
        raise LoadInputError("wall load overflow")
    return {"formula_id": "JP-LOAD-WALL-002",
            "net_height_m": H-d, "line_load_kN_m": w}


def member_self_weight(area_m2: float, length_m: float, unit_weight_kN_m3: float) -> dict:
    A = _num(area_m2, "area_m2")
    L = _num(length_m, "length_m")
    gamma = _num(unit_weight_kN_m3, "unit_weight_kN_m3")
    w = A*L*gamma
    if not math.isfinite(w):
        raise LoadInputError("member weight overflow")
    return {"formula_id": "JP-LOAD-SELF-003", "self_weight_kN": w}


def explicit_seismic_weight(loads: Sequence[Mapping]) -> dict:
    """W=sum(W_i*explicit_factor_i); does not derive mass placement."""
    if not isinstance(loads, (list, tuple)) or not loads:
        raise LoadInputError("nonempty load list required")
    seen, parts = set(), []
    for load in loads:
        if not isinstance(load, Mapping):
            raise LoadInputError("invalid load record")
        key = load.get("id")
        if not isinstance(key, str) or not key.strip() or key in seen:
            raise LoadInputError("missing/duplicate load id")
        seen.add(key)
        w = _num(load.get("downward_load_kN"), "downward_load_kN", True)
        factor = _fraction(load.get("participation_factor"), "participation_factor")
        parts.append({"id": key, "participation_factor": factor, "included_weight_kN": w*factor})
    W = math.fsum(x["included_weight_kN"] for x in parts)
    if not math.isfinite(W) or W <= 0:
        raise LoadInputError("total seismic weight must be positive")
    return {"formula_id": "JP-LOAD-MASS-004",
            "total_seismic_weight_kN": W, "components": parts}


def mass_from_weight(weight_kN: float, gravity_m_s2: float) -> dict:
    """m=W/g in kN*s²/m, numerically metric tonnes for kN/m/s."""
    W, g = _num(weight_kN, "weight_kN"), _num(gravity_m_s2, "gravity_m_s2")
    return {"formula_id": "JP-LOAD-MASS-005", "mass_kN_s2_per_m": W/g}
