"""R6.23 independent multi-storey conforming shell/frame finite-element engine.

Supported: orthogonal rectilinear floor meshes, source-declared internal
rectangular cell openings, shared shell/beam/column node identities, source
declared gravity/wall/lateral loads and optional horizontal rigid MPC.
ShellMITC4 carries biaxial plate bending and membrane stiffness: NO
one-way/two-way tributary-force prescription is used.  This is a bounded
elastic research implementation, NOT member/foundation design approval.
Units: kN, m, s, kN/m^2 = kPa.
"""
from __future__ import annotations

from collections import defaultdict, deque
from hashlib import sha256
import json
import math
from typing import Any

SCHEMA = "jp.structural.r6p23.rectilinear_multifloor_shell.v0.1"
MODES = ("FLEXIBLE_SHELL", "RIGID_INPLANE_MPC")
BASE_CASES = ("SHELL_DL", "FRAME_DL", "DL", "LL")
ACTION_NAMES = ("N", "Vy", "Vz", "T", "My", "Mz")
NAMES = ("Fx", "Fy", "Fz", "Mx", "My", "Mz")


class StructuralHold(ValueError):
    """Input/physicality gap: do not silently promote it into solver success."""


def require(ok: bool, message: str) -> None:
    if not ok:
        raise StructuralHold("ENGINEERING HOLD: " + message)


def finite(value: Any, field: str, *, positive=False, nonnegative=False) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value), field + ": finite numeric required")
    v = float(value)
    if positive:
        require(v > 0, field + " must be positive")
    if nonnegative:
        require(v >= 0, field + " must be nonnegative")
    return v


def source_id(value: Any, field: str) -> str:
    require(isinstance(value, str) and len(value.strip()) >= 8,
            field + ": traceable source/assumption ID required")
    return value.strip()


def digest(value: Any) -> str:
    return sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")).hexdigest()


def node_id(level: int, i: int, j: int) -> str:
    return f"L{level}:X{i}:Y{j}"


def _grid(values: Any, label: str) -> list[float]:
    require(isinstance(values, list) and 4 <= len(values) <= 24,
            label + ": at least 3 bays, at most 23")
    numbers = [finite(v, label) for v in values]
    require(all(numbers[i + 1] - numbers[i] > 1e-6
                for i in range(len(numbers) - 1)),
            label + " must be strictly ascending with nonzero intervals")
    return numbers


