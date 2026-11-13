"""R6.23 command-line independently solved multistorey shell/diaphragm report.

Usage: python -m r6p23.runner --reference --output-dir build/r6p23
For actual private source JSON, keep BOTH input/output outside public checkout.
"""
from __future__ import annotations

import argparse
import csv
import html
import hashlib
import io
import json
from pathlib import Path

from r6p23.engine import build, digest, SCHEMA, StructuralHold

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "r6p23-multifloor-shell"


def _inside(path: Path, parent: Path) -> bool:
    a, b = path.resolve(), parent.resolve()
    return a == b or b in a.parents


def reference_fixture() -> dict:
    """Fully synthetic two-floor, two-way shell with an internal opening."""
    floors = [
        {
            "level_index": 1, "source_id": "SYNTHETIC_F1_TWO_WAY_SLAB",
            "thickness_m": .12, "finish_kPa": 1.5, "imposed_kPa": 2.0,
            "opening_cells": [],
            "interior_beam_y_grid_indices": [],
            "interior_beam_x_grid_indices": []
        },
        {
            "level_index": 2, "source_id": "SYNTHETIC_F2_OPENING_SLAB",
            "thickness_m": .12, "finish_kPa": 1.5, "imposed_kPa": 2.0,
            "opening_cells": [[1, 1]],
            "interior_beam_y_grid_indices": [],
            "interior_beam_x_grid_indices": []
        }
    ]
    return {
        "schema": SCHEMA, "case_id": "R6P23_SYNTHETIC_2F_FRAME_SHELL",
        "classification": "SYNTHETIC_REFERENCE",
        "units": {"force": "kN", "length": "m",
                  "moment": "kN.m", "pressure": "kPa"},
        "source_refs": {
            "geometry": "SYNTHETIC_4x4_GRID_TWO_FLOORS",
            "material": "SYNTHETIC_25GPA_25KNM3_RC",
            "support": "SYNTHETIC_FOUR_FIXED_CORNER_BASES",
            "loads": "SYNTHETIC_DEAD_FINISH_IMPOSED_WALL_HX",
            "diaphragm": "SYNTHETIC_FLEXIBLE_VS_RIGID_MPC_TEST",
            "code": "RESEARCH_SOURCE_ONLY_NO_COMPLETE_NBC_CHECKS"
        },
        "x_grid_m": [0., 1., 2., 3., 4.],
        "y_grid_m": [0., 1., 2., 3., 4.],
        "levels_m": [0., 3., 6., 9.],
        "concrete": {
            "E_kN_m2": 25_000_000, "poisson": 0.2,
            "unit_weight_kN_m3": 25.0,
            "source_id": "SYNTHETIC_CONCRETE_25KNM3_25GPA"
        },
        "beam": {"width_m": .30, "depth_m": .45,
                 "source_id": "SYNTHETIC_BEAM_300x450MM"},
        "column": {"width_m": .4, "depth_m": .4,
                   "source_id": "SYNTHETIC_COLUMN_400x400MM"},
        "floors": floors,
        "walls": [{
            "level_index": 1, "edge": "Y_MIN",
            "height_m": 2.5, "thickness_m": .15,
            "unit_weight_kN_m3": 18.0, "opening_area_m2": 1.0,
            "source_id": "SYNTHETIC_WALL_NET_OPENING_1M2"
        }],
        "lateral_cases": [{
            "case_id": "HX", "source_id": "SYNTHETIC_HORIZONTAL_LATERAL_AT_F2",
            "level_index": 2, "grid_i": 4, "grid_j": 4,
            "Fx_kN": 10.0, "Fy_kN": 0.0, "Fz_kN": 0.0,
            "Mx_kNm": 0.0, "My_kNm": 0.0, "Mz_kNm": 0.0
        }],
        "combinations": [
            {"id": "U_PLUS", "source_id": "SYNTHETIC_COMBO_DL_LL_HX_PLUS",
             "factors": {"DL": 1.2, "LL": 1.5, "HX": 1.}},
            {"id": "U_MINUS", "source_id": "SYNTHETIC_COMBO_DL_LL_HX_MINUS",
             "factors": {"DL": 1.2, "LL": 1.5, "HX": -1.}}
        ],
    }


