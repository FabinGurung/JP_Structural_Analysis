"""OpenSees translation and modal analysis for the canonical structural model.

This module is intentionally fail-closed. It only translates structural meaning
that is explicit in the canonical model. It does not derive mass from load
patterns, invent diaphragm behaviour, infer release/offset behaviour, translate
shells, or claim ETABS/OpenSees equivalence.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any

import openseespy.opensees as ops

from jp_structural.model.ids import stable_id
from jp_structural.qa.pre_solve import run_pre_solve_qa


_DOF_INDEX = {"UX": 0, "UY": 1, "UZ": 2, "RX": 3, "RY": 4, "RZ": 5}
_AXIS_TO_DOF = {"X": 1, "Y": 2, "Z": 3}
_TRANSLATIONAL_AXES = ("X", "Y", "Z")


class CanonicalTranslationError(ValueError):
    """Raised when the canonical model lacks required explicit solver meaning."""


@dataclass
class CanonicalBuildResult:
    node_tags: dict[str, int]
    element_tags: dict[str, int]
    transformation_tags: dict[str, int]
    diaphragm_constraints: list[dict[str, Any]]
    node_masses: dict[str, tuple[float, float, float, float, float, float]]
    warnings: list[dict[str, Any]] = field(default_factory=list)
    pre_solve_qa: dict[str, Any] = field(default_factory=dict)


def _finite(value: Any, *, field_name: str) -> float:
    try:
        out = float(value)
    except Exception as exc:
        raise CanonicalTranslationError(f"{field_name} must be numeric") from exc
    if not math.isfinite(out):
        raise CanonicalTranslationError(f"{field_name} must be finite")
    return out


def _positive(value: Any, *, field_name: str) -> float:
    out = _finite(value, field_name=field_name)
    if out <= 0:
        raise CanonicalTranslationError(f"{field_name} must be > 0")
    return out


def _normalized_vector(values: Any, *, field_name: str) -> tuple[float, float, float]:
    if not isinstance(values, (list, tuple)) or len(values) != 3:
        raise CanonicalTranslationError(f"{field_name} must contain exactly three values")
    vec = tuple(_finite(v, field_name=field_name) for v in values)
    norm = math.sqrt(sum(v * v for v in vec))
    if norm <= 1e-12:
        raise CanonicalTranslationError(f"{field_name} must be non-zero")
    return tuple(v / norm for v in vec)


def _model_digest(model: dict[str, Any]) -> str:
    payload = json.dumps(
        model,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _material_lookup(model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id") or item.get("name")): item
        for item in model.get("materials", []) or []
        if item.get("id") is not None or item.get("name") is not None
    }


def _section_lookup(model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id") or item.get("name")): item
        for item in model.get("sections", []) or []
        if item.get("id") is not None or item.get("name") is not None
    }


def _support_lookup(model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id")): item
        for item in model.get("supports", []) or []
        if item.get("id") is not None
    }


def _rect_torsion_j(width: float, depth: float) -> float:
    a = max(width, depth)
    t = min(width, depth)
    ratio = t / a
    return a * t**3 * (1.0 / 3.0 - 0.21 * ratio * (1.0 - ratio**4 / 12.0))


def _rectangular_elastic_properties(
    section: dict[str, Any],
    material: dict[str, Any],
) -> dict[str, float]:
    width = _positive(section.get("width"), field_name="section.width")
    depth = _positive(section.get("depth"), field_name="section.depth")
    elastic_modulus = _positive(material.get("E"), field_name="material.E")
    poisson = _finite(material.get("poisson", 0.2), field_name="material.poisson")
    if not (-1.0 < poisson < 0.5):
        raise CanonicalTranslationError("material.poisson must be between -1 and 0.5")

    area_modifier = _positive(section.get("area_modifier", 1.0), field_name="section.area_modifier")
    i2_modifier = _positive(section.get("i2_modifier", 1.0), field_name="section.i2_modifier")
    i3_modifier = _positive(section.get("i3_modifier", 1.0), field_name="section.i3_modifier")
    torsion_modifier = _positive(
        section.get("torsion_modifier", 1.0),
        field_name="section.torsion_modifier",
    )

    area = width * depth * area_modifier
    iy = depth * width**3 / 12.0 * i2_modifier
    iz = width * depth**3 / 12.0 * i3_modifier
    shear_modulus = elastic_modulus / (2.0 * (1.0 + poisson))
    torsion = _rect_torsion_j(width, depth) * torsion_modifier
    return {
        "A": area,
        "E": elastic_modulus,
        "G": shear_modulus,
        "J": torsion,
        "Iy": iy,
        "Iz": iz,
    }


def _restraint_vector(tokens: Any) -> list[int]:
    if tokens is None:
        return [0] * 6
    if isinstance(tokens, str):
        values = [x for x in tokens.replace(",", " ").split() if x]
    elif isinstance(tokens, (list, tuple, set)):
        values = [str(x) for x in tokens]
    else:
        values = [str(tokens)]

    unknown = sorted(set(values) - set(_DOF_INDEX))
    if unknown:
        raise CanonicalTranslationError(f"Unknown restrained DOF token(s): {unknown}")

    vector = [0] * 6
    for token in values:
        vector[_DOF_INDEX[token]] = 1
    return vector


def _member_orientation(
    member: dict[str, Any],
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[tuple[float, float, float], bool]:
    explicit = member.get("local_axis_vector")
    if explicit is not None:
        vec = _normalized_vector(explicit, field_name="frame_member.local_axis_vector")
        dx = tuple(b[i] - a[i] for i in range(3))
        dnorm = math.sqrt(sum(v * v for v in dx))
        xaxis = tuple(v / dnorm for v in dx)
        cross = (
            xaxis[1] * vec[2] - xaxis[2] * vec[1],
            xaxis[2] * vec[0] - xaxis[0] * vec[2],
            xaxis[0] * vec[1] - xaxis[1] * vec[0],
        )
        if math.sqrt(sum(v * v for v in cross)) <= 1e-8:
            raise CanonicalTranslationError(
                f"Member {member.get('id')} local_axis_vector is parallel to the member axis"
            )
        return vec, True

    if member.get("local_axis_angle") is not None or member.get("orientation") is not None:
        raise CanonicalTranslationError(
            f"Member {member.get('id')} has local-axis data not implemented by this adapter; "
            "provide local_axis_vector explicitly"
        )

    dx = b[0] - a[0]
    dy = b[1] - a[1]
    dz = b[2] - a[2]
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length <= 1e-12:
        raise CanonicalTranslationError(f"Member {member.get('id')} has zero length")

    if abs(dz / length) > 0.999999:
        return (1.0, 0.0, 0.0), False
    return (0.0, 0.0, 1.0), False


def _explicit_nodal_masses(
    model: dict[str, Any],
    node_ids: set[str],
) -> dict[str, tuple[float, float, float, float, float, float]]:
    records = list(model.get("nodal_masses", []) or [])
    if not records:
        return {}

    if not (model.get("units") or {}).get("mass"):
        raise CanonicalTranslationError(
            "Explicit nodal masses require units.mass in the canonical model"
        )

    masses: dict[str, tuple[float, float, float, float, float, float]] = {}
    for item in records:
        node_id = str(item.get("node_id"))
        if node_id not in node_ids:
            raise CanonicalTranslationError(
                f"Nodal mass references missing node: {node_id}"
            )
        if node_id in masses:
            raise CanonicalTranslationError(f"Duplicate nodal mass record: {node_id}")

        values = tuple(
            _finite(item.get(key, 0.0), field_name=f"nodal_mass.{key}")
            for key in ("mx", "my", "mz", "mrx", "mry", "mrz")
        )
        if any(v < 0 for v in values):
            raise CanonicalTranslationError(
                f"Nodal mass values must be non-negative for node {node_id}"
            )
        masses[node_id] = values

    if not any(any(v > 0 for v in values[:3]) for values in masses.values()):
        raise CanonicalTranslationError("At least one positive translational nodal mass is required")
    return masses


def _apply_rigid_diaphragms(
    model: dict[str, Any],
    node_tags: dict[str, int],
) -> list[dict[str, Any]]:
    applied: list[dict[str, Any]] = []
    for diaphragm in sorted(model.get("diaphragms", []) or [], key=lambda x: str(x.get("id"))):
        did = str(diaphragm.get("id"))
        kind = str(diaphragm.get("constraint_type") or "").upper()
        if kind != "RIGID":
            raise CanonicalTranslationError(
                f"Diaphragm {did} does not explicitly declare constraint_type='RIGID'"
            )

        axis = str(diaphragm.get("perpendicular_axis") or "").upper()
        if axis not in _AXIS_TO_DOF:
            raise CanonicalTranslationError(
                f"Diaphragm {did} must explicitly declare perpendicular_axis as X, Y, or Z"
            )

        retained = diaphragm.get("retained_node_id")
        if retained is None:
            raise CanonicalTranslationError(
                f"Diaphragm {did} must explicitly declare retained_node_id"
            )
        retained = str(retained)

        member_nodes = sorted({str(x) for x in diaphragm.get("node_ids", []) or []})
        if retained not in member_nodes:
            raise CanonicalTranslationError(
                f"Diaphragm {did} retained_node_id must be included in node_ids"
            )
        missing = sorted(set(member_nodes) - set(node_tags))
        if missing:
            raise CanonicalTranslationError(
                f"Diaphragm {did} references missing node(s): {missing}"
            )
        constrained = [nid for nid in member_nodes if nid != retained]
        if not constrained:
            raise CanonicalTranslationError(
                f"Diaphragm {did} must constrain at least one node in addition to the retained node"
            )

        ops.rigidDiaphragm(
            _AXIS_TO_DOF[axis],
            node_tags[retained],
            *[node_tags[nid] for nid in constrained],
        )
        applied.append(
            {
                "diaphragm_id": did,
                "perpendicular_axis": axis,
                "retained_node_id": retained,
                "constrained_node_ids": constrained,
            }
        )
    return applied


def build_canonical_frame_model(model: dict[str, Any]) -> CanonicalBuildResult:
    """Build a 3D, six-DOF OpenSees elastic frame from canonical schema v0.1."""
    if str(model.get("schema_version")) != "0.1":
        raise CanonicalTranslationError("Only canonical schema_version 0.1 is supported")

    qa = run_pre_solve_qa(model)
    if qa.get("blocking"):
        codes = [
            finding.get("code")
            for finding in qa.get("findings", [])
            if finding.get("status") in {"FAIL", "UNRESOLVED"}
        ]
        raise CanonicalTranslationError(
            f"Pre-solve QA is blocking: {', '.join(str(x) for x in codes)}"
        )

    if model.get("shell_elements"):
        raise CanonicalTranslationError(
            "Shell translation is not implemented in Phase B; shell_elements must be empty"
        )
    if model.get("end_releases"):
        raise CanonicalTranslationError(
            "End-release solver equivalence is not implemented in Phase B"
        )
    if model.get("rigid_offsets"):
        raise CanonicalTranslationError(
            "Rigid-offset solver equivalence is not implemented in Phase B"
        )

    nodes = sorted(model.get("nodes", []) or [], key=lambda x: str(x.get("id")))
    if not nodes:
        raise CanonicalTranslationError("Canonical model contains no nodes")

    node_tags = {str(node["id"]): i + 1 for i, node in enumerate(nodes)}
    node_coords = {
        str(node["id"]): (
            _finite(node.get("x"), field_name="node.x"),
            _finite(node.get("y"), field_name="node.y"),
            _finite(node.get("z"), field_name="node.z"),
        )
        for node in nodes
    }

    ops.wipe()
    ops.model("Basic", "-ndm", 3, "-ndf", 6)

    for node in nodes:
        nid = str(node["id"])
        ops.node(node_tags[nid], *node_coords[nid])

    supports = _support_lookup(model)
    support_by_node: dict[str, dict[str, Any]] = {}
    for support in supports.values():
        node_id = str(support.get("node_id"))
        if node_id in support_by_node:
            raise CanonicalTranslationError(f"Multiple support records target node {node_id}")
        support_by_node[node_id] = support

    for node in nodes:
        nid = str(node["id"])
        support = support_by_node.get(nid)
        if support is None and node.get("support_id") is not None:
            support = supports.get(str(node.get("support_id")))
        if support is None:
            continue
        fixity = _restraint_vector(
            support.get("restrained_dofs") or support.get("restraint")
        )
        if any(fixity):
            ops.fix(node_tags[nid], *fixity)

    materials = _material_lookup(model)
    sections = _section_lookup(model)
    warnings: list[dict[str, Any]] = []
    element_tags: dict[str, int] = {}
    transformation_tags: dict[str, int] = {}

    frames = sorted(model.get("frame_members", []) or [], key=lambda x: str(x.get("id")))
    if not frames:
        raise CanonicalTranslationError("Canonical model contains no frame_members")

    for index, member in enumerate(frames, start=1):
        mid = str(member.get("id"))
        ni = str(member.get("i_node"))
        nj = str(member.get("j_node"))
        if ni not in node_tags or nj not in node_tags:
            raise CanonicalTranslationError(
                f"Frame member {mid} references missing node(s): {ni}, {nj}"
            )

        section_id = member.get("section_id") or member.get("section")
        if section_id is None or str(section_id) not in sections:
            raise CanonicalTranslationError(f"Frame member {mid} has no resolvable section")
        section = sections[str(section_id)]
        if str(section.get("section_family") or "frame").lower() != "frame":
            raise CanonicalTranslationError(
                f"Frame member {mid} references non-frame section {section_id}"
            )

        material_id = section.get("material_id") or section.get("material")
        if material_id is None or str(material_id) not in materials:
            raise CanonicalTranslationError(
                f"Section {section_id} has no resolvable elastic material"
            )
        material = materials[str(material_id)]

        shape = str(section.get("shape") or "")
        if shape not in {
            "Rectangular",
            "Concrete Rectangular",
            "Concrete Rectangular Section",
        }:
            raise CanonicalTranslationError(
                f"Section {section_id} shape is not supported by Phase B: {shape!r}"
            )

        props = _rectangular_elastic_properties(section, material)
        vecxz, explicit_axis = _member_orientation(
            member,
            node_coords[ni],
            node_coords[nj],
        )
        transf_tag = index
        ops.geomTransf("Linear", transf_tag, *vecxz)
        transformation_tags[mid] = transf_tag
        if not explicit_axis:
            warnings.append(
                {
                    "code": "LOCAL_AXIS_DETERMINISTIC_FALLBACK",
                    "member_id": mid,
                    "message": (
                        "Axis-aligned member used deterministic OpenSees orientation; "
                        "source-model local-axis equivalence still requires validation"
                    ),
                }
            )

        element_tag = index
        ops.element(
            "elasticBeamColumn",
            element_tag,
            node_tags[ni],
            node_tags[nj],
            props["A"],
            props["E"],
            props["G"],
            props["J"],
            props["Iy"],
            props["Iz"],
            transf_tag,
        )
        element_tags[mid] = element_tag

    diaphragm_constraints = _apply_rigid_diaphragms(model, node_tags)
    node_masses = _explicit_nodal_masses(model, set(node_tags))
    for node_id, values in node_masses.items():
        ops.mass(node_tags[node_id], *values)

    return CanonicalBuildResult(
        node_tags=node_tags,
        element_tags=element_tags,
        transformation_tags=transformation_tags,
        diaphragm_constraints=diaphragm_constraints,
        node_masses=node_masses,
        warnings=warnings,
        pre_solve_qa=qa,
    )


def _solve_eigenvalues(
    num_modes: int,
    *,
    solver: str,
) -> tuple[list[float], str]:
    if num_modes < 1:
        raise CanonicalTranslationError("num_modes must be >= 1")
    if solver not in {"auto", "arpack", "fullGenLapack"}:
        raise CanonicalTranslationError(f"Unsupported eigen solver: {solver!r}")

    ops.constraints("Transformation")
    ops.numberer("RCM")
    ops.system("BandGeneral")
    ops.test("NormDispIncr", 1e-12, 10, 0)
    ops.algorithm("Linear")
    ops.integrator("LoadControl", 1.0)
    ops.analysis("Static")

    used = solver
    if solver == "fullGenLapack":
        raw = ops.eigen("-fullGenLapack", num_modes)
    elif solver == "arpack":
        raw = ops.eigen(num_modes)
    else:
        try:
            raw = ops.eigen(num_modes)
            used = "arpack"
        except Exception:
            raw = ops.eigen("-fullGenLapack", num_modes)
            used = "fullGenLapack"

    values = [float(x) for x in raw]
    if len(values) != num_modes:
        raise CanonicalTranslationError(
            f"OpenSees returned {len(values)} eigenvalues; expected {num_modes}"
        )
    if any((not math.isfinite(x)) or x <= 0 for x in values):
        raise CanonicalTranslationError(f"OpenSees returned invalid eigenvalues: {values}")
    return values, used


def _modal_mass_data(
    build: CanonicalBuildResult,
    num_modes: int,
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    total_mass = {
        axis: sum(values[i] for values in build.node_masses.values())
        for i, axis in enumerate(_TRANSLATIONAL_AXES)
    }

    modes: list[dict[str, Any]] = []
    for mode in range(1, num_modes + 1):
        generalized_mass = 0.0
        numerators = {axis: 0.0 for axis in _TRANSLATIONAL_AXES}

        for node_id, masses in build.node_masses.items():
            tag = build.node_tags[node_id]
            for dof_index, mass in enumerate(masses, start=1):
                if mass <= 0:
                    continue
                phi = float(ops.nodeEigenvector(tag, mode, dof_index))
                generalized_mass += mass * phi * phi
                if dof_index <= 3:
                    numerators[_TRANSLATIONAL_AXES[dof_index - 1]] += mass * phi

        if generalized_mass <= 0 or not math.isfinite(generalized_mass):
            raise CanonicalTranslationError(
                f"Mode {mode} has invalid generalized mass {generalized_mass!r}"
            )

        participation_factors: dict[str, float] = {}
        effective_modal_mass: dict[str, float] = {}
        participation_ratio: dict[str, float | None] = {}
        for axis in _TRANSLATIONAL_AXES:
            gamma = numerators[axis] / generalized_mass
            effective = gamma * gamma * generalized_mass
            participation_factors[axis] = gamma
            effective_modal_mass[axis] = effective
            participation_ratio[axis] = (
                effective / total_mass[axis] if total_mass[axis] > 0 else None
            )

        modes.append(
            {
                "mode": mode,
                "generalized_mass": generalized_mass,
                "participation_factor": participation_factors,
                "effective_modal_mass": effective_modal_mass,
                "participation_ratio": participation_ratio,
            }
        )

    cumulative = {axis: 0.0 for axis in _TRANSLATIONAL_AXES}
    for item in modes:
        item["cumulative_participation_ratio"] = {}
        for axis in _TRANSLATIONAL_AXES:
            ratio = item["participation_ratio"][axis]
            if ratio is not None:
                cumulative[axis] += ratio
                item["cumulative_participation_ratio"][axis] = cumulative[axis]
            else:
                item["cumulative_participation_ratio"][axis] = None
    return modes, total_mass


def run_modal_analysis(
    model: dict[str, Any],
    num_modes: int,
    *,
    eigen_solver: str = "auto",
) -> dict[str, Any]:
    """Build and solve a canonical elastic-frame modal analysis."""
    model_id = model.get("model_id")
    if not isinstance(model_id, str) or not model_id:
        raise CanonicalTranslationError(
            "Canonical modal analysis requires a non-empty model_id"
        )
    units = model.get("units") or {}
    if not units.get("time"):
        raise CanonicalTranslationError(
            "Canonical modal analysis requires units.time for period/frequency results"
        )

    build = build_canonical_frame_model(model)
    if not build.node_masses:
        raise CanonicalTranslationError(
            "Canonical modal analysis requires explicit nodal_masses; "
            "mass-source load factors are not silently converted to nodal mass"
        )

    eigenvalues, solver_used = _solve_eigenvalues(num_modes, solver=eigen_solver)
    mass_modes, total_mass = _modal_mass_data(build, num_modes)

    modal_rows = []
    for eigenvalue, mass_row in zip(eigenvalues, mass_modes):
        omega = math.sqrt(eigenvalue)
        frequency = omega / (2.0 * math.pi)
        period = 2.0 * math.pi / omega
        modal_rows.append(
            {
                **mass_row,
                "eigenvalue": eigenvalue,
                "circular_frequency": omega,
                "frequency": frequency,
                "period": period,
            }
        )

    digest = _model_digest(model)
    analysis_key = f"{model_id}:opensees-modal:{digest}:{num_modes}:{solver_used}"
    analysis_run_id = stable_id("ANR", analysis_key)
    result_set_id = stable_id("RES", analysis_key)

    try:
        solver_version = str(ops.version())
    except Exception:
        solver_version = "UNKNOWN"

    return {
        "schema_version": "0.1",
        "result_set_id": result_set_id,
        "analysis_run_id": analysis_run_id,
        "model_id": model_id,
        "solver": {
            "name": "OpenSeesPy",
            "engine": "OpenSees",
            "version": solver_version,
            "analysis_type": "MODAL_EIGEN",
            "eigen_solver": solver_used,
        },
        "units": {
            **units,
            "circular_frequency": f"rad/{units['time']}",
            "frequency": f"1/{units['time']}",
            "period": units["time"],
        },
        "case_results": [
            {
                "case_id": stable_id("CASE", f"{model_id}:modal-eigen"),
                "case_type": "MODAL_EIGEN",
                "num_modes": num_modes,
                "total_translational_mass": total_mass,
                "modes": modal_rows,
            }
        ],
        "qa": {
            "status": "PASS",
            "pre_solve": build.pre_solve_qa,
            "warnings": build.warnings,
            "scope": {
                "frame_translation": "IMPLEMENTED_ELASTIC_RECTANGULAR",
                "explicit_nodal_mass": "IMPLEMENTED",
                "rigid_diaphragm": "IMPLEMENTED_WHEN_EXPLICIT",
                "modal_eigen": "IMPLEMENTED",
                "modal_participation": "IMPLEMENTED_TRANSLATIONAL",
                "shells": "NOT_IMPLEMENTED",
                "end_releases": "NOT_IMPLEMENTED",
                "rigid_offsets": "NOT_IMPLEMENTED",
                "response_spectrum": "NOT_IN_PHASE_B",
            },
        },
        "provenance": {
            "adapter": "jp_structural.solvers.opensees.canonical_frame/v0.1",
            "model_sha256": digest,
            "source_reference_ids": [
                str(item.get("id"))
                for item in model.get("source_references", []) or []
                if item.get("id") is not None
            ],
            "deterministic_ids": True,
            "source_preserving": True,
        },
    }
