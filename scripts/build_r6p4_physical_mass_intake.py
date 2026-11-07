#!/usr/bin/env python3
"""R6.4 physical mass reconciliation and site-source intake (fail-closed).

The original report 6831.9109kN and private Gate08's de-identified,
PROVISIONAL 5520.483743 / 6059.877983kN are different evidence states.
Their difference is genuine UNEXPLAINED residual, not an adjustment load.
No invented floor geometry, real ETABS mass export, soils, parcel or
NBC seismic factor. A PRIVATE supplied component CSV may be checked for
arithmetic/provenance, but never auto-approved and is never exported raw.

No private original member, cadastral identity, owner, engineer, grid or
floor-by-floor source file is published. Public artifacts contain only
prior-approved, de-identified aggregate QA and explicit holds.
"""
from __future__ import annotations
import argparse
import csv
from decimal import Decimal,InvalidOperation
import hashlib
import html
import io
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_structural_template_engine import CONTRACT,COVERAGE
SOURCE=ROOT/"registry/r6p4_mass_reconciliation_source.v0.1.json"
PARENT=ROOT/"registry/r6p3_original_site_mass_evidence.v0.1.json"
INTAKE=ROOT/"registry/r6p4_original_mass_components.csv"
PFX="r6p4-mass-source-reconciliation"
SCHEMA="jp.structural.r6p4.physical_mass_preflight.v0.1"
CATEGORIES=("DEAD_FRAME","DEAD_SLAB","DEAD_WALL","DEAD_FINISH",
            "DEAD_STAIRS","DEAD_TANK_FIXED_EQUIPMENT","LIVE_IMPOSED",
            "OTHER_PERMANENT","EXCLUDED")
UNITS=("m","m2","m3","count")
HEADERS=("floor_ref","component_ref","load_category","quantity",
         "quantity_unit","unit_weight_kN_per_unit",
         "seismic_participation_fraction","source_document_sha256",
         "source_evidence_ref","independent_review_sha256",
         "independent_review_status")
PATTERN=re.compile(r"^[0-9a-f]{64}$")
REF=re.compile(r"^[A-Z0-9][A-Z0-9_-]{0,63}$")

class MassIntakeError(ValueError):pass

def d(x,name,positive=False):
    try:
        if isinstance(x,bool) or x is None or isinstance(x,(list,dict)):
            raise InvalidOperation
        z=Decimal(str(x))
    except (ValueError,TypeError,InvalidOperation) as exc:
        raise MassIntakeError(name+" requires a finite decimal number") from exc
    if not z.is_finite() or (positive and z<=0):
        raise MassIntakeError(name+" requires "+("positive " if positive else "")+"finite decimal number")
    return z

def hashjson(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False,separators=(",",":")).encode("utf8")).hexdigest()

