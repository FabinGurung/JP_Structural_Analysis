#!/usr/bin/env python3
"""Produce independent 7-chapter SAR evidence from real synthetic OpenSees signed actions.

The FE case is deliberately NOT joined to the separate 3-level template case.
Concurrent signed OpenSees local I/J actions feed the existing M08/M09/M10
bounded check bridge; modal/ULS source/engineering approvals never invented.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import html
import io
import json
import math
from pathlib import Path
import sys

# Executable as `python scripts/...py` as well as imported by pytest.
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from jp_structural.solvers.opensees.synthetic_d2_example import case_fixture
from scripts.build_d2_signed_frame_case import build as d2_build
from scripts.build_structural_template_engine import CONTRACT, COVERAGE

SCHEMA="jp.structural.template.signed_FE_design_handoff.v0.3"
OUTPUT_PREFIX="template-signed-fe-handoff"

class SignedReportError(ValueError):
    pass

def digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")).hexdigest()

def _number(x):
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x):
        raise SignedReportError("nonfinite signed action")
    return float(x)

def _member_rows(solved):
    rows=[]
    components=solved["member_end_order"]
    if components!=["N","Vy","Vz","T","My","Mz"]:
        raise SignedReportError("unsupported signed local action component order")
    groups=[("RAW",row["case_id"],row["local_end_resisting_actions"])
            for row in solved["raw_cases"]]
    groups += [("COMBINATION",row["combination_id"],row["local_end_resisting_actions"])
               for row in solved["combinations"]]
    for kind,case_id,by_member in groups:
        for mid in sorted(by_member):
            for end in ("I","J"):
                a=by_member[mid][end]
                if set(a)!=set(components):raise SignedReportError("incomplete end force vector")
                rows.append({"kind":kind,"case_id":case_id,"member_id":mid,"end":end,
                    **{x:_number(a[x]) for x in components}})
    return rows

def build():
    contract=json.loads(CONTRACT.read_text(encoding="utf8"))
    coverage=json.loads(COVERAGE.read_text(encoding="utf8"))
    model,cases,combinations,beams,columns,joints=case_fixture()
    payload=d2_build()  # Calls actual OpenSees solves and the SAME-MEMBER RC bridge.
    signed=payload["signed_fe_actions"]
    checked=payload["design_checks"]
    if (signed["engineering_approval"] is not False or
        checked["engineering_approval"] is not False or
        payload["engineering_approval"] is not False):
        raise SignedReportError("upstream physical approval must be false")
    if (payload["schema"]!="jp.structural.d2_m08_m09_m10_synthetic_demo.v0.1" or
        signed["schema"]!="jp.structural.signed_design_actions.v0.1" or
        checked["schema"]!="jp.structural.m08_m09_m10_design_bridge.v0.1"):
        raise SignedReportError("source contract changed")
    if checked["source_action_digest"]!=signed["input_bundle_sha256"]:
        raise SignedReportError("design bridge references a different signed source input")
    if digest({"model":model,"cases":cases,"combinations":combinations})!=signed["input_bundle_sha256"]:
        raise SignedReportError("signed model/case/combination inputs differ from fixture")
    if len(signed["raw_cases"])!=len(cases) or len(signed["combinations"])!=len(combinations):
        raise SignedReportError("FE input/response case counts differ")
    if any(row["global_equilibrium_pass"] is not True for row in signed["raw_cases"]):
        raise SignedReportError("static global six-component equilibrium not verified")
    bound=max(abs(x) for row in signed["raw_cases"]
        for x in row["global_force_moment_equilibrium_residual"].values())
    if bound>=1e-5:raise SignedReportError("global equilibrium tolerance exceeded")
    if len(contract["chapters"])!=7:raise SignedReportError("TOC contract mismatch")
    existing={x["id"]:x for x in coverage["requirements"]}
    if set(existing)!={f"M{i:02d}" for i in range(1,17)}|{"S17","S18"}:
        raise SignedReportError("18-module coverage changed")
    rows=_member_rows(signed)
    member_ids={x["id"] for x in model["frame_members"]}
    assert len(member_ids)>0
    if len(rows)!=(len(cases)+len(combinations))*len(member_ids)*2:
        raise SignedReportError("incomplete I/J member action coverage")
    b=checked["beam_design"];c=checked["column_design"];j=checked["joint_design"]
    if not(b and c and j):raise SignedReportError("M08/09/10 needs all three design classes")
    for x in b:
        if x["check"]["engineering_approval"] is not False:
            raise SignedReportError("M08 mislabelled as approved")
        if not set(v["combination_id"] for v in x["signed_combination_end_shear"])<=set(
            row["combination_id"] for row in signed["combinations"]):
            raise SignedReportError("M08 signed case/source mismatch")
    for x in c:
        if not x["scenarios"] or any(v["check"]["engineering_approval"] is not False for v in x["scenarios"]):
            raise SignedReportError("M09 source/approval mismatch")
        if not all(v["combination_id"] in {s["combination_id"] for s in signed["combinations"]} for v in x["scenarios"]):
            raise SignedReportError("M09 unsolved combination referenced")
    for x in j:
        if any(v["check"]["engineering_approval"] is not False for v in x["scenarios"]):
            raise SignedReportError("M10 unsafe approval")
    implemented={"M04":"SIGNED_STATIC_ELASTIC_FE_WITH_GLOBAL_EQUILIBRIUM",
       "M08":"SIGNED_END_TO_NBC_CAPACITY_SHEAR_WITH_ASSUMED_STRENGTHS",
       "M09":"SIGNED_END_TO_BIAXIAL_SECTION_WITH_SYNTHETIC_BARS",
       "M10":"SIGNED_END_TO_JOINT_SHEAR_WITH_UNRESOLVED_DIRECTION"}
    chapters=[{"chapter":ch["id"],"title":ch["title"],
       "headings":ch["headings"],"requirements":[{
           "id":mid,"title":existing[mid]["title"],
           "registry_status":existing[mid]["status"],
           "run_status":implemented.get(mid,"NOT_EVALUATED_BY_THIS_SIGNED_FE_CASE")}
           for mid in ch["requirement_ids"]]} for ch in contract["chapters"]]
    result={
       "schema":SCHEMA,"case_id":"SYNTHETIC-D2-FRAME-001",
       "case_class":"SYNTHETIC_STATIC_FE_REUSABLE_REPORT_PROOF",
       "independent_of_three_level_and_F3_cases":True,
       "source":"scripts/build_d2_signed_frame_case.py / synthetic_d2_example.case_fixture",
       "source_scope":"2D-in-3D synthetic four-member elastic frame with six DOF/node",
       "model_input_sha256":signed["model_digest_sha256"],
       "source_bundle_sha256":signed["input_bundle_sha256"],
       "signed_result_sha256":signed["results_digest_sha256"],
       "source_payload_sha256":payload["payload_sha256"],
       "input_provenance":{"model":model,"raw_cases":cases,"signed_combinations":combinations,
             "beam_design_bindings":beams,"column_design_bindings":columns,
             "joint_design_bindings":joints},
       "code_sources":[{"id":"NBC105_2025","url":"https://ebps.kathmandu.gov.np/UploadFiles/NBC_105_2025_Sesmic_Design.pdf"},
          {"id":"IS456_2000","url":"https://wriddodoti.gov.np/uploads/blog/20230331071217_IS-456-with-all-ammendments.pdf"}],
       "chapters":chapters,"registered_requirement_count":len(existing),
       "implemented_in_this_FE_case":sorted(implemented),
       "case_count":len(signed["raw_cases"]),
       "combination_count":len(signed["combinations"]),
       "member_count":len(member_ids),
       "member_end_action_rows":len(rows),
       "global_six_component_balance_max_kN_or_kNm":bound,
       "case_ids":[x["case_id"] for x in signed["raw_cases"]],
       "combination_ids":[x["combination_id"] for x in signed["combinations"]],
       "signed_member_end_records":rows,
       "signed_analysis":signed,
       "member_design_checks":checked,
       "source_flags":["SYNTHETIC_ONLY","CONCURRENT_SIGNED_STATIC_CASES_ONLY",
           "NO_MODAL_OR_MRSM_SIGNED_CASE_RECONSTRUCTION",
           "NO_REAL_PROJECT_SECTION_OR_SOIL_PROVENANCE",
           "M08_M09_M10_PARTIAL_DESIGN_NOT_DETAILING_COMPLETE"],
       "original_F3_verdict_changed":False,
       "original_F3_test_not_included":True,
       "all_18_modules_complete":False,
       "submission_items":[{"id":f"SUB-{i:02d}","accepted":False} for i in range(1,8)],
       "engineer_approved":False,"permit_eligible":False,"engineering_approval":False,
       "status":"REAL_SYNTHETIC_OPENSEES_SIGNED_FE_TO_RC_REPORT_INTEGRATION_NO_APPROVAL"
    }
    return result

def formatv(v):
    if isinstance(v,bool):return str(v)
    if isinstance(v,(int,float)):return f"{v:.6f}"
    return str(v)

def table_html(head,items):
    esc=lambda x:html.escape(formatv(x),quote=True)
    return "<div class=\"scroll\"><table><thead><tr>"+"".join("<th>"+esc(x)+"</th>" for x in head)+"</tr></thead><tbody>"+"".join("<tr>"+"".join("<td>"+esc(x)+"</td>" for x in row)+"</tr>" for row in items)+"</tbody></table></div>"

def result_tables(r):
    action_header=["Case type","Load case / combo","Frame member","End","N kN","Vy kN","Vz kN","T kNm","My kNm","Mz kNm"]
    action_rows=[[x["kind"],x["case_id"],x["member_id"],x["end"]]+[x[k] for k in ("N","Vy","Vz","T","My","Mz")]
                 for x in r["signed_member_end_records"]]
    beam_rows=[[x["member_id"],x["shear_component"],
                ", ".join(v["combination_id"] for v in x["signed_combination_end_shear"]),
                max(d["required_shear_kN"] for d in x["check"]["end_demands"]),
                x["check"]["status"]]
               for x in r["member_design_checks"]["beam_design"]]
    col_rows=[[x["member_id"],x["governing_combination_id"],x["governing_member_end"],
               x["governing_interaction_utilization"],x["status"]]
               for x in r["member_design_checks"]["column_design"]]
    joint_rows=[[x["joint_node_id"],x["column_member_id"],x["beam_member_id"],
                 x["governing_uncertain_direction_shear_kN"],x["status"]]
                 for x in r["member_design_checks"]["joint_design"]]
    return {"actions":(action_header,action_rows),
      "beams":(["Beam","Local shear","Combinations","Max capacity-design end shear kN","Status"],beam_rows),
      "columns":(["Column","Governing combo","End","PMM utilization","Status"],col_rows),
      "joints":(["Joint","Column","Beam","Upper uncertain-direction shear kN","Status"],joint_rows)}

def markdown(r):
    rows=[
       "# SAR template — Actual signed OpenSees FE → bounded RC checks",
       "",
       f"**Case:** {r['case_id']} (separate independent synthetic model, not the original building or the 3-level reference).",
       "",
       "**NOT ENGINEERING APPROVED / NOT PERMIT ELIGIBLE.**",
       "",
       f"**Provenance SHA:** {r['source_bundle_sha256']} · **signed result SHA:** {r['signed_result_sha256']}",
       "",
       f"**Cases:** {r['case_count']} raw + {r['combination_count']} signed simultaneous combinations; "
       f"{r['member_count']} members; {r['member_end_action_rows']} I/J signed action rows.",
       "",
       "## Seven-chapter TOC",
       ""]
    for ch in r["chapters"]:rows.append(f"- [{ch['chapter']} {ch['title']}](#chapter-{ch['chapter']})")
    for ch in r["chapters"]:
        rows+=["",f'<a id="chapter-{ch["chapter"]}"></a>',f"## Chapter {ch['chapter']} — {ch['title']}",""]
        for sec in ch["headings"]:rows.append(f"### {sec['number']} {sec['name']}")
        rows+=["","| Module | This signed case |","|---|---|"]
        for mod in ch["requirements"]:rows.append(f"| {mod['id']} | {mod['run_status']} |")
        if ch["chapter"]=="05":
            rows+=["",f"Raw and combination local I/J records: {r['member_end_action_rows']}; "
                 f"max six-DOF equilibrium residual: {r['global_six_component_balance_max_kN_or_kNm']:.10g} (kN or kNm).",
                 "Full concurrent signed actions are in the accompanying JSON and CSV, NOT independent maxima.",""]
        if ch["chapter"]=="06":
            for kind,table in result_tables(r).items():
                if kind=="actions":continue
                head,values=table
                rows+=["",f"### {kind.title()} — synthetic member checks","",
                       "| "+" | ".join(head)+" |",
                       "| "+" | ".join(["---"]*len(head))+" |"]
                for row in values:rows.append("| "+" | ".join(formatv(v) for v in row)+" |")
    rows+=["","## Explicit limitations","",
       "- D2 synthetic frame is a separate case, not secretly joined to the prior three-storey model.",
       "- Signed static FE equilibrium and source-digest checks do not validate physical member design.",
       "- M08 is demand under externally assumed moment strengths, M09 depends on provided bar layouts, M10 retains uncertain joint shear direction.",
       "- Member rebar, detailed anchorage, ductility, accidental torsion, response-spectrum, settlement and project provenance remain unverified.",
       "- Original F3 unsafe flag is unchanged; no F3 analysis was run in this synthetic D2 package.",
       "- All professional approval, permit eligibility and submission items remain false.",""]
    return "\n".join(rows)

def render_html(r):
    esc=lambda x:html.escape(str(x),quote=True)
    t=result_tables(r)
    nav="".join(f'<a href="#chapter-{x["chapter"]}">{x["chapter"]} {esc(x["title"])}</a>' for x in r["chapters"])
    chunks=[]
    for ch in r["chapters"]:
        headers="".join(f"<h3>{esc(h['number'])} {esc(h['name'])}</h3>" for h in ch["headings"])
        cover=table_html(["Module","Original coverage","This run"],
            [[x["id"],x["registry_status"],x["run_status"]] for x in ch["requirements"]])
        extra=""
        if ch["chapter"]=="04":
            extra=f'<p>Canonical source model hash: <code>{esc(r["model_input_sha256"])}</code>. No original ETABS model imported.</p>'
        if ch["chapter"]=="05":
            extra=f'<p><strong>{r["case_count"]} separately solved static cases, {r["combination_count"]} concurrent signed combinations.</strong> Max global force/moment equilibrium residual: {r["global_six_component_balance_max_kN_or_kNm"]:.8g} kN or kNm. Local <code>eleResponse("localForce")</code> I/J member end actions are signed, not an envelope of unrelated maxima.</p>'
            extra+=table_html(*t["actions"])
        if ch["chapter"]=="06":
            for k in ("beams","columns","joints"):
                extra+=f"<h3>Signed FE-to-RC {k} bounded precheck</h3>"+table_html(*t[k])
            extra+='<p class="alert">No detailing/compliance approval; no F3 redesign. Source case is synthetic, not a real building.</p>'
        chunks.append(f'<section id="chapter-{esc(ch["chapter"])}"><h2>Chapter {esc(ch["chapter"])} — {esc(ch["title"])}</h2>{headers}<h3>18-module coverage contract</h3>{cover}{extra}</section>')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SAR Template Signed FE Handoff — Synthetic Reference</title>
<style>*{{box-sizing:border-box}}body{{max-width:1120px;margin:0 auto;padding:24px;background:#f7f8fb;color:#20314b;font:14px/1.55 system-ui,sans-serif}}
header,section{{background:white;margin:16px 0;padding:22px;border:1px solid #dce1e9;border-radius:12px}}h1{{font-size:26px}}h2{{font-size:19px}}h3{{font-size:14px}}nav{{display:flex;gap:8px;flex-wrap:wrap}}nav a{{color:#214a6d;text-decoration:none;border:1px solid #bdcbd9;border-radius:7px;padding:6px}}
.alert{{border-left:4px solid #b65149;padding:12px;background:#fff0ed}}.scroll{{max-height:460px;overflow:auto}}table{{border-collapse:collapse;min-width:600px;width:100%;font-size:12px}}td,th{{border:1px solid #ced6e0;padding:7px;text-align:left;vertical-align:top}}th{{background:#eef3f6}}code{{overflow-wrap:anywhere}}@media print{{nav{{display:none}}body{{background:white;padding:0}}section{{border:0}}tr{{break-inside:avoid}}}}</style></head>
<body><header><small>JP STRUCTURAL · SYNTHETIC REFERENCE · OPEN SEES SIGNED FE → RC REPORT</small>
<h1>Signed member actions and design checks — 7-chapter SAR engine</h1>
<p><strong>{esc(r["case_id"])}</strong> · {r["member_count"]} members · {r["member_end_action_rows"]} auditable signed member-end records.</p>
<p class="alert"><strong>NOT ENGINEERING APPROVED.</strong> This D2 synthetic FE model is separate from the three-level reference case and original G+1.5 building. Original F3 unsafe verdict unchanged.</p><nav>{nav}</nav></header>
{''.join(chunks)}
<section><h2>Annex — provenance, code and submission controls</h2>
<p>Input model SHA256: <code>{esc(r["model_input_sha256"])}</code></p>
<p>Signed input SHA256: <code>{esc(r["source_bundle_sha256"])}</code></p>
<p>Signed numerical results SHA256: <code>{esc(r["signed_result_sha256"])}</code></p>
<p>Full data: <a href="template-signed-fe-handoff.json">JSON</a> · signed records: <a href="template-signed-fe-handoff.csv">CSV</a> · <a href="template-signed-fe-handoff-manifest.json">SHA-256 manifest</a>.</p>
<p><a href="https://ebps.kathmandu.gov.np/UploadFiles/NBC_105_2025_Sesmic_Design.pdf">NBC 105:2025</a> · <a href="https://wriddodoti.gov.np/uploads/blog/20230331071217_IS-456-with-all-ammendments.pdf">IS 456:2000 with amendments</a>.</p>
<p class="alert">Status: NOT CERTIFIED · NOT PERMIT ELIGIBLE · NO PHYSICAL MODEL VALIDATION · NO PROFESSIONAL SIGNOFF.</p></section></body></html>"""

