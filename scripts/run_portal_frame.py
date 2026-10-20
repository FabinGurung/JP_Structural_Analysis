"""Safe public GitHub Pages -> GitHub Issue -> OpenSees scenario runner.

Only synthetic three-floor, single-bay planar frames. Never accepts model
files, paths, code snippets or private building coordinates. A CI fixture
exercises the same runner that GitHub Actions uses for authorized issues.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from jp_structural.solvers.native.nbc105_2025_esm import (
    design_coefficients, equivalent_static_floor_forces,
)

SCHEMA = "jp.structural.portal.frame.v1"
ALLOWED = {
    "schema", "model", "span_m", "storey_height_m", "floor_weights_kN",
    "period_s", "elastic_site_C", "Rmu", "overstrength",
    "beam_width_m", "beam_depth_m", "column_width_m", "column_depth_m",
    "Ec_MPa", "beam_EI_factor", "column_EI_factor",
}
SAMPLE = {
    "schema": SCHEMA, "model": "SYNTHETIC_FRAME_ONLY",
    "span_m": 5.0, "storey_height_m": 3.0,
    "floor_weights_kN": [400.0, 450.0, 350.0],
    "period_s": 0.45, "elastic_site_C": 0.7875,
    "Rmu": 4.0, "overstrength": 1.5,
    "beam_width_m": 0.3, "beam_depth_m": 0.45,
    "column_width_m": 0.4, "column_depth_m": 0.4,
    "Ec_MPa": 22360.68, "beam_EI_factor": 0.35,
    "column_EI_factor": 0.70,
}


def bounded(x, label, lo, hi):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise ValueError(f"{label}: numeric value required")
    value = float(x)
    if not math.isfinite(value) or not lo <= value <= hi:
        raise ValueError(f"{label}: must be finite in [{lo}, {hi}]")
    return value


def validate(request):
    if not isinstance(request, dict) or set(request) != ALLOWED:
        raise ValueError("request must contain only and all approved numeric fields")
    if request["schema"] != SCHEMA or request["model"] != "SYNTHETIC_FRAME_ONLY":
        raise ValueError("unsupported schema or non-synthetic model")
    b = {}
    for k, limits in {
        "span_m": (2, 15), "storey_height_m": (2.4, 4.5),
        "period_s": (0.1, 3), "elastic_site_C": (0.01, 2),
        "Rmu": (1, 6), "overstrength": (1, 2.5),
        "beam_width_m": (.20, .60), "beam_depth_m": (.30, .90),
        "column_width_m": (.25, .90), "column_depth_m": (.25, .90),
        "Ec_MPa": (10000, 50000),
        "beam_EI_factor": (.1, 1),
        "column_EI_factor": (.1, 1),
    }.items():
        b[k] = bounded(request[k], k, *limits)
    weights = request["floor_weights_kN"]
    if not isinstance(weights, list) or len(weights) != 3:
        raise ValueError("exactly three floor seismic weights are required")
    b["floor_weights_kN"] = [bounded(w, f"floor[{i}]", 20, 10000) for i, w in enumerate(weights)]
    b["schema"] = SCHEMA
    b["model"] = "SYNTHETIC_FRAME_ONLY"
    return b


def parse_issue(event_path):
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    issue = event["issue"]
    if issue["user"]["login"] != "FabinGurung":
        raise ValueError("issue author is not the authorized repository owner")
    if not issue["title"].startswith("[JP Frame MVP]"):
        raise ValueError("not an approved portal job")
    text = issue.get("body") or ""
    if len(text) > 4000 or not text.startswith("JP_FRAME_RUN_V1\n"):
        raise ValueError("malformed or oversized issue request")
    raw = text.splitlines()[1]
    if len(raw) > 1400:
        raise ValueError("request length exceeds permitted bound")
    return validate(json.loads(raw))


def run_opensees(request):
    """Linear elastic OpenSees 2D frame, source-labelled independent load cases.

    Analytical idealization: two fixed columns, three beams, one sway plane,
    nodal vertical gravity weights, horizontal ESM forces equally shared
    between both outer frame nodes. No real slab, torsion, biaxial interaction,
    member design acceptance or physical G+1.5 building reconstruction.
    """
    import openseespy.opensees as ops

    d = validate(request)
    heights = [d["storey_height_m"] * i for i in (1, 2, 3)]
    co = design_coefficients(
        elastic_horizontal_C=d["elastic_site_C"],
        ductility_Rmu=d["Rmu"],
        overstrength_ULS=d["overstrength"],
        elastic_SLS_Cs=d["elastic_site_C"] * .2,
        overstrength_SLS=1.25,
    )
    esm = equivalent_static_floor_forces(
        floor_weights_kN=d["floor_weights_kN"],
        floor_heights_m=heights,
        period_seconds=d["period_s"],
        design_coefficient=co["ULS"],
    )
    def section(w, depth, fact):
        area = w * depth
        inertia = w * depth**3 / 12
        # OpenSees model units kN, m, kN/m^2.
        return area, inertia * fact

    col_a, col_EI = section(d["column_width_m"], d["column_depth_m"], d["column_EI_factor"])
    beam_a, beam_EI = section(d["beam_width_m"], d["beam_depth_m"], d["beam_EI_factor"])
    spans = {1: (1, 3), 2: (3, 5), 3: (5, 7)} # node pairs at successive left-column levels
    output_cases = []
    for kind, sign in (("GRAVITY", 0), ("ESM_PLUS_X", 1), ("ESM_MINUS_X", -1)):
        ops.wipe()
        ops.model("basic", "-ndm", 2, "-ndf", 3)
        for floor in range(4):
            z = floor * d["storey_height_m"]
            ops.node(2 * floor + 1, 0., z)
            ops.node(2 * floor + 2, d["span_m"], z)
        ops.fix(1, 1, 1, 1)
        ops.fix(2, 1, 1, 1)
        ops.geomTransf("Linear", 1)
        ops.geomTransf("Linear", 2)
        members = {}
        for floor in range(1, 4):
            members[f"C_L{floor}"] = floor
            members[f"C_R{floor}"] = 10 + floor
            members[f"B_L{floor}"] = 20 + floor
            ops.element("elasticBeamColumn", floor, 2 * floor-1, 2*floor+1,
                        col_a, d["Ec_MPa"] * 1000, col_EI, 1)
            ops.element("elasticBeamColumn", 10+floor, 2*floor, 2*floor+2,
                        col_a, 1., col_EI, 1)
            ops.element("elasticBeamColumn", 20+floor, 2*floor+1, 2*floor+2,
                        beam_a, d["Ec_MPa"] * 1000, beam_EI, 2)
        ops.timeSeries("Linear", 1)
        ops.pattern("Plain", 1, 1)
        for floor in range(1, 4):
            fx = sign * esm["floor_forces_kN"][floor-1] / 2
            fy = (-d["floor_weights_kN"][floor-1] / 2 if kind == "GRAVITY" else 0.)
            ops.load(2*floor+1, fx, fy, 0.)
            ops.load(2*floor+2, fx, fy, 0.)
        ops.system("BandGeneral")
        ops.numberer("RCM")
        ops.constraints("Plain")
        ops.integrator("LoadControl", 1.)
        ops.algorithm("Linear")
        ops.analysis("Static")
        if ops.analyze(1) != 0:
            ops.wipe()
            raise RuntimeError(f"OpenSees failed case {kind}")
        disp = []
        member_forces = []
        for floor in range(1, 4):
            disp.append((ops.nodeDisp(2*floor+1, 1)+ops.nodeDisp(2*floor+2, 1))/2)
        for label, tag in members.items():
            forces = list(ops.eleResponse(tag, "localForce"))
            if len(forces) != 6 or not all(math.isfinite(v) for v in forces):
                raise RuntimeError("invalid local force vector")
            member_forces.append({
                "member": label,
                "signed_local_kN_kNm": [round(float(x), 8) for x in forces],
                "local_order": ["Ni", "Vi", "Mi", "Nj", "Vj", "Mj"],
            })
        ops.reactions()
        reaction_x = sum(ops.nodeReaction(n, 1) for n in (1,2))
        reaction_y = sum(ops.nodeReaction(n, 2) for n in (1,2))
        expected_x = -sign * esm["base_shear_kN"]
        expected_y = sum(d["floor_weights_kN"]) if kind == "GRAVITY" else 0.
        if not math.isclose(reaction_x, expected_x, abs_tol=.0005) or not math.isclose(reaction_y, expected_y, abs_tol=.0005):
            ops.wipe()
            raise RuntimeError(f"global force equilibrium fail: {kind}")
        drifts = [abs(x-y) / d["storey_height_m"] for x,y in zip(disp, [0.,*disp[:-1]])]
        output_cases.append({
            "case": kind, "floor_displacements_m": [round(v, 9) for v in disp],
            "max_elastic_drift_ratio": max(drifts),
            "ULS_design_drift_ratio_Rmu_scaled": max(drifts) * d["Rmu"],
            "ULS_limit_reference": .025,
            "drift_screen_exceeded": kind != "GRAVITY" and max(drifts)*d["Rmu"] > .025,
            "support_reaction_x_kN": reaction_x,
            "support_reaction_y_kN": reaction_y,
            "max_abs_member_end_moment_kNm": max(
                max(abs(q["signed_local_kN_kNm"][j]) for j in (2,5))
                for q in member_forces),
            "signed_end_actions": member_forces,
            "equilibrium_verified": True,
        })
        ops.wipe()
    return {
        "schema": "jp.structural.portal.frame.output.v1",
        "request": d, "esm": esm,
        "cases": output_cases,
        "solver": "OpenSeesPy 2D elasticBeamColumn, independent signed load cases",
        "model_scope": "SYNTHETIC_2D_THREE_STOREY_SINGLE_BAY_FIXED_BASE",
        "diaphragm": "NOT_MODELLED", "accidental_torsion": "NOT_MODELLED",
        "nonlinear": False, "building_approval": False,
        "engineering_approval": False, "report_accepted": False,
        "actual_g15_project_model": False,
        "limitations": [
            "NOT the 165-member G+1.5 source frame",
            "no floor diaphragms, wall-line mapping, eccentric torsion or seismic mass validation",
            "no foundation, P-Delta, RC detailing or member design acceptance",
            "UI parameter sets submitted to public GitHub issues must contain no private client data",
        ]
    }


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sample", action="store_true")
    group.add_argument("--event-file", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    opts = parser.parse_args()
    inp = SAMPLE if opts.sample else parse_issue(opts.event_file)
    result = run_opensees(inp)
    opts.output.parent.mkdir(parents=True, exist_ok=True)
    opts.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+"\n",encoding="utf-8")
    print("PORTAL_OPENSEES_EQUILIBRIUM_PASS_ENGINEERING_HOLD",len(result["cases"]),opts.output)

if __name__ == "__main__":
    main()
