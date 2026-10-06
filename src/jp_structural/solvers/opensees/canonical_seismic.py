"""Fail-closed canonical response-spectrum analysis for supported OpenSees frames.

Phase C deliberately consumes an explicit response spectrum instead of inventing
code parameters, damping, unit conversions, storey response points, or accidental
eccentricity.  The numerical response is modal superposition on the canonical
elastic-frame model established by Phase B.
"""
from __future__ import annotations

import math
from typing import Any

import openseespy.opensees as ops

from jp_structural.model.ids import stable_id
from jp_structural.solvers.opensees.canonical_frame import (
    CanonicalTranslationError,
    _modal_mass_data,
    _model_digest,
    _solve_eigenvalues,
    build_canonical_frame_model,
)


_AXES = {"X": 1, "Y": 2, "Z": 3}


class ResponseSpectrumError(CanonicalTranslationError):
    """Raised when explicit Phase-C response-spectrum meaning is insufficient."""


def _finite(value: Any, *, field_name: str) -> float:
    try:
        out = float(value)
    except Exception as exc:
        raise ResponseSpectrumError(f"{field_name} must be numeric") from exc
    if not math.isfinite(out):
        raise ResponseSpectrumError(f"{field_name} must be finite")
    return out


def _positive(value: Any, *, field_name: str) -> float:
    out = _finite(value, field_name=field_name)
    if out <= 0:
        raise ResponseSpectrumError(f"{field_name} must be > 0")
    return out


def normalize_response_spectrum(
    spectrum: dict[str, Any],
    *,
    model_units: dict[str, Any],
) -> dict[str, Any]:
    """Validate and deterministically normalize explicit acceleration-spectrum data."""
    if not isinstance(spectrum, dict):
        raise ResponseSpectrumError("response spectrum must be an object")

    spectrum_id = spectrum.get("id")
    if not isinstance(spectrum_id, str) or not spectrum_id:
        raise ResponseSpectrumError("response spectrum requires a non-empty id")

    ordinate_type = str(spectrum.get("ordinate_type") or "").upper()
    if ordinate_type != "ACCELERATION":
        raise ResponseSpectrumError(
            "response spectrum ordinate_type must explicitly be 'ACCELERATION'"
        )

    damping = _finite(spectrum.get("damping_ratio"), field_name="spectrum.damping_ratio")
    if not (0.0 < damping < 1.0):
        raise ResponseSpectrumError("spectrum.damping_ratio must be between 0 and 1")

    units = spectrum.get("units") or {}
    if not isinstance(units, dict):
        raise ResponseSpectrumError("spectrum.units must be an object")
    for key in ("period", "spectral_acceleration", "displacement", "base_shear"):
        if not isinstance(units.get(key), str) or not units[key]:
            raise ResponseSpectrumError(f"spectrum.units.{key} must be explicit")

    model_time = model_units.get("time")
    model_length = model_units.get("length")
    model_force = model_units.get("force")
    if not all(isinstance(x, str) and x for x in (model_time, model_length, model_force)):
        raise ResponseSpectrumError(
            "model units must explicitly include force, length, and time"
        )
    if units["period"] != model_time:
        raise ResponseSpectrumError(
            "spectrum period unit must exactly match canonical model units.time"
        )
    if units["displacement"] != model_length:
        raise ResponseSpectrumError(
            "spectrum displacement unit must exactly match canonical model units.length"
        )
    if units["base_shear"] != model_force:
        raise ResponseSpectrumError(
            "spectrum base_shear unit must exactly match canonical model units.force"
        )
    if spectrum.get("unit_consistency_verified") is not True:
        raise ResponseSpectrumError(
            "response spectrum requires unit_consistency_verified=true; "
            "the engine will not infer mass/acceleration/force conversion"
        )

    scale_factor = _positive(
        spectrum.get("scale_factor", 1.0),
        field_name="spectrum.scale_factor",
    )

    raw_points = spectrum.get("points")
    if not isinstance(raw_points, list) or len(raw_points) < 2:
        raise ResponseSpectrumError("response spectrum requires at least two points")

    points: list[dict[str, float]] = []
    seen_periods: set[float] = set()
    for index, item in enumerate(raw_points):
        if not isinstance(item, dict):
            raise ResponseSpectrumError(f"spectrum.points[{index}] must be an object")
        period = _finite(item.get("period"), field_name=f"spectrum.points[{index}].period")
        acceleration = _finite(
            item.get("spectral_acceleration"),
            field_name=f"spectrum.points[{index}].spectral_acceleration",
        )
        if period < 0:
            raise ResponseSpectrumError("spectrum periods must be >= 0")
        if acceleration < 0:
            raise ResponseSpectrumError("spectral acceleration must be >= 0")
        if period in seen_periods:
            raise ResponseSpectrumError(f"duplicate spectrum period: {period}")
        seen_periods.add(period)
        points.append({"period": period, "spectral_acceleration": acceleration})

    points.sort(key=lambda row: row["period"])
    return {
        "id": spectrum_id,
        "ordinate_type": "ACCELERATION",
        "damping_ratio": damping,
        "scale_factor": scale_factor,
        "units": {
            "period": units["period"],
            "spectral_acceleration": units["spectral_acceleration"],
            "displacement": units["displacement"],
            "base_shear": units["base_shear"],
        },
        "unit_consistency_verified": True,
        "points": points,
        "source_reference": spectrum.get("source_reference"),
    }


