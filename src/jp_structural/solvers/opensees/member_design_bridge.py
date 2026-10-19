"""Phase D2: signed OpenSees elastic member-end action and RC-check bridge.

Source cases are explicit concurrent nodal actions. An algebraic combination is
formed BEFORE absolute-value end demand/enveloping. Read OpenSees 'localForce'
(i-end and j-end *resisting* actions), not global eleForce or unsigned SRSS.
Elastic frame only; no equivalent nonlinear/plastic design, seismic MRSM sign
reconstruction, source-model parity, detailing or engineering approval.
"""
from __future__ import annotations
import hashlib
import json
import math
from collections.abc import Mapping, Sequence

import openseespy.opensees as ops

from jp_structural.solvers.opensees.canonical_frame import (
    build_canonical_frame_model, _model_digest,
)
from jp_structural.solvers.native.rc_report_kernels import (
    nbc_capacity_design_beam_shear, nbc_joint_shear,
)
from jp_structural.solvers.native.rc_column_section import (
    biaxial_interaction_from_bars,
)

_COMPONENTS = ("N", "Vy", "Vz", "T", "My", "Mz")
_LOAD_COMPONENTS = ("Fx_kN", "Fy_kN", "Fz_kN", "Mx_kNm", "My_kNm", "Mz_kNm")
_MEMBER_TYPE = ("BEAM", "COLUMN")
_SCHEMA = "jp.structural.signed_design_actions.v0.1"


class DesignBridgeError(ValueError):
    """Invalid or unsupported FE-to-RC workflow, rejects inferred facts."""


def _require_string(row, key):
    value = row.get(key) if isinstance(row, Mapping) else None
    if not isinstance(value, str) or not value.strip():
        raise DesignBridgeError(f"{key} must be a nonempty source ID")
    return value.strip()


def _finite(x, name, *, positive=False):
    if isinstance(x, bool):
        raise DesignBridgeError(f"{name}: boolean not numeric")
    try:
        value = float(x)
    except (TypeError, ValueError, OverflowError) as exc:
        raise DesignBridgeError(f"{name}: numeric required") from exc
    if not math.isfinite(value) or (positive and value <= 0):
        raise DesignBridgeError(f"{name}: finite {'positive' if positive else ''} numeric required")
    return value


def _records(rows, label):
    if isinstance(rows, (str, bytes)) or not isinstance(rows, (list, tuple)) or not rows:
        raise DesignBridgeError(f"{label}: nonempty list required")
    return rows


def _members(model):
    rows = {m["id"]: m for m in model.get("frame_members", [])}
    if len(rows) != len(model.get("frame_members", [])):
        raise DesignBridgeError("duplicate frame member ID")
    return rows


def _end(local, end):
    if end not in ("I", "J"):
        raise DesignBridgeError("only exact member end I/J supported")
    return local[end]


