"""Original Chapter6 arithmetic and user-authorized engineering choice safety proofs."""
from pathlib import Path
import math
import pytest
from scripts.build_g15_chapter06_source_design import build,bar_area,COLUMN_GROUPS

@pytest.fixture(scope="module")
def data():return build()

def test_source_column_steel_group_ratios(data):
    c=data["section6_1_columns"]
    assert c["source_grid_count"]==23 and len(c["source_schedule_rows"])==12
    assert {r["mark"] for r in c["source_schedule_rows"]}=={"C1","C2","C3","C4"}
    assert len({g for g in COLUMN_GROUPS for g in g[3]})==23
    assert all(abs(r["source_percentage_difference_points"])<.025 for r in c["source_schedule_rows"])
    assert c["reported_ETABS_examples"][0]["recalculated_As_percent"]==pytest.approx(1.33375)
    assert c["column_moment_axial_capacity_approved"] is False
    assert all(r["original_ETABS_object_link_verified"] is False for r in c["source_schedule_rows"])

def test_slab_staircase_geometry_disagreements_fidelity(data):
    slab=data["section6_3_slab"]
    assert slab["sample_D_mm"]==125 and slab["general_schedule_D_mm"]==120
    assert slab["computed_trial_factored_load_kPa"]==pytest.approx(10.695)
    assert slab["computed_provided_As_mm2_per_m"]==pytest.approx(math.pi*8**2/4*1000/150)
    assert slab["source_thickness_conflict_resolved"] is False
    st=data["section6_5_staircase"]
    assert st["general_waist_mm"]==150 and st["worksheet_adopted_D_mm"]==127
    assert st["source_150_vs_127_depth_resolved"] is False
    assert st["computed_provided_main_As_mm2_per_m"]==pytest.approx(bar_area(1000/127,12))
    assert st["staircase_flexure_shear_design_approved"] is False

def test_unsafe_f3_and_bearing_assumptions_do_not_clear(data):
    f=data["section6_4_footing"]
    assert f["F3_warning"]=="NOT SAFE IN ONE WAY SHEAR"
    assert f["F3_original_schedule_accepted"] is False
    assert f["F3_soil_SBC_verified"] is False
    assert f["F3_derived"]["cover_based_scenario_effective_d_mm"]==394
    assert f["F3_derived"]["worksheet_d_exceeds_cover_scenario_mm"]==pytest.approx(29.46278)
    assert f["F3_derived"]["original_factored_pressure_recomputed_kPa"]==pytest.approx(194.2176870748)
    assert f["F3_derived"]["service_pressure_from_printed_total_kPa"]==pytest.approx(600/4.41)
    assert f["CF1_verified_in_native_ETABS"] is False

def test_source_gate_acceptance_is_distinct_from_owner_model_authorization(data):
    assert data["open_source_acceptance_count"]==15
    assert data["source_acceptance_count"]==0
    assert len(data["source_acceptance_gates"])==15
    assert not any(x["accepted"] for x in data["source_acceptance_gates"])
    assert data["code_standard_document_identified"] is True
    assert data["code_project_compliance_demonstrated"] is False
    assert data["native_original_ETABS_member_parity"] is False
    assert data["engineering_approval"] is False
    assert data["original_F3_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"

def test_integration_and_source_ledger_expose_all_original_sections():
    site=Path(__file__).resolve().parents[1]/"site"
    html=(site/"report.html").read_text()
    js=(site/"chapter06-design.js").read_text()
    for i in range(1,6):assert 'id="toc-6-'+str(i)+'"' in html
    for item in ("c06-columns","c06-beams","c06-slab","c06-footing","c06-stair","c06-gates"):
        assert 'id="'+item+'"' in html
    assert "chapter06-design.js" in html and "chapter06-design.css" in html
    assert "g15-chapter06-source-design.v0.1.json" in js
    assert "NOT SAFE IN ONE WAY SHEAR" in js
    assert "engineering_approval!==false" in js
