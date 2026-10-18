"""Bounded first-party RC column P-M section integration (IS 456:2000).

All lengths mm, areas mm2, stresses MPa, axial loads kN and moments kN m.
Concrete: IS 456 Fig. 21 parabolic-rectangle idealization, 0.446 fck peak.
Ultimate strain: Cl. 38.1 / Cl. 39.1. Rebar: BILINEAR APPROXIMATION
of Fig. 23, not the exact cold-worked Fe415/Fe500 stress-strain curve.
Accordingly the output is a mathematical PRECHECK, not an approved IS 456
capacity table, independently SP16-benchmarked chart or complete design.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from jp_structural.solvers.native.rc_report_kernels import (
    IS456, RCDesignError, is456_biaxial_column,
)

ENGINE_ID = "JP-M09-FIBER-SECTION-001"
STEEL_MODEL = "IDEAL_ELASTIC_PLASTIC_APPROXIMATION_FIG23_VERIFICATION_HOLD"
ES_MPA = 200_000.0
CONCRETE_STRESS_FACTOR = 0.446
CONCRETE_PARABOLIC_STRAIN = 0.002
CONCRETE_ULTIMATE_STRAIN = 0.0035


class ColumnSectionError(RCDesignError):
    """Unsupported or invalid column-section input; no guessed capacity."""


def _number(value: object, label: str, *, allow_zero: bool = False) -> float:
    if isinstance(value, bool):
        raise ColumnSectionError(f"{label}: boolean is invalid")
    try:
        v = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ColumnSectionError(f"{label}: a finite number is required") from exc
    if not math.isfinite(v) or (v < 0 if allow_zero else v <= 0):
        raise ColumnSectionError(f"{label}: positive finite value required")
    return v


def _bars(bars: Sequence[Mapping], width: float, depth: float, *,
          require_reinforced: bool) -> list[tuple[float, float, float]]:
    if isinstance(bars, (str, bytes)) or not isinstance(bars, (list, tuple)):
        raise ColumnSectionError("bars: list of source-defined bar records required")
    if require_reinforced and len(bars) < 4:
        raise ColumnSectionError("column needs at least four explicitly located bars")
    prepared = []
    for i, bar in enumerate(bars):
        if not isinstance(bar, Mapping):
            raise ColumnSectionError(f"bar {i}: mapping required")
        x = _number(bar.get("x_mm"), f"bar {i}.x_mm")
        y = _number(bar.get("y_mm"), f"bar {i}.y_mm")
        area = _number(bar.get("area_mm2"), f"bar {i}.area_mm2")
        if x >= width or y >= depth:
            raise ColumnSectionError("bars must lie strictly inside section")
        prepared.append((x, y, area))
    ast = math.fsum(a for _, _, a in prepared)
    if ast >= 0.08 * width * depth:
        raise ColumnSectionError("steel above bounded 8% gross section limit")
    if not math.isfinite(ast):
        raise ColumnSectionError("bar areas overflow")
    return prepared


def _concrete_stress(strain: float, fck: float) -> float:
    if strain <= 0:
        return 0.0
    r = min(strain / CONCRETE_PARABOLIC_STRAIN, 1.0)
    return CONCRETE_STRESS_FACTOR * fck * (2 * r - r * r)


def _steel_stress(strain: float, fy: float) -> float:
    return max(-0.87 * fy, min(0.87 * fy, ES_MPA * strain))


def _extreme_strain(c: float, size: float) -> float:
    if c <= size:
        return CONCRETE_ULTIMATE_STRAIN
    # Cl. 39.1(b): epsilon_near = .0035 - .75 epsilon_far.
    return CONCRETE_ULTIMATE_STRAIN / (1.0 + 0.75 * (1.0 - size / c))


def section_resultants(
    *, width_mm: float, depth_mm: float, fck_MPa: float, fy_MPa: float,
    bars: Sequence[Mapping], axis: str, compression_face: str,
    neutral_axis_depth_mm: float, integration_slices: int = 256,
) -> dict:
    """Integrate concrete fibers and displaced-steel forces about gross centroid.

    axis 'X': gradient across depth, bending about x; 'Y': gradient across
    width, bending about y. Face START/END corresponds to y=0/D or x=0/b.
    Returns signed moment positive toward selected compression face.
    """
    b = _number(width_mm, "width_mm")
    d = _number(depth_mm, "depth_mm")
    fck = _number(fck_MPa, "fck_MPa")
    fy = _number(fy_MPa, "fy_MPa")
    c = _number(neutral_axis_depth_mm, "neutral_axis_depth_mm")
    if axis not in ("X", "Y") or compression_face not in ("START", "END"):
        raise ColumnSectionError("axis X/Y and compression face START/END required")
    if (not isinstance(integration_slices, int) or isinstance(integration_slices, bool)
            or not 32 <= integration_slices <= 4096):
        raise ColumnSectionError("integration_slices must be an integer 32..4096")
    if not (fck in (20, 25, 30, 35, 40) and fy in (415, 500)):
        raise ColumnSectionError("bounded section supports M20..M40 and Fe415/Fe500 only")
    layout = _bars(bars, b, d, require_reinforced=False)
    size = d if axis == "X" else b
    breadth = b if axis == "X" else d
    eps_max = _extreme_strain(c, size)
    dx = size / integration_slices
    nc = mc = 0.0
    for i in range(integration_slices):
        u = (i + .5) * dx  # measured from selected compression face
        e = eps_max * (1 - u / c)
        force = _concrete_stress(e, fck) * breadth * dx
        nc += force
        mc += force * (size / 2 - u)
    ns = ms = 0.0
    for x, y, area in layout:
        location = y if axis == "X" else x
        u = location if compression_face == "START" else size - location
        eps = eps_max * (1 - u / c)
        net_force = area * (_steel_stress(eps, fy) - _concrete_stress(eps, fck))
        ns += net_force
        ms += net_force * (size / 2 - u)
    axial = (nc + ns) / 1000
    moment = (mc + ms) / 1_000_000
    if not (math.isfinite(axial) and math.isfinite(moment)):
        raise ColumnSectionError("numerical section force overflow")
    return {
        "axial_kN": axial, "moment_about_selected_axis_kNm": moment,
        "concrete_axial_kN": nc / 1000, "steel_net_axial_kN": ns / 1000,
        "concrete_moment_kNm": mc / 1_000_000,
        "steel_net_moment_kNm": ms / 1_000_000,
        "maximum_compression_strain": eps_max,
        "neutral_axis_depth_mm": c,
    }


def uniaxial_capacity_at_axial_load(
    *, width_mm: float, depth_mm: float, fck_MPa: float, fy_MPa: float,
    bars: Sequence[Mapping], target_axial_kN: float,
    axis: str, compression_face: str, source_id: str,
    integration_slices: int = 256,
) -> dict:
    """Bisection for one section strain plane matching factored axial force.

    Brackets are checked (never extrapolate). The returned section moment is
    the computed equilibrium resultant; the steel law still needs independent
    Fig. 23/SP16 verification before design acceptance.
    """
    b = _number(width_mm, "width_mm")
    d = _number(depth_mm, "depth_mm")
    load = _number(target_axial_kN, "target_axial_kN")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ColumnSectionError("source_id: explicit geometry/bar provenance required")
    clean = _bars(bars, b, d, require_reinforced=True)
    if len({(x, y) for x, y, _ in clean}) != len(clean):
        raise ColumnSectionError("coincident bar centers unsupported")
    # Convert to dictionaries because section_resultants intentionally accepts
    # only explicit named coordinates for traceability.
    bar_map = [{"x_mm": x, "y_mm": y, "area_mm2": a} for x, y, a in clean]
    size = d if axis == "X" else b
    opts = dict(width_mm=b, depth_mm=d, fck_MPa=fck_MPa, fy_MPa=fy_MPa,
                bars=bar_map, axis=axis, compression_face=compression_face,
                integration_slices=integration_slices)
    lower = size * 1.e-8
    upper = size * 1.e7
    low_p = section_resultants(neutral_axis_depth_mm=lower, **opts)["axial_kN"]
    high_p = section_resultants(neutral_axis_depth_mm=upper, **opts)["axial_kN"]
    if not low_p <= load <= high_p:
        raise ColumnSectionError(
            f"target axial {load:.6g} kN outside bounded section "
            f"envelope [{low_p:.6g},{high_p:.6g}] kN")
    lo, hi = lower, upper
    for _ in range(90):
        c = (lo + hi) / 2
        result = section_resultants(neutral_axis_depth_mm=c, **opts)
        if result["axial_kN"] < load:
            lo = c
        else:
            hi = c
    result = section_resultants(neutral_axis_depth_mm=(lo + hi)/2, **opts)
    residual = result["axial_kN"] - load
    if abs(residual) > max(1.e-5, load * 1.e-8):
        raise ColumnSectionError("section axial equilibrium not converged")
    return {
        "engine": ENGINE_ID, "code": "IS456:2000",
        "source": IS456, "clauses": ["38.1", "39.1", "39.6", "Fig.21", "Fig.23"],
        "source_id": source_id.strip(), "axis": axis,
        "compression_face": compression_face,
        "input_target_axial_kN": load,
        "input_bars": bar_map,
        "width_mm": b, "depth_mm": d, "fck_MPa": float(fck_MPa),
        "fy_MPa": float(fy_MPa), "integration_slices": integration_slices,
        "axial_equilibrium_residual_kN": residual,
        "moment_capacity_kNm": abs(result["moment_about_selected_axis_kNm"]),
        "signed_moment_kNm": result["moment_about_selected_axis_kNm"],
        "section_resultants": result,
        "steel_law": STEEL_MODEL,
        "status": "BOUNDED_NUMERIC_SECTION_HOLD_STEEL_LAW_VALIDATION",
        "independently_SP16_benchmarked": False, "engineering_approval": False,
    }


def biaxial_interaction_from_bars(
    *, width_mm: float, depth_mm: float, fck_MPa: float, fy_MPa: float,
    bars: Sequence[Mapping], Pu_kN: float, Mux_kNm: float, Muy_kNm: float,
    clear_height_mm: float, effective_length_x_mm: float,
    effective_length_y_mm: float, source_id: str,
    integration_slices: int = 256,
) -> dict:
    """Bridge numeric section strengths into the existing IS456 §39.6 kernel.

    If moment sign is not supplied, adopt the LESSER of START and END
    compression-face magnitudes, for each axis. This is a conservative
    direction screen, NOT a replacement for signed FE envelope matching.
    """
    layout = _bars(bars, _number(width_mm, "width_mm"),
                   _number(depth_mm, "depth_mm"), require_reinforced=True)
    if not isinstance(source_id, str) or not source_id.strip():
        raise ColumnSectionError("source_id required")
    per_face = []
    for axis in ("X", "Y"):
        for face in ("START", "END"):
            per_face.append(uniaxial_capacity_at_axial_load(
                width_mm=width_mm, depth_mm=depth_mm, fck_MPa=fck_MPa,
                fy_MPa=fy_MPa, bars=bars, target_axial_kN=Pu_kN,
                axis=axis, compression_face=face, source_id=source_id,
                integration_slices=integration_slices))
    x_capacity = min(v["moment_capacity_kNm"] for v in per_face if v["axis"] == "X")
    y_capacity = min(v["moment_capacity_kNm"] for v in per_face if v["axis"] == "Y")
    if x_capacity <= 0 or y_capacity <= 0:
        raise ColumnSectionError("nonpositive section moment capacity")
    steel = math.fsum(a for _, _, a in layout)
    interaction = is456_biaxial_column(
        width_mm=width_mm, depth_mm=depth_mm, fck_MPa=fck_MPa,
        fy_MPa=fy_MPa, Ast_mm2=steel, Pu_kN=Pu_kN,
        Mux_kNm=Mux_kNm, Muy_kNm=Muy_kNm, Mux1_kNm=x_capacity,
        Muy1_kNm=y_capacity, clear_height_mm=clear_height_mm,
        effective_length_x_mm=effective_length_x_mm,
        effective_length_y_mm=effective_length_y_mm,
        uniaxial_capacity_source_id=f"{ENGINE_ID}:{source_id}")
    return {
        "engine": "M09_IS456_BIAXIAL_WITH_NATIVE_SECTION_CAPACITIES",
        "source_id": source_id,
        "section_solver": ENGINE_ID,
        "chosen_conservative_Mux1_kNm": x_capacity,
        "chosen_conservative_Muy1_kNm": y_capacity,
        "face_capacities": per_face,
        "legacy_interaction": interaction,
        "checks": {
            "axial_and_biaxial_screen": interaction["status"] != "FAIL",
            "all_axial_equilibria": all(
                abs(v["axial_equilibrium_residual_kN"]) < 1.e-4 for v in per_face),
            "steel_curve_independently_verified": False,
            "section_bar_layout_source_verified": False,
        },
        "status": "FAIL" if interaction["status"] == "FAIL"
                  else "BOUNDED_NUMERICAL_PRECHECK_SP16_AND_STEEL_LAW_HOLD",
        "uniaxial_capacity_solver_implemented": True,
        "code_check_complete": False,
        "engineering_approval": False,
    }