def _case_bundle(model, case, *, tol):
    built = build_canonical_frame_model(model)
    ops.timeSeries("Linear", 982)
    ops.pattern("Plain", 982, 982)
    nodeids = {r["id"] for r in model["nodes"]}
    seen = set()
    input_loads = []
    for row in _records(case["nodal_loads"], "nodal_loads"):
        nid = _require_string(row, "node_id")
        if nid in seen or nid not in nodeids:
            raise DesignBridgeError("duplicated or unknown nodal load ID")
        seen.add(nid)
        if set(row) != {"node_id", *_LOAD_COMPONENTS}:
            raise DesignBridgeError("nodal forces require all six signed named components")
        vec = [_finite(row[k], k) for k in _LOAD_COMPONENTS]
        input_loads.append({"node_id": nid, **dict(zip(_LOAD_COMPONENTS, vec))})
        ops.load(built.node_tags[nid], *vec)
    ops.constraints("Transformation")
    ops.numberer("RCM")
    ops.system("BandGeneral")
    ops.algorithm("Linear")
    ops.integrator("LoadControl", 1.0)
    ops.analysis("Static")
    if ops.analyze(1) != 0:
        raise DesignBridgeError(f"OpenSees failed case {case['case_id']}")
    members = {}
    for mid, tag in built.element_tags.items():
        response = ops.eleResponse(tag, "localForce")
        if response is None or len(response) != 12:
            raise DesignBridgeError(f"localForce returned invalid vector: {mid}")
        f = [_finite(x, "localForce") for x in response]
        members[mid] = {"I": dict(zip(_COMPONENTS, f[:6])),
                        "J": dict(zip(_COMPONENTS, f[6:]))}
    ops.reactions()
    supported = sorted({str(x.get("node_id")) for x in model.get("supports", [])})
    if not supported or not set(supported).issubset(built.node_tags):
        raise DesignBridgeError("explicit known support nodes required")
    reactions = {nid: [_finite(ops.nodeReaction(built.node_tags[nid], i), "reaction")
                       for i in range(1, 7)] for nid in supported}
    xyz = {n["id"]: tuple(_finite(n[axis], axis) for axis in ("x", "y", "z"))
           for n in model["nodes"]}
    sums = [0.] * 6
    def accumulate(nid, vec):
        x, y, z = xyz[nid]
        fx, fy, fz, mx, my, mz = vec
        for i, value in enumerate((
            fx, fy, fz,
            mx + y*fz-z*fy,
            my + z*fx-x*fz,
            mz + x*fy-y*fx,
        )):
            sums[i] += value
    for row in input_loads:
        accumulate(row["node_id"], [row[k] for k in _LOAD_COMPONENTS])
    for nid, v in reactions.items():
        accumulate(nid, v)
    scale = max(1., sum(abs(x) for row in input_loads for k in _LOAD_COMPONENTS
                        for x in [row[k]]))
    residual = max(abs(x) for x in sums)
    if residual > max(tol, 1e-8 * scale):
        raise DesignBridgeError(f"global 6-DOF free-body residual {residual} exceeds tolerance")
    return {
        "case_id": case["case_id"], "source_id": case["source_id"],
        "local_end_resisting_actions": members,
        "nodal_loads": input_loads,
        "global_force_moment_equilibrium_residual": dict(zip(
            ("Fx_kN","Fy_kN","Fz_kN","Mx_kNm","My_kNm","Mz_kNm"), sums)),
        "global_equilibrium_pass": True,
        "solver_orientation_warnings": built.warnings,
    }


