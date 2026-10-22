"""Gate17 hard source-mass truth and documented unresolved design gates."""
import math
from scripts.build_g15_gate17_source_audit import build

def test_source_hash_counts_density_and_slab_rounding():
    d=build()
    assert d["schema"]=="jp.structural.g15.gate17.source_mass_conflict_ledger.v0.1"
    assert d["audit_fact_count"]==11
    assert d["source_pdf_sha256"]=="f122904444a2e2f75230d9d4e41da0093d050da25c6e8140c86d466b7e37cc52"
    assert math.isclose(d["slab_125mm_25kN_m3_implied_selfweight_kPa"],3.125,abs_tol=1e-9)
    assert math.isclose(d["slab_report_rounded_selfweight_kPa"],3.13,abs_tol=1e-9)
    assert math.isclose(d["slab_125mm_20kN_m3_counterfactual_selfweight_kPa"],2.5,abs_tol=1e-9)
    assert not d["whole_building_concrete_density_reconciled"]
    assert not d["slab_thickness_120mm_vs_125mm_reconciled"]

def test_no_hidden_mass_plugs_and_modal_wording():
    d=build()
    g08,g10=d["gap_scenarios"]
    assert math.isclose(g08["unexplained_kN"],772.0329166282687,abs_tol=1e-6)
    assert math.isclose(g10["unexplained_kN"],715.467677,abs_tol=.01)
    assert math.isclose(d["report_seismic_weight_kN"],6831.9109,abs_tol=1e-7)
    assert abs(d["gate08_subtotal_rounding_residual_kN"])<.001
    assert d["mode5_horizontal_90pct_reached"] is True
    assert d["mode6_rotational_90pct_reached"] is True
    assert not d["first_mode_vs_report_period_consistent"]
    assert d["table_first_modal_period_seconds"]==.618
    assert d["narrative_claim_period_seconds"]==.185
    assert not d["modal_screen_source_wording_resolved"]
    assert all(not v["source_verified_reconciliation"] for v in d["gap_scenarios"])

def test_p0_p1_source_blockers_f3_unchanged():
    d=build()
    assert d["original_ETABS_e2k_for_this_building_found"] is False
    assert not d["source_ground_occupancy_consistent_with_residential_summary"]
    assert all(g["ready"] is False for g in d["decision_gates"])
    assert d["F3_status"]=="NOT SAFE IN ONE WAY SHEAR"
    assert not d["source_mass_reconciled"]
    assert not d["engineering_approval"]
    assert d["roadmap"][0]["state"]=="GATE17_NUMERICAL_AUDIT_COMPLETE"
