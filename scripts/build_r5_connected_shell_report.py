#!/usr/bin/env python3
"""R5.5 report packaging from actual connected ShellMITC4 source mesh models."""
from __future__ import annotations
import argparse
import csv
import hashlib
import html
import io
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_r5_connected_shell_frame import build,PFX,SCHEMA

def _csv(rows,cols):
    o=io.StringIO();w=csv.writer(o,lineterminator="\n");w.writerow(cols)
    for r in rows:w.writerow([r.get(k) for k in cols])
    return o.getvalue()

def chart(r):
    values=[(int(k),v*1000) for k,v in r["gravity_mesh_center_Uz_m"].items()]
    peak=max(abs(v) for _,v in values)
    width=410;height=150
    polys=" ".join(f"{58+(i*165):.1f},{70+(v/peak)*55:.1f}" for i,(n,v) in enumerate(values))
    points="".join(f'<circle cx="{58+i*165:.1f}" cy="{70+(v/peak)*55:.1f}" r="4" fill="#29465a"/>'
            f'<text x="{58+i*165:.1f}" y="144" text-anchor="middle" font-size="12">{n}x{n}</text>'
            for i,(n,v) in enumerate(values))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Connected shell center displacement by 2x2, 4x4 and 8x8 grid"><line x1="32" y1="70" x2="395" y2="70" stroke="#d0d7e0"/><polyline points="{polys}" fill="none" stroke="#29465a" stroke-width="2.5"/>{points}<text x="20" y="14" font-size="12" fill="#29465a">Centre Uz (negative = downward)</text></svg>'