def validate(spec: dict) -> dict:
    require(isinstance(spec, dict) and spec.get("schema") == SCHEMA,
            "R6.23 native source contract required")
    require(spec.get("classification") in (
        "SYNTHETIC_REFERENCE", "PROJECT_SOURCE_DERIVED_UNVERIFIED"
    ), "synthetic or unapproved project source classification required")
    source_id(spec.get("case_id"), "case_id")
    require(spec.get("units") == {"force": "kN", "length": "m",
                                    "moment": "kN.m", "pressure": "kPa"},
            "kN/m/kNm/kPa source units required")
    refs = spec.get("source_refs")
    require(isinstance(refs, dict) and set(refs) == {
        "geometry", "material", "support", "loads", "diaphragm", "code"
    }, "complete geometry/material/support/load/diaphragm/code source refs required")
    for key, value in refs.items():
        source_id(value, key + " reference")
    xs, ys, zs = (_grid(spec.get(k), k)
                  for k in ("x_grid_m", "y_grid_m", "levels_m"))
    require(zs[0] >= 0, "ground level must not be negative")
    material = spec.get("concrete")
    require(isinstance(material, dict), "source-defined elastic concrete required")
    E = finite(material.get("E_kN_m2"), "concrete.E", positive=True)
    nu = finite(material.get("poisson"), "concrete.poisson")
    require(0 <= nu < 0.5, "Poisson ratio out of elastic isotropic range")
    gamma = finite(material.get("unit_weight_kN_m3"), "concrete unit weight",
                   positive=True)
    source_id(material.get("source_id"), "concrete source")
    props = {}
    for name in ("beam", "column"):
        p = spec.get(name)
        require(isinstance(p, dict), name + " section required")
        props[name] = (finite(p.get("width_m"), name + " width", positive=True),
                       finite(p.get("depth_m"), name + " depth", positive=True))
        source_id(p.get("source_id"), name + " section source")
    require(len(zs) - 1 <= 5, "bounded research maximum is five floors")
    floors = spec.get("floors")
    require(isinstance(floors, list) and len(floors) == len(zs) - 1,
            "every upper storey must provide a floor source")
    floor_info = {}
    nxi, nyi = len(xs) - 1, len(ys) - 1
    for n, floor in enumerate(floors, start=1):
        require(isinstance(floor, dict) and floor.get("level_index") == n,
                "unique ordered floor level index required")
        source_id(floor.get("source_id"), "floor geometry/material source")
        thick = finite(floor.get("thickness_m"), "floor thickness", positive=True)
        finish = finite(floor.get("finish_kPa"), "floor finish", nonnegative=True)
        live = finite(floor.get("imposed_kPa"), "floor imposed", nonnegative=True)
        require(thick < zs[n] - zs[n - 1],
                "slab thickness exceeds storey height")
        require(props["beam"][1] > thick,
                "beam downstand must be positive; slab/beam overlap double count")
        raw_voids = floor.get("opening_cells", [])
        require(isinstance(raw_voids, list), "opening cells must be explicit array")
        openings = set()
        for cell in raw_voids:
            require(isinstance(cell, list) and len(cell) == 2
                    and all(isinstance(x, int) and not isinstance(x, bool) for x in cell),
                    "openings must be integer grid cell pairs")
            i, j = cell
            require(1 <= i < nxi - 1 and 1 <= j < nyi - 1,
                    "current opening mesh supports only internal cells, not free perimeter cuts")
            require((i, j) not in openings, "duplicated opening cell")
            openings.add((i, j))
        active = {(i, j) for i in range(nxi) for j in range(nyi)} - openings
        require(active, "floor with no shell panels is unsupported")
        rows = floor.get("interior_beam_y_grid_indices", [])
        cols = floor.get("interior_beam_x_grid_indices", [])
        require(isinstance(rows, list) and isinstance(cols, list)
                and all(isinstance(x, int) and 0 < x < nyi for x in rows)
                and all(isinstance(x, int) and 0 < x < nxi for x in cols)
                and len(rows) == len(set(rows)) and len(cols) == len(set(cols)),
                "interior beam gridlines must be distinct valid internal grid indices")
        floor_info[n] = {
            "thickness_m": thick, "finish_kPa": finish, "imposed_kPa": live,
            "openings": sorted(openings), "cells": sorted(active),
            "interior_rows": rows, "interior_cols": cols,
            "area_m2": math.fsum(
                (xs[i + 1] - xs[i]) * (ys[j + 1] - ys[j])
                for i, j in active
            )
        }
    walls = spec.get("walls", [])
    require(isinstance(walls, list), "wall source list required")
    wall_keys = set()
    for w in walls:
        require(isinstance(w, dict), "wall source object required")
        fl = w.get("level_index")
        edge = w.get("edge")
        require(fl in floor_info and edge in ("X_MIN", "X_MAX", "Y_MIN", "Y_MAX"),
                "wall requires real floor and full outer beam edge")
        require((fl, edge) not in wall_keys,
                "duplicate wall on same floor edge: double count")
        wall_keys.add((fl, edge))
        source_id(w.get("source_id"), "wall source")
        height = finite(w.get("height_m"), "wall height", positive=True)
        require(height <= zs[fl] - zs[fl - 1],
                "wall height exceeds source storey")
        thick = finite(w.get("thickness_m"), "wall thickness", positive=True)
        unit_weight = finite(w.get("unit_weight_kN_m3"), "masonry unit weight",
                             positive=True)
        opening = finite(w.get("opening_area_m2"), "wall opening area",
                         nonnegative=True)
        run = ys[-1] - ys[0] if edge.startswith("X") else xs[-1] - xs[0]
        require(opening < height * run,
                "wall openings exceed gross elevation")
    lateral = spec.get("lateral_cases", [])
    require(isinstance(lateral, list), "lateral cases must be explicit list")
    seen = set(BASE_CASES)
    for row in lateral:
        require(isinstance(row, dict), "lateral record object required")
        name = row.get("case_id")
        require(isinstance(name, str) and len(name) > 1 and name not in seen,
                "duplicate/reserved lateral case")
        seen.add(name)
        source_id(row.get("source_id"), "lateral action source")
        fl, i, j = (row.get(k) for k in ("level_index", "grid_i", "grid_j"))
        require(fl in floor_info and isinstance(i, int) and isinstance(j, int)
                and 0 <= i <= nxi and 0 <= j <= nyi,
                "lateral force target is not a valid real floor grid node")
        require(all(isinstance(row.get(k), (int, float))
                    and not isinstance(row.get(k), bool)
                    and math.isfinite(row[k])
                    for k in ("Fx_kN", "Fy_kN", "Fz_kN", "Mx_kNm", "My_kNm", "Mz_kNm")),
                "lateral force/moment components must be explicitly signed")
    combos = spec.get("combinations", [])
    require(isinstance(combos, list) and combos,
            "source-labelled static combinations required")
    cids = set()
    for combo in combos:
        require(isinstance(combo, dict) and
                isinstance(combo.get("id"), str) and combo["id"] not in cids
                and combo["id"] not in seen,
                "unique combination ID required")
        cids.add(combo["id"])
        source_id(combo.get("source_id"), "combination source")
        factors = combo.get("factors")
        require(isinstance(factors, dict) and factors and
                set(factors) <= ({"DL", "LL"} | {x["case_id"] for x in lateral})
                and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                        and math.isfinite(v) for v in factors.values()),
                "combination references unsupported physical source or factor")
    return {
        "x": xs, "y": ys, "z": zs, "material_E": E, "nu": nu, "gamma": gamma,
        "floors": floor_info, "beam_size": props["beam"],
        "column_size": props["column"], "walls": walls,
        "lateral": lateral, "combinations": combos,
    }


