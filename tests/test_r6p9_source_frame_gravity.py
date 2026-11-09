"""R6.9 native-source ETABS21-to-OpenSees frame-only bridge and fail-closed QA."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import math

import pytest
from scripts.run_r6p9_source_frame_gravity import (
    BridgeError, CONTROLS, UNCOMPRESSED_SHA256, controls, topology,
    section_props, solve, generate,
)

def test_private_governing_source_binding_and_source_controls():
    model,src=controls()
    assert len(src["roles"])==2
    assert len(src["roles"]["ULS"]["supports"])==27
    assert len(src["roles"]["SLS"]["diaphragms"]["GF:D1"])==67
    assert len(src["roles"]["SLS"]["diaphragms"]["FF:D2"])==80
    assert len(src["roles"]["SLS"]["diaphragms"]["TF:D3"])==54
    assert len(src["roles"]["ULS"]["mesh"])==115
    assert len(src["roles"]["ULS"]["combos"])==11
    assert src["status"]["F3_one_way_shear_unsafe"]
    assert not src["status"]["professional_approval"]
    assert not model["result_scope"]["complete_solved_member_end_forces"]

def test_uls_sls_original_modifiers_differ_without_relabeling_geometry():
    _,a=controls()
    for role,beam,col in (("ULS",.35,.7),("SLS",.7,.9)):
        sec=a["roles"][role]["frame_modifiers"]
        assert sec["beam 12*16"]["I3MOD"]==beam
        assert sec["Col 400*400"]["I2MOD"]==col
        assert sec["BEAM 9*12"]["JMOD"]==.1
    assert a["roles"]["ULS"]["supports"]==a["roles"]["SLS"]["supports"]

def test_topology_honors_unconnected_4_islands_not_fake_shell_supported():
    model,src,elements,xyz,supported,loads,ledger=topology()
    assert ledger["frame_components"]==7
    assert ledger["anchored_frame_components"]==3
    assert ledger["unanchored_islands"]==4
    assert ledger["unsupported_island_nodes"]==8
    assert ledger["source_frame_elements_retained"]==161
    assert ledger["source_frame_elements_withheld_without_support"]==4
    assert len(elements)==161
    assert all(u in supported and v in supported for m,u,v in elements)
    assert len(loads)==70
    assert ledger["direct_beam_wall_loads_deferred"]==7
    assert ledger["unsectioned_loaded_line_records_deferred"]==30
    assert ledger["source_wall_load_records"]==107
    assert ledger["source_selfweight_excluded"]
    assert ledger["rigid_diaphragm_source_assignments_not_yet_enforced"]
    assert not ledger["accepted_full_model_analysis"] and ledger["F3_one_way_shear_unsafe"]

def test_source_frame_section_explicit_cracking_and_st_venant_torsion_proxy():
    model,src,*_=topology()
    sec=model["frame_sections"]["beam 12*16"]
    mat=src["roles"]["ULS"]["material_elasticity"][sec["material"]]
    cracked=section_props(sec,mat,src["roles"]["ULS"]["frame_modifiers"]["beam 12*16"])
    gross=section_props(sec,mat,{})
    assert cracked[0]==120000
    assert cracked[1]==22360.68
    assert cracked[2]==pytest.approx(22360.68/2.4)
    assert cracked[4]==pytest.approx(gross[4]*.35)
    assert cracked[5]==pytest.approx(gross[5]*.35)
    assert gross[3]>0

def test_rigid_diaphragm_and_shell_transfer_remain_unmodeled():
    *_,ledger=topology()
    assert ledger["original_rigid_diaphragm_point_assignments"]==201
    assert ledger["original_shell_assignments"]==115
    assert ledger["original_ETABS21_solver_result_verified"] is False
    assert ledger["member_force_scope_if_solved"]=="BOUNDED_WALL_LOAD_BASELINE_ONLY"

@pytest.mark.parametrize("role",["ULS","SLS"])
def test_supported_actual_source_3d_frame_numeric_case_and_reaction_equilibrium(role):
    s=solve(role)
    assert s["status"]=="SOURCE_NATIVE_BOUNDED_GRAVITY_FRAME_NUMERICALLY_SOLVED"
    assert s["solved_elements"]==161
    assert s["direct_assigned_uniform_loads"]==70
    assert s["reaction_vertical_residual_N"]<.05
    assert s["reconstructed_base_reaction_kN"][2]==pytest.approx(s["applied_vertical_load_kN"],abs=.001)
    assert len(s["actual_source_member_end_actions_bounded_only"])==161
    assert all(len(v)==12 and all(math.isfinite(x) for x in v) for v in s["actual_source_member_end_actions_bounded_only"].values())
    assert not s["shell_force_transfer_included"]
    assert not s["rigid_diaphragm_enforced"]
    assert not s["original_ETABS21_result"]
    assert not s["engineering_approval"] and s["F3_one_way_shear_unsafe"]

def test_both_stiffness_variants_distinct_without_passing_for_approved_design():
    u=solve("ULS")
    v=solve("SLS")
    assert u["applied_vertical_load_kN"]==v["applied_vertical_load_kN"]
    assert abs(u["maximum_nodal_translation_mm"]-v["maximum_nodal_translation_mm"])>1e-9
    assert u["status"]==v["status"]
    assert not u["full_member_design_envelope"] and not v["full_member_design_envelope"]

def test_deterministic_json_and_manifest_source_guardrails():
    doc,receipt=generate()
    p=Path("site/data/r6p9-etabs21-bounded-frame-solver.json")
    assert receipt["result_sha256"]==hashlib.sha256(p.read_bytes()).hexdigest()
    assert receipt["source_control_sha256"]==UNCOMPRESSED_SHA256
    assert receipt["solved_cases"]==["ULS","SLS"]
    assert not receipt["full_ETABS21_solver_replication"]
    assert not receipt["engineering_approval"] and receipt["F3_one_way_shear_unsafe"]
    txt=p.read_text()
    assert "RAMBAZZAR" not in txt and "E:\\\\" not in txt
    assert not doc["professional_engineering_approval"]
