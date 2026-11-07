"""R6.3 physical source and mass admission fails closed before NBC spectral scaling."""
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
import pytest
from scripts.build_r6p3_site_mass_modal_admission import (
    LEDGER, PFX, GATES,AdmissionError,
    audit_evidence,audit_modal_participation,build,emit,
)
from scripts.build_r6_connected_shell_modal import (
    build as connected_modal,DEFAULT,SETTINGS
)

@pytest.fixture(scope="module")
def source():
    return json.loads(LEDGER.read_text(encoding="utf8"))

@pytest.fixture(scope="module")
def modal():
    return connected_modal(meshes=(2,4))

@pytest.fixture(scope="module")
def audited(source,modal):
    return build(source,modal)

def test_original_drive_report_claims_remain_source_assertions_not_accepted(source,audited):
    assert source["original_report"]["file_id"]=="1TpWUmOdrcQqOpkN6qvmhZ12KrYaNABBM"
    assert source["original_report"]["source_document_located_and_text_read"] is True
    claims=source["original_report_assertions"]
    assert claims["address_general"]=="Pokhara"
    assert "Leknath" in claims["location_phrase"]
    assert "Kathmandu" in claims["seismic_zone_phrase"]
    assert claims["soil_profile_description"]=="Medium Soil Site"
    assert "D" in claims["soil_class"]
    assert claims["zone_factor_Z"]==pytest.approx(0.35)
    assert claims["seismic_weight_ETABS_reported_kN"]==pytest.approx(6831.9109)
    assert claims["reported_F3_verdict"]=="NOT SAFE IN ONE WAY SHEAR"
    assert len(audited["original_source_conflicts"])==3
    assert all(g["status"]=="HOLD" for g in audited["site_authentication_gates"])
    assert audited["gates_on_hold"]==8
    assert [g["id"] for g in audited["site_authentication_gates"]]==list(GATES)

def test_original_building_mass_never_substituted_with_synthetic_reference(audited,modal):
    assert audited["real_ETABS_mass_kN_reported_not_verified"]==pytest.approx(6831.9109)
    assert audited["synthetic_reference_weight_kN"]==pytest.approx(111.2)
    assert audited["seismic_mass_physical_vs_synthetic_status"]=="NON_COMPARABLE_DIFFERENT_MODELS"
    assert audited["actual_vs_synthetic_mass_comparison_valid"] is False
    assert audited["real_independent_mass_reconciliation_completed"] is False
    assert audited["original_building_mass_source_admitted"] is False
    assert audited["real_project_MRSM_scale_factor"] is None
    assert audited["ESM_MRSM_code_scaling_executed"] is False
    assert audited["original_F3_failure"]=="NOT SAFE IN ONE WAY SHEAR"
    assert audited["original_accepted_evidence_gates"]==0
    assert audited["original_required_evidence_gates"]==15
    assert not audited["engineering_approval"] and not audited["permit_eligible"]
    assert modal["source_total_gravity_kN"]==pytest.approx(128)

def test_real_r6p2_numeric_modal_screens_each_axis_mesh_mode_without_claiming_original_acceptance(audited,modal):
    screens=audited["modal_synthetic_participation_screen"]
    assert len(screens)==8
    assert len({(r["mesh"],r["axis"],r["diaphragm_mode"]) for r in screens})==8
    assert all(r["mesh"] in (2,4) and r["axis"] in ("X","Y") for r in screens)
    assert all(0<=r["source_effective_mass_fraction_first_modes"]<=1.001
               for r in screens)
    assert all(0<=r["eligible_under_33Hz_mass_fraction"]<=1.001
               for r in screens)
    assert all(r["unrepresented_mass_fraction"]>=-0.001 for r in screens)
    assert all(r["original_building_code_acceptance"] is False for r in screens)
    assert all(r["not_mode_convergence_verified"] is True for r in screens)
    assert all(r["numerical_90pct_eligible_mass_screen"] in (
        "MEETS_IN_SYNTHETIC_CASE","INSUFFICIENT_IN_SYNTHETIC_CASE") for r in screens)
    assert audited["modal_synthetic_screens_total"]==8
    assert audited["modal_synthetic_90pct_screens_meeting"]==sum(
        r["eligible_under_33Hz_mass_fraction"]>=.9-1e-10 for r in screens)
    assert audited["original_building_modal_compliance"] is False

