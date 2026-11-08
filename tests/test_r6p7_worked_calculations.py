"""R6.7: full hand-traceable procedures with safe model/fixture separation."""
from hashlib import sha256
import json
from pathlib import Path
import pytest
from scripts.build_r6p7_worked_calculations import build,compute,sources


def test_governed_source_identity_and_engineering_holds():
    old,seis,model,f3,r5,grid=sources()
    assert old["source"]["report_sha256"]==f3["source_pdf"]["sha256"]
    assert model["decision"]["state"]=="USER_CONFIRMED_CURRENT_GOVERNING_ETABS21_ULS_SLS"
    assert r5["classification"]=="SYNTHETIC_REFERENCE_NOT_A_BUILDING"
    assert grid["status"]=="SOURCE_DERIVED_HYPOTHETICAL_FRAME_NOT_VERIFIED_AS_BUILT"
    assert old["foundation"]["report_status"]=="NOT SAFE IN ONE WAY SHEAR"


def test_every_historical_mass_is_converted_with_units_and_reconciled():
    d=compute()
    assert len(d["floor_distribution"])==3
    assert abs(d["historical_mass_total_kN"]-6831.9109)<.0002
    assert d["floor_distribution"][0]["reported_mass_unprinted_unit"]==270076.47
    assert all(row["explicitly_not_reported_ETABS_floor_force"] for row in d["floor_distribution"])
    assert d["ETABS21_results_reproduced"] is False


def test_report_coefficients_and_seismic_shear_are_derived():
    d=compute()
    assert d["elastic_coefficient_report"]==.7875
    assert d["uls_unrounded_source_coefficient"]==.13125
    assert d["uls_printed_coefficient"]==.131
    assert d["sls_coefficient"]==.126
    assert abs(d["historical_uls_base_shear_hand_kN"]-894.9803)<.0001
    assert abs(d["historical_sls_base_shear_hand_kN"]-860.8208)<.0001
    assert abs(sum(row["hand_distributed_force_uls_kN"] for row in d["floor_distribution"])-d["historical_uls_base_shear_hand_kN"])<.000001
    assert d["floor_distribution_method"]=="CONDITIONAL_HAND_EXAMPLE_NOT_PRINTED_FLOOR_FORCES"


def test_modal_source_increments_and_conflict_preserved():
    d=compute()
    rows=d["reported_mode_rows_augmented"]
    assert len(rows)==12
    assert rows[4]["ux_increment"]==pytest.approx(.1383)
    assert rows[4]["uy_increment"]==pytest.approx(.0046)
    assert d["first_both_axes_90pct_mode_by_printed_table"]==5
    assert d["report_prose_says_six_modes"]
    assert not d["engineer_approval"]


def test_f3_pressure_and_section_bar_density_not_used_to_clear_shear():
    d=compute()
    assert abs(d["f3_factored_pressure_kPa"]-194.22)<.005
    assert abs(d["f3_bar_area_mm2_per_m"]-753.98223686)<.00001
    assert d["f3_shear_capacity_not_recomputed"] and d["f3_unsafe"]


def test_synthetic_r5_hand_calc_is_independent_and_conserves_load():
    d=compute()
    x=d["synthetic_R5"]
    assert x["panel_area_m2"]==12
    assert x["dead_panel_kN"]==72
    assert x["seismic_live_panel_kN"]==7.2
    assert x["wall_line_kN"]==32
    assert x["total_seismic_eligible_kN"]==111.2
    assert x["not_project_data"] is True


def test_generated_book_has_input_substitution_check_2d_3d_and_source_links(tmp_path):
    d=build(tmp_path)
    html=(tmp_path/"worked-calculations.html").read_text()
    assert len(d["steps"])==7
    for label in ["Formula","Substitute","Calculate","Verify / limit","source","linked-member"]:
        assert label in html
    for source_id in ["MASS-01","SEIS-01","BASE-01","FLOOR-01","MODE-01","FOOT-01","R5-01"]:
        assert 'id="'+source_id+'"' in html
    assert 'id="worked-plan"' in html and 'id="worked-perspective"' in html
    assert "worked-calculations.js" in html
    assert "NOT SAFE IN ONE WAY SHEAR" in html
    assert "NOT ETABS21" in html or "not imported ETABS21" in html
    assert "site-specific permit approved" not in html


def test_machine_readable_working_check_and_manifest(tmp_path):
    build(tmp_path)
    data=tmp_path/"reports/r6p7-worked-calculations.json"
    manifest=json.loads((tmp_path/"reports/r6p7-worked-calculations-manifest.json").read_text())
    d=json.loads(data.read_text())
    assert len(d["steps"])==7
    assert d["source"]=="HISTORICAL_REPORT_REPRODUCTION_PLUS_DISTINCT_SYNTHETIC_FIXTURE"
    assert manifest["generated_sha256"][data.name]==sha256(data.read_bytes()).hexdigest()
    html=tmp_path/"worked-calculations.html"
    assert manifest["generated_sha256"][html.name]==sha256(html.read_bytes()).hexdigest()
    assert manifest["source_report_engineering_approved"] is False
    assert manifest["new_ETABS21_run"] is False
    assert manifest["private_model_raw_bytes_published"] is False


def test_qa_wont_blend_current_etabs21_and_old_hypothetical_geometry():
    d=compute()
    assert d["governing_ETABS21_model_user_selected"] is True
    assert d["provisional_grid_not_ETABS21"] is True
    assert d["provisional_viewer_geometry"]["is_current_ETABS21_geometry"] is False
    assert d["provisional_viewer_geometry"]["hypothetical_edges"]==2
