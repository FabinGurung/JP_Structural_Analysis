"""Gate20 exact source crosswalk and F3 source contradictions, never structural approval."""
import math,json
from pathlib import Path
import pytest
from scripts.build_g15_gate20_crosswalk import build

def test_15_evidence_gates_have_source_FKs_and_no_false_pass():
 d=build()
 assert d["schema"]=="jp.structural.g15.gate20.crosswalk_F3_reconciliation.v0.1"
 assert d["gate_count"]==15 and d["accepted_gate_count"]==0
 assert d["topological_dependencies_acyclic"] is True
 assert all(g["source_observation_ids"] and g["acceptance_test"] and
            g["required_by_role"] and not g["accepted"] and not g["source_provider_readback"]
            for g in d["gates"])
 assert {g["priority"] for g in d["gates"]}=={"P0","P1"}
 assert d["upstream_native_ETABS_model_found"] is False
 assert d["engineering_approval"] is False

def test_F3_worksheet_pressure_reconstruction_catches_missing_selfweight():
 f=build()["f3"]
 assert math.isclose(f["foundation_plan_area_m2"],4.41,abs_tol=1e-12)
 assert math.isclose(f["reconstructed_printed_q_from_1p5_times_571_kPa"],194.2176870748,abs_tol=1e-7)
 assert math.isclose(f["alternative_1p5_times_600_kPa"],204.081632653,abs_tol=1e-7)
 assert math.isclose(f["factored_pressure_difference_kPa"],9.8639455782,abs_tol=1e-7)
 assert math.isclose(f["source_service_with_selfweight_pressure_kPa"],136.0544217687,abs_tol=1e-7)
 assert f["source_verdict"]=="NOT SAFE IN ONE WAY SHEAR"
 assert f["source_nominal_and_allowable_shear_stresses_displayed_equal_only_after_rounding"] is True
 assert f["soil_bearing_settlement_verified"] is False

def test_F3_depth_and_reinforcement_obligation_preserved():
 d=build()
 f=d["f3"]
 assert f["source_sheet_effective_depth_mm"]==423.46278
 assert f["previous_trial_effective_depth_mm"]==394
 assert math.isclose(f["discrepancy_mm"],29.46278,abs_tol=1e-8)
 assert not f["F3_redesign_verified"] and not f["source_f3_design_accepted"]
 assert next(x for x in d["gates"] if x["id"]=="G20-F3-015")["status"]=="FAILED_SOURCE_ONE_WAY_SHEAR"

def test_no_fake_ETABS_mass_parity_from_source_aggregate():
 d=build()
 assert d["reported_ETABS_W_kN"]==6831.9109
 assert d["source_three_storey_mass_arithmetic_identity"] is True
 assert d["native_ETABS_mass_unit_and_source_definition_verified"] is False
 assert d["component_mass_reconciliation_complete"] is False
 assert math.isclose(d["trial_G08_mass_gap_kN"],772.032916628269,abs_tol=1e-5)
 assert math.isclose(d["trial_G10_mass_gap_kN"],715.467677,abs_tol=.01)

def test_model_provider_missing_does_not_clear_any_hard_gate():
 d=build()
 assert [g["id"] for g in d["gates"] if g["accepted"]]==[]
 assert not d["source_engineering_signoff"]
 assert all(g["status"]!="PASS" for g in d["gates"])