def solve_signed_member_cases(*, model: dict, cases: Sequence[dict],
                              combinations: Sequence[dict],
                              tolerance: float = 1e-5) -> dict:
    """Solve signed, separate static cases and combine each local end component.

    Every raw nodal load and combination factor is signed; NO max-abs actions
    are added together across incompatible cases or different member ends.
    """
    if not isinstance(model, dict):
        raise DesignBridgeError("canonical model object required")
    expected = {"force": "kN", "length": "m", "time": "s"}
    if any(model.get("units", {}).get(k) != v for k, v in expected.items()):
        raise DesignBridgeError("canonical model requires kN, m, s units")
    if any(model.get(key) for key in ("joint_loads", "frame_loads", "area_loads",
                                     "load_patterns", "load_cases", "load_combinations")):
        raise DesignBridgeError("existing live loads/cases disallowed: double counting hazard")
    if any(model.get(k) for k in ("shell_elements", "end_releases", "rigid_offsets")):
        raise DesignBridgeError("unsupported shell/release/offset cannot be transferred")
    tol = _finite(tolerance, "tolerance", positive=True)
    case_rows, combo_rows = _records(cases, "cases"), _records(combinations, "combinations")
    case_by_id, raw = {}, []
    for case in case_rows:
        cid = _require_string(case, "case_id")
        if cid in case_by_id:
            raise DesignBridgeError("duplicate case ID")
        _require_string(case, "source_id")
        if set(case) != {"case_id", "source_id", "nodal_loads"}:
            raise DesignBridgeError("case schema unsupported")
        case_by_id[cid] = case
        raw.append(_case_bundle(model, case, tol=tol))
    combination_results = []
    seen = set()
    for combo in combo_rows:
        cid = _require_string(combo, "combination_id")
        _require_string(combo, "source_id")
        if cid in seen or cid in case_by_id:
            raise DesignBridgeError("duplicate or colliding combination ID")
        seen.add(cid)
        components = _records(combo.get("components"), "combination components")
        if set(combo) != {"combination_id", "source_id", "components"}:
            raise DesignBridgeError("combination schema unsupported")
        factors = {}
        for comp in components:
            src = _require_string(comp, "case_id")
            if set(comp) != {"case_id", "factor"} or src not in case_by_id or src in factors:
                raise DesignBridgeError("missing/duplicated/unsupported combination component")
            factors[src] = _finite(comp["factor"], "factor")
        by_id = {r["case_id"]: r for r in raw}
        actions = {}
        for mid in raw[0]["local_end_resisting_actions"]:
            ends = {}
            for end in ("I", "J"):
                ends[end] = {
                    comp: math.fsum(factor * by_id[sid]["local_end_resisting_actions"][mid][end][comp]
                                    for sid, factor in factors.items())
                    for comp in _COMPONENTS
                }
            actions[mid] = ends
        combination_results.append({
            "combination_id": cid, "source_id": combo["source_id"],
            "signed_factors": [{"case_id": c, "factor": f} for c, f in factors.items()],
            "local_end_resisting_actions": actions,
        })
    payload = json.dumps({"model": model, "cases": cases, "combinations": combinations},
                         sort_keys=True, separators=(",", ":"), allow_nan=False)
    return {
        "schema": _SCHEMA, "model_id": _require_string(model, "model_id"),
        "model_digest_sha256": _model_digest(model),
        "input_bundle_sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "units": {"N":"kN", "Vy":"kN", "Vz":"kN", "T":"kN.m",
                  "My":"kN.m", "Mz":"kN.m"},
        "member_end_order": ["N", "Vy", "Vz", "T", "My", "Mz"],
        "element_response": "OpenSees elasticBeamColumn eleResponse('localForce')",
        "sign_rule": "LOCAL_I_AND_J_RESISTING_END_ACTIONS_UNALTERED",
        "raw_cases": raw, "combinations": combination_results,
        "status": "SIGNED_STATIC_ACTIONS_AND_EQUILIBRIUM_VERIFIED_NOT_DESIGN_APPROVAL",
        "modal_combinations_supported": False, "engineering_approval": False,
    }


