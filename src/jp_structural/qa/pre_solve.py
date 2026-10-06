"""Fail-closed pre-solve QA for the evolving canonical model."""
from __future__ import annotations

import math
from collections import Counter, defaultdict, deque
from typing import Any

_DOF = {"UX", "UY", "UZ", "RX", "RY", "RZ"}
_TRANSLATIONAL_DOF = {"UX", "UY", "UZ"}


def _f(code: str, status: str, message: str, **context: Any) -> dict[str, Any]:
    return {"code": code, "status": status, "message": message, "context": context}


def _frames(model: dict[str, Any]) -> list[dict[str, Any]]:
    return list(model.get("frame_members", model.get("frames", [])) or [])


def _sections(model: dict[str, Any]) -> list[dict[str, Any]]:
    return list(model.get("sections", model.get("frame_sections", [])) or [])


def _member_nodes(member: dict[str, Any]) -> tuple[str, str]:
    return (
        str(member.get("i_node") or member.get("i")),
        str(member.get("j_node") or member.get("j")),
    )


def _section_ref(member: dict[str, Any]) -> Any:
    return member.get("section_id") or member.get("section")


def _parse_restraint(text: Any) -> set[str]:
    if not text:
        return set()
    if isinstance(text, str):
        return {x for x in text.replace(",", " ").split() if x}
    if isinstance(text, (list, tuple, set)):
        return {str(x) for x in text if str(x)}
    return {str(text)}


def _connected_components(adjacency: dict[str, set[str]]) -> list[set[str]]:
    remaining = set(adjacency)
    components: list[set[str]] = []
    while remaining:
        start = next(iter(remaining))
        comp: set[str] = set()
        queue = deque([start])
        while queue:
            node = queue.popleft()
            if node in comp:
                continue
            comp.add(node)
            remaining.discard(node)
            queue.extend(adjacency.get(node, ()))
        components.append(comp)
    return components


def _is_axis_aligned(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    tol: float,
) -> bool:
    nonzero = sum(abs(p - q) > tol for p, q in zip(a, b))
    return nonzero <= 1


