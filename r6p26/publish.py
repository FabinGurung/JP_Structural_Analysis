"""Publish a six-chapter source-report-shaped Narayani analysis from actual OpenSees.

Public deliverable is a reviewed BOUNDED independent structural calculation,
not a final permit/structural design, and does not silently claim ETABS parity.
"""
from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import shutil

from r6p26.engine import make_spec, analyze, digest, EngineHold, CASE_NAMES

HERE=Path(__file__).resolve().parent
OUT="reports/r6p26"
SOURCE_NAME="narayani-independent-frame-source.json"
RESULT_NAME="narayani-independent-frame-results.json"
MEMBER_CSV="narayani-member-forces.csv"
REACTION_CSV="narayani-base-reactions.csv"
MANIFEST_NAME="narayani-verified-manifest.json"
SCHEMA="jp.structural.r6p26.report_reproduction_receipt.v0.1"

def json_dump(path:Path,data:dict)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,sort_keys=True,indent=2,ensure_ascii=False,
                               allow_nan=False)+"\n",encoding="utf-8")

def make_csv(path:Path,headers:list[str],rows:list[list])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf8",newline="") as stream:
        writer=csv.writer(stream);writer.writerow(headers);writer.writerows(rows)

def insert_navigation(site:Path)->list[str]:
    updated=[]
    for page in ("index.html","report.html","more.html","r6p23.html","r6p25.html"):
        path=site/page
        if not path.is_file():continue
        h=path.read_text(encoding="utf8")
        if 'href="r6p26-report.html"' in h:continue
        needle='href="r6p25.html"'
        if needle in h:
            h=h.replace(needle,'href="r6p26-report.html">Narayani Engine Report</a><a '+needle,1)
        else:
            if "</nav>" not in h:
                raise EngineHold("Existing report navigation not located: "+page)
            h=h.replace("</nav>",'<a href="r6p26-report.html">Narayani Engine Report</a></nav>',1)
        path.write_text(h,encoding="utf8")
        updated.append(page)
    return updated

def publish(cad_root:Path,site:Path)->dict:
    spec=make_spec(cad_root)
    result=analyze(spec)
    if result["professional_engineering_approval"] or result["construction_release"]:
        raise EngineHold("Real report cannot publish building safety approval")
    if result["member_design_checked"] or result["seismic_code_design_performed"]:
        raise EngineHold("Source input has not verified code member/seismic checks")
    site.mkdir(parents=True,exist_ok=True)
    out=site/OUT;out.mkdir(parents=True,exist_ok=True)
    json_dump(out/SOURCE_NAME,spec)
    json_dump(out/RESULT_NAME,result)
    member_rows=[]
    for case in CASE_NAMES:
        for m in result["cases"][case]["signed_local_member_forces"]:
            for end in ("I","J"):
                r=m["local_I_J"][end]
                member_rows.append([case,m["id"],m["type"],m["floor"],m["ni"],m["nj"],
                                    end,r["N"],r["Vy"],r["Vz"],r["T"],r["My"],r["Mz"],
                                    "ASSUMED_GEOMETRY_NOT_DESIGN_APPROVED"])
    make_csv(out/MEMBER_CSV,
      ["case","member","type","level","node_I","node_J","end",
       "N_kN","Vy_kN","Vz_kN","T_kNm","My_kNm","Mz_kNm","engineering_status"],member_rows)
    reaction_rows=[]
    for case in CASE_NAMES:
        for s in result["cases"][case]["base_support_reactions"]:
            reaction_rows.append([case,s["axis"],s["node"],s["Fx_kN"],
                s["Fy_kN"],s["Fz_kN"],s["Mx_kNm"],s["My_kNm"],s["Mz_kNm"],
                "FIXED_SUPPORT_NOT_SOIL_APPROVED"])
    make_csv(out/REACTION_CSV,
      ["case","axis","node","Fx_kN","Fy_kN","Fz_kN","Mx_kNm","My_kNm","Mz_kNm","engineering_status"],reaction_rows)
    for src,dst in (("report.html","r6p26-report.html"),
                    ("report.css","r6p26-report.css"),
                    ("report.js","r6p26-report.js")):
        shutil.copyfile(HERE/src,site/dst)
    updated=insert_navigation(site)
    targets=[
        "r6p26-report.html","r6p26-report.css","r6p26-report.js",
        f"{OUT}/{SOURCE_NAME}",f"{OUT}/{RESULT_NAME}",
        f"{OUT}/{MEMBER_CSV}",f"{OUT}/{REACTION_CSV}",
    ]
    receipt={
        "schema":SCHEMA,
        "source_sha256":digest(spec),
        "result_sha256":digest(result),
        "modeled_source_CAD_sha":spec["geometry_source_cad_commit"],
        "opensees_cases":list(CASE_NAMES),
        "signed_member_end_actions_csv_rows":len(member_rows),
        "support_reaction_csv_rows":len(reaction_rows),
        "navigation_pages_linked":updated,
        "source_original_report_restructured":True,
        "independent_engine_recalculated":True,
        "complete_building_design":False,
        "NBC105_code_seismic_assessed":False,
        "F3_one_way_shear_unsafe_preserved":True,
        "engineering_approval":False,
        "files_sha256":{p:sha256((site/p).read_bytes()).hexdigest() for p in targets}
    }
    json_dump(out/MANIFEST_NAME,receipt)
    verify(site)
    return receipt