def render_html(r):
    e=lambda x:html.escape(str(x),quote=True)
    nav=" ".join(f'<a href="#chapter-{c["id"]}">{c["id"]} {e(c["title"])}</a>' for c in r["chapters"])
    chapters=[]
    for c in r["chapters"]:
        rows="".join(f'<tr><td>{e(m["id"])}</td><td>{e(m["title"])}</td><td>{e(m["status"])}</td></tr>' for m in c["modules"])
        extra=""
        if c["id"]=="04":
            extra=f'<p>Shared shell-edge and beam vertices are identical six-DOF OpenSees node tags, and the four corners connect to frame columns. Connected ShellMITC4 thickness {r["shell_thickness_m"]:.3f} m, assumed E {r["shell_material_E_kN_m2"]:.0f} kN/m², Poisson {r["shell_poisson"]:.3f}. Meshes: 2×2, 4×4, 8×8.</p>'
        if c["id"]=="05":
            extra=f'<h3>Mesh refinement: center slab vertical displacement</h3><div class="figure">{chart(r)}</div><p>Measured gravity case center Uz (m): '+", ".join(f'{e(k)}×{e(k)}: {v:.9g}' for k,v in r["gravity_mesh_center_Uz_m"].items())+f'. Each mesh case passed all six global force/moment reaction balances. 3 raw cases × 3 meshes = 9 FE analyses. Signed load combinations are not yet evaluated on this connected model.</p>'
        chapters.append(f'<section id="chapter-{e(c["id"])}"><h2>Chapter {e(c["id"])} — {e(c["title"])}</h2><div class="scroll"><table><tr><th>Module</th><th>Requirement</th><th>R5.5 case status</th></tr>{rows}</table></div>{extra}</section>')
    debt="".join("<li>"+e(x)+"</li>" for x in r["open_debt"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>R5.5 Connected shell-frame source QA</title><style>body{{font:14px/1.55 system-ui;color:#26374d;background:#f6f8fc;max-width:1110px;margin:auto;padding:16px}}header,section{{padding:18px;background:#fff;border:1px solid #d6dfea;margin:16px 0;border-radius:10px}}nav a{{display:inline-block;padding:6px;border:1px solid #b2c3d4;border-radius:5px;margin:3px}}.hold{{padding:12px;border-left:5px solid #b55143;background:#fff1eb}}h1{{font-size:25px}}h2{{font-size:20px}}.scroll{{overflow:auto}}table{{width:100%;min-width:560px;border-collapse:collapse}}td,th{{font-size:12px;padding:7px;text-align:left;border:1px solid #d7dfe7}}th{{background:#eff3f8}}.figure{{max-width:640px}}.figure svg{{width:100%;height:auto}}@media print{{body{{background:white}}nav{{display:none}}}}</style></head><body><header>
<small>JP STRUCTURAL / R5.5 / BOUNDED SYNTHETIC CONNECTED SHELLMITC4</small>
<h1>Connected slab shell → beam → column → support</h1>
<p class="hold"><strong>NOT ENGINEER APPROVED · NOT FOR CONSTRUCTION OR PERMITS.</strong> This is a synthetic rectangle with assumed elastic material/thickness. It has no verified real-building geometry or signed seismic code combinations. Original F3 is NOT SAFE IN ONE WAY SHEAR.</p>
<p>{r["source_total_gravity_kN"]:.2f} kN total source gravity (dead and live); source-assumed seismic eligible weight {r["source_seismic_weight_kN"]:.2f} kN. Connected 3D ShellMITC4, 2×2/4×4/8×8, three raw cases each.</p>
<p><a href="{PFX}.json">Numerical model and full signed I/J actions</a> · <a href="{PFX}-mesh.csv">Mesh/results CSV</a> · <a href="{PFX}-member-ends.csv">Member action CSV</a> · <a href="{PFX}-manifest.json">SHA-256 checksums</a></p>
<nav>{nav}</nav></header>{''.join(chapters)}
<section><h2>Annex — explicit debt / physical source holds</h2><ul>{debt}</ul>
<p>Original source F3 <strong>NOT SAFE IN ONE WAY SHEAR</strong>. Physical evidence 0/15 accepted. Shell load is conservatively applied as four-node quad equivalent forces, not fictitious nodal tributary-to-frame loading; the shell is attached to frame beams at shared vertices.</p></section></body></html>"""

def emit(folder:Path):
    r=build();folder.mkdir(parents=True,exist_ok=True)
    summary=[]
    ends=[]
    for x in r["mesh_case_results"]:
        summary.append({"mesh":x["mesh_divisions"],"case_id":x["case_id"],
                        "shell_nodes":x["shell_nodes"],"shell_elements":x["shell_elements"],
                        "boundary_beam_segments":x["connected_boundary_beam_segments"],
                        "applied_Fx_kN":x["applied_force_kN"][0],
                        "applied_Fz_kN":x["applied_force_kN"][2],
                        "reaction_Fz_kN":x["support_reaction_total_Fz_kN"],
                        "center_Uz_m":x["center_shell_Uz_m"],
                        "max_force_moment_residual":max(abs(v) for v in x["global_force_moment_residual"].values())})
        for member,segments in sorted(x["signed_member_end_actions"].items()):
            for segment in segments:
                for end in ("I","J"):
                    ends.append({"mesh":x["mesh_divisions"],"case_id":x["case_id"],"member_id":member,
                                 "element_tag":segment["element_tag"],"end":end,**segment[end]})
    data={
      PFX+".json":json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+"\n",
      PFX+".html":render_html(r),
      PFX+"-mesh.csv":_csv(summary,["mesh","case_id","shell_nodes","shell_elements","boundary_beam_segments","applied_Fx_kN","applied_Fz_kN","reaction_Fz_kN","center_Uz_m","max_force_moment_residual"]),
      PFX+"-member-ends.csv":_csv(ends,["mesh","case_id","member_id","element_tag","end","N","Vy","Vz","T","My","Mz"])}
    for k,v in data.items():(folder/k).write_text(v,encoding="utf8")
    manifest={"schema":"jp.structural.r5.shell_report_manifest.v0.1","source_input_SHA256":r["source_input_SHA256"],
              "files":{k:hashlib.sha256(v.encode("utf8")).hexdigest() for k,v in data.items()},
              "engineering_approval":False}
    (folder/(PFX+"-manifest.json")).write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf8")
    return r

def main():
    a=argparse.ArgumentParser();a.add_argument("--output-dir",type=Path,required=True)
    opts=a.parse_args();r=emit(opts.output_dir)
    print("R5P5_SHELLMITC4_9_CASES_3_MESHES_128KN_SOURCE_111P2_SEISMIC_MASS_NOT_APPROVED",
          r["convergence_abs_displacement_differences_m"])
if __name__=="__main__":main()
