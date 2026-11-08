"""R6.5 governing ETABS21 source selection is not engineering acceptance."""
import hashlib
import json
import pytest

from scripts.build_r6p5_etabs21_governing_reconciliation import (
    load_registry, build, inspect_raw, emit, SourceError
)


def test_model_authority_updates_without_overwriting_historical_report():
    d=build()
    assert d["model_user_designated_governing"] is True
    assert d["model_versions"]==["21.0.0", "21.0.0"]
    assert d["historic_report_ETABS_version"]==20
    assert d["historic_report_seismic_weight_kN"]==6831.9109
    assert d["historic_report_mass_reproduced_from_current_model"] is False
    assert d["offline_private_source_integrated_applied_mass_eligible_load_kN_excluding_dead_selfweight"]==3290.2187486
    assert d["offline_integral_recomputed_by_CI"] is False
    assert d["offline_integral_is_not_solved_current_model_mass"] is True
    assert d["current_model_stories_mass_kN"] is None
    assert d["current_model_mass_total_kN"] is None
    assert not d["engineering_approval"]
    assert d["physical_mass_reconciliation"]=="HOLD_MODEL_RESULTS_REQUIRED"


def test_registry_contains_exact_governing_drive_source_pair_and_holds():
    r=load_registry()
    assert r["drive_provenance"]["folder_id"]=="172Acs4IPX7AhlcDo9MEmIsc0lizezwL3"
    assert r["model_pair"]["ULS"]["sha256"]=="8860223c80171cd7437b2d54841171f1bafe4ce98c71fd86024e2ec95d08aaa3"
    assert r["model_pair"]["SLS"]["sha256"]=="7b6ca674447e38302d0647d89fbca1830e7d120795ad260bcf926bb9d335227e"
    assert r["local_inspection_observations"]["grid_extent_mm"]==[21000,12550]
    assert r["local_inspection_observations"]["source_patterns"]["Live"]==0.3
    assert not r["admission_gates"]["engineering_approval"]


def test_source_authority_cannot_silently_claim_approval(tmp_path):
    r=load_registry()
    r["admission_gates"]["engineering_approval"]=True
    p=tmp_path/"bad.json";p.write_text(json.dumps(r))
    with pytest.raises(SourceError,match="cannot be claimed"):
        load_registry(p)


def test_regression_rejects_model_sha_tampering(tmp_path):
    r=load_registry()
    r["model_pair"]["ULS"]["sha256"]="x"*64
    p=tmp_path/"bad.json";p.write_text(json.dumps(r))
    with pytest.raises(SourceError,match="Invalid governing model digest"):
        load_registry(p)


def test_missing_private_pair_or_wrong_raw_source_fails_closed(tmp_path):
    r=load_registry()
    p=tmp_path/"dummy.e2k";p.write_bytes(b"$ PROGRAM INFORMATION\n")
    with pytest.raises(SourceError,match="Both ULS and SLS"):
        build(uls=p)
    with pytest.raises(SourceError,match="size mismatch"):
        inspect_raw(p,r["model_pair"]["ULS"])


def test_public_generation_is_idempotent_with_checksum_and_no_model_bytes(tmp_path):
    out=tmp_path/"r6p5-etabs21.json"
    d=emit(out)
    text=out.read_text()
    assert d["current_model_source_binary_verified_in_this_run"] is False
    assert '"current_model_mass_total_kN": null' in text
    assert '"engineering_approval": false' in text
    assert "E:\\" not in text
    assert "LINEASSIGN" not in text and "AREALOAD" not in text
    assert "RAMBAZZAR 2.5 STORY FINAL DEISGN" not in text
    receipt=json.loads((tmp_path/"r6p5-etabs21-manifest.json").read_text())
    assert receipt["sha256"]==hashlib.sha256(out.read_bytes()).hexdigest()
    assert receipt["raw_private_bytes_in_artifact"] is False
    assert receipt["engineer_approval"] is False