def verify(site:Path)->dict:
    d=json.loads((site/OUT/MANIFEST_NAME).read_text(encoding="utf8"))
    if d.get("schema")!=SCHEMA or d.get("engineering_approval") is not False or \
       d.get("complete_building_design") is not False or \
       d.get("F3_one_way_shear_unsafe_preserved") is not True:
        raise EngineHold("Report release/unsafe F3 classification changed")
    for name,hashval in d["files_sha256"].items():
        path=site/name
        if not path.is_file() or sha256(path.read_bytes()).hexdigest()!=hashval:
            raise EngineHold("R6.26 output SHA256/readback failed: "+name)
    spec=json.loads((site/OUT/SOURCE_NAME).read_text(encoding="utf8"))
    result=json.loads((site/OUT/RESULT_NAME).read_text(encoding="utf8"))
    if digest(spec)!=d["source_sha256"] or digest(result)!=d["result_sha256"]:
        raise EngineHold("R6.26 report data/source fingerprints disagree")
    if result["model_source_digest"]!=digest(spec):
        raise EngineHold("Results do not descend from the actual published source model")
    if result["original_F3_unsafe_status_retained"] is not True or \
       result["model_counts"]["actual_NBC105_seismic_design_cases"]!=0 or \
       result["model_counts"]["fully_verified_beam_column_connections"]!=0:
        raise EngineHold("R6.26 incorrectly claims structural/code design readiness")
    html=(site/"r6p26-report.html").read_text(encoding="utf8")
    expected=("1.0 Introduction","2.0 General Data","3.0 Analysis and Design Procedure",
              "4.0 Independent OpenSees","5.0 Design Output","6.0 Design",
              "NOT SAFE IN ONE WAY SHEAR","Engineering HOLD",
              "reports/r6p26/narayani-independent-frame-results.json")
    if not all(x in html for x in expected):
        raise EngineHold("Original structural report chapter skeleton or engineering hold missing")
    for case in CASE_NAMES:
        c=result["cases"][case]
        if len(c["signed_local_member_forces"]) != len(result["source_members"]) or \
           c["max_6axis_equilibrium_residual"]>=1e-4:
            raise EngineHold("Report member action or true 6DOF equilibrium incomplete "+case)
    return d

def main()->None:
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--cad-root",type=Path,required=True)
    cli.add_argument("--site-dir",type=Path,required=True)
    args=cli.parse_args()
    m=publish(args.cad_root,args.site_dir)
    print(json.dumps({
        "R6P26_INDEPENDENT_SOURCE_REPORT_VERIFIED":True,
        "real_engine_cases":len(m["opensees_cases"]),
        "member_end_action_records":m["signed_member_end_actions_csv_rows"],
        "support_reaction_records":m["support_reaction_csv_rows"],
        "source_sha256":m["source_sha256"],
        "engineering_approval":False,
    },sort_keys=True))

if __name__=="__main__":
    main()
