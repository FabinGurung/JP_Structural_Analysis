"""R6.21 independent first-party SAR casebook for source-labelled 3D frame inputs.

This is a *reusable* OpenSees/Python integration, not an ETABS adapter and
not a claim of a complete real building design.  A source-derived model may
run without native ETABS joints; its assumptions and unfinished code checks
stay visible.  Outputs for real projects must remain in private storage.
"""
from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import math
from pathlib import Path
from typing import Any

from jp_structural.solvers.opensees.member_design_bridge import (
    solve_signed_member_cases, evaluate_m08_m09_m10
)

SCHEMA = "jp.structural.independent_sar_casebook.v0.1"
INPUT_SCHEMA = "jp.structural.independent_sar_input.v0.1"
PROVENANCE_KEYS = ("geometry", "materials", "supports", "loads",
                   "reinforcement", "design_code")
CLASSES = {"SYNTHETIC_REFERENCE", "PROJECT_SOURCE_DERIVED_UNVERIFIED"}
STATUS = ("NOT_EVALUATED", "BOUNDED_FE", "BOUNDED_RC")
ACTIONS = ("N", "Vy", "Vz", "T", "My", "Mz")


class IndependentSARInputError(ValueError):
    pass


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise IndependentSARInputError(message)


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")).hexdigest()


def validate_input(payload: dict) -> None:
    _require(isinstance(payload, dict) and payload.get("schema") == INPUT_SCHEMA,
             "Independent casebook input schema required")
    _require(payload.get("classification") in CLASSES,
             "Case must be labelled synthetic or source-derived unverified")
    cid = payload.get("case_id")
    _require(isinstance(cid, str) and len(cid.strip()) >= 8 and
             all(c.isalnum() or c in "-_" for c in cid),
             "Safe stable case identifier required")
    provenance = payload.get("provenance")
    _require(isinstance(provenance, dict) and
             set(provenance) == set(PROVENANCE_KEYS) and
             all(isinstance(provenance[k], str) and len(provenance[k].strip()) >= 10
                 for k in PROVENANCE_KEYS),
             "Source ID for geometry/material/support/load/rebar/code required")
    model = payload.get("model")
    _require(isinstance(model, dict) and isinstance(model.get("model_id"), str),
             "Canonical model with model_id required")
    _require(isinstance(model.get("source_references"), list) and
             model["source_references"], "Original/synthetic source registry required")
    if payload["classification"] == "PROJECT_SOURCE_DERIVED_UNVERIFIED":
        _require(all(str(x.get("source_type", "")).upper() != "SYNTHETIC_TEST"
                     for x in model["source_references"]),
                 "Real project cannot reuse synthetic source registry")
    for key in ("cases", "combinations"):
        x = payload.get(key)
        _require(isinstance(x, list) and x,
                 "Nonempty source-labelled "+key+" required")
    bindings = payload.get("design_bindings")
    _require(isinstance(bindings, dict) and set(bindings) == {"beams", "columns", "joints"}
             and all(isinstance(bindings[k], list) for k in bindings),
             "Separate explicit member and joint design bindings required")
    _require(all(isinstance(x, dict) for k in bindings for x in bindings[k]),
             "Design bindings must be complete objects")
    codes = payload.get("code_references")
    _require(isinstance(codes, list) and codes and
             all(isinstance(x, dict) and isinstance(x.get("id"), str) and x["id"]
                 and isinstance(x.get("url"), str) and x["url"].startswith("https://")
                 for x in codes), "Explicit published code references required")
    _require(not payload.get("engineering_approval", False),
             "A case submission cannot carry assumed engineering approval")