def interpolate_spectral_acceleration(
    normalized_spectrum: dict[str, Any],
    period: float,
) -> float:
    """Linearly interpolate Sa; fail outside the explicitly supplied period domain."""
    target = _finite(period, field_name="period")
    points = normalized_spectrum["points"]
    minimum = points[0]["period"]
    maximum = points[-1]["period"]
    if target < minimum or target > maximum:
        raise ResponseSpectrumError(
            f"period {target} is outside explicit spectrum domain [{minimum}, {maximum}]"
        )
    if target == minimum:
        return points[0]["spectral_acceleration"] * normalized_spectrum["scale_factor"]
    if target == maximum:
        return points[-1]["spectral_acceleration"] * normalized_spectrum["scale_factor"]

    for left, right in zip(points, points[1:]):
        p0 = left["period"]
        p1 = right["period"]
        if p0 <= target <= p1:
            if target == p0:
                value = left["spectral_acceleration"]
            elif target == p1:
                value = right["spectral_acceleration"]
            else:
                ratio = (target - p0) / (p1 - p0)
                value = left["spectral_acceleration"] + ratio * (
                    right["spectral_acceleration"] - left["spectral_acceleration"]
                )
            return value * normalized_spectrum["scale_factor"]

    raise ResponseSpectrumError("spectrum interpolation failed unexpectedly")


def _srss(values: list[float]) -> float:
    return math.sqrt(sum(float(value) ** 2 for value in values))


def _response_point_map(
    model: dict[str, Any],
    response_points: list[dict[str, Any]] | None,
    node_tags: dict[str, int],
) -> list[dict[str, Any]]:
    if response_points is None:
        return []
    if not isinstance(response_points, list) or not response_points:
        raise ResponseSpectrumError("response_points must be a non-empty list or null")

    storeys = {
        str(item.get("id")): item
        for item in model.get("storeys", []) or []
        if item.get("id") is not None
    }
    normalized: list[dict[str, Any]] = []
    seen_storeys: set[str] = set()
    for item in response_points:
        if not isinstance(item, dict):
            raise ResponseSpectrumError("each response point must be an object")
        storey_id = str(item.get("storey_id"))
        node_id = str(item.get("node_id"))
        if storey_id not in storeys:
            raise ResponseSpectrumError(
                f"response point references missing storey: {storey_id}"
            )
        if node_id not in node_tags:
            raise ResponseSpectrumError(
                f"response point references missing node: {node_id}"
            )
        if storey_id in seen_storeys:
            raise ResponseSpectrumError(
                f"multiple response points supplied for storey {storey_id}"
            )
        seen_storeys.add(storey_id)
        elevation = _finite(
            storeys[storey_id].get("elevation"),
            field_name=f"storey[{storey_id}].elevation",
        )
        normalized.append(
            {"storey_id": storey_id, "node_id": node_id, "elevation": elevation}
        )

    normalized.sort(key=lambda row: (row["elevation"], row["storey_id"]))
    return normalized