def _edge_key(a: tuple, b: tuple):
    return tuple(sorted((a, b)))


def topology(spec: dict) -> dict:
    """Exact shared-ID shell, beam and column paths; no geometric auto-ties."""
    v = validate(spec)
    nx, ny = len(v["x"]) - 1, len(v["y"]) - 1
    active = {}
    cells = []
    beams = []
    columns = []
    for fl, f in v["floors"].items():
        for i, j in f["cells"]:
            corners = [(fl, i, j), (fl, i + 1, j),
                       (fl, i + 1, j + 1), (fl, i, j + 1)]
            cells.append({"floor": fl, "i": i, "j": j, "corners": corners,
                          "area_m2": (v["x"][i + 1] - v["x"][i]) *
                                     (v["y"][j + 1] - v["y"][j])})
            for key in corners:
                active[key] = True
        edges = set()
        for j in [0, ny, *f["interior_rows"]]:
            for i in range(nx):
                edges.add(_edge_key((fl, i, j), (fl, i + 1, j)))
        for i in [0, nx, *f["interior_cols"]]:
            for j in range(ny):
                edges.add(_edge_key((fl, i, j), (fl, i, j + 1)))
        for a, b in sorted(edges):
            require(a != b, "collapsed frame edge")
            axis = "X" if a[1] != b[1] else "Y"
            beams.append({"key": f"B:{node_id(*a)}:{node_id(*b)}",
                          "a": a, "b": b, "floor": fl, "axis": axis})
            active[a] = active[b] = True
    for fl in range(1, len(v["z"])):
        for i in (0, nx):
            for j in (0, ny):
                a = (fl - 1, i, j)
                b = (fl, i, j)
                columns.append({"key": f"C:{node_id(*a)}:{node_id(*b)}",
                                "a": a, "b": b, "floor": fl})
                active[a] = active[b] = True
    supports = [(0, i, j) for i in (0, nx) for j in (0, ny)]
    graph = defaultdict(set)
    for member in [*beams, *columns]:
        a, b = member["a"], member["b"]
        graph[a].add(b)
        graph[b].add(a)
    for panel in cells:
        corners = panel["corners"]
        for a, b in zip(corners, corners[1:] + corners[:1]):
            graph[a].add(b)
            graph[b].add(a)
    visited = set(supports)
    queue = deque(supports)
    while queue:
        a = queue.popleft()
        for b in graph[a]:
            if b not in visited:
                visited.add(b)
                queue.append(b)
    require(visited == set(active),
            "unconnected shell/frame node cannot reach real column/base support")
    nxy = {fl: [k for k in sorted(active) if k[0] == fl]
           for fl in v["floors"]}
    return {
        "v": v, "active": sorted(active),
        "shell_cells": cells, "beams": beams, "columns": columns,
        "supports": supports, "floor_nodes": nxy,
        "physical_node_count": len(active),
        "shell_count": len(cells), "beam_segment_count": len(beams),
        "column_segment_count": len(columns),
        "floor_areas_m2": {str(fl): f["area_m2"]
                           for fl, f in v["floors"].items()},
        "removed_opening_cells": {str(fl): f["openings"]
                                  for fl, f in v["floors"].items()},
        "all_shell_nodes_connected_to_base": True,
        "coordinate_proximity_ties_used": False,
    }