def _actions(solved: dict) -> list[dict]:
    _require(solved.get("member_end_order") == list(ACTIONS),
             "Unexpected signed action component convention")
    rows = []
    cases = [
        ("RAW", a["case_id"], a["local_end_resisting_actions"])
        for a in solved["raw_cases"]
    ] + [
        ("COMBINATION", a["combination_id"], a["local_end_resisting_actions"])
        for a in solved["combinations"]
    ]
    for kind, cid, members in cases:
        for mid, ends in sorted(members.items()):
            _require(set(ends) == {"I", "J"}, "Member local end coverage incomplete")
            for end in ("I", "J"):
                local = ends[end]
                _require(set(local) == set(ACTIONS) and all(
                    isinstance(local[a], (int, float)) and
                    not isinstance(local[a], bool) and math.isfinite(local[a])
                    for a in ACTIONS
                ), "Missing/nonfinite signed I/J action")
                rows.append({
                    "kind": kind, "case_id": cid, "member_id": mid, "end": end,
                    **{a: float(local[a]) for a in ACTIONS}
                })
    return rows


def _design_summary(checks: dict) -> list[dict]:
    """Summarize executed RC kernels without treating demand as a PASS."""
    summary = []
    for beam in checks["beam_design"]:
        ends = beam["check"]["end_demands"]
        _require(len(ends) == 2 and
                 all(math.isfinite(float(e["required_shear_kN"])) for e in ends),
                 "M08 two-ended capacity-design shear demands missing")
        summary.append({
            "module": "M08", "component_id": beam["member_id"],
            "governing_reference": "BEAM_I_AND_J",
            "quantity": "max|required capacity-design shear|",
            "value": round(max(float(e["required_shear_kN"]) for e in ends), 7),
            "unit": "kN",
            "status": "DEMAND_ONLY_STIRRUPS_AND_DETAILING_UNCHECKED",
        })
    for column in checks["column_design"]:
        value = float(column["governing_interaction_utilization"])
        _require(math.isfinite(value) and value >= 0,
                 "M09 interaction utilization missing/nonfinite")
        summary.append({
            "module": "M09", "component_id": column["member_id"],
            "governing_reference": column["governing_combination_id"] +
                                   ":" + column["governing_member_end"],
            "quantity": "bounded P-M-M interaction utilization",
            "value": round(value, 7), "unit": "ratio",
            "status": column["status"],
        })
    for joint in checks["joint_design"]:
        value = float(joint["governing_uncertain_direction_shear_kN"])
        _require(math.isfinite(value) and value >= 0,
                 "M10 governing uncertain joint shear missing/nonfinite")
        summary.append({
            "module": "M10", "component_id": joint["joint_node_id"],
            "governing_reference": joint["governing_combination_id"],
            "quantity": "adverse-direction joint shear screening",
            "value": round(value, 7), "unit": "kN",
            "status": joint["status"],
        })
    return summary