def _explicit_design_checks(
    *,
    config: dict[str, Any] | None,
    cumulative_mass_ratio: float | None,
    storey_drifts: list[dict[str, Any]],
) -> dict[str, Any]:
    if config is None:
        return {
            "status": "NOT_REQUESTED",
            "code_reference": None,
            "checks": [],
            "note": "No numerical code limits are hard-coded or inferred.",
        }
    if not isinstance(config, dict):
        raise ResponseSpectrumError("design_checks must be an object or null")

    code_reference = config.get("code_reference")
    if not isinstance(code_reference, str) or not code_reference:
        raise ResponseSpectrumError(
            "design_checks.code_reference must explicitly identify the governing source"
        )

    checks: list[dict[str, Any]] = []
    if "minimum_modal_mass_participation_ratio" in config:
        limit = _positive(
            config["minimum_modal_mass_participation_ratio"],
            field_name="design_checks.minimum_modal_mass_participation_ratio",
        )
        if limit > 1.0:
            raise ResponseSpectrumError(
                "minimum modal mass participation ratio cannot exceed 1.0"
            )
        if cumulative_mass_ratio is None:
            status = "UNRESOLVED"
        else:
            status = "PASS" if cumulative_mass_ratio >= limit else "FAIL"
        checks.append(
            {
                "check": "MINIMUM_MODAL_MASS_PARTICIPATION_RATIO",
                "limit": limit,
                "value": cumulative_mass_ratio,
                "status": status,
            }
        )

    if "maximum_interstorey_drift_ratio" in config:
        limit = _positive(
            config["maximum_interstorey_drift_ratio"],
            field_name="design_checks.maximum_interstorey_drift_ratio",
        )
        if not storey_drifts:
            status = "UNRESOLVED"
            value = None
        else:
            value = max(row["drift_ratio"] for row in storey_drifts)
            status = "PASS" if value <= limit else "FAIL"
        checks.append(
            {
                "check": "MAXIMUM_INTERSTOREY_DRIFT_RATIO",
                "limit": limit,
                "value": value,
                "status": status,
            }
        )

    overall = "PASS"
    if any(item["status"] == "FAIL" for item in checks):
        overall = "FAIL"
    elif any(item["status"] == "UNRESOLVED" for item in checks):
        overall = "UNRESOLVED"
    elif not checks:
        overall = "NO_NUMERICAL_LIMITS"

    return {
        "status": overall,
        "code_reference": code_reference,
        "checks": checks,
        "note": (
            "Limits are caller-supplied governed inputs; this engine does not "
            "manufacture Nepal-code numerical parameters."
        ),
    }


