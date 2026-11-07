"""R6.5 privacy-preserving conditional original-storey mass preflight tests."""
import copy
import csv
import hashlib
import json
from pathlib import Path
import pytest
from scripts.build_r6p4_physical_mass_intake import HEADERS, MassIntakeError
from scripts.build_r6p5_original_storey_mass_preflight import (
    build, emit, source_benchmark, private_conditional_comparison,
    GATE18, R6P4_SOURCE, SOURCE_STORIES
)

def test_conditional_printed_story_mass_is_arithmetic_not_composition():
    r=build()
    assert r["reported_original_ETABS_weight_kN"]==6831.9109
    assert abs(r["story_table_vs_report_rounding_delta_kN"])<=r["source_precision_bound_kN"]
    assert r["gate08_hypothetical_wall_case_unexplained_kN"]==772.032917
    assert r["source_story_count"]==3
    assert r["private_comparison"]["conditional_all_three_story_numeric_match"] is None
    assert not r["real_original_mass_approved"] and not r["engineering_approval"]
    assert r["MRSM_scale_factor"] is None and not r["MRSM_scaling_executed"]
    assert r["f3_source_verdict"]=="NOT SAFE IN ONE WAY SHEAR"

def test_report_mass_and_source_identity_tampering_blocked():
    a=json.loads(GATE18.read_text())
    b=json.loads(R6P4_SOURCE.read_text())
    a["source_pdf"]["sha256"]="0"*64
    with pytest.raises(MassIntakeError,match="identity"):
        source_benchmark(a,b)
    a=json.loads(GATE18.read_text())
    a["source_mass_table"]["reported_stories"][0]["printed_mass_value"]+=5000
    with pytest.raises(MassIntakeError,match="do not reproduce"):
        source_benchmark(a,b)

def test_units_f3_and_physical_approvals_cannot_be_silently_reclassified():
    a=json.loads(GATE18.read_text()); b=json.loads(R6P4_SOURCE.read_text())
    a["source_mass_table"]["units_explicitly_printed"]=True
    with pytest.raises(MassIntakeError,match="unverified kg"):
        source_benchmark(a,b)
    a=json.loads(GATE18.read_text()); a["f3_source"]["as_issued_one_way_shear_verdict"]="SAFE"
    with pytest.raises(MassIntakeError,match="F3"):
        source_benchmark(a,b)
    a=json.loads(GATE18.read_text()); b["engineering_approval"]=True
    with pytest.raises(MassIntakeError,match="authentication"):
        source_benchmark(a,b)

def test_private_input_requires_mapping_pair(tmp_path):
    with pytest.raises(MassIntakeError,match="provided together"):
        build(tmp_path/"private.csv",None)

def fixture_private(tmp_path, difference=False, extra=False):
    expected,_=source_benchmark()
    ids=("FLOOR-X1","FLOOR-X2","FLOOR-X3")
    rows=[]
    for i,(name,ref) in enumerate(zip(SOURCE_STORIES,ids)):
        value=expected[name]
        if difference and i==1:value+=1
        rows.append(dict(zip(HEADERS,(
          ref, "TEST_COMPONENT", "DEAD_SLAB", str(value),
          "m2","1","1","a"*64,"test-private-fixture-"+str(i),
          "", "UNVERIFIED"
        ))))
    if extra:rows.append({**rows[0],"component_ref":"DUPLICATE_FLOOR_EXTRA","floor_ref":"FLOOR-X4"})
    path=tmp_path/"PRIVATE_TEST_LEDGER.csv"
    with path.open("w",encoding="utf8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=HEADERS); w.writeheader();w.writerows(rows)
    mapping={
      "schema":"jp.structural.r6p5.private_story_mapping.v0.1",
      "original_native_ETABS_export_sha256":"b"*64,
      "independent_floor_mapping_receipt_sha256":"c"*64,
      "source_units_status":"CONDITIONAL_KG_NOT_NATIVE_VERIFIED",
      "floor_bindings":[{"reported_story":name,"private_floor_ref":ref} for name,ref in zip(SOURCE_STORIES,ids)]
    }
    m=tmp_path/"PRIVATE_TEST_MAPPING.json";m.write_text(json.dumps(mapping))
    return path,m

def test_private_numeric_match_still_never_accepts_design(tmp_path):
    p,m=fixture_private(tmp_path)
    r=build(p,m)
    s=r["private_comparison"]
    assert s["private_floor_count"]==3
    assert s["conditional_all_three_story_numeric_match"] is True
    assert not s["independently_authenticated_ETABS_export"]
    assert not s["professional_review_authenticated"]
    assert not s["actual_building_mass_accepted"]
    assert not r["real_original_mass_approved"]

def test_private_story_mismatch_held(tmp_path):
    p,m=fixture_private(tmp_path,difference=True)
    r=build(p,m)
    assert r["private_comparison"]["conditional_all_three_story_numeric_match"] is False

def test_unmapped_private_floor_never_counted_as_complete(tmp_path):
    p,m=fixture_private(tmp_path,extra=True)
    with pytest.raises(MassIntakeError,match="unmapped floors"):
        build(p,m)

def test_report_privacy_and_reproducibility(tmp_path):
    p,m=fixture_private(tmp_path)
    out=tmp_path/"public"/"r6p5.json"
    r=emit(out,p,m)
    text=out.read_text()
    assert "FLOOR-X" not in text and "TEST_COMPONENT" not in text
    assert "test-private-fixture" not in text
    assert "PRIVATE_TEST_LEDGER" not in text
    assert '"actual_building_mass_accepted": false' in text
    assert "SOURCE_REPORTED_KG_INFERENCE" in text
    receipt=json.loads((out.parent/"r6p5-manifest.json").read_text())
    assert receipt["json_sha256"]==hashlib.sha256(text.encode()).hexdigest()
    assert receipt["private_source_rows_exported"] is False
    assert r["source_story_count"]==3
