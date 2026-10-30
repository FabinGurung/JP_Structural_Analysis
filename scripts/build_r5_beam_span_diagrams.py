#!/usr/bin/env python3
"""R5.3 real signed OpenSees full-span uniform-beam shear and moment diagrams.

The diagram mathematics integrates *actual* source-matched I/J FE end forces,
not an assumed simply supported beam or independent peak action envelope.
"""
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
from jp_structural.solvers.native.beam_span_diagrams import build_signed_span_diagrams
from scripts.build_r5_uniform_beam_case import DEFAULT,build as baseline_build
from scripts.build_structural_template_engine import CONTRACT,COVERAGE

SCHEMA="jp.structural.r5.source_signed_beam_span_SAR.v0.3"
PFX="r5-beam-span-diagrams"

def build(case=None):
    base=baseline_build(case)
    diagrams=build_signed_span_diagrams(
       model=base["source_signed_case_model"],
       solved=base["signed_FE"],
       raw_cases=base["source_signed_raw_cases"],
       combinations=base["source_signed_combinations"],
       sample_divisions=16)
    if diagrams["source_signed_input_sha256"]!=base["signed_FE_input_sha256"]:
        raise ValueError("beam diagram input does not match source solver input")
    if diagrams["source_signed_result_sha256"]!=base["signed_FE_result_sha256"]:
        raise ValueError("beam diagram source signed action digest mismatch")
    if not diagrams["all_J_cut_boundary_equilibrium_pass"]:
        raise ValueError("member cut equilibrium failed")
    requirements={x["id"]:x for x in json.loads(COVERAGE.read_text(encoding="utf8"))["requirements"]}
    contract=json.loads(CONTRACT.read_text(encoding="utf8"))
    scope={
      "M02":"SOURCE_GEOMETRY_LOAD_MASS_AUDIT_THROUGH_R5",
      "M04":"SIGNED_OPEN_SEES_IJ_TO_INSPAN_BEAM_VZ_MY_RECONSTRUCTION",
      "M08":"INSPAN_BEAM_MOMENT_EXTREMA_AVAILABLE_BUT_NOT_FULL_STEEL_DESIGN",
      "M09":"EXISTING_BOUNDED_SYNTHETIC_COLUMN_CHECK",
      "M10":"EXISTING_BOUNDED_SYNTHETIC_JOINT_CHECK",
      "S17":"SOURCE_DIGEST_J_END_FORCE_EQUILIBRIUM_AND_FIXED_BEAM_BENCHMARK",
    }
    chapters=[{"id":x["id"],"title":x["title"],"headings":x["headings"],
        "modules":[{"id":mid,"title":requirements[mid]["title"],
            "status":scope.get(mid,"NOT_CALCULATED_IN_THIS_REFERENCE")}
                   for mid in x["requirement_ids"]]} for x in contract["chapters"]]
    if len(chapters)!=7 or {x["id"] for c in chapters for x in c["modules"]}!=set(requirements):
        raise ValueError("seven chapter/18 module contract changed")
    source_case=base["case_id"]
    summary={
       "schema":SCHEMA,
       "case_id":source_case,
       "status":"SIGNED_STATIC_NATIVE_BEAM_UNIFORM_INSPAN_VZ_MY_PASS_NOT_DESIGN_APPROVED",
       "original_source_case":base["source_input_sha256"],
       "canonical_model_sha256":base["canonical_model_digest_sha256"],
       "signed_FE_input_sha256":base["signed_FE_input_sha256"],
       "signed_FE_result_sha256":base["signed_FE_result_sha256"],
       "source_total_gravity_kN":base["source_total_gravity_kN"],
       "source_seismic_weight_kN":base["source_seismic_weight_kN"],
       "native_element_uniform_resultants_kN":base["true_element_uniform_resultants_kN"],
       "raw_case_count":base["raw_case_count"],
       "signed_combination_count":base["signed_combination_count"],
       "beam_member_count":diagrams["source_member_count"],
       "in_span_case_beam_diagram_count":diagrams["diagram_record_count"],
       "all_IJ_end_force_and_moment_residuals_pass":True,
       "source_audited_signed_beam_diagrams":diagrams,
       "chapters":chapters,
       "previous_R5_UDL_reference_source_SHA256":base["signed_FE_result_sha256"],
       "engineering_approval":False,
       "original_building_certified":False,
       "original_F3_failure":"NOT SAFE IN ONE WAY SHEAR",
       "panel_area_forces_remain_nodal_equivalents":True,
       "shell_diaphragm_FE_completed":False,
       "gravity_selfweight_independently_verified":False,
       "code_load_combinations_verified":False,
       "full_member_detailing_verified":False,
       "limitations":[
          "Source model and loads are fully synthetic; original building not verified.",
          "Only canonical horizontal elastic beams with full-span uniform local Wz are processed.",
          "Local Vz/My cut reconstruction is linear-static equilibrium, not sampled stress/strain and not a nonlinear section analysis.",
          "Signed case combinations preserve contemporaneous load factors; not independently enveloped peaks.",
          "Area panel loads still enter as explicit nodal shares; no two-way shell/diaphragm FE.",
          "No complete RC flexure/steel/detailing/deflection checks for in-span extrema; software results are not construction approval.",
          "Original G+1.5 F3 unsafe source and 15 unaccepted source gates remain untouched.",
       ],
    }
    return summary