def run_pre_solve_qa(
    model: dict[str, Any],
    *,
    near_node_tol: float = 1e-6,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    units = model.get("units") or {}
    for key in ("force", "length"):
        if not units.get(key):
            findings.append(_f("UNITS_MISSING", "FAIL", f"Missing {key} unit", field=key))

    nodes = list(model.get("nodes", []) or [])
    node_ids = [str(n.get("id")) for n in nodes]
    for nid, count in Counter(node_ids).items():
        if count > 1:
            findings.append(
                _f("DUPLICATE_NODE_ID", "FAIL", "Duplicate node ID", node_id=nid, count=count)
            )

    coords: dict[str, tuple[float, float, float]] = {}
    for n in nodes:
        nid = str(n.get("id"))
        try:
            xyz = tuple(float(n[k]) for k in ("x", "y", "z"))
        except Exception:
            findings.append(
                _f(
                    "INVALID_NODE_COORDINATE",
                    "FAIL",
                    "Node coordinates incomplete/non-numeric",
                    node_id=nid,
                )
            )
            continue
        if not all(math.isfinite(v) for v in xyz):
            findings.append(
                _f("INVALID_NODE_COORDINATE", "FAIL", "Node coordinate non-finite", node_id=nid)
            )
            continue
        coords[nid] = xyz

    cids = list(coords)
    tol2 = near_node_tol**2
    for i, a in enumerate(cids):
        for b in cids[i + 1 :]:
            d2 = sum((p - q) ** 2 for p, q in zip(coords[a], coords[b]))
            if d2 == 0:
                findings.append(
                    _f(
                        "COINCIDENT_NODES",
                        "WARNING",
                        "Distinct node IDs share coordinates",
                        node_a=a,
                        node_b=b,
                    )
                )
            elif d2 <= tol2:
                findings.append(
                    _f(
                        "NEAR_DUPLICATE_NODES",
                        "WARNING",
                        "Nodes are within tolerance",
                        node_a=a,
                        node_b=b,
                        distance=math.sqrt(d2),
                    )
                )

    materials = {
        str(m.get("id") or m.get("name")): m
        for m in model.get("materials", []) or []
    }
    sections = {
        str(s.get("id") or s.get("name")): s
        for s in _sections(model)
    }

    frames = _frames(model)
    frame_ids = {str(f.get("id")) for f in frames}
    used: set[str] = set()
    adjacency: dict[str, set[str]] = defaultdict(set)

    for member in frames:
        mid = str(member.get("id"))
        ni, nj = _member_nodes(member)
        if ni not in coords or nj not in coords:
            findings.append(
                _f(
                    "MEMBER_NODE_REFERENCE",
                    "FAIL",
                    "Member references missing node",
                    member_id=mid,
                    i_node=ni,
                    j_node=nj,
                )
            )
            continue

        used.update((ni, nj))
        adjacency[ni].add(nj)
        adjacency[nj].add(ni)

        if ni == nj or math.dist(coords[ni], coords[nj]) <= near_node_tol:
            findings.append(
                _f("ZERO_LENGTH_MEMBER", "FAIL", "Member length zero/near-zero", member_id=mid)
            )

        sec = _section_ref(member)
        if sec and str(sec) not in sections:
            findings.append(
                _f(
                    "MISSING_SECTION",
                    "FAIL",
                    "Member references missing section",
                    member_id=mid,
                    section=sec,
                )
            )

        if not _is_axis_aligned(coords[ni], coords[nj], near_node_tol):
            has_axis = any(
                member.get(key) is not None
                for key in ("local_axis_angle", "local_axis_vector", "orientation")
            )
            if not has_axis:
                findings.append(
                    _f(
                        "LOCAL_AXIS_UNRESOLVED",
                        "UNRESOLVED",
                        "Non-axis-aligned member has no explicit local-axis definition",
                        member_id=mid,
                    )
                )

    for sid, section in sections.items():
        mat = section.get("material_id") or section.get("material")
        if mat and str(mat) not in materials:
            findings.append(
                _f(
                    "MISSING_MATERIAL",
                    "FAIL",
                    "Section references missing material",
                    section_id=sid,
                    material=mat,
                )
            )

    for nid in sorted(set(coords) - used):
        findings.append(
            _f("ORPHAN_NODE", "WARNING", "Node not referenced by frame member", node_id=nid)
        )

    supported_nodes: set[str] = set()
    translational_coverage: set[str] = set()
    supports = list(model.get("supports", []) or [])
    for support in supports:
        sid = str(support.get("id"))
        nid = str(support.get("node_id"))
        if nid not in coords:
            findings.append(
                _f(
                    "SUPPORT_NODE_REFERENCE",
                    "FAIL",
                    "Support references missing node",
                    support_id=sid,
                    node_id=nid,
                )
            )
            continue
        dofs = _parse_restraint(
            support.get("restrained_dofs") or support.get("restraint")
        )
        invalid = sorted(dofs - _DOF)
        if invalid:
            findings.append(
                _f(
                    "SUPPORT_DOF_INVALID",
                    "FAIL",
                    "Support contains unknown degree-of-freedom token",
                    support_id=sid,
                    invalid_dofs=invalid,
                )
            )
        valid = dofs & _DOF
        if valid:
            supported_nodes.add(nid)
            translational_coverage.update(valid & _TRANSLATIONAL_DOF)

    if not supports:
        for node in nodes:
            nid = str(node.get("id"))
            dofs = _parse_restraint(node.get("restraint"))
            invalid = sorted(dofs - _DOF)
            if invalid:
                findings.append(
                    _f(
                        "SUPPORT_DOF_INVALID",
                        "FAIL",
                        "Node restraint contains unknown degree-of-freedom token",
                        node_id=nid,
                        invalid_dofs=invalid,
                    )
                )
            valid = dofs & _DOF
            if valid and nid in coords:
                supported_nodes.add(nid)
                translational_coverage.update(valid & _TRANSLATIONAL_DOF)

    if frames and not supported_nodes:
        findings.append(
            _f(
                "NO_SUPPORTS",
                "FAIL",
                "Frame model has no recognized restrained support node",
            )
        )
    elif frames:
        missing_axes = sorted(_TRANSLATIONAL_DOF - translational_coverage)
        if missing_axes:
            findings.append(
                _f(
                    "SUPPORT_STABILITY_UNRESOLVED",
                    "UNRESOLVED",
                    "Support restraints do not demonstrate translational restraint in all global axes",
                    missing_translational_dofs=missing_axes,
                )
            )

    if adjacency:
        components = _connected_components(adjacency)
        unsupported = [
            sorted(component)
            for component in components
            if not (component & supported_nodes)
        ]
        if unsupported:
            findings.append(
                _f(
                    "UNSUPPORTED_FRAME_COMPONENT",
                    "FAIL",
                    "A frame-connected component has no restrained support node",
                    component_count=len(unsupported),
                    component_sizes=[len(x) for x in unsupported],
                )
            )
        if len(components) > 1:
            findings.append(
                _f(
                    "DISCONNECTED_FRAME_COMPONENTS",
                    "UNRESOLVED",
                    "Model contains multiple disconnected frame components",
                    component_count=len(components),
                    component_sizes=sorted(len(x) for x in components),
                )
            )

    diaphragms = list(model.get("diaphragms", []) or [])
    diaphragm_ids = {str(d.get("id")) for d in diaphragms}
    membership: dict[str, set[str]] = defaultdict(set)

    for diaphragm in diaphragms:
        did = str(diaphragm.get("id"))
        for raw_nid in diaphragm.get("node_ids", []) or []:
            nid = str(raw_nid)
            if nid not in coords:
                findings.append(
                    _f(
                        "DIAPHRAGM_NODE_REFERENCE",
                        "FAIL",
                        "Diaphragm references missing node",
                        diaphragm_id=did,
                        node_id=nid,
                    )
                )
            else:
                membership[nid].add(did)

    for node in nodes:
        did = node.get("diaphragm_id")
        if did is None:
            continue
        did = str(did)
        nid = str(node.get("id"))
        if diaphragms and did not in diaphragm_ids:
            findings.append(
                _f(
                    "DIAPHRAGM_REFERENCE",
                    "FAIL",
                    "Node references missing diaphragm",
                    node_id=nid,
                    diaphragm_id=did,
                )
            )
        membership[nid].add(did)

    for nid, dids in membership.items():
        if len(dids) > 1:
            findings.append(
                _f(
                    "MULTIPLE_DIAPHRAGM_MEMBERSHIP",
                    "FAIL",
                    "Node is assigned to multiple diaphragms",
                    node_id=nid,
                    diaphragm_ids=sorted(dids),
                )
            )

    end_releases = list(model.get("end_releases", []) or [])
    for release in end_releases:
        rid = str(release.get("id"))
        mid = str(release.get("frame_member_id") or release.get("member_id"))
        if mid not in frame_ids:
            findings.append(
                _f(
                    "END_RELEASE_MEMBER_REFERENCE",
                    "FAIL",
                    "End release references missing frame member",
                    release_id=rid,
                    member_id=mid,
                )
            )
        for end_key in ("released_dofs_i", "released_dofs_j"):
            dofs = _parse_restraint(release.get(end_key))
            invalid = sorted(dofs - _DOF)
            if invalid:
                findings.append(
                    _f(
                        "END_RELEASE_DOF_INVALID",
                        "FAIL",
                        "End release contains unknown degree-of-freedom token",
                        release_id=rid,
                        end=end_key,
                        invalid_dofs=invalid,
                    )
                )
    if end_releases:
        findings.append(
            _f(
                "RELEASE_MECHANISM_CHECK_REQUIRED",
                "WARNING",
                "Release references are valid but mechanism stability requires solver/result verification",
                release_count=len(end_releases),
            )
        )

    rigid_offsets = list(model.get("rigid_offsets", []) or [])
    for offset in rigid_offsets:
        oid = str(offset.get("id"))
        mid = str(offset.get("frame_member_id") or offset.get("member_id"))
        if mid not in frame_ids:
            findings.append(
                _f(
                    "RIGID_OFFSET_MEMBER_REFERENCE",
                    "FAIL",
                    "Rigid offset references missing frame member",
                    rigid_offset_id=oid,
                    member_id=mid,
                )
            )
        for key, value in offset.items():
            if key.startswith(("offset_", "length_")) and isinstance(
                value, (int, float)
            ):
                if not math.isfinite(float(value)):
                    findings.append(
                        _f(
                            "RIGID_OFFSET_INVALID",
                            "FAIL",
                            "Rigid offset contains non-finite numeric value",
                            rigid_offset_id=oid,
                            field=key,
                        )
                    )
    if rigid_offsets:
        findings.append(
            _f(
                "RIGID_OFFSET_SOLVER_SUPPORT_REQUIRED",
                "UNRESOLVED",
                "Rigid offsets are present but solver-equivalent treatment is not yet verified",
                rigid_offset_count=len(rigid_offsets),
            )
        )

    patterns = {
        str(p.get("id") or p.get("name"))
        for p in model.get("load_patterns", []) or []
    }
    for item in (model.get("mass_source") or {}).get("load_factors", []) or []:
        pat = str(item.get("load_pattern_id") or item.get("pattern"))
        if patterns and pat not in patterns:
            findings.append(
                _f(
                    "MASS_PATTERN_REFERENCE",
                    "FAIL",
                    "Mass source references missing load pattern",
                    pattern=pat,
                )
            )

    load_cases = list(model.get("load_cases", []) or [])
    case_ids = {str(c.get("id") or c.get("name")) for c in load_cases}
    response_case_present = False
    for case in load_cases:
        case_type = str(case.get("type") or "").lower().replace("_", " ")
        if "response spectrum" in case_type:
            response_case_present = True
            modal_ref = case.get("modal_case_id") or case.get("modal_case")
            if (
                modal_ref is not None
                and case_ids
                and str(modal_ref) not in case_ids
            ):
                findings.append(
                    _f(
                        "RESPONSE_SPECTRUM_MODAL_CASE_REFERENCE",
                        "FAIL",
                        "Response-spectrum case references missing modal case",
                        case_id=str(case.get("id") or case.get("name")),
                        modal_case=modal_ref,
                    )
                )

    spectra = list(model.get("response_spectra", []) or [])
    if response_case_present and not spectra:
        findings.append(
            _f(
                "RESPONSE_SPECTRUM_INPUT_MISSING",
                "FAIL",
                "Response-spectrum load case exists but no response spectrum is normalized",
            )
        )
    for spectrum in spectra:
        sid = str(spectrum.get("id") or spectrum.get("name"))
        periods = spectrum.get("periods") or []
        ordinates = spectrum.get("ordinates") or spectrum.get("values") or []
        if not periods or len(periods) != len(ordinates):
            findings.append(
                _f(
                    "RESPONSE_SPECTRUM_SERIES_INVALID",
                    "FAIL",
                    "Response spectrum must contain equal non-empty period and ordinate arrays",
                    spectrum_id=sid,
                    period_count=len(periods),
                    ordinate_count=len(ordinates),
                )
            )
        damping = spectrum.get("damping_ratio")
        if damping is None:
            damping = (model.get("design_basis") or {}).get("damping_ratio")
        if damping is None:
            findings.append(
                _f(
                    "RESPONSE_SPECTRUM_DAMPING_UNRESOLVED",
                    "UNRESOLVED",
                    "Response-spectrum damping ratio is not normalized",
                    spectrum_id=sid,
                )
            )

    for case in model.get("analysis_cases", []) or []:
        case_type = (
            str(case.get("type") or "")
            .lower()
            .replace("_", "")
            .replace("-", "")
        )
        if "pdelta" in case_type:
            if not any(
                case.get(key) is not None
                for key in ("load_combination_id", "load_pattern_ids", "loads")
            ):
                findings.append(
                    _f(
                        "PDELTA_LOAD_STATE_UNRESOLVED",
                        "UNRESOLVED",
                        "P-Delta case does not identify its governing gravity/load state",
                        analysis_case_id=str(case.get("id")),
                    )
                )

    shells = list(
        model.get("shell_elements", model.get("areas", [])) or []
    )
    if shells:
        shell_mesh_qa = model.get("shell_mesh_qa") or {}
        if shell_mesh_qa.get("status") != "PASS":
            findings.append(
                _f(
                    "SHELL_MESH_ADEQUACY_UNVERIFIED",
                    "UNRESOLVED",
                    "Shell elements exist but mesh adequacy has not been independently verified",
                    shell_count=len(shells),
                )
            )

    if not model.get("design_basis"):
        findings.append(
            _f(
                "DESIGN_BASIS_UNRESOLVED",
                "UNRESOLVED",
                "Design basis/code edition not normalized",
            )
        )

    order = {"PASS": 0, "WARNING": 1, "UNRESOLVED": 2, "FAIL": 3}
    worst = max((order[x["status"]] for x in findings), default=0)
    status = next(k for k, value in order.items() if value == worst)
    return {
        "status": status,
        "blocking": status in {"FAIL", "UNRESOLVED"},
        "summary": {
            state: sum(x["status"] == state for x in findings)
            for state in order
        },
        "findings": findings,
    }