def _section(width: float, depth: float) -> tuple:
    A = width * depth
    Iy = depth * width ** 3 / 12
    Iz = width * depth ** 3 / 12
    a, b = max(width, depth), min(width, depth)
    ratio = b / a
    J = a * b ** 3 * (1 / 3 - .21 * ratio * (1 - ratio ** 4 / 12))
    return A, J, Iy, Iz


def _point(top: dict, key: tuple) -> tuple:
    fl, i, j = key
    v = top["v"]
    return v["x"][i], v["y"][j], v["z"][fl]


def _accumulate_six(out: list, xyz: tuple, f: tuple) -> None:
    x, y, z = xyz
    fx, fy, fz, mx, my, mz = f
    for k, value in enumerate((
        fx, fy, fz, mx + y * fz - z * fy,
        my + z * fx - x * fz, mz + x * fy - y * fx
    )):
        out[k] += value


def _load_book(top: dict) -> dict:
    v = top["v"]
    gamma = v["gamma"]
    beam_width, beam_depth = v["beam_size"]
    col_width, col_depth = v["column_size"]
    sources = []
    slab_node = {name: defaultdict(float)
                 for name in ("SHELL_DL", "DL", "LL")}
    line = {name: [] for name in ("FRAME_DL", "DL")}
    for panel in top["shell_cells"]:
        fl = panel["floor"]
        area = panel["area_m2"]
        f = v["floors"][fl]
        q_dl = f["thickness_m"] * gamma + f["finish_kPa"]
        q_ll = f["imposed_kPa"]
        for case, q, kind in (("SHELL_DL", q_dl, "SLAB_PLUS_FINISH"),
                              ("LL", q_ll, "IMPOSED")):
            w = area * q
            if w <= 0:
                continue
            for corner in panel["corners"]:
                slab_node[case][corner] += w / 4
                if case == "SHELL_DL":
                    slab_node["DL"][corner] += w / 4
            sources.append({"case": case, "kind": kind, "floor": fl,
                            "source_id": f"FLOOR-{fl}-SHELL-{kind}",
                            "weight_kN": w, "area_m2": area,
                            "cell": [panel["i"], panel["j"]]})
    for frame in top["beams"]:
        fl = frame["floor"]
        beam_length = math.dist(_point(top, frame["a"]), _point(top, frame["b"]))
        w = beam_width * (beam_depth - v["floors"][fl]["thickness_m"]) * gamma
        require(w > 0, "negative/downstand beam selfweight")
        for case in ("FRAME_DL", "DL"):
            line[case].append((frame, w, "BEAM_DOWNSTAND"))
        sources.append({"case": "FRAME_DL", "kind": "BEAM_DOWNSTAND",
                        "floor": fl, "source_id": frame["key"],
                        "weight_kN": w * beam_length})
    for frame in top["columns"]:
        fl = frame["floor"]
        span = v["z"][fl] - v["z"][fl - 1]
        w = col_width * col_depth * gamma
        for case in ("FRAME_DL", "DL"):
            line[case].append((frame, w, "COLUMN_AXIAL"))
        sources.append({"case": "FRAME_DL", "kind": "COLUMN_AXIAL",
                        "floor": fl, "source_id": frame["key"],
                        "weight_kN": w * span})
    for wall in v["walls"]:
        fl, edge = wall["level_index"], wall["edge"]
        target = [
            b for b in top["beams"] if b["floor"] == fl and
            ((edge == "Y_MIN" and all(n[2] == 0 for n in (b["a"], b["b"]))) or
             (edge == "Y_MAX" and all(n[2] == len(v["y"]) - 1
                                       for n in (b["a"], b["b"]))) or
             (edge == "X_MIN" and all(n[1] == 0 for n in (b["a"], b["b"]))) or
             (edge == "X_MAX" and all(n[1] == len(v["x"]) - 1
                                       for n in (b["a"], b["b"]))))
        ]
        length = (v["y"][-1] - v["y"][0] if edge.startswith("X")
                  else v["x"][-1] - v["x"][0])
        require(target and math.isclose(
            sum(math.dist(_point(top, b["a"]), _point(top, b["b"]))
                for b in target), length, abs_tol=1e-8),
            "wall line has no complete real beam support")
        total = ((wall["height_m"] * length - wall["opening_area_m2"]) *
                 wall["thickness_m"] * wall["unit_weight_kN_m3"])
        for frame in target:
            for case in ("FRAME_DL", "DL"):
                line[case].append((frame, total / length, "WALL"))
        sources.append({"case": "FRAME_DL", "kind": "WALL", "floor": fl,
                        "source_id": wall["source_id"], "weight_kN": total})
    frame_weight = math.fsum(x["weight_kN"] for x in sources
                             if x["case"] == "FRAME_DL")
    shell_weight = math.fsum(x["weight_kN"] for x in sources
                             if x["case"] == "SHELL_DL")
    imposed = math.fsum(x["weight_kN"] for x in sources
                        if x["case"] == "LL")
    require(math.isclose(
        sum(slab_node["SHELL_DL"].values()), shell_weight, abs_tol=1e-7),
        "surface load not conserved at shell grid nodes")
    require(math.isclose(
        sum(slab_node["LL"].values()), imposed, abs_tol=1e-7),
        "imposed load not conserved")
    return {
        "slab_nodes": slab_node, "frame_lines": line,
        "source_components": sources,
        "expected_case_gravity_kN": {
            "SHELL_DL": shell_weight, "FRAME_DL": frame_weight,
            "DL": shell_weight + frame_weight, "LL": imposed
        },
    }


