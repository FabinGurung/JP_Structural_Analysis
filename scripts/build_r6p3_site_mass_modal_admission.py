#!/usr/bin/env python3
"""R6.3: independent evidence admission before ORIGINAL building MRSM scaling.

Primary authority is the original ETABS PDF + independently verified site,
geotechnical, approved design and itemized physical floor mass sources. The
PDF's assertions are *not* accepted site facts: Pokhara/Leknath is mixed
with Kathmandu seismic-zone text; medium soil with obsolete Type D; NBC
105:2020 factors with NBC 105:2025 claims. ETABS weight 6831.9109 kN is
NOT directly comparable to the 111.2 kN synthetic four-node R6.2 mass.

This engine deliberately cannot approve the design; even future verified
inputs are only admissible to independent professional review.
Separately audit modal adequacy for the real R6.2 connected FE, using the
2025-code 90% effective mass criterion per direction (clause 7.3) and
33Hz missing-mass rule, without ever asserting the synthetic FE is an
accepted original-building model. Do NOT compute or apply ESM/MRSM scale.
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

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_r5_generic_frame_case import DEFAULT
from scripts.build_r6_connected_shell_modal import SETTINGS as R6P2_SETTINGS,build as build_r6p2,SCHEMA as R6P2_SCHEMA
from scripts.build_structural_template_engine import CONTRACT,COVERAGE

LEDGER=ROOT/"registry/r6p3_original_site_mass_evidence.v0.1.json"
PFX="r6p3-seismic-evidence-admission"
SCHEMA="jp.structural.r6p3.site_mass_modal_admission.v0.1"

SITE_FIELDS=(
 "approved_cadastral_parcel_or_survey_uri",
 "current_local_jurisdiction_identifier",
 "site_georeferenced_municipality_certification_uri",
 "nbc105_2025_zone_table_entry_and_provenance_uri",
 "geotechnical_report_uri",
 "reviewed_soil_class_2025",
 "approved_building_use_document_uri",
 "approved_lateral_system_document_uri",
 "reviewed_importance_class_and_factor_uri",
 "qualified_independent_design_review_receipt_uri",
)
SOIL_ALTERNATIVES=("measured_Vs30_m_s","documented_SPT_profile_uri")
MASS_FIELDS=(
 "actual_storey_geometry_and_floor_ledger_uri",
 "structural_member_volume_and_density_ledger_uri",
 "wall_cladding_tank_and_permanent_load_ledger_uri",
 "occupancy_imposed_load_partition_ledger_uri",
 "floor_by_floor_ETABS_mass_export_and_node_mapping_uri",
 "gravity_vs_seismic_participation_review_uri",
 "independently_reconciled_total_seismic_weight_kN",
 "reconciliation_signed_engineer_receipt_uri",
)
GATES=("SITE_PARCEL_AND_JURISDICTION","SITE_HAZARD_CODE_EDITION",
       "SOIL_VS30_OR_SPT_EVIDENCE","OCCUPANCY_STRUCTURAL_SYSTEM_APPROVAL",
       "PHYSICAL_FLOOR_MASS_RECONCILIATION","MODAL_ADEQUACY_REAL_MODEL",
       "SCALING_ELIGIBILITY","ORIGINAL_PHYSICAL_EVIDENCE")
class AdmissionError(ValueError):pass

def _digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf8")).hexdigest()

def _positive_number(x,key):
    if isinstance(x,bool) or not isinstance(x,(float,int)) or not math.isfinite(x) or x<=0:
        raise AdmissionError(key+" must be positive finite")
    return float(x)

def _text(v,key):
    if not isinstance(v,str) or not v.strip():
        raise AdmissionError(key+" must contain a source-backed text reference")
    return v.strip()

def _status(key,description,ok=False,why=None):
    return {"id":key,"status":"INPUTS_PRESENT_FOR_REVIEW" if ok else "HOLD",
            "description":description,"reason":why or ("Needs qualified independent verification" if ok else "Required independent evidence not admitted"),
            "professional_approval":False}

def audit_modal_participation(modal,code_rules):
    if modal.get("schema")!=R6P2_SCHEMA or not modal.get("same_R5p6_connected_shell_FE") or not modal.get("original_source_seismic_corner_mass_unchanged"):
        raise AdmissionError("R6.3 requires an actual source-mass-audited connected R6.2 result")
    threshold=_positive_number(code_rules["modal_fraction_required_each_direction"],"NBC modal fraction")
    freq_limit=_positive_number(code_rules["frequency_cutoff_for_modal_combination_Hz"],"high-frequency cut-off")
    if not math.isclose(threshold,.90,abs_tol=1e-12) or not math.isclose(freq_limit,33,abs_tol=1e-12):
        raise AdmissionError("R6.3 governing official NBC105:2025 clause 7.3 criteria have changed")
    observed=[]
    expected=len(modal["mesh_divisions"])*len(modal["diaphragm_modes"])*len(modal["axes"])
    summaries=modal.get("participation_summaries")
    if not isinstance(summaries,list) or len(summaries)!=expected:
        raise AdmissionError("missing connected FE mesh/axis/diaphragm modal coverage")
    identities=set()
    for s in summaries:
        key=(s.get("mesh"),s.get("diaphragm_mode"),s.get("axis"))
        if key in identities:raise AdmissionError("duplicated connected model modal participation identity")
        identities.add(key)
        modes=s.get("modes")
        if not isinstance(modes,list) or len(modes)!=modal["modes_per_axis"]:
            raise AdmissionError("partial or missing actual modal frequency/participation list")
        fractions=[];included=[]
        last=-1.;high=[]
        for i,m in enumerate(modes,1):
            if m.get("mode")!=i:raise AdmissionError("eigenmode index source ordering inconsistent")
            freq=_positive_number(m["omega_rad_s"],"modal frequency omega")/(2*math.pi)
            p=m["participation_fraction"]
            if isinstance(p,bool) or not isinstance(p,(int,float)) or not math.isfinite(p) or p<0:
                raise AdmissionError("invalid effective modal mass fraction")
            fractions.append(float(p))
            if freq<freq_limit:included.append(float(p))
            else:high.append({"mode":i,"frequency_Hz":freq,"mass_fraction":float(p)})
            cumulative=m["cumulative_participation_fraction"]
            if not math.isclose(cumulative,math.fsum(fractions),abs_tol=2e-6):
                raise AdmissionError("cumulative modal participation not conserved")
            if cumulative<last-1e-8:raise AdmissionError("modal cumulative participation decreased")
            last=cumulative
        total=math.fsum(fractions);eligible=math.fsum(included)
        if total>1.001 or total<0 or eligible>total+1e-8:
            raise AdmissionError("source total mass exceeded by modal effective mass")
        _observed=s.get("cumulative_modal_participation_fraction")
        if not math.isclose(_observed,total,abs_tol=2e-6):
            raise AdmissionError("R6.2 participation summary misaligned with modes")
        observed.append({
         "mesh":key[0],"diaphragm_mode":key[1],"axis":key[2],
         "source_effective_mass_fraction_first_modes":total,
         "eligible_under_33Hz_mass_fraction":eligible,
         "unrepresented_mass_fraction":1-total,
         "included_mode_count":len(included),
         "excluded_at_or_above_33Hz_modes":high,
         "numerical_90pct_eligible_mass_screen":"MEETS_IN_SYNTHETIC_CASE" if eligible+1e-10>=threshold else "INSUFFICIENT_IN_SYNTHETIC_CASE",
         "original_building_code_acceptance":False,
         "needs_high_frequency_missing_mass_assessment":bool(high),
         "not_mode_convergence_verified":True
        })
    if set(modal["axes"])!={"X","Y"} or set(modal["diaphragm_modes"])!={"FLEXIBLE_SHELL","RIGID_INPLANE_MPC"}:
        raise AdmissionError("must retain both lateral axes and both FE diaphragm branches")
    return observed

def audit_evidence(evidence,modal):
    if evidence.get("schema")!="jp.structural.r6.project_site_evidence_admission.v0.1":
        raise AdmissionError("original-site evidence schema missing")
    r=evidence.get("original_report")
    if not isinstance(r,dict) or r.get("file_id")!="1TpWUmOdrcQqOpkN6qvmhZ12KrYaNABBM" or not r.get("source_document_located_and_text_read"):
        raise AdmissionError("original ETABS PDF identity and Drive readback not grounded")
    if r.get("engineer_source_design_acceptance") is not False or evidence.get("overall_engineering_approval") is not False:
        raise AdmissionError("no original engineer approval or permit is source admitted")
    claims=evidence.get("original_report_assertions")
    if not isinstance(claims,dict) or claims.get("reported_F3_verdict")!="NOT SAFE IN ONE WAY SHEAR":
        raise AdmissionError("original unsafe footing F3 finding missing")
    physical=_positive_number(claims.get("seismic_weight_ETABS_reported_kN"),"ETABS reported seismic weight")
    site=evidence.get("authoritative_site_evidence",{})
    masses=evidence.get("authoritative_mass_evidence",{})
    if not isinstance(site,dict) or not isinstance(masses,dict):
        raise AdmissionError("site/mass authority evidence ledgers required")
    if any(k not in site for k in SITE_FIELDS+SOIL_ALTERNATIVES) or any(k not in masses for k in MASS_FIELDS):
        raise AdmissionError("source authority fields missing from live evidence ledger")
    if any(not isinstance(c,dict) or c.get("status")!="UNRESOLVED" for c in evidence.get("conflicts",[])) or len(evidence.get("conflicts",[]))!=3:
        raise AdmissionError("source conflicting location/soil/code claims cannot silently vanish")
    if not math.isclose(physical,masses["physical_reported_ETABS_weight_kN"],rel_tol=0,abs_tol=1e-6):
        raise AdmissionError("ETABS original mass statement inconsistent with physical ledger")
    if not math.isclose(modal["audited_seismic_weight_kN"],
        evidence["synthetic_R6p2_reference"]["audited_seismic_weight_kN"],abs_tol=1e-8):
        raise AdmissionError("synthetic modal source mass changed without version")
    if evidence["synthetic_R6p2_reference"]["may_not_replace_or_scale_original_mass"] is not True:
        raise AdmissionError("original physical mass must be separate from synthetic reference")
    if evidence["original_building_physical_evidence_gates_accepted"]!=0 or evidence["original_building_physical_evidence_gates_total"]!=15:
        raise AdmissionError("original 15 physical source evidence gates changed without review")
    code=evidence["nbc105_2025_admission_rules"]
    if code.get("code_edition")!="NBC 105:2025 SECOND REVISION" or not code.get("official_code_uri","").startswith("https://giwmscdnone.gov.np/"):
        raise AdmissionError("official code revision/provenance not verified")
    screen=audit_modal_participation(modal,code)
    have=lambda x: isinstance(x,str) and bool(x.strip())
    site_identity=all(have(site[x]) for x in SITE_FIELDS[:3])
    site_hazard=all(have(site[x]) for x in (SITE_FIELDS[3],))
    soil=have(site["geotechnical_report_uri"]) and have(site["reviewed_soil_class_2025"]) and (
        (isinstance(site["measured_Vs30_m_s"],(float,int)) and not isinstance(site["measured_Vs30_m_s"],bool) and site["measured_Vs30_m_s"]>0) or
        have(site["documented_SPT_profile_uri"]))
    occupancy=all(have(site[k]) for k in SITE_FIELDS[6:9])
    mass_authority=all(have(masses[k]) for k in MASS_FIELDS if k!="independently_reconciled_total_seismic_weight_kN")
    mw=masses["independently_reconciled_total_seismic_weight_kN"]
    numeric_mass=isinstance(mw,(float,int)) and not isinstance(mw,bool) and math.isfinite(mw) and mw>0
    mass_ready=bool(mass_authority and numeric_mass and math.isclose(float(mw),physical,rel_tol=1e-3,abs_tol=1.0))
    modal_ready=False # source model not authenticated; synthetic mode adequacy cannot qualify real model
    conflict=bool(evidence.get("conflicts"))
    gates=[
        _status("SITE_PARCEL_AND_JURISDICTION","Approved site/parcel and municipality authority",site_identity and not conflict,
                "Original report claims Pokhara/Leknath but also refers to Kathmandu seismic zone"),
        _status("SITE_HAZARD_CODE_EDITION","NBC105:2025 jurisdiction-specific site Z with table/record provenance",site_hazard and site_identity and not conflict,
                "Original Z=0.35 is reported using mixed 2020/2025 table references, not authenticated"),
        _status("SOIL_VS30_OR_SPT_EVIDENCE","Site-specific geotechnical Vs30 or N-SPT and independently classified soil",soil and not conflict,
                "Original says medium soil and type D without accepted Vs30/SPT proof"),
        _status("OCCUPANCY_STRUCTURAL_SYSTEM_APPROVAL","Approved residential use, structural system and importance class",occupancy,
                "Source report claims residential SMRF; approved planning/system evidence missing"),
        _status("PHYSICAL_FLOOR_MASS_RECONCILIATION","Storey-by-storey dead/live source breakdown to the real ETABS mass and node mapping",mass_ready,
                "ETABS claims 6831.9109 kN but authenticated physical storey/mass ledgers are absent; synthetic 111.2kN is unrelated"),
        _status("MODAL_ADEQUACY_REAL_MODEL","Authenticated full-building eigen modes attain >=90% effective mass in each axis, include <=33Hz mode rule",modal_ready,
                "Only first four synthetic shell modes were tested; physical original model/mass and missing-mass correction are unaccepted"),
        _status("SCALING_ELIGIBILITY","Authenticated original seismic input, modal adequacy and ESM/MRSM comparison required",False,
                "NBC 105:2025 clause 7.5 V/VR calculation/application BLOCKED: code parameters, physical mass, modal sufficiency not verified"),
        _status("ORIGINAL_PHYSICAL_EVIDENCE","Independent structural evidence gate acceptance and professional design receipt",False,
                "0 of 15 original building evidence gates accepted and F3 remains NOT SAFE IN ONE WAY SHEAR"),
    ]
    if len(gates)!=len(GATES) or [g["id"] for g in gates]!=list(GATES):
        raise AdmissionError("governed evidence gate order drift")
    if any(g["status"]=="INPUTS_PRESENT_FOR_REVIEW" for g in gates) and evidence["force_design_acceptance"] is not False:
        raise AdmissionError("engine cannot issue engineer construction acceptance")
    return {
       "site_gates":gates,"gates_on_hold":sum(x["status"]=="HOLD" for x in gates),
       "original_pdf_reports":claims,"original_report_file_id":r["file_id"],
       "source_document_found_and_read":True,
       "site_conflicts_open":evidence["conflicts"],
       "modal_synthetic_participation_screen":screen,
       "modal_synthetic_90pct_screens_meeting":sum(x["numerical_90pct_eligible_mass_screen"]=="MEETS_IN_SYNTHETIC_CASE" for x in screen),
       "modal_synthetic_screens_total":len(screen),
       "site_specific_zone_factor_accepted":False,
       "site_specific_soil_accepted":False,
       "real_ETABS_mass_kN_reported_not_verified":physical,
       "real_independent_mass_reconciliation_completed":False,
       "synthetic_reference_weight_kN":modal["audited_seismic_weight_kN"],
       "actual_vs_synthetic_mass_comparison_valid":False,
       "original_building_mass_source_admitted":False,
       "original_building_modal_compliance":False,
       "real_project_MRSM_scale_factor":None,
       "ESM_MRSM_code_scaling_executed":False,
       "whole_building_engineering_approval":False
    }

def build(evidence=None,modal=None):
    if evidence is None:evidence=json.loads(LEDGER.read_text(encoding="utf8"))
    if modal is None:modal=build_r6p2(meshes=(2,4))
    a=audit_evidence(evidence,modal)
    cov={x["id"]:x for x in json.loads(COVERAGE.read_text(encoding="utf8"))["requirements"]}
    template=json.loads(CONTRACT.read_text(encoding="utf8"))
    statuses={"M02":"ORIGINAL_ETABS_SOURCE_CLAIMS_VS_SYNTHETIC_R6P2_SOURCE_MASS_DISTINCT",
              "M05":"NBC105_2025_CLAUSE_7_3_90PCT_PER_DIRECTION_AND_33HZ_HIGH_MODE_SCREEN",
              "M06":"NBC105_2025_CLAUSE_7_5_ESM_MRSM_SCALING_NOT_AUTHORIZED",
              "S17":"FAIL_CLOSED_ORIGINAL_LOCATION_SOIL_CODE_WEIGHT_SOURCE_CONFLICT_GATE"}
    chapters=[{"id":x["id"],"title":x["title"],
       "modules":[{"id":n,"title":cov[n]["title"],
        "status":statuses.get(n,"NOT_VERIFIED_OR_ACCEPTED_IN_R6P3_ORIGINAL_SITE_AUDIT")}
        for n in x["requirement_ids"]]} for x in template["chapters"]]
    if len(chapters)!=7 or {x["id"] for c in chapters for x in c["modules"]}!=set(cov):
        raise AdmissionError("7 chapter/18 module source reporting contract drift")
    return {"schema":SCHEMA,
        "original_source_ledger_SHA256":_digest(evidence),
        "synthetic_connected_modal_report_SHA256":_digest(modal),
        "original_report_Drive_file_id":evidence["original_report"]["file_id"],
        "original_report_Drive_url":evidence["original_report"]["url"],
        "official_code_source":evidence["nbc105_2025_admission_rules"]["official_code_uri"],
        "code_revision":"NBC 105:2025 SECOND REVISION",
        "modals_evaluated_on_synthetic_R6p2":True,
        "site_authentication_gates":a["site_gates"],
        "original_source_conflicts":a["site_conflicts_open"],
        "seismic_mass_physical_vs_synthetic_status":"NON_COMPARABLE_DIFFERENT_MODELS",
        **{k:v for k,v in a.items() if k not in ("site_gates","site_conflicts_open")},
        "chapters":chapters,
        "release_scope":"R6P3_SITE_MASS_MODAL_EVIDENCE_GATE_NO_CODE_SCALING_NO_APPROVAL",
        "original_F3_failure":"NOT SAFE IN ONE WAY SHEAR",
        "original_accepted_evidence_gates":0,"original_required_evidence_gates":15,
        "engineering_approval":False,"permit_eligible":False,
        "reason_for_hold":"Original site jurisdiction, revised 2025 soil classification, physical mass and code-modal coverage are not independently authenticated. Reported original data are not executable design inputs.",
        "next_required_evidence":[
           "Cadastral/municipal approval tying the report's actual site to the jurisdiction and current NBC105:2025 zone table.",
           "Geotechnical report with valid Vs30 or SPT profile, site soil category independently reviewed.",
           "Signed original building occupancy/structural system and importance factor approval.",
           "Storey-by-storey approved physical dead/live mass participation with full ETABS exported mass ledger reconciliation.",
           "Validated actual-building eigenanalysis both axes with >=90% mass participation and missing-high-frequency assessment.",
           "Only after all upstream proof, independent ESM base shear and MRSM comparison to decide code scaling (drift/displacement not scaled per clause 7.5).",
           "Remedy and professionally verify original footing F3 NOT SAFE IN ONE WAY SHEAR."
         ]}
def _csv(rows,columns):
    b=io.StringIO();w=csv.writer(b,lineterminator="\n");w.writerow(columns)
    for r in rows:w.writerow([r.get(k) for k in columns])
    return b.getvalue()

def render_html(r):
    e=lambda x:html.escape(str(x),quote=True)
    gate_rows="".join(f'<tr><td>{e(g["id"])}</td><td>{e(g["status"])}</td><td>{e(g["reason"])}</td></tr>'
                      for g in r["site_authentication_gates"])
    modal="".join(f'<tr><td>{x["mesh"]}</td><td>{e(x["diaphragm_mode"])}</td><td>{x["axis"]}</td><td>{x["eligible_under_33Hz_mass_fraction"]:.4f}</td><td>{x["unrepresented_mass_fraction"]:.4f}</td><td>{e(x["numerical_90pct_eligible_mass_screen"])}</td></tr>'
         for x in r["modal_synthetic_participation_screen"])
    chapters="".join(f'<section><h2>Chapter {e(c["id"])} — {e(c["title"])}</h2><table><tr><th>Module</th><th>Status</th></tr>'+''.join(f'<tr><td>{e(a["id"])}</td><td>{e(a["status"])}</td></tr>' for a in c["modules"])+"</table></section>" for c in r["chapters"])
    conflicts="".join(f'<li><strong>{e(c["key"])}:</strong> {e(" vs ".join(c["source_assertions"]))}</li>'
                     for c in r["original_source_conflicts"])
    nexts="".join("<li>"+e(x)+"</li>" for x in r["next_required_evidence"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>R6.3 Site/mass evidence gate and modal 90% screening</title>
<style>body{{font:14px/1.5 system-ui;max-width:1150px;margin:auto;padding:18px;color:#263e55;background:#f4f7fb}}header,section{{background:#fff;border:1px solid #d5deec;border-radius:12px;margin:14px 0;padding:20px}}.warn{{border-left:5px solid #ba5347;background:#fff0e8;padding:12px}}table{{width:100%;border-collapse:collapse;font-size:12px;min-width:600px}}th,td{{border:1px solid #d4dce7;padding:7px;text-align:left}}th{{background:#edf2f9}}.scroll{{overflow:auto}}a{{color:#245e95}}@media print{{body{{background:white}}}}</style></head><body><header>
<small>JP STRUCTURAL · R6.3 · SOURCE EVIDENCE ADMISSION · NBC 105:2025</small>
<h1>Original site and physical mass authentication: HELD</h1>
<p class="warn"><strong>NOT VERIFIED FOR STRUCTURAL DESIGN.</strong> {r["gates_on_hold"]} independent evidence gates remain on HOLD; no actual project response spectrum, scaling factor, accepted mass or engineer permit sign-off was produced. The original F3 still states <strong>NOT SAFE IN ONE WAY SHEAR</strong>.</p>
<p>Original ETABS PDF <a href="{e(r["original_report_Drive_url"])}">source report</a> reports seismic weight <strong>{r["real_ETABS_mass_kN_reported_not_verified"]:.4f} kN</strong>. Synthetic R6.2 mass weight is {r["synthetic_reference_weight_kN"]:.1f} kN for a DIFFERENT 4-column reference model. These figures cannot be equated or used for proportional seismic force scaling.</p>
<p><a href="{PFX}.json">Full source evidence and modal audit JSON</a> · <a href="{PFX}-gates.csv">Gate register CSV</a> · <a href="{PFX}-modal.csv">Synthetic modal adequacy screen CSV</a> · <a href="{PFX}-manifest.json">SHA-256 manifest</a></p></header>
<section><h2>Original ETABS source claims requiring proof</h2><ul>{conflicts}</ul><p>No accepted parcel record, geotechnical Vs30/SPT, approved 2025 municipal seismic zone entry, itemized floor mass export or engineer review receipt was located and admitted.</p><p>Official standard: <a href="{e(r["official_code_source"])}">NBC 105:2025 second revision</a>; Clause 7.3 requires at least 90% effective seismic mass per direction and prescribes a 33Hz missing-mass rule. This audit does not attempt design acceptance.</p></section>
<section><h2>Original building source admission gates</h2><div class="scroll"><table><tr><th>Gate</th><th>Status</th><th>Source/proof blocker</th></tr>{gate_rows}</table></div></section>
<section><h2>Measured R6.2 synthetic connected-shell modal participation</h2><p>The comparison below is a numerical diagnostic, NOT proof of original building code adequacy. First four modes, four modeled cases per mesh, and zero inferred slab interior mass.</p><div class="scroll"><table><tr><th>Mesh</th><th>Mode</th><th>Axis</th><th>Eligible mass (&lt;33Hz)</th><th>Unrepresented mass</th><th>Numerical 90% check</th></tr>{modal}</table></div></section>
<section><h2>Evidence to acquire before seismic scaling</h2><ol>{nexts}</ol><p><strong>Scaling not executed:</strong> NBC105:2025 Clause 7.5 requires ESM versus MRSM base-shear comparison before force scaling; it does not authorize scaling MRSM drift or displacement.</p></section>{chapters}</body></html>"""

