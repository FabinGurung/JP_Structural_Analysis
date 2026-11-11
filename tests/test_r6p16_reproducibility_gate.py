"""R6.16 verify honest bounded-engine vs full original report distinction."""
from copy import deepcopy
import pytest
from scripts.build_r6p16_reproducibility_gate import (
    build, read_json, COVERAGE, GOVERNING, HISTORICAL, SCHEMA
)
from scripts.build_r6p15_incomplete_edge_audit import build as r615_build
from scripts.build_g15_gate21_report import calculate as gate21_calculate

@pytest.fixture(scope="module")
def authorities():
    return (read_json(COVERAGE),read_json(GOVERNING),read_json(HISTORICAL))

@pytest.fixture(scope="module")
def existing():
    return r615_build(),gate21_calculate()[0]

def audit(authorities,existing,**overrides):
    a,b,c=authorities
    d,gate=existing
    return build(
       r615=overrides.get("r615",d),
       coverage=overrides.get("coverage",a),
       governing=overrides.get("governing",b),
       historical=overrides.get("historical",c),
       gate21=overrides.get("gate21",gate))

def test_real_source_engine_runs_but_full_ETABS_and_design_not_claimed(authorities,existing):
    d=audit(authorities,existing)
    assert d["schema"]==SCHEMA
    assert d["module_count"]==18
    assert d["module_coverage_status_counts"]=={
        "DRAFT_UNVALIDATED":1,"IMPLEMENTED_BOUNDED":2,"MISSING":4,"PARTIAL":11}
    assert len(d["modules"])==18
    assert len(d["reproducibility_stages"])==7
    assert len(d["critical_gates"])==6
    assert len({m["id"] for m in d["modules"]})==18
    assert all(not m["engineered_design_approved"] for m in d["modules"])
    assert {g["priority"] for g in d["critical_gates"]}=={"P0","P1"}
    assert not d["module_coverage_is_sufficient_for_full_project_report"]
    scope=d["reproduction"]
    assert scope["first_party_bounded_engine_solutions_executable"]
    assert scope["Gate21_assumption_frame_solved_cases"]==5
    assert scope["Gate21_assumption_frame_member_end_action_rows"]==825
    assert scope["R610_original_source_shells"]==115
    assert scope["R610_source_shells_in_bounded_coarse_solver"]==103
    assert scope["R610_source_shells_excluded"]==12
    assert scope["R615_reviewed_missing_perimeter_slabs"]==77
    assert scope["R615_original_edges_inspected"]==308
    assert not scope["full_governing_ETABS21_model_equivalent"]
    assert not scope["all_historical_report_results_recomputed"]
    assert not scope["complete_project_code_based_RCC_design_approved"]
    assert not scope["signed_original_support_reactions_obtained"]
    assert not scope["engineering_approval"]
    assert scope["F3_one_way_shear_unsafe"]
    assert not d["engineering_approval"]
    assert d["engineering_acceptance"]=="NOT ACCEPTED"
    assert d["twelve_unsupported_shells_excluded"]
    assert d["F3_one_way_shear_unsafe"]
    assert d["never_replace_missing_source_reactions_with_zeros"]

def test_drive_provenance_version_registered_but_not_live_pages_source(authorities,existing):
    d=audit(authorities,existing)
    auth=d["source_scope"]
    assert auth["governing_ULS_SLS_SHA256"]=={
        "ULS":"8860223c80171cd7437b2d54841171f1bafe4ce98c71fd86024e2ec95d08aaa3",
        "SLS":"7b6ca674447e38302d0647d89fbca1830e7d120795ad260bcf926bb9d335227e"}
    assert not auth["raw_private_E2K_checked_into_public_github"]
    assert not auth["source_drift_detection_against_drive_at_each_build"]
    assert not auth["governing_model_last_verified_Google_Drive_metadata_in_this_audit"]
    assert not auth["historical_pdf_is_original_current_model_solution"]
    assert "not continuous Google Drive" in auth["published_pipeline"]

def test_tampering_cannot_upgrade_engine_or_foundation(authorities,existing):
    a,b,c=authorities
    edge,gate=existing
    stale=deepcopy(a)
    stale["requirements"][0]["status"]="IMPLEMENTED_BOUNDED"
    with pytest.raises(ValueError,match="Unreviewed change"):
        audit(authorities,existing,coverage=stale)
    bad=deepcopy(b);bad["admission_gates"]["engineering_approval"]=True
    with pytest.raises(ValueError,match="Source acceptance"):
        audit(authorities,existing,governing=bad)
    bad=deepcopy(c);bad["foundation"]["acceptance"]=True
    with pytest.raises(ValueError,match="Historical report"):
        audit(authorities,existing,historical=bad)
    bad=deepcopy(edge);bad["coverage"]["slabs_examined"]=78
    with pytest.raises(ValueError,match="R6.15"):
        audit(authorities,existing,r615=bad)
    bad=deepcopy(gate);bad["model_ETABS_source_verified"]=True
    with pytest.raises(ValueError,match="Gate21"):
        audit(authorities,existing,gate21=bad)
    bad=deepcopy(gate);bad["F3_verdict"]="SAFE"
    with pytest.raises(ValueError,match="Gate21"):
        audit(authorities,existing,gate21=bad)