def _html_report(data: dict) -> str:
    e = lambda s: html.escape(str(s), quote=True)
    lines = []
    for floor, area in data["topology"]["floor_areas_m2"].items():
        holes = data["topology"]["removed_opening_cells"][floor]
        lines.append(f"<tr><td>{e(floor)}</td><td>{area:.3f}</td>"
                     f"<td>{e(holes)}</td></tr>")
    modes = []
    for mode, cases in data["solutions"].items():
        for case, row in cases.items():
            modes.append("<tr><td>"+e(mode)+"</td><td>"+e(case)+"</td>"
                         f"<td>{row['max_equilibrium_residual']:.8g}</td>"
                         f"<td>{row['gravity_resultants']['Fz_kN']:.4f}</td>"
                         f"<td>{row['shell_to_beam_directional_vz_abs_sum']['X']:.5g}</td>"
                         f"<td>{row['shell_to_beam_directional_vz_abs_sum']['Y']:.5g}</td></tr>")
    l = data["source_ledger"]["gravity_totals_kN"]
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>R6.23 independent 3D ShellMITC4 research report</title>
<style>body{{font:15px/1.55 system-ui,sans-serif;max-width:1100px;padding:24px;margin:auto;color:#243144}}
section{{padding:16px;margin:12px 0;border:1px solid #cbd5e1;border-radius:10px}}
table{{border-collapse:collapse;width:100%;min-width:560px}}th,td{{border:1px solid #cbd5e1;padding:7px;text-align:left;font-size:12px}}
th{{background:#f1f5f9}}.scroll{{overflow-x:auto}}.hold{{background:#fff2ef;border-left:5px solid #b3261e;padding:12px}}
@media print{{section{{break-inside:avoid}}}}</style></head><body>
<h1>R6.23 · Independent multi-floor shell/frame FEM</h1>
<p>{e(data["case_id"])} · {e(data["classification"])} · real OpenSeesPy ShellMITC4</p>
<p class="hold"><b>ENGINEERING HOLD:</b> rectilinear elastic research model, code load factors
source-assumed; actual project geometry, soil, slab/column punching, seismic/wind,
nonlinear detailing and historical F3 one-way shear NOT approved or cleared.</p>
<section><h2>Source geometry and actual openings</h2>
<p>{data["topology"]["physical_node_count"]} physical model nodes,
{data["topology"]["shell_count"]} shells,
{data["topology"]["beam_segment_count"]} beam segments,
{data["topology"]["column_segment_count"]} column segments.</p>
<div class="scroll"><table><tr><th>Floor</th><th>Shell area m²</th><th>Removed cells</th></tr>
{''.join(lines)}</table></div></section>
<section><h2>Independent source load totals</h2>
<p>Slab+finishes {l["SHELL_DL"]:.3f} kN; frame/wall {l["FRAME_DL"]:.3f} kN;
<b>Total dead load {l["DL"]:.3f} kN</b>; imposed {l["LL"]:.3f} kN.</p></section>
<section><h2>OpenSees numerical equilibrium and two-way beam reactions</h2>
<div class="scroll"><table><tr><th>Diaphragm mode</th><th>Case</th><th>Max residual</th>
<th>Applied gravity kN</th><th>X-beam |Vz| kN</th><th>Y-beam |Vz| kN</th></tr>
{''.join(modes)}</table></div></section>
<section><h2>Source and analysis limitations</h2>
<p>Signed case combinations and 3D beam-end actions are available in
<a href="{PREFIX}.json">the complete calculation JSON</a>. Every source/result file
is SHA-256 verified by the <a href="{PREFIX}-manifest.json">manifest</a>.</p>
<p>Shell bending is computed by OpenSees rather than a prescribed tributary split.
Hole cells have no shell stiffness or pressure. Flexible and rigid diaphragms use
different in-plane constraints, not different gravity inputs.</p>
<p>No professional design, permit, or construction authorization. No ETABS parity is required.</p>
</section></body></html>"""


def emit(data: dict, folder: Path) -> dict:
    if data.get("engineering_approval") is not False:
        raise StructuralHold("No export of presumed approved design")
    folder.mkdir(parents=True, exist_ok=True)
    keyfields = ("mode", "case", "floor", "node", "Ux_m", "Uy_m", "Uz_m")
    handle = io.StringIO()
    writer = csv.DictWriter(handle, fieldnames=keyfields, lineterminator="\n")
    writer.writeheader()
    for mode, cases in data["solutions"].items():
        for case, result in cases.items():
            for fl, nodes in result["node_displacements"].items():
                for nid, vec in sorted(nodes.items()):
                    writer.writerow(dict(zip(keyfields, (mode, case, fl, nid,
                                                         vec[0], vec[1], vec[2]))))
    contents = {
        PREFIX+".json": json.dumps(data, indent=2, sort_keys=True,
                                    allow_nan=False)+"\n",
        PREFIX+".html": _html_report(data),
        PREFIX+"-displacements.csv": handle.getvalue()
    }
    for name, value in contents.items():
        (folder/name).write_text(value, encoding="utf-8")
    manifest = {
        "schema": "jp.structural.r6p23.artifact_manifest.v0.1",
        "source_SHA256": data["source_SHA256"],
        "files": {name: hashlib.sha256(value.encode()).hexdigest()
                  for name, value in contents.items()},
        "engineering_approval": False
    }
    (folder/(PREFIX+"-manifest.json")).write_text(
        json.dumps(manifest, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    return manifest


def verify(folder: Path) -> dict:
    manifest = json.loads((folder/(PREFIX+"-manifest.json")).read_text())
    if manifest.get("schema") != "jp.structural.r6p23.artifact_manifest.v0.1":
        raise StructuralHold("Invalid R6.23 source/report manifest")
    if manifest.get("engineering_approval") is not False:
        raise StructuralHold("False design approval")
    if set(manifest.get("files", {})) != {PREFIX+".json", PREFIX+".html",
                                            PREFIX+"-displacements.csv"}:
        raise StructuralHold("Artifact manifest incomplete")
    for name, expected in manifest["files"].items():
        got = hashlib.sha256((folder/name).read_bytes()).hexdigest()
        if got != expected:
            raise StructuralHold("Tampered report artifact: "+name)
    data = json.loads((folder/(PREFIX+".json")).read_text())
    if data["source_SHA256"] != manifest["source_SHA256"] or data["engineering_approval"] is not False:
        raise StructuralHold("Source fingerprint/design status mismatch")
    return manifest


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--reference", action="store_true")
    g.add_argument("--input", type=Path, help="Private canonical model JSON outside repo")
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    if args.input:
        if _inside(args.input, ROOT) or _inside(args.output_dir, ROOT):
            raise StructuralHold("Custom real-source input/output must be outside public repository")
        spec = json.loads(args.input.read_text())
    else:
        spec = reference_fixture()
    data = build(spec)
    emit(data, args.output_dir)
    verify(args.output_dir)
    print(json.dumps({
        "case_id": data["case_id"],
        "source_sha256": data["source_SHA256"],
        "shell_elements": data["topology"]["shell_count"],
        "beam_segments": data["topology"]["beam_segment_count"],
        "floor_area_m2": data["topology"]["floor_areas_m2"],
        "dead_kN": data["source_ledger"]["gravity_totals_kN"]["DL"],
        "live_kN": data["source_ledger"]["gravity_totals_kN"]["LL"],
        "engineering_approval": False, "report_generated": True
    }, sort_keys=True))


if __name__ == "__main__":
    main()
