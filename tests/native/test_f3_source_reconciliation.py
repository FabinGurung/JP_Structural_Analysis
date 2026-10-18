"""Source-derived F3 unsafe flag dominates any math scenario."""
from scripts.reconcile_f3_source import build
def test_source_precedent_unsafe_not_overwritten_by_assumed_f3_calculation():
    f=build()
    r=f["reconstructed_numerics"]
    assert f["status"]=="FAIL_SOURCE_UNSAFE_DO_NOT_ADOPT"
    assert f["source_extraction"]["source_f3_one_way_shear_flag"]=="NOT SAFE IN ONE WAY SHEAR"
    assert f["source_extraction"]["source_adopted_schedule_label"].startswith("IF3")
    assert not f["adopted_design_accepted"]
    assert not f["engineering_approval"]
    assert f["reconciliation"]["source_reconstructed_pressure_matches"]
    assert f["reconciliation"]["ultimate_load_factor_on_source_with_selfweight"]==1.4275
    assert r["factored_pressure_kPa"]>194.
    assert r["engineering_approval"] is False