def esc(x):
    return html.escape(str(x),quote=True)

def svg_series(diagram,axis):
    points=diagram["samples"]
    v=[float(x[axis]) for x in points]
    low,high=min(v),max(v)
    if high-low<1e-9:low-=1;high+=1
    def px(x):return 50+390*x["x_over_L"]
    def py(y):return 128-90*(y-low)/(high-low)
    points_str=" ".join(f"{px(p):.2f},{py(p[axis]):.2f}" for p in points)
    zero_y=py(0)
    zeroline=f'<line x1="50" y1="{zero_y:.2f}" x2="440" y2="{zero_y:.2f}" stroke="#b6bec9" stroke-dasharray="4 5"/>' if 22<zero_y<140 else ""
    max_p=max(points,key=lambda x:x[axis]);min_p=min(points,key=lambda x:x[axis])
    return (f'<svg role="img" aria-label="{esc(axis)} across local member span" viewBox="0 0 470 160" width="100%" xmlns="http://www.w3.org/2000/svg">'
      f'<line x1="50" y1="20" x2="50" y2="140" stroke="#94a4b7"/>'
      f'<line x1="50" y1="140" x2="440" y2="140" stroke="#94a4b7"/>{zeroline}'
      f'<polyline fill="none" stroke="#3c5a85" stroke-width="2.3" points="{points_str}"/>'
      f'<circle cx="{px(max_p):.2f}" cy="{py(max_p[axis]):.2f}" r="3.5" fill="#1e8a7a"/>'
      f'<circle cx="{px(min_p):.2f}" cy="{py(min_p[axis]):.2f}" r="3.5" fill="#af513e"/>'
      f'<text x="50" y="14" font-size="11" fill="#44566d">{esc(axis)}</text>'
      f'<text x="50" y="154" font-size="10">I / 0 m</text>'
      f'<text x="400" y="154" font-size="10">J / L</text>'
      f'<text x="442" y="36" font-size="10" text-anchor="end">max {max_p[axis]:.3f}</text>'
      f'<text x="442" y="48" font-size="10" text-anchor="end">min {min_p[axis]:.3f}</text></svg>')

def render_html(r):
    diagrams=r["source_audited_signed_beam_diagrams"]["diagrams"]
    nav="".join(f'<a href="#c-{x["id"]}">{x["id"]} {esc(x["title"])}</a>' for x in r["chapters"])
    parts=[]
    for c in r["chapters"]:
        rows="".join(f'<tr><td>{esc(x["id"])}</td><td>{esc(x["title"])}</td><td>{esc(x["status"])}</td></tr>' for x in c["modules"])
        specific=""
        if c["id"]=="05":
            charts=[]
            for item in diagrams:
                d=item["diagram"]
                top=d["critical_moment_max"]
                bot=d["critical_moment_min"]
                charts.append(f'<details><summary>{esc(item["kind"])} / {esc(item["case_id"])} / {esc(item["member_id"])}'
                    f' — w={item["downward_uniform_signed_kN_m"]:.3f} kN/m,'
                    f' Mmax={top["My_sagging_positive_kNm"]:.3f} kNm'
                    f'</summary><div class="charts"><div>{svg_series(d,"Vz_section_kN")}</div>'
                    f'<div>{svg_series(d,"My_sagging_positive_kNm")}</div></div>'
                    f'<p>Stationary section x={esc(d["zero_shear_inside_member_x_m"])} m; '
                    f'Mmin={bot["My_sagging_positive_kNm"]:.3f} kNm. '
                    f'J cut residual: V={d["end_boundary_residuals"]["Vz_kN"]:.8g} kN, '
                    f'M={d["end_boundary_residuals"]["My_kNm"]:.8g} kNm.</p></details>')
            specific="<p>Real 3D OpenSees resisting I/J forces integrated as section Vz(x)=Vz_I - w x and My(x)=My_I+Vz_I x-w x²/2. Every J boundary independently matches the source solver.</p>"+"".join(charts)
        parts.append(f'<section id="c-{esc(c["id"])}"><h2>Chapter {esc(c["id"])} — {esc(c["title"])}</h2>'
             f'<div class="scroll"><table><tr><th>Module</th><th>Requirement</th><th>This run</th></tr>{rows}</table></div>{specific}</section>')
    warnings="".join("<li>"+esc(x)+"</li>" for x in r["limitations"])
    return ("""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>JP SAR — R5 beam span V/M diagrams</title><style>
body{font:14px/1.5 system-ui;background:#f5f7fb;color:#26364c;max-width:1120px;margin:auto;padding:18px}
header,section{background:#fff;border:1px solid #dbe3ec;border-radius:10px;padding:18px;margin:14px 0}
nav{display:flex;flex-wrap:wrap;gap:8px}nav a{padding:6px;border:1px solid #aabaca;border-radius:5px}
.warn{background:#fff0eb;border-left:4px solid #af4c41;padding:10px}
.scroll{overflow:auto}table{border-collapse:collapse;min-width:540px;width:100%}
td,th{border:1px solid #d0d9e4;text-align:left;font-size:12px;padding:6px}
th{background:#edf2f7}details{border:1px solid #d1dbe6;border-radius:8px;padding:10px;margin:10px 0}
summary{cursor:pointer;font-weight:600}.charts{display:grid;grid-template-columns:1fr 1fr;gap:9px}
@media(max-width:700px){.charts{grid-template-columns:1fr}}@media print{nav{display:none}body{background:#fff}}
</style></head><body>""" +
      f'<header><small>JP STRUCTURAL · R5.3 · SIGNED LINEAR ELASTIC REFERENCE ONLY</small>'
      f'<h1>In-span beam shear and moment diagrams</h1>'
      f'<p class="warn"><strong>NOT ENGINEERING APPROVED, NOT FOR PERMIT OR CONSTRUCTION.</strong> '
      f'Synthetic four-column source case, not the original building. F3 source remains NOT SAFE IN ONE WAY SHEAR.</p>'
      f'<p>{r["beam_member_count"]} beams; {r["in_span_case_beam_diagram_count"]} source-matched case/member curves '
      f'({r["raw_case_count"]} raw cases + {r["signed_combination_count"]} concurrent combinations). '
      f'All J-end cut equilibrium checks passed.</p>'
      f'<p><a href="{PFX}.json">Full JSON</a> · <a href="{PFX}-stations.csv">Sampled stations CSV</a> · '
      f'<a href="{PFX}-extrema.csv">Exact bending extrema CSV</a> · '
      f'<a href="{PFX}-manifest.json">SHA-256 manifest</a></p><nav>{nav}</nav></header>'
      +"".join(parts)+f'<section><h2>Annex — evidence and remaining debt</h2><ul>{warnings}</ul>'
      f'<p>Original F3: <strong>{esc(r["original_F3_failure"])}</strong>. '
      f'Physical project verified: NO. Professional permit certification: NO.</p></section></body></html>')

