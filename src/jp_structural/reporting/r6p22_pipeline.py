"""R6.22 reproducible geometry/load-path -> real OpenSees FE -> casebook bridge.

Only a *bounded* source-declared one-way/slender frame case. The final project
SAR needs actual drawings, soil, seismic/wind, shell stiffness and design QA.
"""
from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import math
from pathlib import Path

from jp_structural.reporting.independent_casebook import (
    build as build_casebook, emit as emit_casebook,
    verify_bundle as verify_casebook
)
from jp_structural.solvers.native.r6p22_geometry_gravity import (
    derive_sources, GeometryGravityHold, INPUT_SCHEMA
)

SCHEMA = "jp.structural.r6p22.independent_loadpath_sar.v0.1"
PREFIX = "r6p22-geometry-loadpath"


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")).hexdigest()


def _require(condition, message):
    if not condition:
        raise GeometryGravityHold("HOLD: " + message)


def build(payload: dict, *, contract: dict, coverage: dict) -> dict:
    ledger = derive_sources(payload)
    extra = payload.get("additional_cases", [])
    _require(isinstance(extra, list) and all(isinstance(x, dict) for x in extra),
             "explicit additional case list required")
    raw = []
    nodal = ledger["column_gravity_node_loads"]
    for cid, line in sorted(ledger["gravity_by_case_element"].items()):
        nodes = []
        if cid == "DL":
            nodes = [{
                "node_id": nid, "Fx_kN": 0.0, "Fy_kN": 0.0,
                "Fz_kN": -weight, "Mx_kNm": 0.0, "My_kNm": 0.0,
                "Mz_kNm": 0.0
            } for nid, weight in sorted(nodal.items()) if weight > 0]
        raw.append({
            "case_id": cid,
            "source_id": "R6P22_INDEPENDENT_MATERIAL_GEOMETRY_" + cid,
            "nodal_loads": nodes,
            "uniform_beam_loads": line
        })
    known = {row["case_id"] for row in raw}
    _require({"DL", "LL"} <= known, "separate dead and imposed source cases required")
    for row in extra:
        cid = row.get("case_id")
        _require(isinstance(cid, str) and cid and cid not in known,
                 "additional source case duplicates gravity case")
        known.add(cid)
        raw.append(row)
    combos = payload.get("combinations")
    _require(isinstance(combos, list) and combos,
             "explicit nonempty design combinations required")
    _require(set(known) == {x["case_id"] for x in raw},
             "raw cases must be unique")
    source_case = {
        "schema": "jp.structural.independent_sar_input.v0.1",
        "case_id": payload["case_id"],
        "classification": payload["classification"],
        "provenance": payload["provenance"],
        "model": payload["model"],
        "cases": raw,
        "combinations": combos,
        "design_bindings": payload["design_bindings"],
        "code_references": payload["code_references"],
        "engineering_approval": False
    }
    casebook = build_casebook(source_case, contract=contract, coverage=coverage)
    _require(casebook.get("signed_input_sha256") ==
             casebook["bounded_design_checks"].get("source_action_digest"),
             "real FE result not bound to the same model/design source")
    solved = {r["case_id"]: r for r in casebook["signed_analysis"]["raw_cases"]}
    actual = sum(
        sum(float(r["downward_resultant_kN"]) for r in solved[k]["uniform_beam_loads"])
        + sum(-float(r["Fz_kN"]) for r in solved[k]["nodal_loads"])
        for k in ("DL", "LL")
    )
    source_weight = ledger["gravity_totals"]["total_source_gravity_kN"]
    _require(math.isclose(actual, source_weight, rel_tol=1e-10, abs_tol=1e-7),
             "FE applied gravity differs from source-declared material volumes")
    _require(casebook["max_six_component_equilibrium_residual"] < 1e-5
             and ledger["gravity_plan_first_moment_balance_pass"] is True,
             "global six-axis/plan-moment source checks not satisfied")
    return {
        "schema": SCHEMA,
        "case_id": payload["case_id"],
        "input_schema": INPUT_SCHEMA,
        "input_sha256": _digest(payload),
        "casebook_input_sha256": casebook["input_sha256"],
        "source_material_gravity": ledger,
        "casebook": casebook,
        "actual_native_frame_gravity_kN": actual,
        "gravity_force_balance_pass": True,
        "gravity_plan_moment_balance_pass": True,
        "no_ETABS_calculation_or_export_required": True,
        "loads_generated_from_material_geometry": True,
        "one_way_rectangular_slab_load_paths_only": True,
        "physical_diaphragm_and_shell_stiffness": "NOT_MODELLED",
        "live_and_seismic_code_factors": "EXPLICIT_EXTERNAL_SOURCES_NOT_AUTOMATICALLY_VERIFIED",
        "column_weight_effect_on_member_axial_diagrams": "HALF_NODAL_EQUIVALENT_APPROXIMATION",
        "all_applicable_design_modules_complete": False,
        "construction_release_authorised": False,
        "engineering_approval": False,
        "status": "INDEPENDENT_GEOMETRY_TO_STATIC_FE_AND_PARTIAL_SAR_NOT_APPROVED"
    }


