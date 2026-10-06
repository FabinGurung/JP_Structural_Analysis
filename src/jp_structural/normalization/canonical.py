"""Bridge the source-preserving legacy E2K payload into the canonical model.

This translator only converts meaning already normalized from the source. It does
not infer releases, rigid offsets, local-axis rotations, shell meshing, seismic
parameters, or member design data that were not parsed from the E2K.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from jp_structural.model.ids import stable_id

_NONE = {None, "", "NONE", "None"}


def _clean(value: Any) -> Any:
    return None if value in _NONE else value


def _entity_id(prefix: str, source_key: str) -> str:
    return stable_id(prefix, str(source_key))


def _copy_without(item: dict[str, Any], *keys: str) -> dict[str, Any]:
    blocked = set(keys)
    return {k: deepcopy(v) for k, v in item.items() if k not in blocked}


def canonicalize_e2k_model(
    legacy: dict[str, Any],
    *,
    project_id: str,
    model_id: str | None = None,
    design_basis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert the current legacy E2K normalization payload to schema v0.1.

    Stable canonical IDs are generated from source keys. Source labels and raw
    normalization warnings are preserved so a later adapter can reconcile the
    canonical model back to the governed source evidence.
    """
    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("project_id must be a non-empty string")

    source_schema = str(legacy.get("schema") or "")
    if not source_schema.startswith("jp_structural.normalized_model.legacy_e2k."):
        raise ValueError(f"Unsupported legacy source schema: {source_schema!r}")

    source = deepcopy(legacy.get("source") or {})
    source_key = source.get("sha256") or source.get("filename") or "unknown-e2k-source"
    source_id = _entity_id("SRC", f"e2k:{source_key}")

    stories = list(legacy.get("stories") or [])
    storey_ids = {str(x.get("name")): _entity_id("STY", str(x.get("name"))) for x in stories}

    legacy_materials = list(legacy.get("materials") or [])
    material_ids = {
        str(x.get("name")): _entity_id("MAT", str(x.get("name")))
        for x in legacy_materials
        if _clean(x.get("name")) is not None
    }

    legacy_frame_sections = list(legacy.get("frame_sections") or [])
    legacy_shell_sections = list(legacy.get("slab_properties") or [])
    frame_section_ids = {
        str(x.get("name")): _entity_id("SEC", f"frame:{x.get('name')}")
        for x in legacy_frame_sections
        if _clean(x.get("name")) is not None
    }
    shell_section_ids = {
        str(x.get("name")): _entity_id("SEC", f"shell:{x.get('name')}")
        for x in legacy_shell_sections
        if _clean(x.get("name")) is not None
    }

    legacy_nodes = list(legacy.get("nodes") or [])
    node_ids = {
        str(x.get("id")): _entity_id("NOD", str(x.get("id")))
        for x in legacy_nodes
        if _clean(x.get("id")) is not None
    }

    legacy_frames = list(legacy.get("frames") or [])
    frame_ids = {
        str(x.get("id")): _entity_id("FRM", str(x.get("id")))
        for x in legacy_frames
        if _clean(x.get("id")) is not None
    }

    legacy_areas = list(legacy.get("areas") or [])
    shell_ids = {
        str(x.get("id")): _entity_id("SHL", str(x.get("id")))
        for x in legacy_areas
        if _clean(x.get("id")) is not None
    }

    diaphragm_names = sorted({
        str(v)
        for item in [*legacy_nodes, *legacy_areas]
        for v in [item.get("diaphragm")]
        if _clean(v) is not None
    })
    diaphragm_ids = {name: _entity_id("DIA", name) for name in diaphragm_names}

    patterns = list(legacy.get("load_patterns") or [])
    pattern_ids = {
        str(x.get("name")): _entity_id("LPAT", str(x.get("name")))
        for x in patterns
        if _clean(x.get("name")) is not None
    }

    cases = list(legacy.get("load_cases") or [])
    case_ids = {
        str(x.get("name")): _entity_id("CASE", str(x.get("name")))
        for x in cases
        if _clean(x.get("name")) is not None
    }

    materials = []
    for src in legacy_materials:
        name = _clean(src.get("name"))
        if name is None:
            continue
        out = _copy_without(src, "name")
        out.update({"id": material_ids[str(name)], "source_name": str(name)})
        materials.append(out)

    sections = []
    for family, source_items, id_map in (
        ("frame", legacy_frame_sections, frame_section_ids),
        ("shell", legacy_shell_sections, shell_section_ids),
    ):
        for src in source_items:
            name = _clean(src.get("name"))
            if name is None:
                continue
            material_name = _clean(src.get("material"))
            out = _copy_without(src, "name", "material")
            out.update({
                "id": id_map[str(name)],
                "source_name": str(name),
                "section_family": family,
                "material_id": material_ids.get(str(material_name)) if material_name is not None else None,
                "source_material": material_name,
            })
            sections.append(out)

    supports = []
    nodes = []
    for src in legacy_nodes:
        legacy_id = _clean(src.get("id"))
        if legacy_id is None:
            continue
        cid = node_ids[str(legacy_id)]
        restraint = _clean(src.get("restraint"))
        support_id = None
        if restraint is not None:
            support_id = _entity_id("SUP", str(legacy_id))
            supports.append({
                "id": support_id,
                "node_id": cid,
                "restrained_dofs": str(restraint).split(),
                "source_text": str(restraint),
            })
        diaphragm = _clean(src.get("diaphragm"))
        nodes.append({
            "id": cid,
            "source_id": str(legacy_id),
            "source_point_id": src.get("source_point_id"),
            "storey_id": storey_ids.get(str(src.get("story"))),
            "source_storey": src.get("story"),
            "x": src.get("x"),
            "y": src.get("y"),
            "z": src.get("z"),
            "support_id": support_id,
            "diaphragm_id": diaphragm_ids.get(str(diaphragm)) if diaphragm is not None else None,
            "user_joint": src.get("user_joint"),
        })

    frame_members = []
    for src in legacy_frames:
        legacy_id = _clean(src.get("id"))
        if legacy_id is None:
            continue
        section_name = _clean(src.get("section"))
        frame_members.append({
            "id": frame_ids[str(legacy_id)],
            "source_id": src.get("source_id"),
            "source_instance_id": str(legacy_id),
            "storey_id": storey_ids.get(str(src.get("story"))),
            "source_storey": src.get("story"),
            "member_type": src.get("type"),
            "i_node": node_ids.get(str(src.get("i_node"))),
            "j_node": node_ids.get(str(src.get("j_node"))),
            "section_id": frame_section_ids.get(str(section_name)) if section_name is not None else None,
            "source_section": section_name,
        })

    shell_elements = []
    for src in legacy_areas:
        legacy_id = _clean(src.get("id"))
        if legacy_id is None:
            continue
        section_name = _clean(src.get("section"))
        diaphragm = _clean(src.get("diaphragm"))
        shell_elements.append({
            "id": shell_ids[str(legacy_id)],
            "source_id": src.get("source_id"),
            "source_instance_id": str(legacy_id),
            "storey_id": storey_ids.get(str(src.get("story"))),
            "source_storey": src.get("story"),
            "element_type": src.get("type"),
            "node_ids": [node_ids.get(str(x)) for x in src.get("nodes", [])],
            "section_id": shell_section_ids.get(str(section_name)) if section_name is not None else None,
            "source_section": section_name,
            "diaphragm_id": diaphragm_ids.get(str(diaphragm)) if diaphragm is not None else None,
            "add_restraint": src.get("add_restraint"),
            "connectivity_tail": src.get("connectivity_tail"),
        })

    diaphragms = []
    for name in diaphragm_names:
        did = diaphragm_ids[name]
        member_nodes = sorted({
            n["id"] for n in nodes if n.get("diaphragm_id") == did
        } | {
            node_id
            for shell in shell_elements if shell.get("diaphragm_id") == did
            for node_id in shell.get("node_ids", [])
            if node_id is not None
        })
        diaphragms.append({"id": did, "source_name": name, "node_ids": member_nodes})

    load_patterns = []
    for src in patterns:
        name = _clean(src.get("name"))
        if name is None:
            continue
        out = _copy_without(src, "name")
        out.update({"id": pattern_ids[str(name)], "source_name": str(name)})
        load_patterns.append(out)

    load_cases = []
    for src in cases:
        name = _clean(src.get("name"))
        if name is None:
            continue
        modal_name = _clean(src.get("modal_case"))
        out = _copy_without(src, "name", "modal_case")
        out.update({
            "id": case_ids[str(name)],
            "source_name": str(name),
            "modal_case_id": case_ids.get(str(modal_name)) if modal_name is not None else None,
            "source_modal_case": modal_name,
        })
        load_cases.append(out)

    load_combinations = []
    for name in legacy.get("load_combinations") or []:
        if _clean(name) is None:
            continue
        load_combinations.append({
            "id": _entity_id("COMBO", str(name)),
            "source_name": str(name),
            "components": [],
            "normalization_status": "SOURCE_COMPONENTS_NOT_PARSED",
        })

    def _load_id(kind: str, index: int, src: dict[str, Any]) -> str:
        return _entity_id(
            "LOAD",
            f"{kind}:{index}:{src.get('story')}:{src.get('source_id')}:{src.get('load_pattern')}:{src.get('type')}",
        )

    frame_loads = []
    for i, src in enumerate(legacy.get("frame_loads") or []):
        pattern_name = _clean(src.get("load_pattern"))
        legacy_member = f"{src.get('story')}::{src.get('source_id')}"
        out = _copy_without(src, "load_pattern")
        out.update({
            "id": _load_id("frame", i, src),
            "frame_member_id": frame_ids.get(legacy_member),
            "load_pattern_id": pattern_ids.get(str(pattern_name)) if pattern_name is not None else None,
            "source_load_pattern": pattern_name,
        })
        frame_loads.append(out)

    area_loads = []
    for i, src in enumerate(legacy.get("area_loads") or []):
        pattern_name = _clean(src.get("load_pattern"))
        legacy_shell = f"{src.get('story')}::{src.get('source_id')}"
        out = _copy_without(src, "load_pattern")
        out.update({
            "id": _load_id("area", i, src),
            "shell_element_id": shell_ids.get(legacy_shell),
            "load_pattern_id": pattern_ids.get(str(pattern_name)) if pattern_name is not None else None,
            "source_load_pattern": pattern_name,
        })
        area_loads.append(out)

    legacy_mass = deepcopy(legacy.get("mass_source") or {})
    mass_factors = []
    for src in legacy_mass.get("load_factors") or []:
        pattern_name = _clean(src.get("pattern") or src.get("load_pattern_id"))
        mass_factors.append({
            "load_pattern_id": pattern_ids.get(str(pattern_name)) if pattern_name is not None else None,
            "source_load_pattern": pattern_name,
            "factor": src.get("factor"),
        })
    mass_source = {
        "id": _entity_id("MASS", legacy_mass.get("definition") or "default"),
        "source_definition": legacy_mass.get("definition"),
        "load_factors": mass_factors,
    }

    storeys = [{
        "id": storey_ids[str(src.get("name"))],
        "source_name": src.get("name"),
        "elevation": src.get("elevation"),
    } for src in stories if _clean(src.get("name")) is not None]

    source_reference = {
        "id": source_id,
        "source_type": "ETABS_E2K",
        "filename": source.get("filename"),
        "sha256": source.get("sha256"),
        "size_bytes": source.get("size_bytes"),
        "authority_role": "SOURCE_EVIDENCE",
    }

    translation_scope = {
        "local_axes": "NOT_NORMALIZED_FROM_LEGACY_PAYLOAD",
        "end_releases": "NOT_NORMALIZED_FROM_LEGACY_PAYLOAD",
        "rigid_offsets": "NOT_NORMALIZED_FROM_LEGACY_PAYLOAD",
        "stiffness_modifiers": "PARTIAL_SECTION_LEVEL_ONLY",
        "response_spectra": "NOT_NORMALIZED_FROM_LEGACY_PAYLOAD",
        "p_delta": "NOT_NORMALIZED_FROM_LEGACY_PAYLOAD",
        "shell_mesh": "SOURCE_CONNECTIVITY_PRESERVED_BUT_ADEQUACY_NOT_VERIFIED",
        "load_combination_components": "NOT_NORMALIZED_FROM_LEGACY_PAYLOAD",
    }

    return {
        "schema_version": "0.1",
        "model_id": model_id or _entity_id("MOD", f"{project_id}:{source_key}"),
        "project": {"project_id": project_id},
        "units": deepcopy(legacy.get("units") or {}),
        "design_basis": deepcopy(design_basis),
        "source_references": [source_reference],
        "storeys": storeys,
        "nodes": nodes,
        "frame_members": frame_members,
        "shell_elements": shell_elements,
        "materials": materials,
        "sections": sections,
        "supports": supports,
        "constraints": [],
        "diaphragms": diaphragms,
        "end_releases": [],
        "rigid_offsets": [],
        "stiffness_modifiers": [],
        "load_patterns": load_patterns,
        "load_cases": load_cases,
        "load_combinations": load_combinations,
        "mass_source": mass_source,
        "joint_loads": [],
        "frame_loads": frame_loads,
        "area_loads": area_loads,
        "response_spectra": [],
        "analysis_cases": [],
        "source_qa": deepcopy(legacy.get("qa") or {}),
        "normalization_warnings": deepcopy((legacy.get("qa") or {}).get("warnings") or []),
        "translation_scope": translation_scope,
        "provenance": {
            "source_schema": source_schema,
            "translator": "canonicalize_e2k_model/v0.1",
            "source_reference_id": source_id,
            "source_preserving": True,
        },
    }