def test_fail_closed_invalid_90pct_or_33Hz_code_rule(source,modal):
    for name,value in (("modal_fraction_required_each_direction",0.80),
                       ("frequency_cutoff_for_modal_combination_Hz",99)):
        e=copy.deepcopy(source)
        e["nbc105_2025_admission_rules"][name]=value
        with pytest.raises(AdmissionError,match="criteria have changed"):
            audit_evidence(e,modal)

def test_fail_closed_invented_mass_or_documentary_approval(source,modal):
    e=copy.deepcopy(source)
    e["original_report_assertions"]["seismic_weight_ETABS_reported_kN"]=111.2
    with pytest.raises(AdmissionError,match="original mass statement inconsistent"):
        audit_evidence(e,modal)
    e=copy.deepcopy(source)
    e["synthetic_R6p2_reference"]["may_not_replace_or_scale_original_mass"]=False
    with pytest.raises(AdmissionError,match="separate"):
        audit_evidence(e,modal)
    e=copy.deepcopy(source)
    e["overall_engineering_approval"]=True
    with pytest.raises(AdmissionError,match="no original engineer approval"):
        audit_evidence(e,modal)
    e=copy.deepcopy(source)
    e["original_report"]["file_id"]="WRONG"
    with pytest.raises(AdmissionError,match="PDF identity"):
        audit_evidence(e,modal)

def test_fail_closed_modal_mass_participation_corruption(source,modal):
    code=source["nbc105_2025_admission_rules"]
    wrong=copy.deepcopy(modal)
    wrong["participation_summaries"][0]["modes"][0]["participation_fraction"]=2.
    with pytest.raises(AdmissionError,match="cumulative|exceeded"):
        audit_modal_participation(wrong,code)
    wrong=copy.deepcopy(modal)
    wrong["participation_summaries"].pop()
    with pytest.raises(AdmissionError,match="coverage"):
        audit_modal_participation(wrong,code)
    wrong=copy.deepcopy(modal)
    wrong["same_R5p6_connected_shell_FE"]=False
    with pytest.raises(AdmissionError,match="actual source-mass"):
        audit_modal_participation(wrong,code)

def test_mode_high_frequency_is_not_counted_towards_eligible_cqc_mass(source,modal):
    c=copy.deepcopy(modal)
    report=c["participation_summaries"][0]
    # Move the last mode above NBC's 33Hz threshold while preserving
    # its original effective mass/cumulative values for this targeted audit.
    report["modes"][3]["omega_rad_s"]=2*math.pi*40
    x=audit_modal_participation(c,source["nbc105_2025_admission_rules"])[0]
    assert x["excluded_at_or_above_33Hz_modes"]
    assert x["eligible_under_33Hz_mass_fraction"] <= x["source_effective_mass_fraction_first_modes"]
    assert x["needs_high_frequency_missing_mass_assessment"]
    assert not x["original_building_code_acceptance"]

def test_seven_chapters_artifact_SHA_report_annex_and_gate_CSV(tmp_path):
    r=emit(LEDGER,DEFAULT,SETTINGS,tmp_path)
    manifest=json.loads((tmp_path/(PFX+"-manifest.json")).read_text())
    assert manifest["engineering_approval"] is False
    assert manifest["scaling_not_executed"] is True
    assert len(manifest["files"])==4
    for name,checksum in manifest["files"].items():
        assert hashlib.sha256((tmp_path/name).read_bytes()).hexdigest()==checksum
    assert len(list(csv.DictReader((tmp_path/(PFX+"-gates.csv")).open())))==8
    assert len(list(csv.DictReader((tmp_path/(PFX+"-modal.csv")).open())))==8
    html=(tmp_path/(PFX+".html")).read_text()
    assert "NOT VERIFIED FOR STRUCTURAL DESIGN" in html
    assert "6831.9109" in html
    assert "NOT SAFE IN ONE WAY SHEAR" in html
    assert r["gates_on_hold"]==8
    assert [x["id"] for x in r["chapters"]]==[f"{i:02d}" for i in range(1,8)]
    assert {x["id"] for c in r["chapters"] for x in c["modules"]}=={
        *(f"M{i:02d}" for i in range(1,17)),"S17","S18"}
    master=(Path(__file__).resolve().parents[1]/"site/report.html").read_text()
    assert 'id="annex-r6p3-site-mass-admission"' in master
    assert "reports/r6p3-seismic-evidence-admission.html" in master
