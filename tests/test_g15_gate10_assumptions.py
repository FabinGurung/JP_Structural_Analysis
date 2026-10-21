"""Bounded floor/wall/ETABS mass assumptions are reproducible, not approval."""
import math
from scripts.build_g15_gate10_assumptions import build,area,hull_of

def test_scaled_candidate_floor_outlines_match_only_source_area_captions():
    d=build()
    f=d["footprints"]
    assert f["grid_hull_area_m2"]>224.3
    assert f["all_physical_slab_boundaries_verified"] is False
    assert [round(area(p["scaled_convex_hull_outline_xy_m"]),2)
            for p in f["assumed_per_floor"]]==[218.68,212.09,188.11]
    assert all(p["drawing_polygon_verified"] is False for p in f["assumed_per_floor"])

def test_explicit_edge_assignments_are_unverified_and_topologically_listed():
    d=build()
    w=d["wall_candidates"]
    assert len(w["edges"])==7
    assert math.isclose(w["trial_length_per_level_m"],
      sum(x["length_m"] for x in w["edges"]),abs_tol=1e-9)
    assert w["wall_locations_verified"] is False
    assert all(x["source_verified_wall"] is False for x in w["edges"])

def test_sensitivity_variants_conserve_weight_without_mass_fabrication():
    d=build()
    W=d["source_seismic_W_kN"]
    base=d["baseline_working_W_kN"]
    assert math.isclose(W-base,772.0329166282687,abs_tol=.001)
    cases={x["id"]:x for x in d["model_cases"]}
    assert len(cases)==9
    for c in cases.values():
        assert len(c["floor_weights_kN"])==3
        assert math.isclose(sum(c["floor_weights_kN"]),
           c["trial_seismic_weight_kN"],abs_tol=1e-7)
        assert math.isclose(c["source_minus_trial_kN"],
           W-c["trial_seismic_weight_kN"],abs_tol=1e-7)
        assert c["seismic_mass_accepted"] is False
        assert c["verified_source_mass_match"] is False
    assert cases["G10_INVERSE_FIT"]["classification"]=="INVERSE_NUMERICAL_FIT_NOT_EVIDENCE"
    assert math.isclose(cases["G10_INVERSE_FIT"]["source_minus_trial_kN"],0,abs_tol=1e-7)
    assert cases["G10_COMMERCIAL"]["hypothetical_mass_change_kN"]>0
    assert cases["G10_THIN_SLAB"]["hypothetical_mass_change_kN"]<0

def test_etabs_mass_source_options_separate_double_count_from_equivalence():
    d=build()
    m={x["id"]:x for x in d["etabs_mass_source_alternatives"]}
    assert math.isclose(m["ELEMENT_SELF_PLUS_ADDITIONAL_LOADS"]["trial_W_kN"],
          m["LOAD_PATTERN_ONLY_WITH_SELFWEIGHT"]["trial_W_kN"],abs_tol=.001)
    assert m["DOUBLE_COUNT_ERROR_SENSITIVITY"]["double_count_flag"] is True
    assert m["DOUBLE_COUNT_ERROR_SENSITIVITY"]["trial_W_kN"]>d["source_seismic_W_kN"]
    assert all(x["actual_ETABS_setting_known"] is False for x in m.values())

def test_nonstorage_and_roof_participation_are_not_mixed():
    d=build()
    occ=d["occupancy_trial"]
    assert math.isclose(occ["assumed_eligible_seismic_live_fraction"],.3)
    assert occ["roof_eligible_live_share"]==0
    assert occ["commercial_source_live_intensity_verified"] is False
    assert d["diaphragm_verified"] is False
    assert d["engineering_approval"] is False
    assert d["source_F3_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"