def load_components(path):
    if not path.exists():raise MassIntakeError("private physical component ledger not supplied")
    with path.open("r",encoding="utf-8-sig",newline="") as fh:
        reader=csv.DictReader(fh)
        if tuple(reader.fieldnames or ())!=HEADERS:
            raise MassIntakeError("physical source CSV schema changed; cannot infer floor/component fields")
        rows=list(reader)
    seen=set();per_floor={};valid_verified=0;preliminary=0
    for line,row in enumerate(rows,2):
        if None in row or any(row[k] is None for k in HEADERS):
            raise MassIntakeError(f"incomplete source CSV row {line}")
        floor=row["floor_ref"];comp=row["component_ref"]
        if not REF.fullmatch(floor) or not REF.fullmatch(comp):
            raise MassIntakeError("floor and component IDs must use stable non-sensitive identifiers")
        key=(floor,comp)
        if key in seen:raise MassIntakeError("duplicate floor/component; cannot double-count mass")
        seen.add(key)
        if row["load_category"] not in CATEGORIES:
            raise MassIntakeError("load category not in governed physical-mass catalog")
        if row["quantity_unit"] not in UNITS:
            raise MassIntakeError("quantity unit not among approved physical units")
        quantity=d(row["quantity"],"measured quantity",True)
        unit_weight=d(row["unit_weight_kN_per_unit"],"physical unit load",True)
        fraction=d(row["seismic_participation_fraction"],"seismic participation fraction")
        if not Decimal(0)<=fraction<=Decimal(1):
            raise MassIntakeError("seismic participation fraction must be between 0 and 1")
        if row["load_category"]=="EXCLUDED" and fraction!=0:
            raise MassIntakeError("excluded physical load must have zero seismic participation")
        if not PATTERN.fullmatch(row["source_document_sha256"]):
            raise MassIntakeError("every component must cite an exact source-document SHA256")
        if not row["source_evidence_ref"] or len(row["source_evidence_ref"])>150:
            raise MassIntakeError("each physical component needs an inspectable private evidence reference")
        status=row["independent_review_status"]
        if status not in ("UNVERIFIED","INDEPENDENTLY_REVIEWED"):
            raise MassIntakeError("independent review status unsupported")
        if status=="INDEPENDENTLY_REVIEWED":
            if not PATTERN.fullmatch(row["independent_review_sha256"]):
                raise MassIntakeError("claimed independent review needs a signed-review SHA256")
            valid_verified+=1
        else:
            if row["independent_review_sha256"]:
                raise MassIntakeError("unverified row must not masquerade as signed review")
            preliminary+=1
        current=per_floor.setdefault(floor,{"row_count":0,"eligible_kN":Decimal(0),"unweighted_gravity_kN":Decimal(0)})
        current["row_count"]+=1
        current["unweighted_gravity_kN"]+=quantity*unit_weight
        current["eligible_kN"]+=quantity*unit_weight*fraction
    # Exact-source privacy: no floor labels/quantities or evidence refs leave
    # this function; output gives only global aggregate COUNT and status.
    gravity=sum((v["unweighted_gravity_kN"] for v in per_floor.values()),Decimal(0))
    seismic=sum((v["eligible_kN"] for v in per_floor.values()),Decimal(0))
    return {"component_count":len(rows),"floor_count":len(per_floor),
        "independently_reviewed_row_count":valid_verified,
        "unverified_row_count":preliminary,
        "global_preliminary_component_gravity_kN":float(gravity) if rows else None,
        "global_preliminary_component_seismic_kN":float(seismic) if rows else None,
        "original_floor_mass_approved":False,
        "raw_private_row_or_floor_breakdown_publicly_exported":False}

