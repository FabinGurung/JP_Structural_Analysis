"""Gate18: independently constrain numeric source seismic weight and source F3 fail."""
import math
from scripts.build_g15_gate18_mass_f3 import build

def test_pdf_three_storey_mass_numbers_reproduce_original_etabs_seismic_weight_with_inferred_kg():
 d=build()
 assert d["schema"]=="jp.structural.g15.gate18.story_mass_and_f3_safety.v0.1"
 assert len(d["source_floor_conditional_weights"])==3
 assert math.isclose(d["source_three_storey_sum_reported_mass_number"],696661.02,abs_tol=1e-9)
 assert math.isclose(d["reconstructed_from_story_table_W_kN"],6831.910791783,abs_tol=1e-8)
 assert abs(d["reported_minus_story_table_W_kN"])<d["max_rounding_bound_kN"]<.0002
 assert d["source_report_ETABS_seismic_W_kN"]==6831.9109
 assert d["reported_mass_table_units_printed"] is False
 assert d["kilograms_inferred_not_native_ETABS_verified"] is True
 assert d["ETABS_source_mass_settings_observed"] is False
 assert not d["mass_source_reconciled"]

def test_independent_base_entry_exclusion_not_concealed():
 d=build()
 assert d["source_base_mass_number"]==18434.33
 assert d["weight_including_base_mass_kN"]>d["source_report_ETABS_seismic_W_kN"]+180
 assert d["base_mass_excluded_from_reproduced_total"] is True
 assert d["base_mass_actual_ETABS_mass_source_exclusion_setting_verified"] is False

def test_previous_component_reconstruction_gaps_not_closed_by_exact_story_mass():
 d=build()
 gap=d["older_trial_composition_gap_remains_unresolved"]
 assert math.isclose(gap["G08_vs_source_difference_kN"],772.0329166282687,abs_tol=1e-6)
 assert math.isclose(gap["G10_vs_source_difference_kN"],715.467677,abs_tol=.01)
 assert gap["source_floor_weights_from_table_not_assigned_to_provisional_slab_objects"] is True
 assert d["actual_slab_and_wall_assignments_observed"] is False

def test_original_unsafe_F3_verdict_and_rounded_shear_conflicts_take_precedence():
 d=build()
 assert d["f3_source_explicit_verdict"]=="NOT SAFE IN ONE WAY SHEAR"
 assert math.isclose(d["f3_source_sheet_effective_depth_mm"],423.46278,abs_tol=1e-6)
 assert d["f3_prior_reconstruction_assumed_depth_mm"]==394
 assert d["f3_source_displayed_shear_stresses_coarsely_rounded"] is True
 assert not d["f3_current_design_accepted"]
 assert not d["f3_actual_geotechnics_verified"]
 assert not d["engineering_approval"]

def test_four_conditional_thickness_cases_never_are_accepted_redesigns():
 d=build()
 s=d["f3_hypothetical_depth_trials"]
 assert [v["trial_overall_thickness_mm"] for v in s]==[450,500,550,600]
 assert all(v["service_P_assumed_kN"]>571 and
            v["ultimate_P_assumed_kN"]>v["service_P_assumed_kN"] and
            not v["redesign_accepted"] and
            v["source_f3_fail_override_prohibited"] for v in s)
 assert all(len(v["oneway_tau_v_MPa"])==2 and len(v["oneway_tau_c_MPa"])==2 for v in s)
 assert all(math.isfinite(v["service_bearing_kPa"]) for v in s)
 assert d["f3_hypothetical_depth_screen_is_NOT_redesign"] is True