def solve_case(spec: dict, case: str, mode: str = "FLEXIBLE_SHELL",
               *, prepared: dict | None = None) -> dict:
    """Run an actual OpenSeesPy model for ONE input case; six-axis free-body."""
    import openseespy.opensees as ops
    require(mode in MODES, "unsupported diaphragm mode")
    top = prepared if prepared is not None else topology(spec)
    v = top["v"]
    book = _load_book(top)
    lateral = {x["case_id"]: x for x in v["lateral"]}
    require(case in (*BASE_CASES, *lateral), "unknown independent load case")
    ops.wipe()
    ops.model("basic", "-ndm", 3, "-ndf", 6)
    tags = {key: i + 1 for i, key in enumerate(top["active"])}
    for key, tag in tags.items():
        ops.node(tag, *_point(top, key))
    for key in top["supports"]:
        ops.fix(tags[key], 1, 1, 1, 1, 1, 1)
    master_tags = {}
    if mode == "RIGID_INPLANE_MPC":
        for fl, nodes in top["floor_nodes"].items():
            master = max(tags.values()) + 100 + fl
            center = ((v["x"][0] + v["x"][-1]) / 2,
                      (v["y"][0] + v["y"][-1]) / 2, v["z"][fl])
            ops.node(master, *center)
            ops.fix(master, 0, 0, 1, 1, 1, 0)
            ops.rigidDiaphragm(3, master, *[tags[k] for k in nodes])
            master_tags[fl] = (master, center)
    E, nu = v["material_E"], v["nu"]
    G = E / (2 * (1 + nu))
    ops.geomTransf("Linear", 1, 1, 0, 0)  # vertical columns
    ops.geomTransf("Linear", 2, 0, 0, 1)  # horizontal beams, local +z global +Z
    tags_frame = {}
    tags_shell = {}
    element_tag = 1
    for frame in [*top["columns"], *top["beams"]]:
        column = frame["key"].startswith("C:")
        w, d = v["column_size"] if column else v["beam_size"]
        A, J, Iy, Iz = _section(w, d)
        ops.element("elasticBeamColumn", element_tag, tags[frame["a"]],
                    tags[frame["b"]], A, E, G, J, Iy, Iz, 1 if column else 2)
        tags_frame[frame["key"]] = element_tag
        element_tag += 1
    ops.nDMaterial("ElasticIsotropic", 100, E, nu)
    for fl, info in v["floors"].items():
        ops.section("PlateFiber", 200 + fl, 100, info["thickness_m"])
    for panel in top["shell_cells"]:
        ops.element("ShellMITC4", element_tag,
                    *[tags[x] for x in panel["corners"]], 200 + panel["floor"])
        tags_shell[(panel["floor"], panel["i"], panel["j"])] = element_tag
        element_tag += 1
    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)
    applied = [0.] * 6
    for key, w in book["slab_nodes"].get(case, {}).items():
        if w > 0:
            ops.load(tags[key], 0., 0., -w, 0., 0., 0.)
            _accumulate_six(applied, _point(top, key), (0, 0, -w, 0, 0, 0))
    for frame, w, kind in book["frame_lines"].get(case, []):
        # Column local x points upward; axial Wx=-w is global -Z.
        # Horizontal beam local z points upward; Wz=-w is global -Z.
        if kind == "COLUMN_AXIAL":
            ops.eleLoad("-ele", tags_frame[frame["key"]], "-type",
                        "-beamUniform", 0.0, 0.0, -w)
        else:
            ops.eleLoad("-ele", tags_frame[frame["key"]], "-type",
                        "-beamUniform", 0.0, -w, 0.0)
        a, b = _point(top, frame["a"]), _point(top, frame["b"])
        L = math.dist(a, b)
        mid = tuple((a[i] + b[i]) / 2 for i in range(3))
        _accumulate_six(applied, mid, (0, 0, -w * L, 0, 0, 0))
    if case in lateral:
        row = lateral[case]
        key = (row["level_index"], row["grid_i"], row["grid_j"])
        require(key in tags, "lateral action points to opening/nonexistent node")
        f = tuple(row[k] for k in (
            "Fx_kN", "Fy_kN", "Fz_kN", "Mx_kNm", "My_kNm", "Mz_kNm"))
        ops.load(tags[key], *f)
        _accumulate_six(applied, _point(top, key), f)
    ops.constraints("Transformation")
    ops.numberer("RCM")
    ops.system("BandGeneral")
    ops.algorithm("Linear")
    ops.integrator("LoadControl", 1.)
    ops.analysis("Static")
    result = ops.analyze(1)
    require(result == 0, "OpenSees static FE analysis failed: " + str(result))
    ops.reactions()
    reactions = {}
    summed = list(applied)
    for key in top["supports"]:
        rec = [float(ops.nodeReaction(tags[key], j)) for j in range(1, 7)]
        require(all(math.isfinite(x) for x in rec), "nonfinite support reaction")
        reactions[node_id(*key)] = dict(zip(NAMES, rec))
        _accumulate_six(summed, _point(top, key), tuple(rec))
    residual = max(abs(x) for x in summed)
    scale = max(1., math.fsum(abs(x) for x in applied))
    require(residual <= 1e-6 * scale,
            "six-component global equilibrium failed: " + str(summed))
    frame_end = {}
    direction_abs_vz = {"X": 0., "Y": 0.}
    for frame in [*top["beams"], *top["columns"]]:
        values = ops.eleResponse(tags_frame[frame["key"]], "localForce")
        require(values is not None and len(values) == 12 and
                all(math.isfinite(float(x)) for x in values),
                "signed frame end actions missing")
        frame_end[frame["key"]] = {
            "I": dict(zip(ACTION_NAMES, map(float, values[:6]))),
            "J": dict(zip(ACTION_NAMES, map(float, values[6:])))
        }
        if "axis" in frame:
            direction_abs_vz[frame["axis"]] += (
                abs(float(values[2])) + abs(float(values[8]))
            )
    displacements = {}
    for fl, nodes in top["floor_nodes"].items():
        values = {node_id(*key): [float(ops.nodeDisp(tags[key], j))
                                  for j in range(1, 7)] for key in nodes}
        require(all(math.isfinite(x) for vec in values.values() for x in vec),
                "nonfinite node displacement")
        displacements[str(fl)] = values
    rigid_residual = None
    if mode == "RIGID_INPLANE_MPC":
        residuals = []
        for fl, nodes in top["floor_nodes"].items():
            master, point = master_tags[fl]
            ux, uy, rz = (float(ops.nodeDisp(master, d))
                          for d in (1, 2, 6))
            for key in nodes:
                x, y, _ = _point(top, key)
                vec = displacements[str(fl)][node_id(*key)]
                residuals.extend((abs(vec[0] - (ux - (y - point[1]) * rz)),
                                  abs(vec[1] - (uy + (x - point[0]) * rz)),
                                  abs(vec[5] - rz)))
        rigid_residual = max(residuals or [0.])
        require(rigid_residual < 1e-7,
                "actual rigid diaphragm in-plane kinematics violated")
    totals = {
        "Fz_kN": -float(applied[2]),
        "Fx_kN": float(applied[0]), "Fy_kN": float(applied[1])
    }
    if case in book["expected_case_gravity_kN"]:
        require(math.isclose(
            totals["Fz_kN"], book["expected_case_gravity_kN"][case],
            rel_tol=1e-9, abs_tol=1e-7),
            "actual OpenSees load != source material load ledger")
    return {
        "mode": mode, "case_id": case,
        "source_sha256": digest(spec),
        "opensees_element_type": "ShellMITC4 + elasticBeamColumn",
        "applied_load_resultant": dict(zip(NAMES, applied)),
        "support_reactions": reactions,
        "global_six_axis_residual": dict(zip(NAMES, summed)),
        "max_equilibrium_residual": residual,
        "force_moment_balance_pass": True,
        "signed_frame_end_actions": frame_end,
        "shell_to_beam_directional_vz_abs_sum": direction_abs_vz,
        "floor_max_vertical_displacement_m": {
            str(fl): max(abs(vec[2]) for vec in values.values())
            for fl, values in (
                (fl, displacements[str(fl)]) for fl in top["floor_nodes"]
            )
        },
        "node_displacements": displacements,
        "rigid_inplane_MPC_residual_m": rigid_residual,
        "counts": {
            "analysis_nodes": len(tags),
            "shell_elements": len(tags_shell),
            "beam_segments": len(top["beams"]),
            "column_segments": len(top["columns"]),
            "base_supports": len(top["supports"])
        },
        "gravity_resultants": totals,
        "engineering_approval": False,
    }


