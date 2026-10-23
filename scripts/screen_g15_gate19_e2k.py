#!/usr/bin/env python3
"""G15 Gate19: local-only original E2K screening, independent source identity HOLD.

Reuses repository inventory and normalizer. Does not copy raw E2K or claim
that matching a candidate checksum authenticates the original project.
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from jp_structural.ingestion.e2k_inventory import inventory
from jp_structural.normalization.e2k_normalizer import normalize
from scripts.build_g15_gate18_mass_f3 import build as gate18

SCHEMA="jp.structural.g15.gate19.e2k_source_intake.v0.1"
SOURCE_SHA="f122904444a2e2f75230d9d4e41da0093d050da25c6e8140c86d466b7e37cc52"
BLOCKED_NAMES=("narayani","rambazzar","saugat","nabin","sabitri")
def result(status,checks=None,source=None,summary=None):
    base=gate18()
    assert base["source_report_sha256"]==SOURCE_SHA
    return {"schema":SCHEMA,"status":status,"source_report_sha256":SOURCE_SHA,
        "reported_ETABS_weight_kN":base["source_report_ETABS_seismic_W_kN"],
        "source_candidate_sha256":source["sha256"] if source else None,
        "source_candidate_bytes":source["bytes"] if source else None,
        "screen_checks":[{"code":k,"passed":bool(v)} for k,v in (checks or {}).items()],
        "inventory_summary":summary or {},
        "raw_model_uploaded":False,"raw_model_published":False,
        "source_model_identity_verified":False,
        "original_etabs_mass_settings_verified":False,
        "full_slab_wall_assignments_verified":False,
        "physical_mass_reconciled":False,
        "source_model_admitted":False,
        "f3_source_status":"NOT SAFE IN ONE WAY SHEAR",
        "engineering_approval":False,
        "next_step":"Obtain actual G+1.5 EDB/E2K and independent model-custodian identity evidence; verify units, area/line loads, mass source, and actual footing geotechnics."}

def build(path=None,expected_sha256=None):
    if path is None:
        return result("BLOCKED_ORIGINAL_ETABS_MODEL_NOT_FOUND",
            {"NATIVE_PROJECT_SOURCE_PRESENT":False,"SOURCE_IDENTITY_ATTESTED":False,
             "MASS_SOURCE_OBSERVED":False,"F3_APPROVED":False})
    p=Path(path)
    if not p.is_file() or p.suffix.lower()!=".e2k":
        return result("REJECT_NON_E2K_OR_MISSING")
    if not 0<p.stat().st_size<=40*1024*1024:
        return result("REJECT_FILE_SIZE")
    data=p.read_bytes()
    digest=hashlib.sha256(data).hexdigest()
    src={"sha256":digest,"bytes":len(data)}
    if not expected_sha256 or len(expected_sha256)!=64 or any(c not in "0123456789abcdef" for c in expected_sha256.lower()):
        return result("REJECT_NO_INDEPENDENT_HASH",source=src)
    if digest.lower()!=expected_sha256.lower():
        return result("REJECT_HASH_MISMATCH",source=src)
    try: text=data.decode("utf-8")
    except UnicodeDecodeError: return result("REJECT_UNSUPPORTED_ENCODING",source=src)
    if "$ END OF MODEL FILE" not in text or "$ PROGRAM INFORMATION" not in text:
        return result("REJECT_TRUNCATED_SOURCE",source=src)
    try:
        i=inventory(p)
        labels=" ".join((p.stem,i["project_info"].get("model_name") or "",
                         i["project_info"].get("title2") or "")).lower()
        units=i["program"]["units"]
        checks={
           "SOURCE_FILE_SHA_MATCH":True,
           "ETABS_PROGRAM":i["program"]["name"]=="ETABS",
           "N_MM_UNITS_FOR_NORMALIZER":units[:2]==["N","MM"],
           "NOT_KNOWN_OTHER_PROJECT":not any(x in labels for x in BLOCKED_NAMES),
           "MULTISTOREY_SOURCE_PRESENT":i["counts"]["stories"]>=4,
           "POINT_COORDINATES_PRESENT":i["counts"]["point_coordinate_records"]>0,
           "FRAME_CONNECTIVITIES_PRESENT":i["counts"]["line_connectivity_records"]>0,
           "AREA_CONNECTIVITIES_PRESENT":i["counts"]["area_connectivity_records"]>0,
           "MASS_SOURCE_PRESENT":i["section_record_counts"].get("MASS SOURCE",0)>0
        }
        if not all(checks.values()):
            return result("REJECT_SOURCE_INCOMPATIBLE",checks,src,
                {"units":units,"counts":i["counts"]})
        n=normalize(p)
    except (ValueError,TypeError,KeyError,IndexError,UnicodeError) as exc:
        return result("REJECT_NORMALIZER_ERROR",
            {"PARSER_SUCCESS":False},src,{"error_type":type(exc).__name__})
    m=n["mass_source"]
    checks.update({
        "CONNECTIVITY_REFERENCES_VALID":n["qa"]["status"]=="PASS_REFERENCE_INTEGRITY",
        "ASSIGNED_FRAME_INSTANCES":n["qa"]["counts"]["frames"]>0,
        "ASSIGNED_SLAB_INSTANCES":n["qa"]["counts"]["areas"]>0,
        "MASS_SOURCE_DEFINITION_PARSED":bool(m["definition"]),
        "MASS_COMPONENT_BASIS_DECLARED":bool(m["load_factors"]) or
            bool(m["definition"] and ("INCLUDELOADS" in m["definition"] or "INCLUDEELEMENTS" in m["definition"]))
    })
    summary={"etabs_version":i["program"]["version"],"units":units,
        "connectivity_counts":i["counts"],"normalized_counts":n["qa"]["counts"],
        "normalizer_warning_codes":sorted(set(x["code"] for x in n["qa"]["warnings"])),
        "mass_load_pattern_factor_count":len(m["load_factors"])}
    status="UNAUTHENTICATED_ETABS_CANDIDATE_REQUIRES_SOURCE_OWNER" if all(checks.values()) else "REJECT_SEMANTIC_INTEGRITY"
    checks["INDEPENDENT_THIS_BUILDING_SOURCE_IDENTITY"]=False
    checks["ORIGINAL_ETABS_STORY_MASS_REPRODUCED"]=False
    return result(status,checks,src,summary)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--e2k",type=Path)
    p.add_argument("--expected-sha256")
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    o=build(a.e2k,a.expected_sha256)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(o,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("GATE19_PROVENANCE_HOLD",o["status"])
    if a.e2k and o["status"].startswith("REJECT"):raise SystemExit(2)
if __name__=="__main__": main()
