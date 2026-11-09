"""R6.8 exact governing ETABS21 source-derived member/area/load intake."""
import hashlib
import json
from pathlib import Path

import pytest

from scripts.build_r6p8_native_source_catalogue import (
    SourceError, SEED, UNCOMPRESSED_SHA256, build, emit, source,
)


def test_source_snapshot_and_original_fingerprints_verified():
    a=source()
    assert a["schema"]=="jp.structural.r6p8.etabs21_governing_source_compact.v0.1"
    assert len(a["points"])==127 and len(a["lines"])==97 and len(a["areas"])==80
    assert len(a["members"])==199 and len(a["shells"])==115 and len(a["loads"])==337
    assert a["status"]["new_ETABS21_solver_executed"] is False
    assert a["status"]["engineering_approval"] is False
    assert a["status"]["F3_one_way_shear_unsafe"] is True
    assert len(a["sha"])==2 and all(len(s)==64 for s in a["sha"])


def test_actual_geometry_is_not_older_23_grid_hypothesis():
    d=build()
    assert len(d["points_xyz_local_mm"])==127
    assert d["points_xyz_local_mm"]["20"][2]==2456.94
    assert d["grid_axes"]["X"]["I"]==21000
    assert d["grid_axes"]["Y"]["7"]==12550
    assert d["grid_axes"]["Y"]["4"]-d["grid_axes"]["Y"]["3"]==655
    assert len(d["members"])==199 and len(d["shells"])==115
    assert d["result_scope"]["actual_native_member_geometry"] is True
    assert d["result_scope"]["new_ULS_SLS_ETABS_solver_run"] is False
    assert d["result_scope"]["engineering_approval"] is False


def test_exact_source_beam_B46_GF_length_section_volume_wall_load():
    d=build()
    m=next(m for m in d["members"] if m["key"]=="GF:B46")
    assert m["kind"]=="BEAM"
    assert m["section"]=="beam 12*16"
    assert m["length_mm"]==pytest.approx(4823,abs=1e-7)
    assert m["section_gross_volume_m3"]==pytest.approx(.57876,abs=1e-8)
    assert m["source_dead_selfweight_proxy_kN"]==pytest.approx(14.464729,abs=1e-6)
    loads=[l for l in m["applied_loads"] if l["pattern"]=="WALL LOAD"]
    assert len(loads)==1 and loads[0]["raw_integrated_kN"]==pytest.approx(44.61275)
    assert loads[0]["working"]["w_N_per_mm"]==9.25
    assert d["historical_report_crosswalk"]["source_B46_GF"]["same_historical_etabs_member_proven"] is False


def test_trapf_partial_load_integral_preserves_900mm_segment():
    d=build()
    m=next(m for m in d["members"] if m["key"]=="TF:B25")
    assert m["length_mm"]==pytest.approx(4812)
    line=next(v for v in m["applied_loads"] if v["method"]=="T")
    assert line["raw_integrated_kN"]==pytest.approx(1.89,abs=1e-6)
    assert line["working"]["start_fraction"]==pytest.approx(.8129676)
    assert line["working"]["end_fraction"]==1


def test_floors_match_previously_verified_source_only_load_budget():
    d=build()
    x=d["level_summary"]
    assert x["GF"]["source_unsectioned_line_count"]==10
    assert x["FF"]["source_unsectioned_line_count"]==21
    assert x["TF"]["source_unsectioned_line_count"]==3
    assert x["GF"]["source_structural_beam_count"]==35
    assert x["FF"]["source_structural_beam_count"]==39
    assert x["TF"]["source_structural_beam_count"]==31
    assert x["GF"]["source_structural_column_count"]==21
    assert x["FF"]["source_structural_column_count"]==21
    assert x["TF"]["source_structural_column_count"]==18
    assert x["GF"]["source_mass_eligible_applied_gravity_kN"]==pytest.approx(1379.707110,abs=.001)
    assert x["FF"]["source_mass_eligible_applied_gravity_kN"]==pytest.approx(1441.352614,abs=.001)
    assert x["TF"]["source_mass_eligible_applied_gravity_kN"]==pytest.approx(469.159024,abs=.001)
    assert d["reconciled_source_applied_mass_eligible_loads_kN"]==pytest.approx(3290.2187486,abs=.01)


def test_original_report_GF_B19_label_not_mapped_into_new_model():
    d=build()
    ids={m["key"] for m in d["members"]}
    assert "GF:B19" not in ids
    assert "TF:C24" in ids
    assert d["historical_report_crosswalk"]["source_B19_GF"]["cannot_transfer_report_forces"] is True


def test_reinforcement_is_source_section_input_not_approved_bbs():
    d=build()
    rb=d["source_model_rebar_section_input_not_approved_BBS"]
    assert rb["Col 400*400"]["PATTERN"]=="R-3-3"
    assert rb["Col 400*400"]["CONFINEBARSPACING"]==150
    assert rb["Circular Col 350"]["PATTERN"]=="C-6"
    assert not d["result_scope"]["approved_rebar_cutting_schedules"]
    assert d["result_scope"]["F3_one_way_shear_unsafe"]


def test_derived_output_deterministic_and_no_source_binary_published():
    d,summary=emit()
    out=Path("site/data/r6p8-etabs21-source-member-catalogue.json")
    assert summary["catalogue_sha256"]==hashlib.sha256(out.read_bytes()).hexdigest()
    assert summary["record_counts"]["points"]==127
    assert summary["record_counts"]["member_assignments"]==199
    assert summary["record_counts"]["shell_assignments"]==115
    assert summary["record_counts"]["assigned_gravity_loads"]==337
    assert not summary["is_solver_result"] and not summary["engineering_approval"]
    assert d["source"]["original_file_bytes_published"] is False
    text=out.read_text()
    assert "RAMBAZZAR" not in text and "creactive builders doc" not in text
    assert "E:\\\\" not in text
    assert "NOT SAFE" not in text or d["result_scope"]["F3_one_way_shear_unsafe"]


def test_unsectioned_line_loads_not_misclassified_as_concrete_beams():
    d=build()
    lines=[m for m in d["members"] if m["kind"]=="LINE"]
    assert len(lines)==34
    assert all(m["section"]=="NONE" and "section_gross_volume_m3" not in m for m in lines)
    load_count=sum(len(m["applied_loads"]) for m in lines)
    assert load_count==30
    assert all(v["pattern"]=="WALL LOAD" for m in lines for v in m["applied_loads"])
    assert d["result_scope"]["complete_solved_member_end_forces"] is False
