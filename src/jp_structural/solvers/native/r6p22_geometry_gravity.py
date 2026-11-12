"""R6.22 first-party drawing-derived geometry -> explicit gravity load path.

Only axis-aligned rectangular horizontal ONE-WAY slab panels with two declared
opposite full-edge beams, horizontal RC beams, and plumb RC columns are
supported. Self-weight is derived from source-declared section geometry and
unit weights; openings are subtracted from wall line loading. Every load
passes through a conserved source ledger and real OpenSees beam element
loading. Column distributed self-weight is HALF-LUMPED at its ends: global
equilibrium is conserved, but this approximation is not an exact internal
column axial-force diagram. No ETABS export or output is required.
"""
from __future__ import annotations

from collections import defaultdict, deque
import hashlib
import json
import math
from typing import Any

from jp_structural.solvers.native.one_way_panel_to_beams import transfer_one_way_panels, PanelRoutingError\nfrom jp_structural.solvers.native.geometry_load_intake import GeometryLoadError

SCHEMA = "jp.structural.r6p22.independent_geometry_gravity.v0.1"
INPUT_SCHEMA = "jp.structural.r6p22.independent_geometry_input.v0.1"


class GeometryGravityHold(ValueError):
    """Missing, unsafe or ambiguous structural geometry/load assumption."""


def require(ok: bool, message: str) -> None:
    if not ok:
        raise GeometryGravityHold("HOLD: " + message)


def number(v: Any, name: str, *, allow_zero: bool = False) -> float:
    require(isinstance(v, (float, int)) and not isinstance(v, bool)
            and math.isfinite(v) and (v >= 0 if allow_zero else v > 0),
            name + " must be finite " + ("nonnegative" if allow_zero else "positive"))
    return float(v)


def source(v: Any, name: str) -> str:
    require(isinstance(v, str) and len(v.strip()) >= 8,
            name + " requires explicit traceable source or assumption ID")
    return v.strip()


def sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")).hexdigest()


def _xyz(node: dict) -> tuple[float, float, float]:
    xyz = []
    for axis in ("x", "y", "z"):
        value = node.get(axis)
        require(isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value), "node coordinate " + axis + " invalid")
        xyz.append(float(value))
    return tuple(xyz)


def _close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=0, abs_tol=1e-8)


def _structural_graph(model: dict) -> dict:
    """Exact node identities, explicit member connectivity and anchored paths."""
    require(model.get("units") == {
        "force": "kN", "length": "m", "time": "s", "mass": "kN*s^2/m"
    }, "kN/m/s canonical model units required")
    require(not any(model.get(x) for x in (
        "joint_loads", "frame_loads", "area_loads", "load_cases",
        "load_patterns", "load_combinations", "mass_source", "nodal_masses",
        "shell_elements", "end_releases", "rigid_offsets", "diaphragms"
    )), "existing loads, masses, shells, end offsets or diaphragms unsupported")
    nodes = model.get("nodes")
    members = model.get("frame_members")
    supports = model.get("supports")
    require(isinstance(nodes, list) and nodes and isinstance(members, list) and
            members and isinstance(supports, list) and supports,
            "explicit nodes/members/physical support constraints required")
    nd = {}
    coords = {}
    for row in nodes:
        nid = row.get("id")
        require(isinstance(nid, str) and nid and nid not in nd,
                "duplicate/missing exact structural node ID")
        nd[nid] = row
        coords[nid] = _xyz(row)
    for a, p in coords.items():
        for b, q in coords.items():
            if a < b:
                require(math.dist(p, q) > 1e-8,
                        "coincident different node IDs " + a + "/" + b +
                        ": no proximity auto-join")
    adj = defaultdict(set)
    edges = set()
    kind = {}
    for row in members:
        mid = row.get("id")
        a, b = row.get("i_node"), row.get("j_node")
        require(isinstance(mid, str) and mid and mid not in kind
                and a in nd and b in nd and a != b,
                "duplicate/missing member or endpoint reference")
        require(row.get("member_type") in {"BEAM", "COLUMN"},
                "only explicit BEAM/COLUMN member types")
        require(not any(row.get(k) is not None for k in (
            "local_axis_vector", "local_axis_angle", "orientation"
        )), "custom local member axis requires separate element mapping")
        pa, pb = coords[a], coords[b]
        length = math.dist(pa, pb)
        require(length > 1e-8, "zero-length member " + mid)
        if row["member_type"] == "BEAM":
            require(_close(pa[2], pb[2]), "inclined beam " + mid +
                    " lacks vertical distributed load mapping")
        else:
            require(_close(pa[0], pb[0]) and _close(pa[1], pb[1]),
                    "non-plumb column " + mid + " lacks axial weight mapping")
        edge = frozenset((a, b))
        require(edge not in edges, "duplicated physical frame span " + mid)
        edges.add(edge)
        adj[a].add(b)
        adj[b].add(a)
        kind[mid] = row
    # A member interior endpoint / hanging node without an actual shared
    # identity is a physical ambiguity, NOT a solver-permitted rigid tie.
    for m in members:
        a, b = coords[m["i_node"]], coords[m["j_node"]]
        delta = tuple(b[i] - a[i] for i in range(3))
        squared = math.fsum(d*d for d in delta)
        for nid, p in coords.items():
            if nid in (m["i_node"], m["j_node"]):
                continue
            t = math.fsum((p[i]-a[i])*delta[i] for i in range(3)) / squared
            if 1e-8 < t < 1-1e-8:
                closest = tuple(a[i]+t*delta[i] for i in range(3))
                require(math.dist(closest, p) > 1e-8,
                        "hanging node " + nid + " on member " + m["id"] +
                        " requires explicit beam split/shared joint")
    ids = {r.get("id") for r in supports}
    require(len(ids) == len(supports), "duplicate base support ID")
    support_nodes = set()
    for row in supports:
        nid = row.get("node_id")
        dofs = row.get("restrained_dofs")
        require(nid in nd and isinstance(dofs, list) and dofs,
                "physical support requires known node and explicit restrained DOFs")
        support_nodes.add(nid)
    visited = set(support_nodes)
    queue = deque(support_nodes)
    while queue:
        for v in adj[queue.popleft()]:
            if v not in visited:
                visited.add(v)
                queue.append(v)
    require(set(nd) <= visited and all(nd[x] for x in visited),
            "frame component or node cannot reach a declared structural base")
    return {
        "node_count": len(nd), "frame_count": len(members),
        "beam_count": sum(x["member_type"] == "BEAM" for x in members),
        "column_count": sum(x["member_type"] == "COLUMN" for x in members),
        "base_support_count": len(supports),
        "all_source_nodes_reach_declared_base": True,
        "proximity_auto_join_count": 0,
        "unsupported_hanging_node_count": 0,
    }


