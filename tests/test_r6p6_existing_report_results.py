"""R6.6: existing report output reuse, provenance, and fail-closed engineering status."""
from copy import deepcopy
from hashlib import sha256
import json
import pytest
from scripts.build_r6p6_existing_report_results import (
    BenchmarkError, load_sources, evaluate, build, SOURCE, GOVERNING, GATE18,
)


def test_old_report_values_are_audit_benchmark_not_new_model_output():
    d=load_sources()
    r=evaluate(d)
    assert r["report_seismic_weight_kN"]==6831.9109
    assert abs(r["report_story_mass_arithmetic_kN_if_kg"]-6831.9109)<0.0002
    assert r["reported_units_explicit"] is False
    assert len(r["reported_static_cases"])==4
    assert {x["base_shear_kN"] for x in r["reported_static_cases"]}=={894.9803,860.8208}
    assert not r["independent_current_etabs21_results_reproduced"]
    assert not r["MRSM_scaling_executed"] and not r["engineering_approval"]


def test_report_modes_are_preserved_and_prose_conflict_explicit():
    r=evaluate(load_sources())
    assert len(r["report_modal_rows"])==12
    assert r["report_modal_rows"][4]["sum_ux"]==0.9297
    assert r["report_modal_rows"][4]["sum_uy"]==0.9538
    assert r["first_report_table_mode_to_reach_90pct_in_both_axes"]==5
    assert r["mode_count_source_disagreement"]=="REPORT_PROSE_SIX_VS_CUMULATIVE_TABLE_FIVE"


def test_report_member_samples_not_full_force_solution():
    r=evaluate(load_sources())
    assert len(r["selected_member_force_samples"])==3
    assert r["selected_member_samples_not_comprehensive"]
    assert r["selected_member_force_samples"][1]["moment3_kNm"]==-99.4853
    assert r["selected_member_force_samples"][1]["shear2_kN"]==129.6723


def test_f3_nonacceptance_and_source_provenance():
    d=load_sources()
    assert d["source"]["report_drive_id"]=="1TpWUmOdrcQqOpkN6qvmhZ12KrYaNABBM"
    assert d["foundation"]["report_status"]=="NOT SAFE IN ONE WAY SHEAR"
    assert not d["foundation"]["acceptance"]
    assert evaluate(d)["F3_one_way_shear_unsafe"]


def test_altered_mass_source_fails_before_publishing(tmp_path):
    d=json.loads(SOURCE.read_text())
    d["original_mass"]["source_masses"][0]["value"]+=1000
    p=tmp_path/"changed-source.json"
    p.write_text(json.dumps(d))
    with pytest.raises(BenchmarkError,match="report story mass rows"):
        load_sources(source=p)


def test_modal_mode_count_tampering_rejected():
    d=load_sources()
    d["modal"]["calculated_by_report_table_first_mode_meeting_90pct_both_axes"]=6
    with pytest.raises(BenchmarkError,match="threshold"):
        evaluate(d)


def test_current_model_status_does_not_upgrade_by_arithmetic(tmp_path):
    g=json.loads(GOVERNING.read_text())
    g["admission_gates"]["engineering_approval"]=True
    p=tmp_path/"invalid.json";p.write_text(json.dumps(g))
    with pytest.raises(BenchmarkError,match="cannot be silently upgraded"):
        load_sources(governing=p)


def test_outputs_are_public_safe_deterministic_and_source_linked(tmp_path):
    r=build(tmp_path)
    p=tmp_path/"r6p6-report-results-review.json"
    html=tmp_path/"r6p6-report-results-review.html"
    manifest=json.loads((tmp_path/"r6p6-report-results-review-manifest.json").read_text())
    assert 'Mode' in html.read_text()
    assert 'NOT SAFE IN ONE WAY SHEAR' in html.read_text()
    assert 'report-prose' not in p.read_text()
    assert "E:\\" not in html.read_text()
    assert manifest["file_sha256"][html.name]==sha256(html.read_bytes()).hexdigest()
    assert manifest["file_sha256"][p.name]==sha256(p.read_bytes()).hexdigest()
    assert not manifest["model_reanalysis_performed"] and not manifest["engineering_approval"]
    assert not manifest["raw_private_source_published"]
    assert r["report_reuse_for_read_only_workbench"] is True