def emit(ledger_path:Path,source_path:Path,settings_path:Path,output_dir:Path):
    e=json.loads(ledger_path.read_text(encoding="utf8"))
    source=json.loads(source_path.read_text(encoding="utf8"))
    settings=json.loads(settings_path.read_text(encoding="utf8"))
    modal=build_r6p2(spec=source,settings=settings,meshes=(2,4))
    r=build(e,modal)
    output_dir.mkdir(parents=True,exist_ok=True)
    files={
      PFX+".json":json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+"\n",
      PFX+".html":render_html(r),
      PFX+"-gates.csv":_csv(r["site_authentication_gates"],["id","status","description","reason","professional_approval"]),
      PFX+"-modal.csv":_csv(r["modal_synthetic_participation_screen"],
              ["mesh","diaphragm_mode","axis","source_effective_mass_fraction_first_modes",
               "eligible_under_33Hz_mass_fraction","unrepresented_mass_fraction",
               "included_mode_count","numerical_90pct_eligible_mass_screen","original_building_code_acceptance"])
    }
    for name,data in files.items():(output_dir/name).write_text(data,encoding="utf8")
    manifest={"schema":"jp.structural.r6p3.evidence_gate_manifest.v0.1",
       "evidence_ledger_sha256":r["original_source_ledger_SHA256"],
       "synthetic_modal_sha256":r["synthetic_connected_modal_report_SHA256"],
       "files":{k:hashlib.sha256(v.encode("utf8")).hexdigest() for k,v in files.items()},
       "scaling_not_executed":True,"engineering_approval":False}
    (output_dir/(PFX+"-manifest.json")).write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n",encoding="utf8")
    return r

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--evidence",type=Path,default=LEDGER)
    a.add_argument("--source",type=Path,default=DEFAULT)
    a.add_argument("--settings",type=Path,default=R6P2_SETTINGS)
    a.add_argument("--output-dir",type=Path,required=True)
    args=a.parse_args()
    r=emit(args.evidence,args.source,args.settings,args.output_dir)
    print("R6P3_EVIDENCE_HELD",r["gates_on_hold"],"GATES",
       r["modal_synthetic_90pct_screens_meeting"],"OF",r["modal_synthetic_screens_total"],
       "SYNTHETIC_SCREENS_NO_SCALING_OR_APPROVAL")
if __name__=="__main__":main()
