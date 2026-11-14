"""R6.25 pinned original-DXF-derived Narayani source intake regression."""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from r6p25.narayani_intake import (
    CAD_SHA, DWG_DIR, PROJECT_ID, REQUIRED, IntakeHold,
    normalize, emit, verify, load_sources, check_git_checkout,
)


@pytest.fixture(scope="module")
def cad_root() -> Path:
    root=os.environ.get("R6P25_CAD_ROOT")
    if not root:
        pytest.skip("Requires pinned CAD repo checkout, provided by R6.25 GitHub Actions")
    return Path(root).resolve()


@pytest.fixture(scope="module")
def model(cad_root):
    return normalize(cad_root)


def test_pinned_drawing_source_checkout_identified(cad_root, model):
    check_git_checkout(cad_root)
    assert model["project_id"] == PROJECT_ID
    assert model["source_repository"]["commit_sha"] == CAD_SHA
    assert set(model["source_repository"]["file_SHA256"]) == set(REQUIRED)
    assert all(len(x) == 64 for x in
               model["source_repository"]["file_SHA256"].values())
    assert model["engineering_approval"] is False
    assert model["construction_release"] is False
    assert model["final_SAR_complete"] is False


def test_original_source_gf_columns_footings_beams_not_invented(model):
    b = model["building"]
    assert len(b["cad_source_ground_floor_column_marks"]) == 23
    assert len(b["cad_source_ground_floor_footing_outlines"]) == 21
    assert len(b["cad_source_ground_floor_edge_strip_candidates"]) == 32
    assert len(b["cad_source_three_floor_strict_line_pair_candidates"]) == 51
    assert {x["level"] for x in b["cad_source_three_floor_strict_line_pair_candidates"]} == {
        "gf", "ff", "sf"}
    assert sum(x["source_footing_family"] == "CF1" for x in
               b["cad_source_ground_floor_footing_outlines"]) == 2
    assert not b["cross_floor_column_member_and_foundation_support_links_verified"]
    assert not b["r6p23_r6p24_FE_input_ready"]


def test_original_I4_working_I3_are_two_separate_versions(model):
    marked={x["source_axis"]:x
            for x in model["building"]["cad_source_ground_floor_column_marks"]}
    assert marked["I4"]["working_axis"] == "I3"
    assert marked["I4"]["source_id"] == "SC-I4"
    assert marked["I4"]["working_position_m"] is not None
    assert marked["I4"]["status"] == "OWNER_WORKING_I3_EXCEPTION_NOT_SOURCE_RELOCATION"
    assert sum(x["working_position_m"] is not None for x in marked.values()) == 1
    assert model["building"]["owner_G2_junction"] == "BEAMS_MEET_NO_EXTRA_COLUMN_SOURCE_ONLY"
    assert not any(x["source_axis"] == "G2" for x in marked.values())


def test_GF_candidate_nearest_column_is_only_proximity_not_support(model):
    b=model["building"]["cad_source_ground_floor_edge_strip_candidates"]
    near=[n for beam in b for n in beam["nearest_columns_source_proximity_only"]]
    assert len(near)==64
    assert all(n["distance_mm"] >=0 and
               isinstance(n["within_250mm"],bool) and
               n["connection_verified"] is False for n in near)
    assert all(x["status"].endswith("_NOT_STRUCTURAL_BEAM") for x in b)


def test_three_levels_are_architectural_and_NOT_structural_slab_geometry(model):
    levels=model["building"]["levels"]
    assert [x["id"] for x in levels] == ["gf", "ff", "sf"]
    assert [x["architectural_scheduled_floor_area_m2"] for x in levels] == [
        205.16,200.67,175.62]
    assert sum(x["architectural_scheduled_floor_area_m2"] for x in levels) == pytest.approx(581.45)
    assert not any(x["release_to_open_sees_shell"] for x in levels)
    assert all(x["source_graph"]["nodes"] and x["source_graph"]["perimeter"] for x in levels)
    assert [x["structural_source_verification"] for x in levels] == [
        "GF_ONLY_COLUMN_SOURCE_MARKS","FF_SF_VERTICAL_SUPPORTS_NOT_REGISTERED",
        "FF_SF_VERTICAL_SUPPORTS_NOT_REGISTERED"]


