"""Fail-closed source integrity and design-HOLD tests for Gate08 public projection."""
import copy
import json
import pytest
from scripts import build_g15_gate08_public as module

def test_complete_sanitized_gate08_projection():
    d=module.build()
    assert d["cohort"]["variants"]==16
    assert d["cohort"]["solved_cases"]==816
    assert d["cohort"]["signed_member_end_action_records"]==134640
    assert d["engineering_approval"] is False
    assert d["mass_kN"]["remaining_residual"]>0
    assert d["f3_source_failure"]=="NOT SAFE IN ONE WAY SHEAR"
    assert any(s["numerical_drift_screen_exceeded"] for s in d["scenarios"])
    assert any(not s["numerical_drift_screen_exceeded"] for s in d["scenarios"])

@pytest.mark.parametrize("mutate",[
    lambda d: d["mass_kN"].update(remaining_residual=0),
    lambda d: d.update(engineering_approval=True),
    lambda d: d.update(exact_slab_edges_verified=True),
    lambda d: d["scenarios"].pop(),
    lambda d: d["scenarios"][0].update(roof_mm=float("nan")),
])
def test_invalid_public_source_projection_is_rejected(tmp_path,monkeypatch,mutate):
    d=json.loads(module.SOURCE.read_text(encoding="utf-8"))
    mutate(d)
    new=tmp_path/"bad_source.json"
    new.write_text(json.dumps(d,allow_nan=True),encoding="utf-8")
    monkeypatch.setattr(module,"SOURCE",new)
    with pytest.raises((AssertionError,ValueError)):
        module.build()
