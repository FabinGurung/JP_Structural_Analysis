#!/usr/bin/env python3
"""Source cited Chapter 2.1–2.4 materials and cover; pure arithmetic with independent cross-checks.

All output is public-safe/illustrative: no inferred original member assignment.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
from jp_structural.solvers.native.material_properties import (
 rectangular_section, concrete_modulus_sqrt_model,isotropic_shear_modulus)
from jp_structural.solvers.native.gravity_loads import member_self_weight
ROOT=Path(__file__).resolve().parents[1]
SCHEMA="jp.structural.g15.chapter02.source_audit.v0.1"
def build():
 d=json.loads((ROOT/"registry/g15-chapter02-source-facts.v0.1.json").read_text())
 assert d["schema"]=="jp.structural.g15.chapter02.source_facts.v0.1"
 assert len(d["recorded"])==21 and len({v["id"] for v in d["recorded"]})==21
 assert all(v["basis"] for v in d["recorded"])
 assert not any(d["public_safety"][k] for k in ("engineering_approval","source_geometry_verified","member_assignments_verified","seismic_mass_path_verified"))
 assert d["public_safety"]["original_F3"]=="NOT SAFE IN ONE WAY SHEAR"
 assert len(d["admission_gates"])==8 and all(x["status"] in ("OPEN","BLOCKED_SOURCE") for x in d["admission_gates"])
 p=d["inputs_for_illustrations"]
 fck=p["concrete_grade_fck_MPa"]
 e=concrete_modulus_sqrt_model(fck,p["concrete_modulus_coefficient"])["elastic_modulus_MPa"]
 hand=p["concrete_modulus_coefficient"]*math.sqrt(fck)
 assert math.isclose(e,hand,rel_tol=1e-13)
 assert math.isclose(e,22360.679774997898,rel_tol=1e-12)
 printE=p["printed_modulus_MPa"]
 assert abs(printE-e)>1000, "Source modulus conflict unexpectedly resolved: audit required"
 nu=next(x["value"] for x in d["recorded"] if x["item"]=="poisson_ratio")
 g=isotropic_shear_modulus(e,nu)["shear_modulus_MPa"]
 assert math.isclose(g,e/(2*(1+nu)),rel_tol=1e-13)
 candidates=[]
 for size in p["competing_square_column_widths_m"]:
  props=rectangular_section(size,size)
  area=props["area_m2"]
  assert math.isclose(area,size*size,abs_tol=1e-13)
  for gamma in sorted({p["conflicting_gamma_kN_m3"],p["plain_gamma_kN_m3"],p["reinforced_gamma_kN_m3"]}):
   w=member_self_weight(area,p["member_length_m"],gamma)["self_weight_kN"]
   assert math.isclose(w,size**2*p["member_length_m"]*gamma,rel_tol=1e-12)
   candidates.append({"scenario_id":f"SQ{round(size*10000):04d}-G{int(gamma)}",
      "square_side_m":size,"area_m2":area,"length_m":p["member_length_m"],
      "gamma_kN_m3":gamma,"trial_member_weight_kN":w,
      "input_status":"UNASSIGNED_SOURCE_ALTERNATIVE","member_or_node_id":None,
      "not_project_selfweight":True})
 cover=[]
 for dia in p["sample_cover_bar_diameters_mm"]:
  cover.append({"bar_diameter_mm":dia,"source_beam_cover_mm":max(25,dia),
   "source_slab_cover_mm":max(20,dia),
   "compliance_status":"SOURCE_FORMULA_ARITHMETIC_ONLY_NOT_VERIFIED_DETAIL"})
 value={
 "schema":SCHEMA,"source_report_sha256":d["original_pdf"]["sha256"],
 "chapter":"2.1–2.4 (plus related source conflicts)",
 "source_record_count":len(d["recorded"]),
 "acceptance_gates":d["admission_gates"],
 "gate_open_count":len(d["admission_gates"]), "gate_accepted_count":0,
 "source_findings":{
  "concrete_fck_MPa":fck,
  "source_printed_E_MPa":printE,
  "original_source_formula":"E_MPa = 5000 * sqrt(20)",
  "independent_formula_E_MPa":e,
  "source_modulus_difference_MPa":printE-e,
  "source_reported_steel_fy_MPa":500,
  "source_printed_steel_E_MPa":200,
  "steel_modulus_admitted_for_design":False,
  "material_density_conflict_kN_m3":[20,24,25],
  "concrete_G_from_formula_MPa":g,
  "source_rebar_standard_conflict":["IS1786:1985","IS1786:2008"]
 },
 "illustrative_square_member_alternatives":candidates,
 "cover_formula_examples":cover,
 "labels":{"all_calculations":"AUDIT_AND_BOUNDING_SCENARIOS_ONLY",
   "scenario_section_geometry":"SOURCE_CONFLICT_TWO_ALTERNATIVES_NOT_SELECTED",
   "scenario_member_length":"SOURCE_REPORTED_LEVEL_HEIGHT_NOT_AUTHENTICATED_ELEMENT",
   "scenario_density":"SOURCE_ALTERNATIVE_NOT_ASSIGNED_TO_ELEMENT"},
 "source_records":d["recorded"],
 "engineering_approval":False,"actual_model_materials_verified":False,
 "actual_member_load_assignments_verified":False,
 "original_F3_verdict":"NOT SAFE IN ONE WAY SHEAR"
 }
 return value
def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--output",default="site/data/g15-chapter02-source-audit.v0.1.json")
 a=parser.parse_args()
 x=build()
 o=Path(a.output);o.parent.mkdir(parents=True,exist_ok=True)
 o.write_text(json.dumps(x,sort_keys=True,indent=2)+"\n")
 print("G15_CHAPTER02_SOURCE_ARITHMETIC_PASS",x["source_record_count"],
       x["gate_open_count"],len(x["illustrative_square_member_alternatives"]),
       "E_COMPARISON",round(x["source_findings"]["independent_formula_E_MPa"],3),
       "NOT_APPROVED")
if __name__=="__main__":main()
