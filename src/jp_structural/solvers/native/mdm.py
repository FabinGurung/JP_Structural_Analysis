"""Transparent limited-scope moment-distribution engine.

The function here is deliberately explicit: callers supply end moments,
distribution factors, joint membership, balancing order, cycle count, and
carry-over exceptions. This makes the arithmetic auditable and avoids hiding
benchmark-specific assumptions inside a general-purpose API.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence


def _far_end(end: str) -> str:
    if len(end) != 2:
        raise ValueError(f"member-end label must contain two node labels, got {end!r}")
    return end[1] + end[0]


def solve_moment_distribution(
    *,
    initial_end_moments: Mapping[str, float],
    joint_ends: Mapping[str, Sequence[str]],
    distribution_factors: Mapping[str, float],
    joint_order: Sequence[str],
    cycles: int,
    carryover_factor: float = 0.5,
    zero_carryover_from: Sequence[str] = (),
    pre_adjustments: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Run sequential moment distribution using explicitly supplied factors.

    Parameters
    ----------
    initial_end_moments:
        Mapping such as ``{"AB": 1.333, "BA": -1.333, ...}``.
    joint_ends:
        Active member-end labels grouped by balancing joint.
    distribution_factors:
        Member-end distribution factors keyed by end label.
    joint_order:
        Sequential balancing order for each cycle.
    cycles:
        Number of distribution cycles.
    carryover_factor:
        Default carry-over factor to the far end.
    zero_carryover_from:
        Near ends whose far ends are released/unlocked.
    pre_adjustments:
        Explicit pre-balancing operations. Each item must contain ``end`` and
        ``delta``; optionally ``far_end`` and ``far_delta``.
    """
    if cycles < 1:
        raise ValueError("cycles must be >= 1")

    moments = {str(k): float(v) for k, v in deepcopy(dict(initial_end_moments)).items()}
    zeros = set(zero_carryover_from)
    trace: list[dict[str, Any]] = []

    for op in pre_adjustments:
        end = str(op["end"])
        delta = float(op["delta"])
        moments[end] = moments.get(end, 0.0) + delta
        record: dict[str, Any] = {"operation": "pre_adjustment", "end": end, "delta": delta}
        if "far_end" in op:
            far_end = str(op["far_end"])
            far_delta = float(op.get("far_delta", 0.0))
            moments[far_end] = moments.get(far_end, 0.0) + far_delta
            record.update({"far_end": far_end, "far_delta": far_delta})
        trace.append(record)

    for cycle in range(1, cycles + 1):
        for joint in joint_order:
            ends = list(joint_ends[joint])
            unbalanced = sum(moments.get(end, 0.0) for end in ends)
            balancing = -unbalanced
            increments: dict[str, float] = {}
            carryovers: dict[str, float] = {}

            for end in ends:
                df = float(distribution_factors.get(end, 0.0))
                inc = balancing * df
                moments[end] = moments.get(end, 0.0) + inc
                increments[end] = inc

                far = _far_end(end)
                factor = 0.0 if end in zeros else float(carryover_factor)
                co = factor * inc
                moments[far] = moments.get(far, 0.0) + co
                carryovers[f"{end}->{far}"] = co

            trace.append(
                {
                    "cycle": cycle,
                    "joint": joint,
                    "unbalanced": unbalanced,
                    "balancing": balancing,
                    "increments": increments,
                    "carryovers": carryovers,
                }
            )

    residuals = {
        joint: sum(moments.get(end, 0.0) for end in ends)
        for joint, ends in joint_ends.items()
    }
    return {"end_moments": moments, "joint_residuals": residuals, "trace": trace}
