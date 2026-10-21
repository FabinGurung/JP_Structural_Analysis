"""Guarded hypothetical diaphragm: eight signed ±X/Y and ±5% eccentricity screens."""
import math
from scripts.build_g15_gate11_torsion_proxy import build

def test_rigid_floor_proxy_reactions_balance_signed_loads_and_moment():
    d=build()
    assert len(d["cases"])==8
    assert d["source_mass_case_id"]=="G10_EDGE_COMM"
    assert all(len(case["floors"])==3 for case in d["cases"])
    assert all(len(x["column_force_distribution"])==23
               for case in d["cases"] for x in case["floors"])
    for case in d["cases"]:
        for p in case["floors"]:
            r=p["column_force_distribution"]
            assert math.isclose(sum(x["signed_floor_shear_X_kN"] for x in r),p["sum_column_X_kN"],abs_tol=1e-7)
            assert math.isclose(sum(x["signed_floor_shear_Y_kN"] for x in r),p["sum_column_Y_kN"],abs_tol=1e-7)
            assert math.isclose(p["sum_column_torsion_kNm"],p["signed_torsional_demand_about_stiffness_center_kNm"],abs_tol=1e-7)

def test_accidental_eccentricity_demand_changes_sign():
    d=build()
    eq=[a for a in d["cases"] if a["axis"]=="X" and a["lateral_sign"]==1]
    assert len(eq)==2
    v=[a["floors"][0]["signed_torsional_demand_about_stiffness_center_kNm"] for a in eq]
    assert not math.isclose(v[0],v[1],abs_tol=1e-7)
    assert math.isclose(abs(d["source_grid_span_xy_m"][0]),21.,abs_tol=1e-8)
    assert math.isclose(d["accidental_eccentricity_fraction"],.05)

def test_assumption_not_rebranded_as_verified_structure():
    d=build("G10_INVERSE_FIT","SLS")
    assert d["footprints_and_real_wall_placements_verified"] is False
    assert d["actual_story_drift_accepted"] is False
    assert d["P_delta_checked"] is False
    assert d["mass_source_reconciled"] is False
    assert d["engineering_approval"] is False
    assert d["foundation_F3_source"]=="NOT SAFE IN ONE WAY SHEAR"

def test_cracked_stiffness_changes_displacement_not_static_load_totals():
    a=build("G10_EDGE_COMM","ULS")
    b=build("G10_EDGE_COMM","SLS")
    assert math.isclose(a["floor_base_shear_kN"],b["floor_base_shear_kN"],abs_tol=1e-7)
    assert a["cases"][0]["max_trial_story_displacement_mm"]>b["cases"][0]["max_trial_story_displacement_mm"]