def _csv(data: list, keys: tuple) -> str:
    s = io.StringIO()
    writer = csv.DictWriter(s, fieldnames=keys, lineterminator="\n")
    writer.writeheader()
    for row in data:
        writer.writerow({key: row.get(key) for key in keys})
    return s.getvalue()


def routes_csv(result: dict) -> str:
    ledger = result["source_material_gravity"]
    rows = [{
        "case_id": x["case_id"],
        "source_key": x["source_key"],
        "load_id": x["id"], "member_id": x["member_id"],
        "downward_kN_per_m": x["downward_kN_per_m"],
        "resultant_kN": x["downward_resultant_kN"],
        "source_provenance": x["source_provenance"]
    } for x in ledger["routing"]["member_element_load_sources"]]
    return _csv(rows, ("case_id", "source_key", "load_id", "member_id",
                       "downward_kN_per_m", "resultant_kN", "source_provenance"))


def render_html(result: dict) -> str:
    e = lambda x: html.escape(str(x), quote=True)
    audit = result["source_material_gravity"]
    loads = audit["gravity_totals"]
    rows = "".join(
        "<tr>" + "".join(f"<td>{e(entry[k])}</td>" for k in (
            "case_id", "member_id", "id", "downward_kN_per_m",
            "downward_resultant_kN", "source_provenance"
        )) + "</tr>"
        for entry in audit["routing"]["member_element_load_sources"]
    )
    columns = "".join(
        f"<li>{e(row['member_id'])}: {e(round(row['weight_kN'], 6))} kN "
        f"(half-lumped to two nodes; not exact column axial diagram)</li>"
        for row in audit["column_source_ledger"]
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>R6.22 independent geometry and gravity ledger</title>
<style>body{{font:15px/1.55 system-ui,sans-serif;max-width:1100px;margin:auto;padding:22px;color:#28364a}}
section{{margin:15px 0;padding:19px;border:1px solid #ccd3dd;border-radius:10px}}
table{{border-collapse:collapse;width:100%;min-width:580px}}td,th{{border:1px solid #cbd5e1;text-align:left;padding:7px;font-size:12px}}
.scroll{{overflow-x:auto}}th{{background:#eef2f7}}.hold{{padding:12px;border-left:5px solid #b33434;background:#fff2f2}}
@media print{{section{{break-inside:avoid}}}}</style></head><body>
<h1>R6.22 — Independent first-party gravity source and connected load paths</h1>
<p>{e(result["case_id"])} · no native ETABS output required</p>
<p class="hold"><strong>ENGINEERING HOLD:</strong> One-way slab assumption is user-declared;
no shell/diaphragm stiffness, full seismic/wind combinations or final foundation,
member/detailing and construction approval. Historical F3 unsafe is not cleared.</p>
<section><h2>1 · Exact-node structural connectivity</h2>
<p>{e(audit["graph"]["node_count"])} nodes, {e(audit["graph"]["frame_count"])} frame elements,
{e(audit["graph"]["base_support_count"])} explicit supports. All frame components reach
a declared support via actual shared node identities; no coordinate auto-join.</p></section>
<section><h2>2 · Material-volume-derived gravity</h2>
<p>Source noncolumn gravity: {loads["noncolumn_source_gravity_kN"]:.5f} kN;
column self-weight: {loads["plumb_column_self_weight_kN"]:.5f} kN.
<strong>Total: {loads["total_source_gravity_kN"]:.5f} kN</strong>.
FE applied gravity: {result["actual_native_frame_gravity_kN"]:.5f} kN.</p>
<p>Source and FE force balance: PASS. Plan X/Y first-moment balance: PASS.
Estimated source seismic-eligible weight (NOT a generated modal model):
{loads["seismic_eligible_weight_kN"]:.5f} kN.</p></section>
<section><h2>3 · Slab and wall loads transferred to real beams</h2>
<div class="scroll"><table><tr><th>Case</th><th>Beam</th><th>Source</th>
<th>kN/m</th><th>kN</th><th>Source reference</th></tr>{rows}</table></div></section>
<section><h2>4 · Vertical column self-weight approximation</h2>
<ul>{columns}</ul></section>
<section><h2>5 · FE solution and design screens</h2>
<p><a href="casebook/independent-sar.html">Open independent OpenSees signed I/J
member force and bounded M08/M09/M10 design casebook</a>.</p>
<p><a href="r6p22-geometry-loadpath.json">Source JSON and FE receipts</a> ·
<a href="r6p22-geometry-loadpath-routes.csv">Beam load-path CSV</a> ·
<a href="r6p22-geometry-loadpath-manifest.json">SHA-256 manifest</a>.</p></section>
</body></html>"""


def emit(result: dict, folder: Path) -> dict:
    _require(result.get("schema") == SCHEMA and
             result.get("engineering_approval") is False,
             "cannot publish invalid or approved geometry-case result")
    folder.mkdir(parents=True, exist_ok=True)
    child = folder / "casebook"
    emit_casebook(result["casebook"], child)
    casebook_manifest = verify_casebook(child)
    files = {
        PREFIX+".json": json.dumps(result, indent=2, sort_keys=True,
                                   allow_nan=False) + "\n",
        PREFIX+".html": render_html(result),
        PREFIX+"-routes.csv": routes_csv(result)
    }
    for name, data in files.items():
        (folder / name).write_text(data, encoding="utf-8")
    manifest = {
        "schema": "jp.structural.r6p22.gravity_report_manifest.v0.1",
        "case_id": result["case_id"], "input_sha256": result["input_sha256"],
        "files_sha256": {
            **{name: hashlib.sha256(data.encode("utf-8")).hexdigest()
               for name, data in files.items()},
            "casebook/independent-sar-manifest.json": hashlib.sha256(
                (child / "independent-sar-manifest.json").read_bytes()
            ).hexdigest()
        },
        "child_casebook_input_sha256": casebook_manifest["input_sha256"],
        "engineering_approval": False
    }
    (folder / (PREFIX+"-manifest.json")).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    return manifest


def verify(folder: Path) -> dict:
    manifest = json.loads((folder / (PREFIX+"-manifest.json")).read_text())
    _require(manifest.get("schema") ==
             "jp.structural.r6p22.gravity_report_manifest.v0.1" and
             manifest.get("engineering_approval") is False,
             "bad report manifest or false source/design acceptance")
    required = {PREFIX+".json", PREFIX+".html", PREFIX+"-routes.csv",
                "casebook/independent-sar-manifest.json"}
    _require(set(manifest["files_sha256"]) == required,
             "incomplete/corrupt geometry report artifact listing")
    for name, expected in manifest["files_sha256"].items():
        _require(hashlib.sha256((folder / name).read_bytes()).hexdigest() ==
                 expected, "source/report SHA mismatch: "+name)
    child = verify_casebook(folder / "casebook")
    _require(child["input_sha256"] == manifest["child_casebook_input_sha256"],
             "source casebook manifest does not belong to this run")
    result = json.loads((folder / (PREFIX+".json")).read_text())
    _require(result.get("input_sha256") == manifest["input_sha256"] and
             result.get("engineering_approval") is False and
             result.get("gravity_force_balance_pass") is True,
             "geometry-ledger source/hash/force balance failed")
    return manifest