def build(payload: dict, *, contract: dict, coverage: dict) -> dict:
    """Solve the supplied canonical case, then check SAME-MODEL signed actions."""
    validate_input(payload)
    _require(contract.get("schema") == "jp.structural.report_template_contract.v0.2" and
             len(contract.get("chapters", [])) == 7,
             "Original seven-chapter SAR contract missing")
    requirements = {x["id"]: x for x in coverage.get("requirements", [])}
    expected = {f"M{i:02}" for i in range(1, 17)} | {"S17", "S18"}
    _require(set(requirements) == expected and len(coverage["requirements"]) == 18,
             "18-module source coverage register changed")
    _require({x for ch in contract["chapters"] for x in ch["requirement_ids"]}
             == expected, "Seven-chapter requirement map mismatch")

    model, cases, combos = (payload[k] for k in ("model", "cases", "combinations"))
    signed = solve_signed_member_cases(model=model, cases=cases, combinations=combos)
    checks = evaluate_m08_m09_m10(
        model=model, solved=signed,
        beam_bindings=payload["design_bindings"]["beams"],
        column_bindings=payload["design_bindings"]["columns"],
        joint_bindings=payload["design_bindings"]["joints"]
    )
    _require(signed.get("engineering_approval") is False and
             checks.get("engineering_approval") is False,
             "Solver and design statuses must remain unapproved")
    original = {"model": model, "cases": cases, "combinations": combos}
    _require(signed.get("input_bundle_sha256") == _hash(original) and
             checks.get("source_action_digest") == signed["input_bundle_sha256"],
             "Independent signed FE/design provenance mismatch")
    raw = signed["raw_cases"]
    _require(len(raw) == len(cases) and len(signed["combinations"]) == len(combos)
             and all(x.get("global_equilibrium_pass") is True for x in raw),
             "OpenSees FE global equilibrium/coverage failed")
    components = [abs(float(v))
                  for row in raw for v in
                  row["global_force_moment_equilibrium_residual"].values()]
    _require(components and all(math.isfinite(v) for v in components)
             and max(components) < 1e-5,
             "Six-component global force/moment residual exceeds tolerance")
    rows = _actions(signed)
    members = model["frame_members"]
    member_types = {m["id"]: m.get("member_type") for m in members}
    _require(len(member_types) == len(members) and
             len(rows) == 2 * len(members) * (len(raw) + len(combos)),
             "Signed action member/end coverage incomplete")
    beams = {m for m, t in member_types.items() if t == "BEAM"}
    columns = {m for m, t in member_types.items() if t == "COLUMN"}
    checked_beams = {x["member_id"] for x in checks["beam_design"]}
    checked_columns = {x["member_id"] for x in checks["column_design"]}
    checked_joints = {x["joint_node_id"] for x in checks["joint_design"]}
    _require(checked_beams <= beams and checked_columns <= columns,
             "FE-to-RC check references unmodelled member")
    _require(len(checked_beams) == len(checks["beam_design"]) and
             len(checked_columns) == len(checks["column_design"]) and
             len(checked_joints) == len(checks["joint_design"]),
             "Duplicated design member/joint mapping")
    module_status = {mid: "NOT_EVALUATED" for mid in expected}
    module_status["M04"] = "BOUNDED_FE"
    for mid, key in (("M08", "beam_design"), ("M09", "column_design"),
                     ("M10", "joint_design")):
        if checks[key]:
            module_status[mid] = "BOUNDED_RC"
    chapters = [{
        "id": c["id"], "title": c["title"], "headings": c["headings"],
        "modules": [{
            "id": mid, "name": requirements[mid]["title"],
            "registry_status": requirements[mid]["status"],
            "case_status": module_status[mid]
        } for mid in c["requirement_ids"]]
    } for c in contract["chapters"]]
    blockers = [
        "No verified complete project geometry/slab/diaphragm/actual soil and support evidence",
        "Model supports only elastic static 3D frames, not complete shell/modal/wind/P-delta cases",
        "User-supplied cases and combinations are not yet proven code-complete",
        "RC checks are bounded capacity screens; full bars, detailing, all members, foundation and serviceability still pending",
        "Professional engineer independent review and construction acceptance not performed",
    ]
    return {
        "schema": SCHEMA, "case_id": payload["case_id"],
        "classification": payload["classification"],
        "analysis_mode": "FIRST_PARTY_OPENSEES_ELASTIC_STATIC_3D_FRAMES",
        "native_ETABS_output_required": False,
        "model_id": model["model_id"],
        "input_sha256": _hash(payload),
        "signed_input_sha256": signed["input_bundle_sha256"],
        "signed_results_sha256": signed["results_digest_sha256"],
        "provenance": payload["provenance"],
        "code_references": payload["code_references"],
        "counts": {
            "frame_members": len(members), "analysis_cases": len(raw),
            "signed_combinations": len(combos), "signed_end_rows": len(rows),
            "beams": len(beams), "beams_screened": len(checked_beams),
            "columns": len(columns), "columns_screened": len(checked_columns),
            "joints_screened": len(checked_joints),
        },
        "unassessed_members": {
            "beams": sorted(beams - checked_beams),
            "columns": sorted(columns - checked_columns)
        },
        "max_six_component_equilibrium_residual": max(components),
        "units": {"force": "kN", "length": "m", "moment": "kN.m"},
        "chapters": chapters,
        "module_status": module_status,
        "signed_end_rows": rows,
        "signed_analysis": signed,
        "bounded_design_checks": checks,
        "bounded_design_summary": _design_summary(checks),
        "input_source_references": model["source_references"],
        "not_evaluated": blockers,
        "historical_F3_unsafe_flag_overridden": False,
        "project_geometry_and_loads_approved": False,
        "all_applicable_design_modules_complete": False,
        "professional_review_complete": False,
        "engineering_approval": False,
        "construction_release_authorised": False,
        "status": "REPRODUCIBLE_BOUNDED_INDEPENDENT_ANALYSIS_NOT_FINAL_BUILDING_REPORT",
    }


