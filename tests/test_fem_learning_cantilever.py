"""Real OpenSees member and manual stiffness cross-validation."""
import math,json
from pathlib import Path
from scripts.build_fem_learning_cantilever import generate,hand
def test_four_load_cases_are_real_opensees_solved():
 d=generate()
 assert d["schema"]=="jp.structural.teaching_cantilever.real_opensees.v0.1"
 assert not d["project_model_used"] and not d["engineering_approval"]
 assert [x["applied_tip_fx_kN"] for x in d["cases"]]==[5,10,15,20]
 for x in d["cases"]:
  f=x["applied_tip_fx_kN"];v=x["opensees"];h=x["independent_hand"]
  assert math.isclose(v["node_tip_ux_m"],h["tip_displacement_m"],rel_tol=1e-8)
  assert math.isclose(abs(v["base_reaction_rx_kN"]),f,abs_tol=1e-7)
  assert math.isclose(v["base_reaction_mz_kNm"],f*3,abs_tol=1e-7)
  assert math.isclose(v["horizontal_force_residual_kN"],0,abs_tol=1e-7)
  assert math.isclose(v["global_moment_residual_kNm"],0,abs_tol=1e-7)
  assert len(v["element_local_end_forces"])==6

def test_analytic_reference_is_not_copied_from_solver():
 h=hand(10.0)
 assert math.isclose(h["I_m4"],0.000675,rel_tol=1e-10)
 assert math.isclose(h["tip_displacement_m"]*1000,5.3333333333,rel_tol=1e-10)
 assert math.isclose(h["support_moment_abs_kNm"],30.0)
 assert math.isclose(h["tip_rotation_abs_rad"],0.00266666666667,rel_tol=1e-9)

def test_workflow_roles_and_structural_code_rules_are_not_automatic_design():
 d=json.loads(Path(__file__).resolve().parents[1].joinpath("registry/fem-workflow-map.v0.1.json").read_text())
 assert d["normalization"]["physical_implementation"]=="PROPOSED_NOT_MIGRATED"
 assert len(d["menus"])==14 and len(d["entities"])==16
 assert d["code_library"]["registered_bounded_clauses"]==14
 assert any(v["name"]=="supports" for v in d["entities"])
 assert any(v["name"]=="load_assignments" for v in d["entities"])
 assert any(v["name"]=="design_checks" for v in d["entities"])
 assert d["support_load_truth"]["rule"].startswith("No actual support")
