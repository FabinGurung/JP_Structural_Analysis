"""Publish synthetic R6.23 FE engine and R6.24 numerical comparison to Pages.

The existing site/reports are not regenerated here; this appends a verified
isolated public preview to the legacy pinned-engine publishing workflow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from r6p23.engine import build, digest, StructuralHold
from r6p23.runner import reference_fixture, emit, verify
from r6p23.convergence import screen, preflight

SCHEMA = "jp.structural.r6p24.pages_independent_shell_preview.v0.1"
HERE = Path(__file__).resolve().parent


def _safe_source(spec: dict, data: dict) -> None:
    if spec.get("classification") != "SYNTHETIC_REFERENCE" or data.get("engineering_approval") is not False:
        raise StructuralHold("Public site requires synthetic, unapproved source")
    if any(not str(v).startswith(("SYNTHETIC", "RESEARCH"))
           for v in spec["source_refs"].values()):
        raise StructuralHold("Public preview source ID is not explicitly synthetic")
    if any(not str(f["source_id"]).startswith("SYNTHETIC")
           for f in spec["floors"]):
        raise StructuralHold("Non-synthetic floor evidence blocked")
    if any(not str(w["source_id"]).startswith("SYNTHETIC")
           for w in spec["walls"]):
        raise StructuralHold("Non-synthetic wall evidence blocked")


def _link_existing_site(site: Path) -> int:
    count = 0
    for name in ("index.html", "report.html", "more.html"):
        file = site/name
        if not file.exists():
            continue
        old = file.read_text(encoding="utf-8")
        if 'href="r6p23.html"' in old:
            continue
        anchor = '<a href="report.html">Report</a>'
        if name == "report.html":
            anchor = '<a aria-current="page" href="report.html">Report</a>'
        if anchor not in old:
            raise StructuralHold("Existing Pages navigation changed: " + name)
        revised = old.replace(anchor,
                              anchor+'<a href="r6p23.html">R6.23 Solver</a>', 1)
        if name == "index.html":
            target = '<details class="section">'
            notice = (
                '<section class="section" id="r6p23-independent-solver">'
                '<div class="section-title"><div><span class="eyebrow">'
                'R6.23–R6.24 · INDEPENDENT OPENSEES</span>'
                '<h2>Multi-floor shell FE and mesh sensitivity</h2></div>'
                '<p>Source-labelled synthetic numerical research, not design approval</p></div>'
                '<div class="split"><div class="panel"><h3>Inspect solved FE</h3>'
                '<p>Floor-by-floor beam/shell forces, reactions, openings, and '
                'flexible/rigid diaphragms from the standalone OpenSees engine.</p>'
                '<a class="text-link" href="r6p23.html">Open the independent FE viewer →</a>'
                '</div><div class="panel"><h3>R6.24 refinement check</h3>'
                '<p>Identical material/gravity geometry compared across 4×4 and '
                '8×8 shell grids. Full design acceptance is explicitly on HOLD.</p>'
                '<a class="text-link" href="r6p23.html#convergence">'
                'Inspect numerical mesh sensitivity →</a>'
                '</div></div></section>\n'
            )
            if target not in revised:
                raise StructuralHold("Home site introduction not found for safe R6.23 link")
            revised = revised.replace(target, notice+target, 1)
        file.write_text(revised, encoding="utf-8")
        count += 1
    return count


def export(site: Path) -> dict:
    spec = reference_fixture()
    data = build(spec)
    _safe_source(spec, data)
    report = site/"reports"/"r6p23-reference"
    emit(data, report)
    report_manifest = verify(report)
    mesh = screen(spec, data)
    if mesh.get("full_asymptotic_mesh_convergence_proven") is not False:
        raise StructuralHold("One-step mesh comparison cannot certify full convergence")
    if mesh.get("engineering_approval") is not False:
        raise StructuralHold("Numerical screen must never be engineering approval")
    public = {
        "schema": SCHEMA,
        "case_id": spec["case_id"],
        "classification": spec["classification"],
        "source_SHA256": digest(spec),
        "source_geometry": {key: spec[key] for key in
                            ("x_grid_m", "y_grid_m", "levels_m")},
        "topology": {key: data["topology"][key] for key in (
            "shell_cells", "beams", "columns",
            "floor_areas_m2", "removed_opening_cells",
            "shell_count", "physical_node_count",
            "beam_segment_count", "column_segment_count"
        )},
        "source_ledger": data["source_ledger"],
        "cases": data["cases"],
        "solutions": data["solutions"],
        "mesh_screen": mesh,
        "project_source_preflight": preflight(),
        "report_manifest": report_manifest,
        "historical_F3_unsafe_retained": True,
        "engineering_approval": False,
    }
    folder = site/"data"
    folder.mkdir(parents=True, exist_ok=True)
    (folder/"r6p23-preview.json").write_text(
        json.dumps(public, sort_keys=True, separators=(",", ":"),
                   allow_nan=False)+"\n", encoding="utf-8"
    )
    for src, dst in (("viewer.html", "r6p23.html"),
                     ("viewer.css", "r6p23.css"),
                     ("viewer.js", "r6p23.js")):
        shutil.copyfile(HERE/src, site/dst)
    linked = _link_existing_site(site)
    sources = ("r6p23.html", "r6p23.css", "r6p23.js",
               "data/r6p23-preview.json")
    receipt = {
        "schema": "jp.structural.r6p24.public_site_receipt.v0.1",
        "source_SHA256": data["source_SHA256"],
        "mesh_screen_source_SHA256": mesh["input_source_sha256"],
        "legacy_report_and_showcase_preserved": True,
        "navigation_pages_linked": linked,
        "files_sha256": {
            name: hashlib.sha256((site/name).read_bytes()).hexdigest()
            for name in sources
        },
        "engineering_approval": False,
    }
    (folder/"r6p24-pages-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True)+"\n",
        encoding="utf-8")
    return receipt


def verify_export(site: Path) -> dict:
    receipt = json.loads((site/"data/r6p24-pages-receipt.json").read_text())
    if receipt.get("schema") != "jp.structural.r6p24.public_site_receipt.v0.1" or receipt.get("engineering_approval") is not False:
        raise StructuralHold("Invalid R6.23 public export or false approval")
    for name, sha in receipt["files_sha256"].items():
        if hashlib.sha256((site/name).read_bytes()).hexdigest() != sha:
            raise StructuralHold("R6.23 public file integrity failure: " + name)
    data = json.loads((site/"data/r6p23-preview.json").read_text())
    if data["source_SHA256"] != receipt["source_SHA256"]:
        raise StructuralHold("R6.23 data and report source fingerprints differ")
    mesh = data["mesh_screen"]
    if (mesh["input_source_sha256"] != receipt["mesh_screen_source_SHA256"]
            or mesh["full_asymptotic_mesh_convergence_proven"] is not False
            or data["historical_F3_unsafe_retained"] is not True):
        raise StructuralHold("R6.24 convergence or unsafe F3 state not preserved")
    verify(site/"reports/r6p23-reference")
    for name in ("index.html", "report.html", "more.html"):
        f = site/name
        if f.exists() and 'href="r6p23.html"' not in f.read_text():
            raise StructuralHold("Public R6.23 nav absent from " + name)
    return receipt


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--site-dir", type=Path, required=True)
    args=p.parse_args()
    a=export(args.site_dir)
    verify_export(args.site_dir)
    print(json.dumps({
        "R6P24_site_export_verified": True,
        "R6P23_source_SHA256": a["source_SHA256"],
        "navigation_pages_linked": a["navigation_pages_linked"],
        "engineering_approval": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
