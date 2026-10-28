"""Stage 7 standards crosswalk and bounded F3 geometric demand safety tests."""
import math
from pathlib import Path
import pytest
from scripts.build_g15_annex_source_recovery import build, demand, SCHEMA

@pytest.fixture(scope="module")
def out():return build()

def test_exact_f3_original_source_and_load_case_arithmetic(out):
    x=out["scenario_inputs"]
    assert out["original_F3_verdict"]=="NOT SAFE IN ONE WAY SHEAR"
    assert x["source_D_mm"]==450 and x["source_d_mm"]==pytest.approx(423.46278)
    assert x["source_axial_kN"]==571 and x["source_axial_including_selfweight_kN"]==600
    assert out["source_F3_effective_depth_conflict_mm"]==pytest.approx(29.46278)
    assert out["source_F3_axial_only_pressure_demand_at_worksheet_d_MPa"]==pytest.approx(
        (1.5*571/4.41)*(0.87-.42346278)/(.42346278*1000))
    assert out["source_F3_axial_only_pressure_demand_at_cover_based_d_MPa"]==pytest.approx(
        (1.5*571/4.41)*(0.87-.394)/(.394*1000))
    assert out["source_F3_axial_only_pressure_demand_at_worksheet_d_MPa"]<
           out["source_F3_axial_only_pressure_demand_at_cover_based_d_MPa"]

def test_scenarios_are_unique_numerically_sensible_and_unapproved(out):
    assert out["schema"]==SCHEMA
    rows=out["F3_sensitivity_scenarios"]
    assert len(rows)==12 and len(set(r["scenario_id"] for r in rows))==12
    bykey={(r["plan_B_and_L_m"],r["overall_D_mm"]):r for r in rows}
    base=bykey[(2.1,450)]
    assert base["cover_based_effective_d_mm"]==394
    assert base["q_1p5_axial_571_kPa"]==pytest.approx(194.2176870748)
    assert base["q_1p5_reported_total_600_kPa"]==pytest.approx(1.5*600/4.41)
    assert bykey[(2.1,550)]["includes_600_demand"]["one_way_uniform_pressure_stress_MPa"]<
           base["includes_600_demand"]["one_way_uniform_pressure_stress_MPa"]
    for row in rows:
        assert row["includes_600_demand"]["one_way_uniform_pressure_stress_MPa"]>=0
        assert row["axial_only_demand"]["one_way_uniform_pressure_stress_MPa"]<=row["includes_600_demand"]["one_way_uniform_pressure_stress_MPa"]
        assert row["design_pass"] is False
        assert row["engineering_approval"] is False
        assert row["true_one_way_shear_strength_determined"] is False
        assert row["base_source_160kPa_number_used_as_verified_soil_strength"] is False

def test_degenerate_cantilever_demand_zero_only_geometric_screen():
    assert demand(194.2,2.1,.36,1000)["cantilever_outside_d_m"]==0
    assert demand(194.2,2.1,.36,1000)["one_way_uniform_pressure_stress_MPa"]==0

def test_acceptance_gates_are_not_mislabelled_by_research(out):
    assert out["gate_count"]==15 and out["accepted_gate_count"]==0
    assert len(out["gates"])==15
    assert set(out["independent_evidence_starting_tasks"])=={"G20-SRC-001","G20-F3-012","G20-F3-013"}
    assert not any(x["physical_source_acceptance"] for x in out["gates"])
    assert all(x["research_reference_ids"] and x["acceptance_test"] and x["required_by_role"] for x in out["gates"])
    assert out["owner_work_authorized"] is True
    assert out["owner_original_source_authenticated"] is False
    assert out["F3_replacement_approved"] is False
    assert out["site_soil_or_bearing_verified"] is False
    assert out["engineering_approval"] is False
    assert out["comparison_is_not_a_code_design_pass"] is True

def test_report_annex_governs_source_citations_and_demand_sensitivity():
    site=Path(__file__).resolve().parents[1]/"site"
    h=(site/"report.html").read_text()
    js=(site/"annex-source-recovery.js").read_text()
    assert 'id="annex-evidence-queue"' in h
    assert 'id="annex-f3-sensitivity"' in h
    assert 'id="annex-standards"' in h
    assert "annex-source-recovery.js" in h
    assert "annex-source-recovery.css" in h
    assert "g15-annex-source-recovery.v0.1.json" in js
    assert 'engineering_approval!==false' in js
    assert 'NOT SAFE IN ONE WAY SHEAR' in js