def derive_sources(payload: dict) -> dict:
    """Build concrete/finish/live/wall/beam and column gravity ledger."""
    require(isinstance(payload, dict) and payload.get("schema") == INPUT_SCHEMA,
            "R6.22 native geometry input schema required")
    require(payload.get("classification") in {
        "SYNTHETIC_REFERENCE", "PROJECT_SOURCE_DERIVED_UNVERIFIED"
    }, "source classification required, never an approval assertion")
    case_id = source(payload.get("case_id"), "case_id")
    g = number(payload.get("gravity_m_s2"), "gravity")
    require(payload.get("include_frame_self_weight") is True,
            "R6.22 requires explicit single-source frame self-weight accounting")
    model = payload.get("model")
    require(isinstance(model, dict), "canonical independent model required")
    require(model.get("model_id") == case_id,
            "case/model identity mismatch")
    graph = _structural_graph(model)
    material_rows = payload.get("physical_materials")
    require(isinstance(material_rows, list) and material_rows,
            "physical unit-weight catalogue required")
    mat = {}
    for row in material_rows:
        mid = row.get("id")
        require(isinstance(mid, str) and mid and mid not in mat,
                "material unit-weight key invalid or duplicate")
        mat[mid] = number(row.get("unit_weight_kN_m3"),
                          "material.unit_weight_kN_m3")
        source(row.get("source_id"), "material.source_id")
    nodes = {n["id"]: n for n in model["nodes"]}
    frames = {m["id"]: m for m in model["frame_members"]}
    secs = {s["id"]: s for s in model.get("sections", [])}
    require(len(secs) == len(model.get("sections", [])) and secs,
            "unique physical section definitions required")
    loads, routes, ledger = [], [], []
    nodal_column = defaultdict(float)
    ledger_column = []
    physical_ids = set()

    def new_id(i):
        require(isinstance(i, str) and len(i) >= 2 and i not in physical_ids,
                "duplicate/short physical object ID " + str(i))
        physical_ids.add(i)

    def add_panel(pid, key, pressure, category, factor, points, provenance):
        if pressure <= 0:
            return
        lid = pid + "::" + key
        require(lid not in {x["id"] for x in loads},
                "duplicate physical panel layer source")
        loads.append({
            "id": lid, "source_key": case_id + "::" + lid,
            "type": "UNIFORM_PANEL_PRESSURE",
            "load_category": category, "case_id": "DL" if category == "DEAD" else "LL",
            "boundary_node_ids": points, "pressure_kPa": pressure,
            "participation_factor": factor,
            "node_shares": [{"node_id": nid, "fraction": 0.25} for nid in points],
            "provenance": provenance
        })
        routes.append({
            "panel_source_id": lid,
            "span_direction": panel["span_direction"],
            "edge_beam_member_ids": panel["edge_beam_member_ids"],
            "transfer_model": "ONE_WAY_SIMPLY_SUPPORTED"
        })

    panels = payload.get("panels")
    require(isinstance(panels, list) and panels,
            "at least one source-declared structural floor panel required")
    bounds = []
    for panel in panels:
        pid = panel.get("id")
        new_id(pid)
        source(panel.get("source_id"), "panel.source_id")
        corners = panel.get("boundary_node_ids")
        require(isinstance(corners, list) and len(corners) == 4
                and len(set(corners)) == 4 and set(corners) <= set(nodes),
                "only four distinct explicit panel corner nodes are supported")
        require(panel.get("span_direction") in ("X", "Y")
                and isinstance(panel.get("edge_beam_member_ids"), list)
                and len(panel["edge_beam_member_ids"]) == 2,
                "one-way span and two opposite full-edge beam IDs required; "
                "two-way, cantilever and unknown slab edges remain HOLD")
        xyz = [_xyz(nodes[n]) for n in corners]
        xx = sorted({p[0] for p in xyz})
        yy = sorted({p[1] for p in xyz})
        require(len(xx) == 2 and len(yy) == 2
                and len({p[2] for p in xyz}) == 1
                and {(p[0],p[1]) for p in xyz} == {
                    (xx[0],yy[0]),(xx[0],yy[1]),(xx[1],yy[0]),(xx[1],yy[1])
                }, "only horizontal axis-aligned rectangles supported")
        require(xx[1] > xx[0] and yy[1] > yy[0],
                "collapsed panel rectangle")
        for prior in bounds:
            if _close(prior[0], xyz[0][2]):
                dx = min(xx[1], prior[2])-max(xx[0], prior[1])
                dy = min(yy[1], prior[4])-max(yy[0], prior[3])
                require(not (dx > 1e-8 and dy > 1e-8),
                        "overlapping physical slab regions: duplicate gravity source")
        bounds.append((xyz[0][2], xx[0], xx[1], yy[0], yy[1]))
        material = panel.get("material_id")
        require(material in mat, "panel concrete material density missing")
        structural = number(panel.get("thickness_m"), "panel thickness") * mat[material]
        finish = number(panel.get("finish_kPa"), "panel.finish_kPa", allow_zero=True)
        imposed = number(panel.get("imposed_kPa"), "panel.imposed_kPa", allow_zero=True)
        f = number(panel.get("live_mass_factor"), "panel.live_mass_factor",
                   allow_zero=True)
        require(f <= 1, "live participation factor must be <=1")
        add_panel(pid, "SLAB-SELFWEIGHT", structural, "DEAD", 1.0,
                  corners, panel["source_id"])
        add_panel(pid, "FINISH", finish, "DEAD", 1.0,
                  corners, panel["source_id"])
        add_panel(pid, "IMPOSED", imposed, "LIVE", f,
                  corners, panel["source_id"])

    def add_line(mid, lid, intensity, prov):
        member = frames[mid]
        a, b = member["i_node"], member["j_node"]
        loads.append({
            "id": lid, "source_key": case_id + "::" + lid,
            "type": "UNIFORM_FRAME_LINE_LOAD", "load_category": "DEAD",
            "case_id": "DL", "member_id": mid, "intensity_kN_m": intensity,
            "participation_factor": 1.0, "node_shares": [
                {"node_id": a, "fraction": 0.5},
                {"node_id": b, "fraction": 0.5}],
            "provenance": prov
        })

    seen_wall_beams = set()
    for wall in payload.get("walls", []):
        wid, mid = wall.get("id"), wall.get("beam_member_id")
        new_id(wid)
        source(wall.get("source_id"), "wall.source_id")
        require(mid in frames and frames[mid]["member_type"] == "BEAM"
                and mid not in seen_wall_beams, "wall must rest on one unique actual beam")
        seen_wall_beams.add(mid)
        a, b = (_xyz(nodes[frames[mid][end]]) for end in ("i_node", "j_node"))
        length = math.dist(a, b)
        height = number(wall.get("height_m"), "wall height")
        thickness = number(wall.get("thickness_m"), "wall thickness")
        opening = number(wall.get("opening_area_m2"),
                         "wall opening area", allow_zero=True)
        require(opening < height*length,
                "wall openings cannot exceed gross wall elevation area")
        material = wall.get("material_id")
        require(material in mat, "wall material unit weight missing")
        total = (height*length - opening)*thickness*mat[material]
        add_line(mid, wid+"::MASONRY", total/length, wall["source_id"])

    for member in model["frame_members"]:
        mid = member["id"]
        section = secs.get(member.get("section_id"))
        require(isinstance(section, dict) and
                section.get("shape") == "Rectangular",
                "source member "+mid+" requires rectangular section")
        width = number(section.get("width"), mid+".width_m")
        depth = number(section.get("depth"), mid+".depth_m")
        material = section.get("material_id")
        require(material in mat, "source member material weight missing")
        provenance = next(r["source_id"] for r in material_rows if r["id"] == material)
        length = math.dist(_xyz(nodes[member["i_node"]]),
                           _xyz(nodes[member["j_node"]]))
        w = width*depth*length*mat[material]
        if member["member_type"] == "BEAM":
            add_line(mid, "SELFWEIGHT-BEAM-"+mid, w/length, provenance)
        else:
            a, b = member["i_node"], member["j_node"]
            nodal_column[a] += w/2
            nodal_column[b] += w/2
            ledger_column.append({
                "member_id": mid, "weight_kN": w, "length_m": length,
                "source_id": provenance, "model": "VERTICAL_COLUMN_HALVED_TO_END_NODES",
                "local_column_axial_force_distribution_exact": False
            })
    require(loads and routes, "no supported physical sources routed")
    try:
        routing = transfer_one_way_panels(
            model=model, loads=loads, routes=routes, gravity_m_s2=g)
    except (PanelRoutingError, GeometryLoadError) as exc:
        raise GeometryGravityHold("HOLD: unsafe slab-to-beam geometry/load source: " +
                                  str(exc)) from exc
    colweight = math.fsum(x["weight_kN"] for x in ledger_column)
    globalweight = routing["source_total_gravity_kN"] + colweight
    require(globalweight > 0, "zero total physical source gravity")
    # Audit plan first-moment conservation for all material+wall+panel loads
    # PLUS exact column self-weight centroid. This does not establish member
    # buckling, shear, concrete strength or complete slab plate behavior.
    original = [0.0, 0.0]
    applied = [0.0, 0.0]
    for panel_route in routing["panel_routes"]:
        for axis in (0, 1):
            original[axis] += panel_route["source_total_kN"]*panel_route[
                "panel_centroid_xyz_m"][axis]
    for row in routing["member_element_load_sources"]:
        for axis in (0,1):
            applied[axis] += row["downward_resultant_kN"]*row[
                "line_centroid_xyz_m"][axis]
        if row["source_panel_id"] is None:
            for axis in (0,1):
                original[axis] += row["downward_resultant_kN"]*row[
                    "line_centroid_xyz_m"][axis]
    for member in ledger_column:
        frame = frames[member["member_id"]]
        a = _xyz(nodes[frame["i_node"]])
        for axis in (0,1):
            original[axis] += member["weight_kN"]*a[axis]
    for nid, w in nodal_column.items():
        for axis in (0,1):
            applied[axis] += w*_xyz(nodes[nid])[axis]
    require(all(math.isclose(original[i], applied[i], rel_tol=1e-10,
                             abs_tol=1e-6) for i in (0,1)),
            "source material loads lost or shifted in global plan moments")
    return {
        "schema": SCHEMA, "case_id": case_id,
        "model_sha256": sha(model), "source_input_sha256": sha(payload),
        "classification": payload["classification"],
        "graph": graph, "source_loads": loads, "routing": routing,
        "column_gravity_node_loads": dict(sorted(nodal_column.items())),
        "column_source_ledger": ledger_column,
        "gravity_by_case_element": routing["native_element_loads_by_case"],
        "gravity_totals": {
            "noncolumn_source_gravity_kN": routing["source_total_gravity_kN"],
            "plumb_column_self_weight_kN": colweight,
            "total_source_gravity_kN": globalweight,
            "seismic_eligible_weight_kN":
                routing["source_seismic_weight_kN"] + colweight,
        },
        "gravity_plan_first_moment_balance_pass": True,
        "source_force_conservation_pass": True,
        "physical_slab_plate_stiffness_modelled": False,
        "seismic_masses_bound_to_dynamic_FE": False,
        "column_axial_force_diagram_selfweight_exact": False,
        "full_code_combinations_generated": False,
        "foundation_design_checked": False,
        "engineering_approval": False,
        "status": "EXPLICIT_GEOMETRY_ONEWAY_GRAVITY_LOADPATH_PARTIAL_ENGINEERING_HOLD",
    }
