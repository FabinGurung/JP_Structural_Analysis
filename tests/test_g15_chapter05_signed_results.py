"""Chapter 5 actual OpenSees signed end-result and original-report source screens."""
import math
from collections import Counter
import pytest
from scripts.build_g15_chapter05_signed_results import build,SCHEMA,CASES,PARTS

@pytest.fixture(scope="module")
def result():
    return build()

def test_real_solved_signed_result_ids_complete_and_no_case_mixing(result):
    d=result
    assert d["schema"]==SCHEMA and d["numerical_engine"].startswith("OpenSeesPy")
    assert len(d["case_summaries"])==5 and len(d["member_case_end_actions"])==825
    assert len({r["member_id"] for r in d["member_case_end_actions"]})==165
    assert len({r["id"] for r in d["member_case_end_actions"]})==825
    assert Counter(r["case_id"] for r in d["member_case_end_actions"])=={c:165 for c in CASES}
    assert all(list(r["local_components"])==list(PARTS) for r in d["member_case_end_actions"])
    assert all(len(r["local_components"])==12 and all(math.isfinite(v) for v in r["local_components"].values())
               for r in d["member_case_end_actions"])
    assert all(r["span_diagram_verified"] is False for r in d["member_case_end_actions"])

def test_real_trial_displacements_and_static_equilibrium_recovered(result):
    d=result
    assert len(d["trial_node_displacements"])==345
    assert Counter(x["case_id"] for x in d["trial_node_displacements"])=={c:69 for c in CASES}
    assert all(math.isfinite(x["ux_mm"]) and math.isfinite(x["uy_mm"]) for x in d["trial_node_displacements"])
    assert all(len(x["story_chord_metrics"])==3 and x["signed_end_action_records"]==165 for x in d["case_summaries"])
    assert all(x["force_residual_kN"]<.001 and x["moment_residual_kNm"]<.001 for x in d["case_summaries"])
    assert all(v["member_id"] in {r["member_id"] for r in d["member_case_end_actions"]}
               for c in d["case_summaries"] for v in c["absolute_signed_end_action_extrema"].values())

def test_original_section5_seismic_and_modal_discrepancies_are_not_resolved_by_fiat(result):
    d=result
    r=d["original_report_claims"]
    assert r["modal_90_percent_first_table_mode"]=={"UX":5,"UY":4,"RZ":6}
    assert r["modal_period_source_conflict_s"]["first_reported_table_s"]==.618
    assert r["modal_period_source_conflict_s"]["surrounding_narrative_s"]==.185
    assert r["modal_period_source_conflict_s"]["resolved"] is False
    assert r["auto_seismic_arithmetic"]["ULS"]["recalculated_kN"]==pytest.approx(894.9803279)
    assert r["auto_seismic_arithmetic"]["SLS"]["recalculated_kN"]==pytest.approx(860.8207734)
    assert abs(r["auto_seismic_arithmetic"]["ULS"]["difference_kN"])<.0001
    assert d["original_observations"]["reported_story_masses"]["units_printed"] is False
    assert d["original_report_claims_independently_verified"] is False

def test_none_of_the_source_gates_or_F3_failure_are_changed(result):
    d=result
    assert d["counts"]=={"cases":5,"members_per_case":165,"signed_member_case_records":825,
      "components_per_record":12,"trial_displacement_records":345,"source_gates_open":15}
    assert d["original_ETABS_model_authenticated"] is False
    assert d["authentic_modal_analysis_performed"] is False
    assert d["authentic_member_span_diagrams_recovered"] is False
    assert d["project_specific_NBC_compliance_evaluated"] is False
    assert d["engineering_approval"] is False
    assert d["original_F3_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"
    assert d["original_observations"]["missing_native_data"]["member_load_map"] is False

def test_report_frontend_is_chaptered_and_source_audited():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]/"site"
    h=(root/"report.html").read_text()
    b=(root/"chapter05-results.js").read_text()
    assert 'id="chapter-05"' in h
    for i in range(1,16):
        assert 'id="toc-5-'+str(i)+'"' in h
    assert 'id="c05-member-diagram"' in h and 'id="c05-modal-source"' in h
    assert "chapter05-results.js" in h and "chapter05-results.css" in h
    assert "g15-chapter05-signed-results.v0.1.json" in b
    assert 'engineering_approval!==false' in b
    assert "NOT SAFE IN ONE WAY SHEAR" in b