def build(spec: dict, *, modes: tuple[str, ...] = MODES) -> dict:
    require(modes and set(modes) <= set(MODES),
            "supported diaphragm branches required")
    top = topology(spec)
    book = _load_book(top)
    cases = (*BASE_CASES, *(x["case_id"] for x in top["v"]["lateral"]))
    results = {mode: {
        case: solve_case(spec, case, mode, prepared=top)
        for case in cases
    } for mode in modes}
    combinations = {}
    for mode in modes:
        combinations[mode] = {}
        raw = results[mode]
        for combo in top["v"]["combinations"]:
            factors = combo["factors"]
            end_actions = {}
            for member in raw["DL"]["signed_frame_end_actions"]:
                end_actions[member] = {
                    end: {
                        comp: math.fsum(
                            factor * raw[cid]["signed_frame_end_actions"][member][end][comp]
                            for cid, factor in factors.items()
                        ) for comp in ACTION_NAMES
                    } for end in ("I", "J")
                }
            support = {
                key: {comp: math.fsum(
                    factor * raw[cid]["support_reactions"][key][comp]
                    for cid, factor in factors.items()
                ) for comp in NAMES}
                for key in raw["DL"]["support_reactions"]
            }
            combinations[mode][combo["id"]] = {
                "source_id": combo["source_id"], "factors": factors,
                "signed_member_end_actions": end_actions,
                "signed_support_reactions": support,
                "linear_superposition_only": True,
                "NBC_code_completeness_verified": False
            }
        # Separate shell and frame source-load cases must reconstruct DL
        # and preserve concurrently signed member actions.
        for member in raw["DL"]["signed_frame_end_actions"]:
            for end in ("I", "J"):
                for comp in ACTION_NAMES:
                    expected = (raw["SHELL_DL"]["signed_frame_end_actions"][member][end][comp]
                                + raw["FRAME_DL"]["signed_frame_end_actions"][member][end][comp])
                    actual = raw["DL"]["signed_frame_end_actions"][member][end][comp]
                    require(math.isclose(actual, expected, rel_tol=2e-7,
                                         abs_tol=2e-4),
                            "shell/frame DL signed FE superposition violated")
        if "SHELL_DL" in raw:
            require(all(raw["SHELL_DL"]["shell_to_beam_directional_vz_abs_sum"][axis] > 1e-9
                        for axis in ("X", "Y")),
                    "two-way ShellMITC4 plate loads not reaching beams in X and Y")
    safe_top = {k: v for k, v in top.items() if k != "v"}
    return {
        "schema": "jp.structural.r6p23.independent_multifloor_results.v0.1",
        "case_id": spec["case_id"], "classification": spec["classification"],
        "source_SHA256": digest(spec),
        "input_source_refs": spec["source_refs"],
        "topology": safe_top,
        "source_ledger": {
            "components": book["source_components"],
            "gravity_totals_kN": book["expected_case_gravity_kN"]
        },
        "modes": list(modes), "cases": list(cases),
        "solutions": results, "signed_combinations": combinations,
        "two_way_shell_plate_behavior": "REAL_ELASTIC_SHELLMITC4_NO_TRIBUTARY_SPLIT",
        "opening_mesh_cells_physically_excluded": True,
        "exact_conforming_shell_beam_column_grid_nodes": True,
        "gravity_code_load_factors_auto_approved": False,
        "site_specific_seismic_modal_design_complete": False,
        "in_plane_diaphagm_choice_source_required": True,
        "soil_foundation_member_capacity_design_complete": False,
        "historical_F3_unsafe_status_retained": True,
        "construction_release_authorised": False,
        "engineering_approval": False,
        "status": "BOUNDED_MULTISTOREY_SHELL_FRAME_FE_NUMERICAL_HOLD",
    }