def csv_text(rows,cols):
    out=io.StringIO()
    w=csv.writer(out,lineterminator="\n");w.writerow(cols)
    for r in rows:w.writerow([r.get(k) for k in cols])
    return out.getvalue()

def emit(source_file:Path,output_dir:Path):
    spec=json.loads(source_file.read_text(encoding="utf8"))
    d=build(spec)
    output_dir.mkdir(parents=True,exist_ok=True)
    rows=[];ext=[]
    for record in d["source_audited_signed_beam_diagrams"]["diagrams"]:
        diagram=record["diagram"]
        group={k:record[k] for k in ("kind","case_id","member_id")}
        for point in diagram["samples"]:
            rows.append({**group,**point,"w_downward_signed_kN_m":diagram["w_downward_signed_kN_m"]})
        ext.append({**group,"stationary_x_m":diagram["zero_shear_inside_member_x_m"],
           "maximum_My_kNm":diagram["critical_moment_max"]["My_sagging_positive_kNm"],
           "maximum_My_x_m":diagram["critical_moment_max"]["x_m"],
           "minimum_My_kNm":diagram["critical_moment_min"]["My_sagging_positive_kNm"],
           "minimum_My_x_m":diagram["critical_moment_min"]["x_m"]})
    outputs={
        PFX+".json":json.dumps(d,sort_keys=True,allow_nan=False,indent=2)+"\n",
        PFX+".html":render_html(d),
        PFX+"-stations.csv":csv_text(rows,["kind","case_id","member_id","x_m","x_over_L","Vz_section_kN","My_sagging_positive_kNm","w_downward_signed_kN_m"]),
        PFX+"-extrema.csv":csv_text(ext,["kind","case_id","member_id","stationary_x_m","maximum_My_kNm","maximum_My_x_m","minimum_My_kNm","minimum_My_x_m"]),
    }
    for k,v in outputs.items():(output_dir/k).write_text(v,encoding="utf8")
    manifest={"schema":"jp.structural.r5.span_diagram_manifest.v0.3",
         "source_SHA256":d["original_source_case"],
         "signed_FE_SHA256":d["signed_FE_result_sha256"],
         "files":{k:hashlib.sha256(v.encode("utf8")).hexdigest() for k,v in outputs.items()},
         "engineering_approval":False}
    (output_dir/(PFX+"-manifest.json")).write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n",encoding="utf8")
    return d

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",type=Path,default=DEFAULT)
    parser.add_argument("--output-dir",type=Path,required=True)
    a=parser.parse_args()
    r=emit(a.input,a.output_dir)
    print("R5_BEAM_SPAN_SOURCE_SIGNED",r["in_span_case_beam_diagram_count"],
          "DIAGRAMS_ALL_END_EQUILIBRIUM_PASS_NO_APPROVAL")
if __name__=="__main__":main()