def run_canonical_response_spectrum(
    model: dict[str, Any],
    spectrum: dict[str, Any],
    num_modes: int,
    *,
    direction: str,
    modal_combination: str = "SRSS",
    response_points: list[dict[str, Any]] | None = None,
    design_checks: dict[str, Any] | None = None,
    eigen_solver: str = "auto",
) -> dict[str, Any]:
    """Run deterministic modal response-spectrum superposition for one direction.

    Storey displacement/drift is emitted only when response_points explicitly maps
    each requested storey to a canonical node. Accidental eccentricity and
    orthogonal-direction combination remain fail-closed future work.
    """
    axis = str(direction).upper()
    if axis not in _AXES:
        raise ResponseSpectrumError("direction must be X, Y, or Z")
    if str(modal_combination).upper() != "SRSS":
        raise ResponseSpectrumError(
            "Phase C seq8 currently supports only explicit modal_combination='SRSS'"
        )
    if not isinstance(num_modes, int) or num_modes < 1:
        raise ResponseSpectrumError("num_modes must be an integer >= 1")

    model_id = model.get("model_id")
    if not isinstance(model_id, str) or not model_id:
        raise ResponseSpectrumError("canonical seismic analysis requires model_id")

    units = model.get("units") or {}
    normalized_spectrum = normalize_response_spectrum(spectrum, model_units=units)

    build = build_canonical_frame_model(model)
    if not build.node_masses:
        raise ResponseSpectrumError(
            "response-spectrum analysis requires explicit nodal_masses"
        )

    eigenvalues, solver_used = _solve_eigenvalues(num_modes, solver=eigen_solver)
    modal_mass_rows, total_mass = _modal_mass_data(build, num_modes)
    response_map = _response_point_map(model, response_points, build.node_tags)
    dof = _AXES[axis]

    modal_rows: list[dict[str, Any]] = []
    point_modal_displacements: dict[str, list[float]] = {
        row["storey_id"]: [] for row in response_map
    }

    for mode_index, (eigenvalue, mass_row) in enumerate(
        zip(eigenvalues, modal_mass_rows),
        start=1,
    ):
        omega = math.sqrt(eigenvalue)
        frequency = omega / (2.0 * math.pi)
        period = 2.0 * math.pi / omega
        acceleration = interpolate_spectral_acceleration(normalized_spectrum, period)
        gamma = float(mass_row["participation_factor"][axis])
        effective_mass = float(mass_row["effective_modal_mass"][axis])
        base_shear = abs(effective_mass * acceleration)

        point_displacements: dict[str, float] = {}
        for point in response_map:
            phi = float(
                ops.nodeEigenvector(
                    build.node_tags[point["node_id"]],
                    mode_index,
                    dof,
                )
            )
            displacement = phi * gamma * acceleration / eigenvalue
            point_displacements[point["storey_id"]] = displacement
            point_modal_displacements[point["storey_id"]].append(displacement)

        modal_rows.append(
            {
                "mode": mode_index,
                "eigenvalue": eigenvalue,
                "circular_frequency": omega,
                "frequency": frequency,
                "period": period,
                "spectral_acceleration": acceleration,
                "participation_factor": gamma,
                "effective_modal_mass": effective_mass,
                "participation_ratio": mass_row["participation_ratio"][axis],
                "cumulative_participation_ratio": mass_row[
                    "cumulative_participation_ratio"
                ][axis],
                "base_shear": base_shear,
                "response_point_displacement": point_displacements,
            }
        )

    combined_base_shear = _srss([row["base_shear"] for row in modal_rows])
    combined_displacements = [
        {
            **point,
            "displacement": _srss(point_modal_displacements[point["storey_id"]]),
        }
        for point in response_map
    ]

    storey_drifts: list[dict[str, Any]] = []
    for lower, upper in zip(response_map, response_map[1:]):
        height = upper["elevation"] - lower["elevation"]
        if height <= 0:
            raise ResponseSpectrumError(
                "response-point storey elevations must be strictly increasing"
            )
        modal_drifts = [
            upper_value - lower_value
            for lower_value, upper_value in zip(
                point_modal_displacements[lower["storey_id"]],
                point_modal_displacements[upper["storey_id"]],
            )
        ]
        drift = _srss(modal_drifts)
        storey_drifts.append(
            {
                "lower_storey_id": lower["storey_id"],
                "upper_storey_id": upper["storey_id"],
                "height": height,
                "drift": drift,
                "drift_ratio": drift / height,
            }
        )

    cumulative_ratio = modal_rows[-1]["cumulative_participation_ratio"]
    checks = _explicit_design_checks(
        config=design_checks,
        cumulative_mass_ratio=cumulative_ratio,
        storey_drifts=storey_drifts,
    )

    digest = _model_digest(model)
    spectrum_key = (
        f"{normalized_spectrum['id']}:{axis}:SRSS:{num_modes}:"
        f"{normalized_spectrum['damping_ratio']}:{normalized_spectrum['scale_factor']}"
    )
    analysis_key = f"{model_id}:opensees-response-spectrum:{digest}:{spectrum_key}"
    try:
        solver_version = str(ops.version())
    except Exception:
        solver_version = "UNKNOWN"

    return {
        "schema_version": "0.1",
        "result_set_id": stable_id("RES", analysis_key),
        "analysis_run_id": stable_id("ANR", analysis_key),
        "model_id": model_id,
        "solver": {
            "name": "OpenSeesPy",
            "engine": "OpenSees",
            "version": solver_version,
            "analysis_type": "RESPONSE_SPECTRUM_MODAL_SUPERPOSITION",
            "eigen_solver": solver_used,
        },
        "case_results": [
            {
                "case_id": stable_id("CASE", analysis_key),
                "case_type": "RESPONSE_SPECTRUM",
                "direction": axis,
                "modal_combination": "SRSS",
                "num_modes": num_modes,
                "spectrum": normalized_spectrum,
                "total_translational_mass": total_mass.get(axis),
                "modes": modal_rows,
                "combined": {
                    "base_shear": combined_base_shear,
                    "storey_displacement": combined_displacements,
                    "interstorey_drift": storey_drifts,
                },
                "design_checks": checks,
            }
        ],
        "units": {
            **units,
            "spectral_acceleration": normalized_spectrum["units"][
                "spectral_acceleration"
            ],
            "base_shear": normalized_spectrum["units"]["base_shear"],
            "response_displacement": normalized_spectrum["units"]["displacement"],
            "drift_ratio": "dimensionless",
        },
        "qa": {
            "status": (
                "ENGINEER_REVIEW_REQUIRED"
                if checks["status"] in {"FAIL", "UNRESOLVED"}
                else "PASS_COMPUTATION"
            ),
            "pre_solve": build.pre_solve_qa,
            "warnings": build.warnings,
            "scope": {
                "response_spectrum_interpolation": "IMPLEMENTED_LINEAR_FAIL_OUTSIDE_DOMAIN",
                "modal_combination": "IMPLEMENTED_SRSS",
                "base_shear": "IMPLEMENTED_MODAL_SRSS",
                "storey_displacement": (
                    "IMPLEMENTED_EXPLICIT_RESPONSE_POINTS"
                    if response_map
                    else "NOT_REQUESTED"
                ),
                "interstorey_drift": (
                    "IMPLEMENTED_EXPLICIT_RESPONSE_POINTS"
                    if response_map
                    else "NOT_REQUESTED"
                ),
                "torsion_from_dynamic_modes": "PRESENT_ONLY_IF_MODEL_MODAL_RESPONSE_CONTAINS_IT",
                "accidental_eccentricity": "NOT_IMPLEMENTED_FAIL_CLOSED",
                "orthogonal_direction_combination": "NOT_IMPLEMENTED_FAIL_CLOSED",
                "nepal_code_numerical_limits": "CALLER_SUPPLIED_ONLY",
                "rc_design": "NOT_IMPLEMENTED",
            },
        },
        "provenance": {
            "adapter": "jp_structural.solvers.opensees.canonical_seismic/v0.1",
            "model_sha256": digest,
            "spectrum_id": normalized_spectrum["id"],
            "spectrum_source_reference": normalized_spectrum.get("source_reference"),
            "deterministic_ids": True,
            "source_preserving": True,
        },
    }