def audit(source,parent,components):
    if source.get("schema")!="jp.structural.r6p4.mass_reconciliation_source.v0.1":
        raise MassIntakeError("governed Gate08 aggregate source schema missing")
    if parent.get("schema")!="jp.structural.r6.project_site_evidence_admission.v0.1":
        raise MassIntakeError("expected original R6.3 site and mass evidence authority")
    if parent.get("overall_engineering_approval") is not False or source.get("engineering_approval") is not False:
        raise MassIntakeError("source cannot silently authorize original building")
    if source.get("original_foundation_F3_verdict")!="NOT SAFE IN ONE WAY SHEAR" or parent["original_report_assertions"].get("reported_F3_verdict")!="NOT SAFE IN ONE WAY SHEAR":
        raise MassIntakeError("source F3 unsafe finding cannot be overwritten")
    if source.get("original_physical_evidence_accepted")!=0 or source.get("original_physical_evidence_total")!=15:
        raise MassIntakeError("the original 15 evidence gates cannot be auto-accepted")
    lineage=source.get("source_lineage",{})
    for k in ("original_report_sha256","gate08_source_summary_sha256","gate08_private_archive_sha256"):
        if not PATTERN.fullmatch(lineage.get(k,"")):
            raise MassIntakeError("immutable source lineage hash missing")
    if lineage.get("full_private_source_model_released_publicly") is not False or source.get("physical_inference_banned") is not True:
        raise MassIntakeError("private source model or invented physical rows must not be published")
    original=d(source["reported_original_ETABS_seismic_weight_kN"],"source ETABS seismic weight",True)
    if original!=d(parent["original_report_assertions"]["seismic_weight_ETABS_reported_kN"],"R6.3 original ETABS mass",True):
        raise MassIntakeError("source ETABS mass disagrees with frozen earlier R6.3 evidence")
    scenarios=source.get("scenarios",[])
    if len(scenarios)!=2 or [x.get("id") for x in scenarios]!=[
         "GATE08_NO_CANDIDATE_WALLS","GATE08_WITH_HYPOTHETICAL_WALLS"]:
        raise MassIntakeError("Gate08 scenario lineage/order changed")
    n,b=[d(x["seismic_weight_kN"],"Gate08 conditional mass",True) for x in scenarios]
    if not(Decimal(0)<n<b<original):raise MassIntakeError("Gate08 conditional mass scenario order invalid")
    if any(x.get("source_status")!="PRIVATE_FE_DERIVED_CONDITIONAL_NOT_VERIFIED_SITE" for x in scenarios):
        raise MassIntakeError("no private Gate08 scenario is a measured physical project mass")
    hypothetical_wall=d(source["gate08_incremental_candidate_wall_weight_kN"],"candidate wall weight",True)
    if abs((b-n)-hypothetical_wall)>Decimal("0.000001"):
        raise MassIntakeError("Gate08 conditional wall mass increment fails arithmetic reconciliation")
    gap_without=original-n
    gap_with=original-b
    if gap_without<=gap_with or gap_with<=0 or gap_without-gap_with!=hypothetical_wall:
        raise MassIntakeError("Gate08 residual mass arithmetic violates source")
    if source.get("direct_original_ETABS_mass_export_found") is not False or source.get("etabs_mass_authenticated") is not False:
        raise MassIntakeError("original ETABS floor-by-floor source export was not authenticated")
    if source.get("scale_factor_generated") is not False or source.get("design_spectrum_generated") is not False:
        raise MassIntakeError("no NBC seismic spectrum or scaling authorized in mass-intake milestone")
    chain=source.get("evidence_chain",[])
    ids=[x.get("type") for x in chain]
    needed={"ORIGINAL_REPORT","PROVISIONAL_GEOMETRY_DECISION","GATE08_MASS_RECONSTRUCTION",
      "GOVERNMENT_PARCEL_RECORD","EXACT_SITE_NBC2025_ZONE_AUTHORITY",
      "SITE_SPECIFIC_VS30_OR_SPT","APPROVED_RESIDENTIAL_STRUCTURAL_SYSTEM",
      "ETABS_STORY_AND_COMPONENT_MASS_EXPORT","INDEPENDENT_MASS_ENGINEER_REVIEW"}
    if len(ids)!=len(needed) or set(ids)!=needed:
        raise MassIntakeError("source evidence intake catalog incomplete")
    if any(x.get("status","").startswith("VERIFIED") for x in chain):
        raise MassIntakeError("independent documents cannot be marked verified without actual source evidence")
    known=[{"id":"NO_WALLS","conditional_mass_kN":float(n),
             "source_unexplained_gap_kN":float(gap_without),
             "source_unexplained_percent":float(gap_without/original*100),
             "modeled_fraction_of_report_percent":float(n/original*100),
             "physical_mass_verified":False},
            {"id":"CANDIDATE_WALLS_ONLY","conditional_mass_kN":float(b),
             "source_unexplained_gap_kN":float(gap_with),
             "source_unexplained_percent":float(gap_with/original*100),
             "modeled_fraction_of_report_percent":float(b/original*100),
             "physical_mass_verified":False}]
    auth=[
      {"key":x["type"],"status":x["status"],"admitted_for_original_seismic_design":False}
      for x in chain
    ]
    # Staged private rows can expose arithmetic errors but never constitute
    # a complete ETABS story-by-story mass reconciliation without a verified
    # native ETABS export, approved floor list and licensed reviewer.
    mass_candidate=components["global_preliminary_component_seismic_kN"]
    preliminary_gap=(float(original)-mass_candidate) if mass_candidate is not None else None
    status="PRIVATE_COMPONENT_ARITHMETIC_ONLY" if components["component_count"] else "NO_PHYSICAL_COMPONENTS_SUPPLIED"
    return {"schema":SCHEMA,
      "original_ETABS_reported_weight_kN":float(original),
      "gate08_conditional_mass_comparisons":known,
      "conditional_candidate_wall_increment_kN":float(hypothetical_wall),
      "conditional_mass_reconciliation_status":"UNRESOLVED_PHYSICAL_RESIDUAL",
      "gap_after_conditional_wall_scenario_kN":float(gap_with),
      "gap_after_conditional_wall_scenario_percent":float(gap_with/original*100),
      "prior_mass_candidate_explains_full_ETABS":False,
      "private_physical_component_status":status,
      "private_physical_components_summary":components,
      "private_preliminary_remaining_mass_gap_kN":preliminary_gap,
      "source_evidence_catalog":auth,
      "independent_site_parcel_verified":False,
      "independent_site_geotechnical_Vs30_SPT_verified":False,
      "approved_site_NBC2025_zone_record_verified":False,
      "approved_use_and_lateral_system_verified":False,
      "real_native_ETABS_mass_export_admitted":False,
      "real_physical_mass_reconciled":False,
      "original_building_seismic_mass_approved":False,
      "R6p3_site_gates_closed":0,
      "R6p3_site_gates_total":8,
      "original_physical_gates_closed":0,
      "original_physical_gates_total":15,
      "original_F3_failure":"NOT SAFE IN ONE WAY SHEAR",
      "code_spectrum_applied":False,"MRSM_scale_factor":None,
      "MRSM_scaling_executed":False,"engineering_approval":False,
      "original_source_lineage_sha256":lineage["original_report_sha256"],
      "private_checkpoint_sha256":lineage["gate08_source_summary_sha256"],
      "private_archive_sha256":lineage["gate08_private_archive_sha256"]}

