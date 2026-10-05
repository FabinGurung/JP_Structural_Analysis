"""First-order linear 2D Euler-Bernoulli frame direct-stiffness solver.

Validated envelope: prismatic frame members, nodal loads, and fixed/free
``ux``, ``uy`` and ``rz`` degrees of freedom. Member loads, releases, shear
deformation, geometric/material nonlinearity, 3D, and dynamics are out of
scope for this module.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import numpy as np

DOF_PER_NODE = 3


def local_stiffness(E: float, A: float, I: float, L: float) -> np.ndarray:
    if min(E, A, I, L) <= 0:
        raise ValueError("E, A, I and L must all be positive")
    ea_l = E * A / L
    ei = E * I
    return np.array(
        [
            [ea_l, 0, 0, -ea_l, 0, 0],
            [0, 12 * ei / L**3, 6 * ei / L**2, 0, -12 * ei / L**3, 6 * ei / L**2],
            [0, 6 * ei / L**2, 4 * ei / L, 0, -6 * ei / L**2, 2 * ei / L],
            [-ea_l, 0, 0, ea_l, 0, 0],
            [0, -12 * ei / L**3, -6 * ei / L**2, 0, 12 * ei / L**3, -6 * ei / L**2],
            [0, 6 * ei / L**2, 2 * ei / L, 0, -6 * ei / L**2, 4 * ei / L],
        ],
        dtype=float,
    )


def transform(c: float, s: float) -> np.ndarray:
    return np.array(
        [
            [c, s, 0, 0, 0, 0],
            [-s, c, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0],
            [0, 0, 0, c, s, 0],
            [0, 0, 0, -s, c, 0],
            [0, 0, 0, 0, 0, 1],
        ],
        dtype=float,
    )


def element_matrices(xi: float, yi: float, xj: float, yj: float, E: float, A: float, I: float):
    dx, dy = xj - xi, yj - yi
    L = math.hypot(dx, dy)
    if L <= 0:
        raise ValueError("zero-length frame member")
    c, s = dx / L, dy / L
    k_local = local_stiffness(E, A, I, L)
    T = transform(c, s)
    k_global = T.T @ k_local @ T
    return L, c, s, k_local, T, k_global


def solve_frame(
    nodes: Mapping[str, Mapping[str, Any]],
    members: Sequence[Mapping[str, Any]],
    nodal_loads: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Assemble and solve a small first-order 2D frame model."""
    node_ids = list(nodes)
    index = {nid: i for i, nid in enumerate(node_ids)}
    ndof = DOF_PER_NODE * len(node_ids)
    K = np.zeros((ndof, ndof), dtype=float)
    F = np.zeros(ndof, dtype=float)
    cache: dict[str, Any] = {}

    for member in members:
        ni, nj = str(member["i"]), str(member["j"])
        xi, yi = float(nodes[ni]["x"]), float(nodes[ni]["y"])
        xj, yj = float(nodes[nj]["x"]), float(nodes[nj]["y"])
        L, c, s, k_local, T, k_global = element_matrices(
            xi,
            yi,
            xj,
            yj,
            float(member["E"]),
            float(member["A"]),
            float(member["I"]),
        )
        dofs = [
            3 * index[ni],
            3 * index[ni] + 1,
            3 * index[ni] + 2,
            3 * index[nj],
            3 * index[nj] + 1,
            3 * index[nj] + 2,
        ]
        K[np.ix_(dofs, dofs)] += k_global
        cache[str(member["id"])] = {
            "L": L,
            "c": c,
            "s": s,
            "k_local": k_local,
            "T": T,
            "k_global": k_global,
            "dofs": dofs,
        }

    for load in nodal_loads:
        base = 3 * index[str(load["node"])]
        F[base : base + 3] += [
            float(load.get("Fx", 0.0)),
            float(load.get("Fy", 0.0)),
            float(load.get("Mz", 0.0)),
        ]

    restrained: list[int] = []
    for nid, node in nodes.items():
        base = 3 * index[nid]
        restraints = node.get("restraints", {})
        for offset, key in enumerate(("ux", "uy", "rz")):
            if bool(restraints.get(key, False)):
                restrained.append(base + offset)
    restrained = sorted(set(restrained))
    free = [i for i in range(ndof) if i not in restrained]
    if not free:
        raise ValueError("model has no free degrees of freedom")

    Kff = K[np.ix_(free, free)]
    Ff = F[free]
    try:
        uf = np.linalg.solve(Kff, Ff)
    except np.linalg.LinAlgError as exc:
        raise ValueError("free stiffness matrix is singular or ill-conditioned") from exc

    U = np.zeros(ndof, dtype=float)
    U[free] = uf
    R = K @ U - F

    element_results: dict[str, Any] = {}
    for member_id, data in cache.items():
        d_global = U[data["dofs"]]
        d_local = data["T"] @ d_global
        f_local = data["k_local"] @ d_local
        element_results[member_id] = {
            "L": data["L"],
            "c": data["c"],
            "s": data["s"],
            "global_d": d_global,
            "local_d": d_local,
            "local_f": f_local,
            "k_local": data["k_local"],
            "T": data["T"],
            "k_global": data["k_global"],
        }

    return {
        "node_ids": node_ids,
        "K": K,
        "F": F,
        "U": U,
        "R": R,
        "free": free,
        "restrained": restrained,
        "elements": element_results,
        "Kff": Kff,
    }