def evaluate_m08_m09_m10(*, model: dict, solved: dict,
                         beam_bindings: Sequence[dict],
                         column_bindings: Sequence[dict],
                         joint_bindings: Sequence[dict]) -> dict:
    """Consume same-case signed FE actions; external design inputs stay explicit."""
    if solved.get("schema") != _SCHEMA or solved.get("engineering_approval") is not False:
        raise DesignBridgeError("verified signed OpenSees result required")
    if solved.get("model_digest_sha256") != _model_digest(model):
        raise DesignBridgeError("model differs from solved OpenSees source")
    members = _members(model)
    nodes = {r["id"]: r for r in model.get("nodes", [])}
    case = {r["case_id"]: r for r in solved["raw_cases"]}
    combos = {r["combination_id"]: r for r in solved["combinations"]}
    def get_member(mid, kind):
        if mid not in members:
            raise DesignBridgeError(f"unknown member {mid}")
        if str(members[mid].get("member_type", "")).upper() != kind:
            raise DesignBridgeError(f"member {mid}: explicit {kind} type required")
        return members[mid]
    def selected_ids(binding):
        ids = _records(binding.get("combination_ids"), "combination_ids")
        if len(set(ids)) != len(ids) or any(i not in combos for i in ids):
            raise DesignBridgeError("unknown or duplicated design combination ID")
        return ids
    beams, columns, joints = [], [], []
    for cfg in beam_bindings:
        mid = _require_string(cfg, "member_id")
        member = get_member(mid, "BEAM")
        axis = cfg.get("shear_component")
        if axis not in ("Vy", "Vz"):
            raise DesignBridgeError("M08 beam shear component must be Vy/Vz")
        ids = selected_ids(cfg)
        gravity = _require_string(cfg, "gravity_case_id")
        if gravity not in case:
            raise DesignBridgeError("M08 explicit gravity case not solved")
        span = math.dist(tuple(nodes[member["i_node"]][k] for k in ("x","y","z")),
                         tuple(nodes[member["j_node"]][k] for k in ("x","y","z"))) * 1000
        shear_candidates = [
            {"combination_id": cid, "I_kN": combos[cid]["local_end_resisting_actions"][mid]["I"][axis],
             "J_kN": combos[cid]["local_end_resisting_actions"][mid]["J"][axis]}
            for cid in ids]
        strength = cfg.get("strengths_kNm")
        if not isinstance(strength, Mapping):
            raise DesignBridgeError("M08 explicit four moment strengths required")
        out = nbc_capacity_design_beam_shear(
            span_mm=span,
            gravity_shear_a_kN=abs(case[gravity]["local_end_resisting_actions"][mid]["I"][axis]),
            gravity_shear_b_kN=abs(case[gravity]["local_end_resisting_actions"][mid]["J"][axis]),
            analysis_shear_a_kN=max(abs(v["I_kN"]) for v in shear_candidates),
            analysis_shear_b_kN=max(abs(v["J_kN"]) for v in shear_candidates),
            sway_right_moment_a_kNm=strength["right_I"],
            sway_right_moment_b_kNm=strength["right_J"],
            sway_left_moment_a_kNm=strength["left_I"],
            sway_left_moment_b_kNm=strength["left_J"],
            moment_capacity_source_id=_require_string(cfg, "strength_source_id"))
        beams.append({"member_id": mid, "source_id": _require_string(cfg, "source_id"),
                      "signed_combination_end_shear": shear_candidates,
                      "gravity_shear_source_case": gravity,
                      "shear_component": axis, "check": out})
    for cfg in column_bindings:
        mid = _require_string(cfg, "member_id")
        get_member(mid, "COLUMN")
        ids = selected_ids(cfg)
        mapping = cfg.get("moment_component_mapping")
        if not isinstance(mapping, Mapping) or set(mapping) != {"Mux", "Muy"} or set(mapping.values()) != {"My", "Mz"}:
            raise DesignBridgeError("M09 explicit unique signed My/Mz mapping required")
        dims = cfg.get("section")
        if not isinstance(dims, Mapping):
            raise DesignBridgeError("M09 section input required")
        for field in ("width_mm","depth_mm","fck_MPa","fy_MPa","bars",
                      "clear_height_mm","effective_length_x_mm","effective_length_y_mm"):
            if field not in dims:
                raise DesignBridgeError("M09 missing "+field)
        secid = members[mid].get("section_id")
        section = next((s for s in model.get("sections", []) if s["id"] == secid), None)
        if section is None:
            raise DesignBridgeError("M09 section foreign key unresolved")
        if (not math.isclose(float(section["width"])*1000, float(dims["width_mm"]),abs_tol=1e-6) or
            not math.isclose(float(section["depth"])*1000, float(dims["depth_mm"]),abs_tol=1e-6)):
            raise DesignBridgeError("M09 design section differs from solved FE section")
        scenarios = []
        for cid in ids:
            actions = combos[cid]["local_end_resisting_actions"][mid]
            for end in ("I","J"):
                v = actions[end]
                # Local end I resisting +N and end J resisting -N correspond
                # to a compressive section force for this elastic orientation.
                pu = v["N"] if end == "I" else -v["N"]
                if pu <= 0:
                    raise DesignBridgeError(f"M09 axial tension/zero unsupported {mid}:{cid}:{end}")
                calculation = biaxial_interaction_from_bars(
                    **dims, Pu_kN=pu,
                    Mux_kNm=abs(v[mapping["Mux"]]),
                    Muy_kNm=abs(v[mapping["Muy"]]),
                    source_id=_require_string(cfg, "source_id"))
                scenarios.append({
                    "combination_id": cid, "member_end": end,
                    "input_signed_end": dict(v), "axial_compression_kN": pu,
                    "section_moment_mapping": dict(mapping),
                    "check": calculation,
                })
        governing = max(scenarios, key=lambda r:r["check"]["legacy_interaction"]["interaction_utilization"])
        columns.append({"member_id":mid,"source_id":cfg["source_id"],"scenarios":scenarios,
                        "governing_combination_id":governing["combination_id"],
                        "governing_member_end":governing["member_end"],
                        "governing_interaction_utilization": governing["check"]["legacy_interaction"]["interaction_utilization"],
                        "status":"FAIL" if any(s["check"]["status"]=="FAIL" for s in scenarios)
                                 else "PARTIAL_SP16_AND_DETAILING_HOLD"})
    for cfg in joint_bindings:
        mid = _require_string(cfg, "column_member_id")
        member = get_member(mid, "COLUMN")
        node_id = _require_string(cfg, "joint_node_id")
        end = _require_string(cfg, "column_end")
        if end not in ("I","J") or member["i_node" if end=="I" else "j_node"] != node_id:
            raise DesignBridgeError("joint node does not coincide with mapped column end")
        beam_id = _require_string(cfg, "beam_member_id")
        beam = get_member(beam_id, "BEAM")
        if node_id not in (beam["i_node"],beam["j_node"]):
            raise DesignBridgeError("joint source beam is not incident at joint node")
        shear = cfg.get("shear_component")
        if shear not in ("Vy","Vz"):
            raise DesignBridgeError("M10 explicit local column shear Vy/Vz required")
        props=cfg.get("joint")
        if not isinstance(props,Mapping):
            raise DesignBridgeError("joint geometry and steel source required")
        scenarios=[]
        for cid in selected_ids(cfg):
            col_end=combos[cid]["local_end_resisting_actions"][mid][end]
            r=nbc_joint_shear(
                **props,
                column_shear_kN=abs(col_end[shear]),
                joint_geometry_source_id=_require_string(cfg, "source_id"))
            scenarios.append({"combination_id":cid,"signed_column_shear_kN":col_end[shear],
                              "column_end":end,"check":r})
        governing=max(scenarios,key=lambda x:x["check"]["factored_Vjh_kN"])
        joints.append({"joint_node_id":node_id,"column_member_id":mid,
                       "beam_member_id":beam_id,"source_id":cfg["source_id"],
                       "shear_component":shear,"scenarios":scenarios,
                       "governing_combination_id":governing["combination_id"],
                       "status":"FAIL" if any(not x["check"]["joint_nominal_shear_pass"]
                                              for x in scenarios)
                               else "PARTIAL_CONFINEMENT_AND_ANCHORAGE_HOLD"})
    return {"schema":"jp.structural.m08_m09_m10_design_bridge.v0.1",
            "model_id":solved["model_id"],
            "source_action_digest":solved["input_bundle_sha256"],
            "beam_design":beams,"column_design":columns,"joint_design":joints,
            "status":"ELASTIC_FE_TO_BOUNDED_RC_CHECKS_HOLD",
            "checks":{
                "signed_concurrent_case_actions":True,
                "independent_sp16_chart_validated":False,
                "signed_modal_orthogonal_envelope_supported":False,
                "nbc_ductile_detailing_complete":False,
                "second_order_design_complete":False,
                "project_source_verified":False,
            }, "engineering_approval":False}
