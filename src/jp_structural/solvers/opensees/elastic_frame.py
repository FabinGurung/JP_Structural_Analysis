#!/usr/bin/env python3
"""Translate a normalized structural model into an elastic OpenSeesPy frame model.

This reusable translator intentionally models frame members only. Shell/slab/stair
translation, ETABS automatic meshing, offsets/end releases, and design checks are
separate controlled extensions. Project-specific source data must not be committed
to the public repository.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import openseespy.opensees as ops


DOF_TOKEN = {"UX":0, "UY":1, "UZ":2, "RX":3, "RY":4, "RZ":5}


@dataclass
class BuildResult:
    node_tags: dict[str, int]
    element_tags: dict[str, int]
    skipped_frames: list[dict[str, Any]]
    warnings: list[dict[str, Any]]


def _section_lookup(model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {s["name"]: s for s in model.get("frame_sections", [])}


def _material_lookup(model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {m["name"]: m for m in model.get("materials", [])}


def _rect_torsion_j(b: float, h: float) -> float:
    """Saint-Venant torsion constant approximation for a solid rectangle."""
    a=max(b,h); t=min(b,h)
    if a <= 0 or t <= 0:
        raise ValueError("Rectangle dimensions must be positive.")
    r=t/a
    return a*t**3*(1.0/3.0 - 0.21*r*(1.0-r**4/12.0))


def _rect_props(section: dict[str, Any], material: dict[str, Any]) -> dict[str, float]:
    b=float(section["width"]); h=float(section["depth"])
    E=float(material["E"])
    nu=float(material.get("poisson",0.2))
    A=b*h*float(section.get("area_modifier",1.0))
    # ETABS local 2/3 modifiers are preserved independently. For rectangular
    # sections, map weak/strong geometric axes deterministically; comparison QA
    # must confirm local-axis orientation against the source model.
    Iweak=h*b**3/12.0*float(section.get("i2_modifier",1.0))
    Istrong=b*h**3/12.0*float(section.get("i3_modifier",1.0))
    G=E/(2.0*(1.0+nu))
    J=_rect_torsion_j(b,h)*float(section.get("torsion_modifier",1.0))
    return {"A":A,"E":E,"G":G,"J":J,"Iy":Iweak,"Iz":Istrong}


def _restraint_vector(text: str | None) -> list[int]:
    v=[0]*6
    if not text:
        return v
    for token in text.split():
        if token in DOF_TOKEN:
            v[DOF_TOKEN[token]]=1
    return v


def build_elastic_frame_model(model: dict[str, Any]) -> BuildResult:
    if model.get("qa",{}).get("status") not in (None,"PASS_REFERENCE_INTEGRITY"):
        raise ValueError("Normalized model reference-integrity QA is not PASS.")

    ops.wipe()
    ops.model("Basic","-ndm",3,"-ndf",6)

    nodes=sorted(model.get("nodes",[]), key=lambda n:n["id"])
    node_tags={n["id"]:i+1 for i,n in enumerate(nodes)}
    for n in nodes:
        tag=node_tags[n["id"]]
        ops.node(tag,float(n["x"]),float(n["y"]),float(n["z"]))
        fix=_restraint_vector(n.get("restraint"))
        if any(fix):
            ops.fix(tag,*fix)

    sections=_section_lookup(model)
    materials=_material_lookup(model)
    warnings=[]; skipped=[]; element_tags={}

    # Two linear transformations cover the dominant member orientations.
    # Vertical column local-axis orientation is anchored by global X; horizontal
    # members are anchored by global Z. Any non-orthogonal member is still
    # supported by Linear transformation but must be checked during source QA.
    ops.geomTransf("Linear",1,0,0,1)  # horizontal / general nonvertical
    ops.geomTransf("Linear",2,1,0,0)  # vertical columns

    next_tag=1
    node_by_id={n["id"]:n for n in nodes}
    for f in sorted(model.get("frames",[]), key=lambda x:x["id"]):
        sec_name=f.get("section")
        if not sec_name or sec_name=="NONE" or f.get("type")=="LINE":
            skipped.append({"id":f["id"],"reason":"NO_STRUCTURAL_SECTION_OR_LINE_OBJECT"})
            continue
        sec=sections.get(sec_name)
        if not sec:
            skipped.append({"id":f["id"],"reason":"MISSING_SECTION","section":sec_name})
            continue
        mat=materials.get(sec.get("material"))
        if not mat or "E" not in mat:
            skipped.append({"id":f["id"],"reason":"MISSING_ELASTIC_MATERIAL","section":sec_name})
            continue
        if sec.get("shape") not in ("Concrete Rectangular","Concrete Rectangular Section","Rectangular"):
            skipped.append({"id":f["id"],"reason":"UNSUPPORTED_SECTION_SHAPE","shape":sec.get("shape")})
            continue
        if sec.get("width") is None or sec.get("depth") is None:
            skipped.append({"id":f["id"],"reason":"MISSING_RECTANGULAR_DIMENSIONS"})
            continue
        ni=f.get("i_node"); nj=f.get("j_node")
        if ni not in node_tags or nj not in node_tags:
            skipped.append({"id":f["id"],"reason":"MISSING_NODE_REFERENCE"})
            continue
        p1=node_by_id[ni]; p2=node_by_id[nj]
        dx=float(p2["x"])-float(p1["x"])
        dy=float(p2["y"])-float(p1["y"])
        dz=float(p2["z"])-float(p1["z"])
        L=math.sqrt(dx*dx+dy*dy+dz*dz)
        if L <= 1e-9:
            skipped.append({"id":f["id"],"reason":"ZERO_LENGTH"})
            continue
        vertical=abs(dz/L)>0.999999
        transf=2 if vertical else 1
        p=_rect_props(sec,mat)
        etag=next_tag; next_tag+=1
        ops.element("elasticBeamColumn",etag,node_tags[ni],node_tags[nj],
                    p["A"],p["E"],p["G"],p["J"],p["Iy"],p["Iz"],transf)
        element_tags[f["id"]]=etag

    return BuildResult(node_tags=node_tags,element_tags=element_tags,
                       skipped_frames=skipped,warnings=warnings)


def assign_lumped_node_masses(build: BuildResult, node_masses: dict[str, tuple[float,float,float]]) -> None:
    """Assign translational masses in model mass units; rotational masses are zero."""
    for node_id,(mx,my,mz) in node_masses.items():
        tag=build.node_tags[node_id]
        ops.mass(tag,float(mx),float(my),float(mz),0.0,0.0,0.0)


def eigen_periods(num_modes: int) -> list[float]:
    vals=ops.eigen(num_modes)
    return [2.0*math.pi/math.sqrt(float(lam)) for lam in vals]


def total_reaction(dof: int) -> float:
    ops.reactions()
    s=0.0
    for tag in ops.getNodeTags():
        try:
            s += float(ops.nodeReaction(tag,dof))
        except Exception:
            pass
    return s
