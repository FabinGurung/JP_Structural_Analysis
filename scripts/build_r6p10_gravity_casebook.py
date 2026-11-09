#!/usr/bin/env python3
"""R6.10 complete original gravity PATTERN matrix on supported source shells.

Runs Dead/Live/WALL LOAD/FLOOR FINISH in BOTH governing ETABS21 ULS/SLS
elastic stiffness variants, 103 source-supported shells and 165 frames each.
Superposes 3 originally defined non-seismic combinations; the other 8 native
seismic combinations are not falsely computed without source mass/eigen checks.

All output is research trial / non-conforming coarse mesh; not building
approval or verified ETABS source auto-generated shell finite elements.
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
PATTERNS=("Dead","Live","WALL LOAD","FLOOR FINISH")

def build_casebook():
    reg=source_register()
    cases={}
    for role in ("ULS","SLS"):
        solutions={}
        for pattern in PATTERNS:
            entry=solve(role,pattern,2)
            assert entry["coarse_numerical_shell_elements"]==412
            assert entry["vertical_equilibrium_residual_N"]<max(
               .05,entry["applied_gravity"]["total_applied_downward_N"]*3e-5)
            assert len(entry["signed_member_end_actions_bounded"])==165
            solutions[pattern]=entry
        combinations=[]
        for combo in reg["original_loadcase_and_combination_register"][role]["source_11_load_combinations"]:
            needed=[term for term in combo["terms"] if term["case"].startswith(("EQX","EQY"))]
            if needed:
                combinations.append({"source_name":combo["name"],"source_terms":combo["terms"],
                    "status":"NATIVE_SEISMIC_CASE_NOT_SOLVED_DO_NOT_CLAIM_DESIGN_ENVELOPE",
                    "signed_actions":None,"base_reactions_N":None,
                    "unsupported_original_shells":12,
                    "source_original_all_load_cases_reproduced":False})
                continue
            actions={}
            for member in solutions["Dead"]["signed_member_end_actions_bounded"]:
                values=[0.]*12
                for term in combo["terms"]:
                    if term["case"] not in solutions:
                        if term["case"] not in ("TANK","STAIRCASE LOAD"):
                            raise ValueError("Unrecognized source gravity pattern "+term["case"])
                        # Those source patterns have no object load assignments.
                        continue
                    operand=solutions[term["case"]]["signed_member_end_actions_bounded"][member]
                    values=[a+term["scale"]*b for a,b in zip(values,operand)]
                actions[member]=[round(x,5) for x in values]
            reactions=[0.,0.,0.]
            total=0.
            for term in combo["terms"]:
                if term["case"] not in solutions:continue
                target=solutions[term["case"]]
                reactions=[x+term["scale"]*y for x,y in zip(
                    reactions,target["sum_native_fixed_base_reactions_N"])]
                total+=term["scale"]*target["applied_gravity"]["total_applied_downward_N"]
            residual=abs(reactions[2]-total)
            if residual>max(.1,abs(total)*4e-5):
                raise ValueError("Original gravity combination lost overall vertical equilibrium")
            combinations.append({
              "source_name":combo["name"],"source_terms":combo["terms"],
              "status":"SOURCE_LINEAR_COMBINATION_SERVED_BY_COARSE_103_SHELL_GRAVITY_RESEARCH_TRIAL",
              "signed_actions":actions,
              "base_reactions_N":[round(v,5) for v in reactions],
              "source_combo_applied_downward_N":round(total,5),
              "vertical_equilibrium_residual_N":round(residual,5),
              "source_original_all_load_cases_reproduced":False,
              "full_building_analysis":False,
              "unsupported_original_shells":12,
              "not_a_design_envelope":True})
        if len(combinations)!=11 or sum(x["signed_actions"] is not None for x in combinations)!=3:
            raise ValueError("Source 11-combo registry/three gravity-only status changed")
        cases[role]={"original_stiffness_variant":role,"source_gravity_pattern_results":solutions,
                     "original_source_linear_combination_register":combinations,
                     "original_seismic_combinations_withheld":8,
                     "original_source_gravity_only_combinations_tried":3,
                     "all_source_ETABS21_seismic_cases_solved":False}
    return {
      "schema":"jp.structural.r6p10.connected_source_shell_gravity_pattern_casebook.v0.1",
      "source_model_fingerprints":reg["governing_source_sha256"],
      "source_mesh_115_imported":True,"source_shells_numerically_solved":103,
      "original_shells_source_vertically_unanchored":12,
      "original_structural_frames_numerically_solved":165,
      "numerical_shell_2x2_coarse_research_only":True,
      "source_8x8_mesh_exactly_reproduced":False,
      "all_original_diaphragm_groups_included_in_trial":True,
      "original_27_base_restraints_declared_21_physically_used":True,
      "all_source_gravity_pattern_cases_in_connected_subset_solved":True,
      "all_source_gravity_and_seismic_combination_envelopes_reproduced":False,
      "role_results":cases,
      "F3_one_way_shear_unsafe":True,
      "engineering_approval":False}

def export():
    doc=build_casebook()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(doc,indent=2,sort_keys=True,allow_nan=False)+"\n")
    manifest={
      "schema":"jp.structural.r6p10.connected_shell_gravity_casebook_receipt.v0.1",
      "output_sha256":hashlib.sha256(OUT.read_bytes()).hexdigest(),
      "governing_E2K_SHA256":doc["source_model_fingerprints"],
      "source_cases_8_gravity":[f"{r}:{p}" for r in ("ULS","SLS") for p in PATTERNS],
      "source_gravity_combinations_replayed_6":True,
      "source_seismic_combinations_replayed":False,
      "source_all_shells_structurally_supported":False,
      "engineering_approval":False,"F3_one_way_shear_unsafe":True}
    MANIFEST.parent.mkdir(parents=True,exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    return doc,manifest

if __name__=="__main__":
    doc,receipt=export()
    print("R6P10_8_SOURCE_GRAVITY_CASES_6_COMBOS_COARSE_103_CONNECTED_SHELLS_HOLD_12_AND_SEISMIC")