def csv_text(result: dict) -> str:
    buf = io.StringIO()
    fieldnames = ("kind", "case_id", "member_id", "end", *ACTIONS)
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(result["signed_end_rows"])
    return buf.getvalue()


def render_html(result: dict) -> str:
    _require(result.get("engineering_approval") is False and
             result.get("schema") == SCHEMA,
             "Only validated unapproved independent SAR casebooks can render")
    esc = lambda x: html.escape(str(x), quote=True)
    headings = "".join(
        f'<a href="#chapter-{esc(ch["id"])}">{esc(ch["id"])} {esc(ch["title"])}</a> '
        for ch in result["chapters"]
    )
    sections = []
    for ch in result["chapters"]:
        table = "".join(
            f"<tr><td>{esc(m['id'])}</td><td>{esc(m['name'])}</td>"
            f"<td>{esc(m['registry_status'])}</td><td>{esc(m['case_status'])}</td></tr>"
            for m in ch["modules"]
        )
        if ch["id"] == "06":
            table += ""  # Keep module status table independent of computed RC results.
        sections.append(
            f'<section id="chapter-{esc(ch["id"])}"><h2>Chapter {esc(ch["id"])}'
            f' — {esc(ch["title"])}</h2><table><thead><tr><th>Module</th>'
            f'<th>Domain</th><th>Registry</th><th>Computed in this run</th>'
            f'</tr></thead><tbody>{table}</tbody></table></section>'
        )
    data = "".join(
        "<tr>" + "".join(f"<td>{esc(row[k])}</td>" for k in (
            "kind", "case_id", "member_id", "end", *ACTIONS
        )) + "</tr>" for row in result["signed_end_rows"]
    )
    design_rows = "".join(
        "<tr>" + "".join(f"<td>{esc(r[key])}</td>" for key in
        ("module", "component_id", "governing_reference",
         "quantity", "value", "unit", "status")) + "</tr>"
        for r in result["bounded_design_summary"]
    )
    design_table = ('<h3>Actual bounded RC check results (NOT a complete design)</h3>'
                    '<div class="scroll"><table><thead><tr>' +
                    ''.join(f'<th>{esc(x)}</th>' for x in
                            ("Module", "Component", "Case/end", "Demand/check",
                             "Computed", "Units", "Disposition")) +
                    '</tr></thead><tbody>' + design_rows + '</tbody></table></div>')
    blockers = "".join(f"<li>{esc(x)}</li>" for x in result["not_evaluated"])
    refs = "".join(f'<li><a href="{esc(x["url"])}">{esc(x["id"])}</a></li>'
                   for x in result["code_references"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Independent OpenSees SAR casebook — {esc(result["case_id"])}</title>
<style>body{{font:15px/1.5 system-ui,sans-serif;max-width:1120px;margin:auto;padding:18px;color:#1e293b}}
header,section{{padding:20px;border:1px solid #cbd5e1;border-radius:10px;margin:12px 0}}
h1{{font-size:24px}}h2{{font-size:19px}}.hold{{border-left:5px solid #ad2929;background:#fff1f1;padding:12px}}
nav a{{display:inline-block;margin:5px}}.scroll{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;min-width:520px}}
th,td{{border:1px solid #d5dae2;padding:6px;text-align:left;font-size:12px}}th{{background:#f1f5f9}}
code{{overflow-wrap:anywhere}}@media print{{nav{{display:none}}body{{padding:0}}section{{break-inside:avoid}}}}</style>
</head><body><header><h1>Independent first-party structural analysis casebook</h1>
<p>{esc(result["case_id"])} · {esc(result["classification"])} · model {esc(result["model_id"])}</p>
<p class="hold"><strong>NOT ENGINEERING APPROVED / NOT A COMPLETE BUILDING REPORT.</strong>
Loads, geometry, supports, building-wide code combinations and full design must be independently established.
Original F3 adverse finding is not cleared.</p><nav>{headings}</nav></header>
{''.join(sections)}
<section><h2>Annex — independent bounded RC checks and signed member actions</h2>
{design_table}
<h3>Real OpenSees signed frame actions</h3>
<p>{esc(result["counts"]["analysis_cases"])} separately solved source-labelled cases;
{esc(result["counts"]["signed_combinations"])} algebraically combined cases;
{esc(result["counts"]["signed_end_rows"])} signed member I/J records.</p>
<p>Global six-component maximum equilibrium residual:
{esc(result["max_six_component_equilibrium_residual"])} kN or kNm.</p>
<div class="scroll"><table><thead><tr>{''.join(f'<th>{esc(k)}</th>' for k in ("Type","Case","Member","End",*ACTIONS))}</tr></thead>
<tbody>{data}</tbody></table></div>
<h3>Unassessed beam members</h3><p>{esc(', '.join(result["unassessed_members"]["beams"]) or "None")}</p>
<h3>Unassessed column members</h3><p>{esc(', '.join(result["unassessed_members"]["columns"]) or "None")}</p>
<h3>Input and result trace</h3><p>Input SHA-256: <code>{esc(result["input_sha256"])}</code></p>
<p>Solver bundle SHA-256: <code>{esc(result["signed_input_sha256"])}</code></p>
<p>Signed action SHA-256: <code>{esc(result["signed_results_sha256"])}</code></p>
<h3>Remaining verification tasks</h3><ul>{blockers}</ul>
<h3>Referenced design standards</h3><ul>{refs}</ul>
<p class="hold">Results are neither a professional approval nor construction authorization.
ETABS numerical parity is not required; an independent physical model and matching code checks are.</p>
</section></body></html>"""


def emit(result: dict, output_dir: Path) -> dict:
    _require(result["schema"] == SCHEMA and
             result["engineering_approval"] is False,
             "Cannot export invalid or engineering-approved casebook")
    _require(not output_dir.is_file(), "Output directory is a file")
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "independent-sar.json": json.dumps(result, indent=2, sort_keys=True,
                                           allow_nan=False) + "\n",
        "independent-sar.html": render_html(result),
        "independent-sar-member-ends.csv": csv_text(result),
    }
    for name, contents in files.items():
        (output_dir / name).write_text(contents, encoding="utf-8")
    manifest = {
        "schema": "jp.structural.independent_sar_manifest.v0.1",
        "case_id": result["case_id"],
        "classification": result["classification"],
        "input_sha256": result["input_sha256"],
        "signed_results_sha256": result["signed_results_sha256"],
        "files": {name: hashlib.sha256(value.encode("utf-8")).hexdigest()
                  for name, value in files.items()},
        "engineering_approval": False,
    }
    (output_dir / "independent-sar-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def verify_bundle(folder: Path) -> dict:
    manifest = json.loads((folder / "independent-sar-manifest.json").read_text(encoding="utf-8"))
    _require(manifest.get("schema") == "jp.structural.independent_sar_manifest.v0.1"
             and manifest.get("engineering_approval") is False,
             "Invalid/approved generated bundle")
    _require(set(manifest["files"]) == {
        "independent-sar.json", "independent-sar.html",
        "independent-sar-member-ends.csv"
    }, "Missing or unrecognized bundle artifacts")
    for name, expected in manifest["files"].items():
        actual = hashlib.sha256((folder / name).read_bytes()).hexdigest()
        _require(actual == expected, "Output SHA256 mismatch: " + name)
    result = json.loads((folder / "independent-sar.json").read_text(encoding="utf-8"))
    _require(result["schema"] == SCHEMA and result["engineering_approval"] is False
             and result["case_id"] == manifest["case_id"]
             and result["input_sha256"] == manifest["input_sha256"]
             and result["signed_results_sha256"] == manifest["signed_results_sha256"],
             "Published manifest/results mismatch")
    _require(len(result["signed_end_rows"]) == result["counts"]["signed_end_rows"],
             "Reported signed member end count mismatch")
    return manifest
