"""Narrow hand-equivalent-frame-method reproduction helpers.

These functions reproduce the governed FLOOR-01 hand-calculation operations.
They are not a shell finite-element solver and do not reproduce spSlab.
"""
from __future__ import annotations

from typing import Sequence

PAIR = {0: 1, 1: 0, 2: 3, 3: 2, 4: 5, 5: 4}
JOINTS = [[0], [1, 2], [3, 4], [5]]
DFS = [[0.395], [0.306, 0.306], [0.306, 0.306], [0.395]]
COL_DF = [1 - sum(group) for group in DFS]
COF = 0.507


def moment_distribution(fem: Sequence[float], distribution_stages: int = 5) -> dict:
    if len(fem) != 6:
        raise ValueError("FLOOR-01 reproduction requires six member-end FEM values")
    if distribution_stages < 1:
        raise ValueError("distribution_stages must be >= 1")
    moments = list(map(float, fem))
    column_branch = [0.0] * 4
    trace = []
    for stage in range(1, distribution_stages + 1):
        dist = [0.0] * 6
        col_dist = [0.0] * 4
        for joint, (indices, dfs) in enumerate(zip(JOINTS, DFS)):
            unbalanced = column_branch[joint] + sum(moments[i] for i in indices)
            for i, df in zip(indices, dfs):
                dist[i] = -unbalanced * df
            col_dist[joint] = -unbalanced * COL_DF[joint]
        moments = [a + b for a, b in zip(moments, dist)]
        column_branch = [a + b for a, b in zip(column_branch, col_dist)]
        record = {"stage": stage, "distribution": dist, "equivalent_column_distribution": col_dist}
        if stage < distribution_stages:
            carryover = [0.0] * 6
            for i, value in enumerate(dist):
                carryover[PAIR[i]] += value * COF
            moments = [a + b for a, b in zip(moments, carryover)]
            record["carryover"] = carryover
        trace.append(record)
    return {"member_end_moments": moments, "equivalent_column_joint_moments": column_branch, "trace": trace}


def span_positive_and_reactions(w_klf: float, L_ft: float, ML_neg: float, MR_neg: float) -> dict[str, float]:
    if w_klf <= 0 or L_ft <= 0:
        raise ValueError("w_klf and L_ft must be positive")
    m_plus = w_klf * L_ft**2 / 8 - (ML_neg + MR_neg) / 2 + (ML_neg - MR_neg) ** 2 / (2 * w_klf * L_ft**2)
    x = L_ft / 2 + (ML_neg - MR_neg) / (w_klf * L_ft)
    v_left = w_klf * L_ft / 2 + (ML_neg - MR_neg) / L_ft
    v_right = w_klf * L_ft / 2 - (ML_neg - MR_neg) / L_ft
    return {"Mplus_ft_kip": m_plus, "x_ft_from_left": x, "VL_kip": v_left, "VR_kip": v_right}


def support_face_negative(centerline_neg: float, reaction_kip: float, w_klf: float, face_offset_ft: float = 0.75) -> float:
    return centerline_neg - reaction_kip * face_offset_ft + w_klf * face_offset_ft**2 / 2


def lateral_distribution(factored_moment: float, column_strip_percent: float, beam_share_fraction: float = 0.85) -> dict[str, float]:
    column = factored_moment * column_strip_percent / 100.0
    beam = column * beam_share_fraction
    return {
        "column_strip_moment_ft_kip": column,
        "beam_strip_moment_ft_kip": beam,
        "column_strip_remainder_ft_kip": column - beam,
        "two_half_middle_strips_moment_ft_kip": factored_moment - column,
    }
