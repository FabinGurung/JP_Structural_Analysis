#!/usr/bin/env python3
"""R6.10 original shell-connected gravity cases AND conditional ESM combinations.

Numerically solves:
  - four original gravity patterns under each ULS/SLS stiffness,
  - centred X/Y equivalent-static source-coefficient sensitivities based on
    independently derived connected-only gross mass, under each role,
  - 11 original ETABS role-specific linear-add combinations using *these
    qualified trial cases* (22 total source-defined algebraic expressions).

CRITICAL: These are NOT the corresponding original ETABS21 design results.
The original source requests ±5% accidental eccentricity and has an
unreconciled seismic mass and 12 original shells without verified base path.
Only the 103 source-connected shells are represented by a 2x2 coarse
non-conforming trial mesh. No engineering approval or final envelopes.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.run_r6p10_connected_shell_gravity import solve
from scripts.build_r6p10_source_shell_mesh import build as source_register

OUT=ROOT/"site/data/r6p10-connected-shell-gravity-casebook.json"
MANIFEST=ROOT/"site/reports/r6p10-connected-shell-gravity-casebook-manifest.json"
GRAVITY=("Dead","Live","WALL LOAD","FLOOR FINISH")
EXPERIMENTAL_SEISMIC=("EQX_CONDITIONAL","EQY_CONDITIONAL")
ALL=GRAVITY+EXPERIMENTAL_SEISMIC

def solve_map(name,source_role):
    if name.startswith("EQX "):
        if name!="EQX "+source_role:raise ValueError("Original combo references seismic case from wrong native role")
        return "EQX_CONDITIONAL"
    if name.startswith("EQY "):
        if name!="EQY "+source_role:raise ValueError("Original combo references seismic case from wrong native role")
        return "EQY_CONDITIONAL"
    if name in ("TANK","STAIRCASE LOAD"):
        return None # zero source object loads in adopted E2K
    if name in GRAVITY:
        return name
    raise ValueError("Unknown source case "+name)

def build_casebook():
    reg=source_register()
    results={}
    for role in ("ULS","SLS"):
        raw={}
        for pattern in ALL:
            entry=solve(role,pattern,2)
            assert entry["coarse_numerical_shell_elements"]==412
            assert len(entry["signed_member_end_actions_bounded"])==165
            if pattern in GRAVITY:
                assert entry["vertical_equilibrium_residual_N"]<max(
                    .05,entry["applied_gravity"]["total_applied_downward_N"]*3e-5)
            else:
                assert entry["horizontal_equilibrium_residual_N"]<max(
                    .1,entry["applied_conditional_lateral"]["conditional_base_shear_input_N"]*3e-5)
                assert not entry["full_source_auto_seismic_case_reproduced"]
            raw[pattern]=entry
        combos=[]
        for combo in reg["original_loadcase_and_combination_register"][role]["source_11_load_combinations"]:
            is_seismic=combo["contains_lateral_seismic"]
            mapped_terms=[]
            for term in combo["terms"]:
                mapped_terms.append((solve_map(term["case"],role),float(term["scale"])))
            member_actions={}
            for member in raw["Dead"]["signed_member_end_actions_bounded"]:
                values=[0.]*12
                for mapped,factor in mapped_terms:
                    if mapped is None:continue
                    operands=raw[mapped]["signed_member_end_actions_bounded"][member]
                    values=[x+factor*y for x,y in zip(values,operands)]
                member_actions[member]=[round(z,5) for z in values]
            reactions=[0.]*3
            applied_N=[0.]*3
            for mapped,scale in mapped_terms:
                if mapped is None:continue
                case=raw[mapped]
                reactions=[x+scale*y for x,y in zip(reactions,case["sum_native_fixed_base_reactions_N"])]
                if mapped in GRAVITY:
                    applied_N[2]-=scale*case["applied_gravity"]["total_applied_downward_N"]
                else:
                    axis_idx=0 if case["applied_conditional_lateral"]["axis"]=="X" else 1
                    applied_N[axis_idx]+=scale*case["applied_conditional_lateral"]["conditional_base_shear_input_N"]
            residuals=[abs(r+applied) for r,applied in zip(reactions,applied_N)]
            maximum=max(residuals)
            tolerance=max(.5,sum(abs(x) for x in applied_N)*6e-5)
            if maximum>tolerance:
                raise ValueError("Original combination sensitivity lost global force equilibrium "+combo["name"])
            combos.append({
              "original_source_name":combo["name"],
              "original_source_terms":combo["terms"],
              "source_seismic_combination":is_seismic,
              "status":("CONDITIONAL_CENTRED_SEISMIC_SOURCE_COEFFICIENT_RESEARCH_COMBINATION_NOT_ETABS"
                        if is_seismic else
                        "SOURCE_GRAVITY_COMBINATION_NUMERICALLY_REPLAYED_ON_COARSE_103_SHELL_RESEARCH_MODEL"),
              "signed_member_end_actions_non_design":member_actions,
              "combined_reactions_N":[round(x,5) for x in reactions],
              "applied_resultant_N":[round(x,5) for x in applied_N],
              "force_residual_N":[round(x,5) for x in residuals],
              "source_eccentricity_plus_minus_5pct_applied":False,
              "source_mass_accepted_by_engineer":False,
              "fully_reproduced_original_source_case":False,
              "design_envelope_approved":False,
              "F3_one_way_shear_unsafe":True})
        if len(combos)!=11 or sum(x["source_seismic_combination"] for x in combos)!=8:
            raise ValueError("Native 11 combination coverage changed")
        results[role]={
          "original_role_specific_stiffness":role,
          "independently_run_research_patterns":raw,
          "recombined_original_11_linear_add_expressions":combos,
          "original_three_gravity_only_combinations_numerically_replayed":True,
          "original_eight_seismic_combinations_evaluated_as_conditional_proxies":True,
          "original_ETABS21_eccentric_seismic_combinations_reproduced":False}
    return {
      "schema":"jp.structural.r6p10.connected_source_shell_gravity_and_conditional_seismic_casebook.v0.2",
      "source_model_fingerprints":reg["governing_source_sha256"],
      "source_mesh_115_imported":True,"source_shells_numerically_solved":103,
      "original_shells_source_vertically_unanchored":12,
      "original_structural_frames_numerically_solved":165,
      "numerical_shell_2x2_coarse_research_only":True,
      "source_8x8_mesh_exactly_reproduced":False,
      "source_diaphragm_groups_included":3,
      "original_27_base_restraints_declared_21_physically_used":True,
      "replayed_source_gravity_pattern_cases":8,
      "replayed_source_conditional_seismic_pattern_cases":4,
      "recombined_original_source_linear_add_expressions":22,
      "original_source_eccentric_seismic_results_reproduced":False,
      "source_approved_seismic_mass_reproduced":False,
      "all_source_gravity_and_seismic_combination_envelopes_reproduced":False,
      "role_results":results,
      "F3_one_way_shear_unsafe":True,"engineering_approval":False}

def export():
    d=build_casebook()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(d,indent=2,sort_keys=True,allow_nan=False)+"\n")
    manifest={
      "schema":"jp.structural.r6p10.connected_shell_casebook_receipt.v0.2",
      "casebook_SHA256":hashlib.sha256(OUT.read_bytes()).hexdigest(),
      "source_governing_E2K_SHA256":d["source_model_fingerprints"],
      "independently_run_gravity_stiffness_cases":8,
      "independently_run_centred_source_coefficient_seismic_sensitivities":4,
      "source_combinations_algebraically_evaluated":22,
      "actual_original_ETABS21_seismic_with_eccentricity_reproduced":False,
      "source_auto_8x8_mesh_reproduced":False,
      "original_unanchored_shells":12,
      "full_building_design_accepted":False,
      "engineering_approval":False,"F3_one_way_shear_unsafe":True}
    MANIFEST.parent.mkdir(parents=True,exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    return d,manifest

if __name__=="__main__":
    a,b=export()
    print("R6P10_8_GRAVITY_PLUS_4_CENTRED_SEISMIC_SENSITIVITIES_22_SOURCE_COMBO_EXPRESSIONS_NOT_ETABS_DESIGN")
