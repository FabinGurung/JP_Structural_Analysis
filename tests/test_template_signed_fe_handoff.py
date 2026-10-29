"""Engine v0.3: signed OpenSees member action → M08/M09/M10 → original TOC SAR."""
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
import pytest

from scripts.build_template_signed_fe_handoff import (
    SCHEMA, OUTPUT_PREFIX, SignedReportError, build, emit,
    csv_text, markdown, render_html, _member_rows,
)
from scripts.build_structural_template_engine import build as isolated_template

@pytest.fixture(scope="module")
def d2():
    return build()

def test_real_OpenSees_cases_and_all_six_global_equilibrium_components(d2):
    assert d2["schema"]==SCHEMA
    assert d2["case_count"]==2 and d2["combination_count"]==2
    assert d2["member_count"]==4
    assert d2["member_end_action_rows"]==32  # 4 cases × 4 members × I/J
    assert d2["global_six_component_balance_max_kN_or_kNm"]<1e-5
    assert d2["signed_analysis"]["engineering_approval"] is False
    assert all(x["global_equilibrium_pass"] is True for x in d2["signed_analysis"]["raw_cases"])
    assert sorted(d2["case_ids"])==["G","HX"]
    assert sorted(d2["combination_ids"])==["U_MINUS","U_PLUS"]
    assert len({(x["kind"],x["case_id"],x["member_id"],x["end"])
                for x in d2["signed_member_end_records"]})==32

def test_signed_each_IJ_component_preserved_without_independent_peak_mixing(d2):
    rows={(x["kind"],x["case_id"],x["member_id"],x["end"]):x
          for x in d2["signed_member_end_records"]}
    for m in ("BM1","BM2","COL1","COL2"):
        for end in ("I","J"):
            g=rows[("RAW","G",m,end)]
            h=rows[("RAW","HX",m,end)]
            plus=rows[("COMBINATION","U_PLUS",m,end)]
            minus=rows[("COMBINATION","U_MINUS",m,end)]
            for axis in ("N","Vy","Vz","T","My","Mz"):
                assert plus[axis]==pytest.approx(1.2*g[axis]+1.2*h[axis],abs=1e-6)
                assert minus[axis]==pytest.approx(1.2*g[axis]-1.2*h[axis],abs=1e-6)

def test_model_and_signed_bridge_provenance_digest_and_same_case_bindings(d2):
    model=d2["input_provenance"]["model"]
    assert model["model_id"]==d2["signed_analysis"]["model_id"]
    assert d2["source_bundle_sha256"]==d2["member_design_checks"]["source_action_digest"]
    assert len(d2["signed_result_sha256"])==64
    assert d2["member_design_checks"]["checks"]["signed_concurrent_case_actions"] is True
    assert d2["member_design_checks"]["checks"]["signed_modal_orthogonal_envelope_supported"] is False
    assert d2["member_design_checks"]["checks"]["independent_sp16_chart_validated"] is False
    assert [x["member_id"] for x in d2["member_design_checks"]["beam_design"]]==["BM1"]
    assert [x["member_id"] for x in d2["member_design_checks"]["column_design"]]==["COL1"]
    assert len(d2["member_design_checks"]["column_design"][0]["scenarios"])==4
    assert [x["joint_node_id"] for x in d2["member_design_checks"]["joint_design"]]==["T1"]

def test_original_toc_maps_18_modules_and_real_run_statuses(d2):
    chapters=d2["chapters"]
    assert [x["chapter"] for x in chapters]==[f"{i:02d}" for i in range(1,8)]
    assert d2["registered_requirement_count"]==18
    req={x["id"] for c in chapters for x in c["requirements"]}
    assert req=={f"M{i:02d}" for i in range(1,17)}|{"S17","S18"}
    assert d2["implemented_in_this_FE_case"]==["M04","M08","M09","M10"]
    chapter05=next(x for x in chapters if x["chapter"]=="05")
    assert any(x["run_status"]=="NOT_EVALUATED_BY_THIS_SIGNED_FE_CASE" for x in chapter05["requirements"])
    assert not d2["all_18_modules_complete"]

def test_separate_reference_cases_and_preserved_F3_unsafe_boundary(d2):
    independent=isolated_template()
    assert d2["independent_of_three_level_and_F3_cases"] is True
    assert d2["case_id"]!=independent["case_id"]
    assert d2["original_F3_test_not_included"] is True
    assert d2["original_F3_verdict_changed"] is False
    assert not d2["engineer_approved"]
    assert not d2["permit_eligible"]
    assert not d2["engineering_approval"]
    assert all(not x["accepted"] for x in d2["submission_items"])

def test_report_and_csv_have_matching_member_ends_and_current_results(d2):
    body=render_html(d2)
    assert "Chapter 05" in body and "Chapter 06" in body
    assert "NOT ENGINEERING APPROVED" in body
    assert "M08" in body and "M09" in body and "M10" in body
    assert "U_MINUS" in body and "U_PLUS" in body
    assert "BM1" in body and "COL1" in body
    assert "F3" in body
    narrative=markdown(d2)
    assert "## Chapter 07" in narrative
    assert "signed" in narrative.lower()
    rows=list(csv.DictReader(csv_text(d2).splitlines()))
    assert len(rows)==32
    assert sum(x["kind"]=="RAW" for x in rows)==16
    assert sum(x["kind"]=="COMBINATION" for x in rows)==16
    assert all(x["end"] in ("I","J") for x in rows)

def test_fail_closed_on_missing_end_component_or_nonfinite_number(d2):
    modified=copy.deepcopy(d2["signed_analysis"])
    modified["raw_cases"][0]["local_end_resisting_actions"]["BM1"]["I"].pop("My")
    with pytest.raises(SignedReportError,match="incomplete end force"):
        _member_rows(modified)
    bad=copy.deepcopy(d2["signed_analysis"])
    bad["raw_cases"][0]["local_end_resisting_actions"]["BM1"]["I"]["My"]=float("nan")
    with pytest.raises(SignedReportError,match="nonfinite"):
        _member_rows(bad)

def test_all_five_public_artifacts_hashed_and_ref_report_linked(tmp_path):
    report=emit(tmp_path)
    p=OUTPUT_PREFIX
    names={p+".json",p+".html",p+".md",p+".csv"}
    manifest=json.loads((tmp_path/(p+"-manifest.json")).read_text())
    assert set(manifest["files"])==names
    for name in names:
        assert hashlib.sha256((tmp_path/name).read_bytes()).hexdigest()==manifest["files"][name]
    assert json.loads((tmp_path/(p+".json")).read_text())["schema"]==SCHEMA
    assert manifest["engineering_approval"] is False
    assert report["engineering_approval"] is False
    site=(Path(__file__).resolve().parents[1]/"site/report.html").read_text()
    assert "reports/template-signed-fe-handoff.html" in site
    assert "reports/template-signed-fe-handoff-manifest.json" in site
