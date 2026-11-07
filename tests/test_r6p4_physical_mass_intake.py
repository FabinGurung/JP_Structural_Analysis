"""R6.4 source-controlled original site/mass admission and private component QA."""
import copy
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import pytest
from scripts.build_r6p4_physical_mass_intake import (
    SOURCE,PARENT,INTAKE,PFX,HEADERS,MassIntakeError,
    audit,build,emit,load_components,
)

@pytest.fixture
def source():
    return json.loads(SOURCE.read_text())

@pytest.fixture
def previous():
    return json.loads(PARENT.read_text())

def write_private(path,rows):
    with path.open("w",encoding="utf8",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=HEADERS,lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

def row(**changes):
    data={
     "floor_ref":"FLOOR-A","component_ref":"COMPONENT-001","load_category":"DEAD_SLAB",
     "quantity":"10","quantity_unit":"m3","unit_weight_kN_per_unit":"25",
     "seismic_participation_fraction":"1",
     "source_document_sha256":"a"*64,
     "source_evidence_ref":"private:measured-quantity-source",
     "independent_review_sha256":"",
     "independent_review_status":"UNVERIFIED"
    }
    data.update(changes);return data

def test_original_vs_two_provisional_mass_scenarios_correct_and_residual_open():
    r=build()
    assert r["schema"]=="jp.structural.r6p4.physical_mass_preflight.v0.1"
    assert r["original_ETABS_reported_weight_kN"]==pytest.approx(6831.9109)
    scenarios=r["gate08_conditional_mass_comparisons"]
    assert [x["id"] for x in scenarios]==["NO_WALLS","CANDIDATE_WALLS_ONLY"]
    assert scenarios[0]["conditional_mass_kN"]==pytest.approx(5520.483743)
    assert scenarios[1]["conditional_mass_kN"]==pytest.approx(6059.877983)
    assert r["conditional_candidate_wall_increment_kN"]==pytest.approx(539.394240)
    assert scenarios[0]["source_unexplained_gap_kN"]==pytest.approx(1311.427157)
    assert scenarios[1]["source_unexplained_gap_kN"]==pytest.approx(772.032917)
    assert r["gap_after_conditional_wall_scenario_kN"]==pytest.approx(772.032917)
    assert r["conditional_mass_reconciliation_status"]=="UNRESOLVED_PHYSICAL_RESIDUAL"
    assert not r["prior_mass_candidate_explains_full_ETABS"]

def test_old_etabs_source_separate_from_synthetic_and_private_raw_data_not_published():
    r=build()
    assert r["source_input_sha256"]
    assert len(r["private_checkpoint_sha256"])==64
    assert len(r["private_archive_sha256"])==64
    assert r["private_physical_component_status"]=="NO_PHYSICAL_COMPONENTS_SUPPLIED"
    assert r["private_physical_components_summary"]["component_count"]==0
    assert r["private_physical_components_summary"]["global_preliminary_component_seismic_kN"] is None
    assert not r["private_physical_components_summary"]["raw_private_row_or_floor_breakdown_publicly_exported"]
    assert all(not x["admitted_for_original_seismic_design"] for x in r["source_evidence_catalog"])
    assert len(r["source_evidence_catalog"])==9
    assert r["R6p3_site_gates_closed"]==0
    assert r["R6p3_site_gates_total"]==8
    assert r["original_physical_gates_closed"]==0
    assert r["original_physical_gates_total"]==15
    assert r["original_F3_failure"]=="NOT SAFE IN ONE WAY SHEAR"
    assert not r["real_physical_mass_reconciled"]
    assert not r["original_building_seismic_mass_approved"]
    assert r["MRSM_scale_factor"] is None
    assert not r["MRSM_scaling_executed"]
    assert not r["engineering_approval"]

def test_private_component_arithmetic_preserves_fraction_and_redacts_rows(tmp_path):
    path=tmp_path/"PRIVATE.csv"
    write_private(path,[row(),row(
       component_ref="COMPONENT-002",floor_ref="FLOOR-B",
       quantity="8",unit_weight_kN_per_unit="2",
       seismic_participation_fraction=".30",load_category="LIVE_IMPOSED")])
    c=load_components(path)
    assert c["component_count"]==2
    assert c["floor_count"]==2
    assert c["global_preliminary_component_gravity_kN"]==pytest.approx(266)
    assert c["global_preliminary_component_seismic_kN"]==pytest.approx(254.8)
    assert c["unverified_row_count"]==2
    assert "floor_labels" not in c
    assert c["original_floor_mass_approved"] is False
    result=build(components=c)
    assert result["private_physical_component_status"]=="PRIVATE_COMPONENT_ARITHMETIC_ONLY"
    assert result["private_preliminary_remaining_mass_gap_kN"]==pytest.approx(6577.1109)
    assert result["real_physical_mass_reconciled"] is False
    assert "private:measured" not in json.dumps(result)

@pytest.mark.parametrize("change,expected",[
  ({"quantity":""},"finite decimal"),
  ({"quantity":"-5"},"positive"),
  ({"unit_weight_kN_per_unit":"nan"},"finite"),
  ({"seismic_participation_fraction":"1.1"},"between 0 and 1"),
  ({"load_category":"EXCLUDED","seismic_participation_fraction":"0.5"},"excluded"),
  ({"load_category":"DENSITY_GUESSED"},"catalog"),
  ({"quantity_unit":"feet"},"physical units"),
  ({"source_document_sha256":""},"SHA256"),
  ({"independent_review_status":"INDEPENDENTLY_REVIEWED"},"signed-review SHA256"),
  ({"independent_review_status":"APPROVED_BY_AI"},"review status"),
])
def test_private_component_fail_closed_on_missing_or_untrusted_inputs(tmp_path,change,expected):
    path=tmp_path/"PRIVATE.csv"
    write_private(path,[row(**change)])
    with pytest.raises(MassIntakeError,match=expected):
        load_components(path)

def test_missing_ledger_and_double_count_rejected(tmp_path):
    with pytest.raises(MassIntakeError,match="not supplied"):
        load_components(tmp_path/"MISSING.csv")
    path=tmp_path/"PRIVATE.csv"
    write_private(path,[row(),row()])
    with pytest.raises(MassIntakeError,match="double-count"):
        load_components(path)

def test_review_document_sha_required_but_still_no_professional_approval(tmp_path):
    path=tmp_path/"PRIVATE.csv"
    write_private(path,[row(
      independent_review_status="INDEPENDENTLY_REVIEWED",
      independent_review_sha256="b"*64,
      quantity="6831.9109",unit_weight_kN_per_unit="1",
      seismic_participation_fraction="1"
    )])
    c=load_components(path)
    assert c["independently_reviewed_row_count"]==1
    r=build(components=c)
    assert r["private_preliminary_remaining_mass_gap_kN"]==pytest.approx(0)
    assert not r["real_physical_mass_reconciled"]
    assert not r["original_building_seismic_mass_approved"]
    assert r["MRSM_scale_factor"] is None
    assert not r["engineering_approval"]

@pytest.mark.parametrize("change,expected",[
  (lambda s:s.update(reported_original_ETABS_seismic_weight_kN=111.2),"disagrees"),
  (lambda s:s.update(gate08_incremental_candidate_wall_weight_kN=0),"positive"),
  (lambda s:s["scenarios"][1].update(seismic_weight_kN=6831.9109),"order"),
  (lambda s:s["source_lineage"].update(gate08_private_archive_sha256="abc"),"hash"),
  (lambda s:s.update(direct_original_ETABS_mass_export_found=True),"not authenticated"),
  (lambda s:s.update(scale_factor_generated=True),"scaling"),
  (lambda s:s.update(original_foundation_F3_verdict="SAFE"),"F3"),
  (lambda s:s["source_lineage"].update(full_private_source_model_released_publicly=True),"private source"),
])
def test_source_tampering_cannot_close_gap_or_original_engineering_holds(source,previous,change,expected):
    s=copy.deepcopy(source);change(s)
    with pytest.raises(MassIntakeError,match=expected):
        audit(s,previous,load_components(INTAKE))

def test_sar_seven_chapters_and_hashed_reports(tmp_path):
    r=emit(tmp_path)
    manifest=json.loads((tmp_path/(PFX+"-manifest.json")).read_text())
    assert len(manifest["files"])==4
    assert manifest["physical_reconciliation_complete"] is False
    assert manifest["no_design_spectrum_or_scaling"] is True
    assert manifest["engineering_approval"] is False
    for fname,h in manifest["files"].items():
        assert hashlib.sha256((tmp_path/fname).read_bytes()).hexdigest()==h
    rows=list(csv.DictReader((tmp_path/(PFX+"-scenarios.csv")).open()))
    sources=list(csv.DictReader((tmp_path/(PFX+"-sources.csv")).open()))
    assert len(rows)==2 and len(sources)==9
    html=(tmp_path/(PFX+".html")).read_text()
    assert "NOT AN APPROVED BUILDING DESIGN" in html
    assert "772.032917" in html
    assert "NOT SAFE IN ONE WAY SHEAR" in html
    assert len(r["chapters"])==7
    assert {m["id"] for c in r["chapters"] for m in c["modules"]}=={
      *(f"M{i:02d}" for i in range(1,17)),"S17","S18"}
    page=(Path(__file__).resolve().parents[1]/"site/report.html").read_text()
    assert 'id="annex-r6p4-physical-mass"' in page
    assert "reports/r6p4-mass-source-reconciliation.html" in page