def test_project_code_location_unit_weight_are_user_approved(model):
    a=model["approved_basis"]
    assert a["seismic_code"] == "NBC 105:2025"
    assert a["project_location"] == "Pokhara"
    assert a["concrete_unit_weight_kN_m3"] == 20.0
    assert "USER_APPROVED" in a["concrete_unit_weight_status"]
    assert a["concrete_grade"] == "M20_DRAWING_DECLARED"
    assert a["reinforcement_grade"] == "Fe500_DRAWING_DECLARED"
    assert a["elastic_modulus_kN_m2"] is None


def test_warehouse_geotech_report_has_source_matched_context_not_false_160_kPa_certification(model):
    s=model["soil"]
    assert s["report_found"] is True
    assert s["approved_conservative_provisional_q_kPa"] == 160.0
    assert s["reference_table_q_kPa_B1p5_Df1p5"] == 166.0
    assert s["report_site_class"] == "B_MEDIUM_SOIL_SITE"
    assert s["older_structural_report_site_class"] == "D"
    assert s["NBC105_2025_site_class"].startswith("NOT_YET")
    assert s["CF1_rectangular_4_by_1p5_direct_table_value"] is None
    assert s["foundation_load_and_geometry_specific_check_pending"] is True


def test_G1_F3_and_unreconciled_design_holds_never_dropped(model):
    holds="\n".join(model["holds"])
    assert "G1" in holds
    assert "F3 NOT SAFE IN ONE WAY SHEAR" in holds
    assert "2025 site-class reconciliation" in holds
    assert "Upper FF/SF structural columns" in holds
    assert "I4 original source column and I3" in holds
    assert not model["building"]["r6p23_r6p24_FE_input_ready"]


def test_json_sha256_readback_refuses_tampering(tmp_path, model):
    m=emit(model,tmp_path)
    assert verify(tmp_path)==m
    fp=tmp_path/m["filename"]
    text=fp.read_text(encoding="utf-8")
    fp.write_text(text.replace('"engineering_approval": false',
                               '"engineering_approval": true', 1),encoding="utf-8")
    with pytest.raises(IntakeHold,match="SHA256"):
        verify(tmp_path)


def test_source_mismatch_fails_closed(cad_root, tmp_path):
    src=cad_root/DWG_DIR
    dst=tmp_path/DWG_DIR
    dst.mkdir(parents=True)
    for name in REQUIRED:
        shutil.copy2(src/name,dst/name)
    file=dst/"source-axis-register.v1.json"
    d=json.loads(file.read_text())
    d["workingException"]["workingAxis"]="I5"
    file.write_text(json.dumps(d),encoding="utf-8")
    with pytest.raises(IntakeHold,match="I4 / owner working I3"):
        normalize(tmp_path)


def test_cli_from_actual_pinned_source_can_generate_same_trace(tmp_path,cad_root,model):
    out=tmp_path/"output"
    cp=subprocess.run([
        os.environ.get("PYTHON","python"),
        "-m","r6p25.narayani_intake",
        "--cad-root",str(cad_root),"--output-dir",str(out)
    ],capture_output=True,text=True,check=True)
    line=json.loads(cp.stdout)
    assert line["gf_columns"]==23
    assert line["gf_footings"]==21
    assert line["three_level_strict_strip_candidates"]==51
    assert line["approved_concrete_unit_weight_kN_m3"]==20
    assert not line["ready_for_real_building_FE"]
    assert verify(out)["cad_source_sha"]==CAD_SHA
    assert json.loads((out/"R6P25-NARAYANI-SOURCE-REGISTER-UNAPPROVED.json").read_text())==model