def build(source=None,parent=None,components=None):
    if source is None:source=json.loads(SOURCE.read_text(encoding="utf8"))
    if parent is None:parent=json.loads(PARENT.read_text(encoding="utf8"))
    if components is None:components=load_components(INTAKE)
    a=audit(source,parent,components)
    cov={r["id"]:r for r in json.loads(COVERAGE.read_text(encoding="utf8"))["requirements"]}
    template=json.loads(CONTRACT.read_text(encoding="utf8"))
    statuses={
      "M02":"SOURCE_REPORTED_ETABS_6831P9109_VS_PRIVATE_GATE08_CONDITIONAL_TWO_MASSES_NOT_CLOSED",
      "M04":"PROVISIONAL_GEOMETRY_ONLY_NO_ACCEPTED_PHYSICAL_STORY_TO_MODEL_LINKS",
      "M05":"R6P3_SOURCE_AUTHENTICATION_AND_MASS_PENDING_NO_SPECTRUM",
      "M06":"CONDITIONAL_MASS_RESIDUAL_772P032917_KN_NO_GUESSED_WALL_OR_FORCE_SCALING",
      "S17":"DOUBLE_COUNTING_SOURCE_SHA_INDEPENDENT_COMPONENT_ARITHMETIC_AND_UNVERIFIED_HOLD"}
    chapters=[{"id":x["id"],"title":x["title"],"modules":[
      {"id":id,"title":cov[id]["title"],
       "status":statuses.get(id,"NOT_VERIFIED_AS_PART_OF_R6P4_PHYSICAL_MASS_RECONCILIATION")}
       for id in x["requirement_ids"]]} for x in template["chapters"]]
    if len(chapters)!=7 or {m["id"] for c in chapters for m in c["modules"]}!=set(cov):
        raise MassIntakeError("seven SAR chapters/18 modules contract drift")
    return {**a,
      "source_input_sha256":hashjson(source),
      "previous_R6p3_source_ledger_sha256":hashjson(parent),
      "all_source_assertions_not_certified":True,
      "chapters":chapters,
      "private_source_protection":"No private 92-node frame, 165-member matrix, client, plot, correspondence or source PDF published",
      "next_required_evidence":[
         "Obtain government land ownership/cadastral map for exact project parcel and approved municipality/ward, then reconcile site identity",
         "Obtain site-specific geotechnical Vs30/SPT and qualified soil class review; regional proxy soils and other projects are excluded",
         "Obtain stamped occupancy, architectural structural plan and exact physical grid/floor footprints",
         "Obtain native matching ETABS mass source definitions and level-by-level exported mass tables, tied to model hash",
         "Provide approved concrete/member/slab/wall/partition/tank/permanent load inventories, measured quantities and eligible imposed load factors with no double counts",
         "Match independent physical component sum and complete story mass and reactions to source ETABS 6831.9109kN, reconcile any residual without phantom items",
         "Independently review source and acceptance, then continue R6.3 original site/modal checks before considering NBC design factors or scaling",
         "Resolve original F3 NOT SAFE IN ONE WAY SHEAR independently and document approved engineer action"]}