def csv_text(r):
    s=io.StringIO(); w=csv.writer(s,lineterminator="\n")
    columns=("kind","case_id","member_id","end","N","Vy","Vz","T","My","Mz")
    w.writerow(columns)
    for row in r["signed_member_end_records"]:
        w.writerow([row[k] for k in columns])
    return s.getvalue()

def emit(output:Path):
    r=build()
    output.mkdir(parents=True,exist_ok=True)
    values={OUTPUT_PREFIX+".json":json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+"\n",
            OUTPUT_PREFIX+".md":markdown(r),OUTPUT_PREFIX+".html":render_html(r),
            OUTPUT_PREFIX+".csv":csv_text(r)}
    for name,data in values.items():(output/name).write_text(data,encoding="utf8")
    m={"schema":"jp.structural.template.signed_FE_manifest.v0.3","case_id":r["case_id"],
      "signed_source_sha256":r["source_bundle_sha256"],
      "files":{k:hashlib.sha256(v.encode("utf8")).hexdigest() for k,v in values.items()},
      "engineering_approval":False}
    (output/(OUTPUT_PREFIX+"-manifest.json")).write_text(json.dumps(m,indent=2,sort_keys=True)+"\n",encoding="utf8")
    return r

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,required=True)
    a=p.parse_args();r=emit(a.output_dir)
    print("TEMPLATE_SIGNED_FE_HOFF",r["case_count"],"RAW",r["combination_count"],
          "COMBINATIONS",r["member_count"],"MEMBERS",r["member_end_action_rows"],
          "SIGNED_IJ_RECORDS_NO_PROJECT_APPROVAL")
if __name__=="__main__":main()
