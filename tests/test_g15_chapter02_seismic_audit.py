"""Original-source Chapter2 seismic, wind, soft-storey, combinations verified without false physical admission."""
import math
from pathlib import Path
from scripts.build_g15_chapter02_seismic_audit import build
ROOT=Path(__file__).resolve().parents[1]
def test_seismic_equations_and_rounded_report_inconsistency():
 d=build();s=d["source_summary"]
 assert s["source_period_distribution_exponent"]==1
 assert math.isclose(s["formula_ULS_coefficient_unrounded"],.13125,abs_tol=1e-14)
 assert s["source_ULS_coefficient_printed"]==.131
 assert math.isclose(s["base_shear_rounded_source_coefficient_kN"],894.9803279,abs_tol=1e-7)
 assert math.isclose(s["base_shear_difference_solely_coefficient_rounding_kN"],.00025*6831.9109,rel_tol=1e-11)
 assert math.isclose(s["base_shear_SLS_formula_kN"],860.8207734,abs_tol=1e-7)
 assert not s["ETABS_source_mass_composition_verified"]
 assert not s["location_hazard_verified"]
 assert not s["accidental_eccentricity_applied_in_numeric_distribution"]
def test_floor_lateral_distribution_conserves_unverified_inferred_mass():
 d=build()
 b=d["balanced_distribution_by_inferred_floor_weights_kN"]
 assert math.isclose(b["ULS"],b["ULS_floor_force_sum_kN"],abs_tol=1e-8)
 assert math.isclose(b["SLS"],b["SLS_floor_force_sum_kN"],abs_tol=1e-8)
 assert len(d["source_conditional_floor_weights_and_forces"])==3
 for x in d["source_conditional_floor_weights_and_forces"]:
  assert x["accepted_load_target_object_id"] is None
  assert x["original_ETABS_story_mass_verified"] is False
 assert b["not_accepted_as_real_model_loading"]
def test_wind_and_soft_story_claims_are_held_without_force_comparisons():
 d=build()
 assert d["wind_screen"]["engineering_status"].startswith("HOLD")
 assert d["wind_screen"]["wind_dominance_proven"] is False
 assert d["soft_storey_screen"]["engineering_status"].startswith("HOLD")
 assert d["soft_storey_screen"]["actual_story_stiffnesses_verified"] is False
 assert d["source_f3_verdict"]=="NOT SAFE IN ONE WAY SHEAR"
 assert d["physical_evidence_accepted"] is False
 assert d["engineering_approval"] is False
def test_combinations_real_code_kernel_only_on_disclosed_synthetic_actions():
 d=build()
 fixture=d["synthetic_load_combination_fixture"]
 assert fixture["input_status"].startswith("SYNTHETIC")
 assert fixture["actual_project_member_or_case_ID"] is None
 assert fixture["result"]["lsm_parallel"]["1_2DL_plus_1_5LL"]==195
 assert fixture["result"]["lsm_parallel"]["DL_plus_lambdaLL_pm_E"]==[95,135]
 assert len(d["open_tasks"])==6
def test_report_sections_in_original_sequential_reading_order():
 s=(ROOT/"site/report.html").read_text()
 a=s.index('id="chapter-02"');z=s.index('id="chapter-03"')
 h=s[a:z]
 assert "g15-chapter02-seismic-audit.v0.1.json" in h
 for tag in ("toc-2-6-4","toc-2-6-5","toc-2-7","toc-2-8"):
  assert h.count('id="'+tag+'"')==1
 assert h.index('id="toc-2-6-4"')<h.index('id="toc-2-6-5"')<h.index('id="toc-2-7"')<h.index('id="toc-2-8"')
 assert "NOT SAFE IN ONE WAY SHEAR" in s
