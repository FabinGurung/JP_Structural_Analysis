"""Fail-closed Chapter 4 source-identity, FE result, and load path regression."""
from pathlib import Path
from collections import Counter
import math
from scripts.build_g15_chapter04_model_graph import build, SCHEMA

ROOT=Path(__file__).resolve().parents[1]

def test_chapter4_graph_has_unique_nodes_members_tags_and_referential_integrity():
    d=build()
    assert d["schema"]==SCHEMA
    assert (len(d["nodes"]),len(d["elements"]),len(d["supports"]))==(92,165,23)
    assert len({x["id"] for x in d["nodes"]})==92
    assert len({x["id"] for x in d["elements"]})==165
    assert len({x["solver_tag"] for x in d["elements"]})==165
    nodeids={x["id"] for x in d["nodes"]}
    for e in d["elements"]:
        assert e["node_i"] in nodeids and e["node_j"] in nodeids
        assert e["original_ETABS_frame_id"] is None
        assert e["engineering_accepted"] is False
    assert {x["node_id"] for x in d["supports"]} <= nodeids
    assert all(len(x["restrained_dofs"])==6 and x["status"]=="ASSUMED" for x in d["supports"])
    assert len([e for e in d["elements"] if e["connection_status"]=="UNVERIFIED_CONNECTOR"])==6
    assert d["counts"]["authenticated_original_frame_ids"]==0

def test_chapter4_solved_cases_and_trial_load_vectors_conserve_force():
    d=build()
    assert len(d["trial_nodal_loads"])==345
    assert Counter(x["pattern_id"] for x in d["trial_nodal_loads"])=={
        "GRAVITY":69, "EQ_PLUS_X":69,"EQ_MINUS_X":69,"EQ_PLUS_Y":69,"EQ_MINUS_Y":69}
    assert {x["target_node_id"] for x in d["trial_nodal_loads"]} <= {x["id"] for x in d["nodes"]}
    assert {x["status"] for x in d["trial_nodal_loads"]} == {"ASSUMED"}
    assert all(x["included_in_seismic_mass"] is None and not x["physical_load_assignment_accepted"] for x in d["trial_nodal_loads"])
    for case in d["solved_cases"]:
        assert case["assignment_count"]==69
        assert case["signed_member_end_records"]==165
        assert case["force_residual_kN"]<0.001
        assert case["moment_residual_kNm"]<0.001
        assert all(math.isfinite(v) for v in case["sum_applied_force_xyz_kN"])
    assert d["counts"]["open_sees_signed_member_case_records"]==825

def test_chapter4_unassigned_source_rates_and_unsafe_design_status():
    d=build()
    assert len(d["unassigned_source_report_load_rates"])==8
    assert all(x["physical_object_id"] is None for x in d["unassigned_source_report_load_rates"])
    assert all(not x["assigned_to_solver"] for x in d["unassigned_source_report_load_rates"])
    assert all(not d[k] for k in ("engineering_approval","supports_authenticated",
        "original_ETABS_model_authenticated","actual_selfweight_assembled",
        "actual_live_floor_finish_loads_mapped","actual_wall_line_loads_mapped",
        "actual_seismic_mass_assembled"))
    assert d["counts"]["source_gate20_open"]==15
    assert d["original_F3_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"

def test_chapter4_in_continuous_report_and_browser_has_no_false_approval():
    html=(ROOT/"site/report.html").read_text(encoding="utf-8")
    assert 'id="chapter-04"' in html
    assert "chapter04-model.js" in html
    assert "c04-member-view" in html
    assert "c04-plan" in html
    browser=(ROOT/"site/chapter04-model.js").read_text(encoding="utf-8")
    assert "g15-chapter04-model-graph.v0.1.json" in browser
    assert "NOT SAFE IN ONE WAY SHEAR" in browser
    assert "engineering_approval!==false" in browser
