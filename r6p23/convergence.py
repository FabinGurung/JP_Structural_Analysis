"""R6.24 mesh-sensitivity and verified source-preflight for independent ShellMITC4.

Preserves identical physical floor area, void footprint, slab thickness and
material/line source geometry under exact orthogonal refinement. A single
4x4 -> 8x8 screen is *not* mathematical mesh-convergence certification.
The real building must be independently sourced and reviewed.
"""
from __future__ import annotations

from copy import deepcopy
from math import isclose, fabs, fsum
from typing import Any

from r6p23.engine import (
    StructuralHold, _load_book, digest, solve_case, topology, validate
)

SCHEMA = "jp.structural.r6p24.independent_shell_mesh_screen.v0.1"


def require(ok, message):
    if not ok:
        raise StructuralHold("MESH CONVERGENCE HOLD: " + message)


def refine(spec: dict, factor: int = 2) -> dict:
    """Refine the source grid without changing physical model quantities.

    Original grid joints, corners, supports and lateral load locations are
    preserved under exact integer index remapping. All opening source cells
    split into factor**2 *actually omitted* shell cells.
    """
    validate(spec)
    require(isinstance(factor, int) and not isinstance(factor, bool)
            and factor == 2, "only independently tested 2x refinement supported")
    refined = deepcopy(spec)
    for axis in ("x_grid_m", "y_grid_m"):
        v = spec[axis]
        new = []
        for a, b in zip(v[:-1], v[1:]):
            new.extend(a + (b-a)*j/factor for j in range(factor))
        new.append(v[-1])
        require(len(new) <= 24, axis + " exceeds current solver mesh budget")
        refined[axis] = new
    for coarse, fine in zip(spec["floors"], refined["floors"]):
        voids = []
        for i, j in coarse.get("opening_cells", []):
            for di in range(factor):
                for dj in range(factor):
                    voids.append([factor*i + di, factor*j + dj])
        fine["opening_cells"] = voids
        fine["interior_beam_y_grid_indices"] = [
            factor * j for j in coarse.get("interior_beam_y_grid_indices", [])
        ]
        fine["interior_beam_x_grid_indices"] = [
            factor * i for i in coarse.get("interior_beam_x_grid_indices", [])
        ]
    for row in refined.get("lateral_cases", []):
        row["grid_i"] *= factor
        row["grid_j"] *= factor
    refined["source_refs"]["geometry"] = (
        spec["source_refs"]["geometry"] + "_NUMERIC_REFINEMENT_2X"
    )
    validate(refined)
    return refined


def _mapped_node(nid: str, factor: int) -> str:
    # Only compare identical physical original nodes preserved on the grid.
    import re
    match = re.fullmatch(r"L(\d+):X(\d+):Y(\d+)", nid)
    require(match is not None, "invalid canonical frame/shell point identity")
    fl, i, j = (int(x) for x in match.groups())
    return f"L{fl}:X{factor*i}:Y{factor*j}"


def preflight(real_project_spec: dict | None = None) -> dict:
    """Describe actual project input requirements; no ETABS parity gate."""
    required = (
        "Approved source drawing plan and floor dimensions",
        "Structural walls, column layout and footing/support boundary conditions",
        "Actual storey heights and slab opening/perimeter detailing",
        "Verified loads, wall locations, occupancies and materials",
        "Project soil report, allowable bearing and site hazard/code parameters",
        "Complete applicable beam-column-slab-stair-footing design source details",
    )
    out = {
        "schema": "jp.structural.r6p24.real_project_source_preflight.v0.1",
        "etabs_native_mesh_or_calculation_required": False,
        "physical_source_requirements": list(required),
        "source_evidence_accepted": False,
        "real_building_structure_verified": False,
        "historical_F3_one_way_shear_unsafe_retained": True,
        "engineering_approval": False,
        "status": "PRIVATE_DRAWING_GROUNDED_GEOMETRY_REQUIRED",
    }
    if real_project_spec is not None:
        checked = validate(real_project_spec)
        out["input_source_sha256"] = digest(real_project_spec)
        out["declared_floor_count"] = len(checked["floors"])
        out["input_classification"] = real_project_spec["classification"]
        out["source_evidence_accepted"] = False
        out["status"] = (
            "MODEL_PARSED_BUT_UNVERIFIED_PHYSICAL_SOURCE"
            if real_project_spec["classification"] == "PROJECT_SOURCE_DERIVED_UNVERIFIED"
            else "SYNTHETIC_NOT_REAL_PROJECT"
        )
    return out


def _same_total(a: float, b: float, key: str) -> None:
    require(isclose(a, b, rel_tol=2e-12, abs_tol=1e-7),
            "physical load/material source mutated on mesh refinement: " + key)