def _csv(rows,cols):
    buf=io.StringIO();w=csv.writer(buf,lineterminator="\n");w.writerow(cols)
    for row in rows:w.writerow([row.get(k) for k in cols])
    return buf.getvalue()

def render_html(r):
    e=lambda x:html.escape(str(x),quote=True)
    comp=r["gate08_conditional_mass_comparisons"]
    table="".join("<tr>"+"".join(f"<td>{e(row[k])}</td>" for k in
       ("id","conditional_mass_kN","source_unexplained_gap_kN","source_unexplained_percent","physical_mass_verified"))+"</tr>" for row in comp)
    ch="".join(f'<section><h2>Chapter {e(c["id"])} — {e(c["title"])}</h2><table><tr><th>Module</th><th>Verification state</th></tr>'+
         "".join(f'<tr><td>{e(m["id"])}</td><td>{e(m["status"])}</td></tr>' for m in c["modules"])+"</table></section>" for c in r["chapters"])
    items="".join("<li>"+e(x)+"</li>" for x in r["next_required_evidence"])
    catalog="".join(f'<tr><td>{e(x["key"])}</td><td>{e(x["status"])}</td></tr>' for x in r["source_evidence_catalog"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>R6.4 Original-building source mass reconciliation</title><style>
body{{font:14px/1.5 system-ui;max-width:1080px;margin:auto;padding:18px;background:#f5f7fb;color:#253954}}header,section{{background:white;border:1px solid #d5dfeb;border-radius:10px;padding:18px;margin:14px 0}}.hold{{background:#fff1eb;border-left:5px solid #a74b39;padding:12px}}.scroll{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;min-width:630px}}th,td{{border:1px solid #d5dfeb;padding:8px;text-align:left;font-size:12px}}th{{background:#eff3f8}}@media print{{body{{background:white}}}}</style></head><body>
<header><small>JP STRUCTURAL · R6.4 SOURCE-GOVERNED MASS RECONCILIATION · PRIVATE ORIGINALS PRESERVED</small>
<h1>Original seismic weight: physical reconciliation remains OPEN</h1>
<p class="hold"><strong>NOT AN APPROVED BUILDING DESIGN.</strong> The original report's seismic weight is <strong>{r["original_ETABS_reported_weight_kN"]:.4f} kN</strong>, not verified from independently approved physical floor components. The conditional Gate08 trial leaves an unexplained <strong>{r["gap_after_conditional_wall_scenario_kN"]:.6f} kN ({r["gap_after_conditional_wall_scenario_percent"]:.2f}%)</strong>. This is a real source gap; do not add phantom wall weights to close it. Original footing F3: <strong>NOT SAFE IN ONE WAY SHEAR</strong>.</p>
<p><a href="{PFX}.json">Aggregate numerical/evidence JSON</a> · <a href="{PFX}-scenarios.csv">Conditional mass arithmetic CSV</a> · <a href="{PFX}-sources.csv">Source admission catalog CSV</a> · <a href="{PFX}-manifest.json">SHA-256 manifest</a></p></header>
<section><h2>Private-source Gate08 aggregate sensitivity: NOT physical acceptance</h2><div class="scroll"><table><tr><th>Conditional model</th><th>Estimated mass (kN)</th><th>Residual to ETABS (kN)</th><th>Residual (%)</th><th>Physical authority</th></tr>{table}</table></div>
<p>Previously derived reference sensitivities were validated against immutable source-checkpoint hashes and independently recalculated using exact decimal arithmetic. The provisional wall increment is {r["conditional_candidate_wall_increment_kN"]:.6f} kN. Hypothetical beams, estimated slab distributions and unknown wall locations remain unmeasured.</p></section>
<section><h2>Authenticated physical evidence and mass-file status</h2><p><strong>{e(r["private_physical_component_status"])}</strong> · Documented components {r["private_physical_components_summary"]["component_count"]}; approved whole-building reconciliation <strong>NO</strong>. Publicly released data never contain the raw private component rows, coordinates, owners or architect reports.</p>
<div class="scroll"><table><tr><th>Source type</th><th>Current authority</th></tr>{catalog}</table></div>
<p>Land records can be requested through the Nepal Survey Department's <a href="https://merokitta.dos.gov.np/">Mero Kitta</a> service; credentials, land certificates, and OTP must be handled by the authorized owner, not inserted in GitHub.</p></section>
<section><h2>Source files required for a defensible ETABS mass reconciliation</h2><ol>{items}</ol><p>Physical mass quantities must use approved original floor/roof outlines, separate component material unit weights and eligible seismic fractions. Missing information is <strong>NOT ZERO</strong>, and a matching total alone is not professional proof. No actual project response spectrum or MRSM scaling was generated.</p></section>{ch}</body></html>"""

def emit(out,source=SOURCE,parent=PARENT,private_csv=INTAKE):
    src=json.loads(Path(source).read_text(encoding="utf8"))
    prev=json.loads(Path(parent).read_text(encoding="utf8"))
    rows=load_components(Path(private_csv))
    r=build(src,prev,rows)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    artifacts={
      PFX+".json":json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+"\n",
      PFX+".html":render_html(r),
      PFX+"-scenarios.csv":_csv(r["gate08_conditional_mass_comparisons"],
        ["id","conditional_mass_kN","source_unexplained_gap_kN",
         "source_unexplained_percent","modeled_fraction_of_report_percent","physical_mass_verified"]),
      PFX+"-sources.csv":_csv(r["source_evidence_catalog"],
        ["key","status","admitted_for_original_seismic_design"]),
    }
    for name,content in artifacts.items():(out/name).write_text(content,encoding="utf8")
    m={"schema":"jp.structural.r6p4.mass_source_manifest.v0.1",
       "source_sha256":r["source_input_sha256"],
       "parent_sha256":r["previous_R6p3_source_ledger_sha256"],
       "private_gate08_checkpoint_sha256":r["private_checkpoint_sha256"],
       "files":{name:hashlib.sha256(data.encode("utf8")).hexdigest() for name,data in artifacts.items()},
       "physical_reconciliation_complete":False,
       "no_design_spectrum_or_scaling":True,"engineering_approval":False}
    (out/(PFX+"-manifest.json")).write_text(json.dumps(m,sort_keys=True,indent=2)+"\n",encoding="utf8")
    return r

def main():
    parser=argparse.ArgumentParser(description="R6.4 auditable physical mass intake and conditional prior residuals")
    parser.add_argument("--output-dir",type=Path,required=True)
    parser.add_argument("--source",type=Path,default=SOURCE)
    parser.add_argument("--parent",type=Path,default=PARENT)
    parser.add_argument("--private-components",type=Path,default=INTAKE)
    args=parser.parse_args()
    r=emit(args.output_dir,args.source,args.parent,args.private_components)
    print("R6P4_CONDITIONAL_MASS_RECONCILIATION",r["original_ETABS_reported_weight_kN"],
          "REPORTED_ETABS_KN",r["gap_after_conditional_wall_scenario_kN"],
          "UNEXPLAINED_KN_NO_PHYSICAL_APPROVAL_NO_MRSM_SCALING_F3_HOLD")
if __name__=="__main__":main()
