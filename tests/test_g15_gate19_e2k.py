"""Original-model E2K ingestion must be fail closed."""
from pathlib import Path
from hashlib import sha256
from scripts.screen_g15_gate19_e2k import build
E2K='''$ PROGRAM INFORMATION
 PROGRAM "ETABS" VERSION "21.0.0"
$ CONTROLS
 UNITS "N" "MM" "C"
$ STORIES - IN SEQUENCE FROM TOP
 STORY "Story3" HEIGHT 3000
 STORY "Story2" HEIGHT 3000
 STORY "Story1" HEIGHT 3000
 STORY "Base" ELEV 0
$ POINT COORDINATES
 POINT "1" 0 0
 POINT "2" 4965 0
 POINT "3" 4965 3600
 POINT "4" 0 3600
$ LINE CONNECTIVITIES
 LINE "C1" COLUMN "1" "1" 1
 LINE "B1" BEAM "1" "2" 0
$ AREA CONNECTIVITIES
 AREA "A1" FLOOR 4 "1" "2" "3" "4" 0 0 0 0
$ LINE ASSIGNS
 LINEASSIGN "C1" "Story1" SECTION "C"
 LINEASSIGN "B1" "Story1" SECTION "B"
$ AREA ASSIGNS
 AREAASSIGN "A1" "Story2" SECTION "S"
$ LOAD PATTERNS
 LOADPATTERN "Dead" TYPE "Dead" SELFWEIGHT 1
$ MASS SOURCE
 MASSSOURCE "Ms1" INCLUDEELEMENTS "Yes" INCLUDELOADS "Yes"
 MASSSOURCELOAD "Ms1" "Dead" 1
$ END OF MODEL FILE
'''
def fixture(tmp_path,txt=E2K,name="synthetic.e2k"):
 p=tmp_path/name;p.write_text(txt,encoding="utf-8")
 return p,sha256(p.read_bytes()).hexdigest()

def test_not_found_records_are_true_holds():
 d=build()
 assert d["status"]=="BLOCKED_ORIGINAL_ETABS_MODEL_NOT_FOUND"
 assert d["reported_ETABS_weight_kN"]==6831.9109
 assert not d["source_model_admitted"] and not d["physical_mass_reconciled"]
 assert d["f3_source_status"]=="NOT SAFE IN ONE WAY SHEAR"

def test_complete_synthetic_candidate_never_accepted_as_this_building(tmp_path):
 p,h=fixture(tmp_path)
 d=build(p,h)
 assert d["status"]=="UNAUTHENTICATED_ETABS_CANDIDATE_REQUIRES_SOURCE_OWNER",d
 assert d["inventory_summary"]["normalized_counts"]["areas"]==1
 assert d["inventory_summary"]["normalized_counts"]["frames"]==2
 assert d["inventory_summary"]["mass_load_pattern_factor_count"]==1
 assert not d["source_model_identity_verified"]
 assert not d["source_model_admitted"] and not d["engineering_approval"]
 assert not d["raw_model_published"] and not d["raw_model_uploaded"]

def test_mismatched_hash_and_missing_hash_rejected(tmp_path):
 p,h=fixture(tmp_path)
 assert build(p)["status"]=="REJECT_NO_INDEPENDENT_HASH"
 assert build(p,"0"*64)["status"]=="REJECT_HASH_MISMATCH"

def test_known_unrelated_project_and_wrong_units_rejected(tmp_path):
 p,h=fixture(tmp_path,name="NARAYANI_MODEL.e2k")
 assert build(p,h)["status"]=="REJECT_SOURCE_INCOMPATIBLE"
 p2,h2=fixture(tmp_path,E2K.replace('UNITS "N" "MM"','UNITS "KN" "M"'))
 assert build(p2,h2)["status"]=="REJECT_SOURCE_INCOMPATIBLE"

def test_missing_point_reference_and_missing_area_rejected(tmp_path):
 p,h=fixture(tmp_path,E2K.replace('"1" "2" "3" "4"','"1" "2" "999" "4"'))
 assert build(p,h)["status"]=="REJECT_SEMANTIC_INTEGRITY"
 p2,h2=fixture(tmp_path,E2K.replace(' AREA "A1" FLOOR',' SKIPAREA "A1" FLOOR'))
 assert build(p2,h2)["status"]=="REJECT_SOURCE_INCOMPATIBLE"