def screen(spec: dict, baseline: dict | None = None) -> dict:
    """Check one coarse/refined pair, same physical sources, two diaphragm branches.

    Workloads are intentionally limited to DL (gravity/plate vertical) and HX
    (lateral/diaphragm if source given); every signed force/moment component
    equilibrates independently. This is a bounded numerical QA screen, not
    proof that any mesh-independent structural design is attained.
    """
    coarse = topology(spec)
    fine_spec = refine(spec)
    finer = topology(fine_spec)
    book0 = _load_book(coarse)
    book1 = _load_book(finer)
    _same_total(coarse["v"]["gamma"], finer["v"]["gamma"], "concrete weight")
    for fl, area in coarse["floor_areas_m2"].items():
        _same_total(area, finer["floor_areas_m2"][fl], "floor area " + fl)
    for k in ("SHELL_DL", "FRAME_DL", "DL", "LL"):
        _same_total(book0["expected_case_gravity_kN"][k],
                    book1["expected_case_gravity_kN"][k], "case " + k)
    require(coarse["shell_count"]*4 == finer["shell_count"],
            "geometry/openings not represented by 4x actual shell cell refinement")
    require(set(coarse["v"]["floors"]) == set(finer["v"]["floors"]),
            "storey identity changed")
    require(coarse["column_segment_count"] == finer["column_segment_count"],
            "actual columns changed")
    base = baseline
    if base is not None:
        require(base.get("source_SHA256") == digest(spec) and
                base.get("engineering_approval") is False,
                "supplied baseline is not the same original physical input")
    modes = ("FLEXIBLE_SHELL", "RIGID_INPLANE_MPC")
    selected_cases = ("DL", "HX")
    lateral_ids = {row["case_id"] for row in spec["lateral_cases"]}
    selected_cases = tuple(case for case in selected_cases
                           if case == "DL" or case in lateral_ids)
    comparisons = []
    all_balance = True
    for mode in modes:
        for case in selected_cases:
            coarse_run = (
                base["solutions"][mode][case]
                if base is not None else
                solve_case(spec, case, mode, prepared=coarse)
            )
            fine_run = solve_case(fine_spec, case, mode, prepared=finer)
            require(coarse_run["force_moment_balance_pass"] and
                    fine_run["force_moment_balance_pass"],
                    "independent six-axis FE source/reaction equilibrium failed")
            loaded = max(
                1.0,
                max(abs(v) for v in fine_run["applied_load_resultant"].values())
            )
            require(max(coarse_run["max_equilibrium_residual"],
                        fine_run["max_equilibrium_residual"]) < 1e-6 * loaded,
                    "mesh refinements failed numerical equilibrium")
            dof = 2 if case == "DL" else 0
            response = "Uz" if case == "DL" else "Ux"
            diffs = []
            sampled = 0
            for floor, nodes in coarse_run["node_displacements"].items():
                match_nodes = fine_run["node_displacements"].get(floor, {})
                # Compare at the SAME physical original grid points.
                for original_name, disp in nodes.items():
                    same = _mapped_node(original_name, 2)
                    require(same in match_nodes, "original physical FE node lost in refinement")
                    a, b = disp[dof], match_nodes[same][dof]
                    if fabs(a) + fabs(b) > 1e-11:
                        diffs.append((original_name, float(a), float(b), abs(a-b)))
                    sampled += 1
            peak = max((max(abs(a), abs(b)) for _,a,b,_ in diffs), default=0.0)
            # Report only displacement differences on original nodes that
            # genuinely respond; avoid near-zero division artifacts.
            dominant = [d for d in diffs if max(abs(d[1]), abs(d[2])) >= .10*peak]
            max_delta = max((d[3] for d in dominant), default=0.0)
            ratio = max_delta / peak if peak > 1e-10 else 0.0
            reactions = []
            for k, data in coarse_run["support_reactions"].items():
                same = _mapped_node(k, 2)
                require(same in fine_run["support_reactions"],
                        "physical footing source identity changed on refinement")
                fv0 = data["Fz"]
                fv1 = fine_run["support_reactions"][same]["Fz"]
                reactions.append({"base": k,
                                  "coarse_Fz_kN": fv0,
                                  "refined_Fz_kN": fv1,
                                  "delta_Fz_kN": fv1-fv0})
            sumload = max(1.0, fabs(fine_run["applied_load_resultant"]["Fz"]))
            reaction_screen = (
                max(abs(r["delta_Fz_kN"]) for r in reactions) / sumload
            )
            comparisons.append({
                "mode": mode, "case": case,
                "displacement_component": response,
                "matched_original_nodes": sampled,
                "max_response_difference_m": max_delta,
                "max_response_difference_over_response_peak": ratio,
                "max_base_Fz_difference_over_total_vertical_action": reaction_screen,
                "base_reaction_differences": reactions,
                "relative_displacement_five_percent_screen_passed":
                    bool(ratio <= .05),
                "base_reaction_five_percent_screen_passed":
                    bool(reaction_screen <= .05),
                "coarse_max_six_axis_equilibrium_residual":
                    coarse_run["max_equilibrium_residual"],
                "refined_max_six_axis_equilibrium_residual":
                    fine_run["max_equilibrium_residual"],
                "full_asymptotic_mesh_convergence_proven": False,
            })
    return {
        "schema": SCHEMA, "input_source_sha256": digest(spec),
        "refined_source_sha256": digest(fine_spec),
        "classification": spec["classification"],
        "coarse_mesh_shells": coarse["shell_count"],
        "refined_mesh_shells": finer["shell_count"],
        "coarse_beam_segments": coarse["beam_segment_count"],
        "refined_beam_segments": finer["beam_segment_count"],
        "column_segments_unchanged": coarse["column_segment_count"],
        "floor_area_preserved": True,
        "all_source_gravity_totals_preserved": True,
        "gravity_totals_kN": book0["expected_case_gravity_kN"],
        "opening_regions_preserved": True,
        "independent_FE_6axis_equilibrium": all_balance,
        "comparisons": comparisons,
        "selected_mesh_pairs": 1,
        "full_asymptotic_mesh_convergence_proven": False,
        "R6P23_source_solver_accepted_for_complete_building": False,
        "historical_F3_one_way_shear_unsafe_retained": True,
        "professional_engineering_approval": False,
        "engineering_approval": False,
        "status": "ONE_STEP_NUMERICAL_REFINEMENT_SCREEN_ONLY_NO_BUILDING_DESIGN_APPROVAL",
    }
