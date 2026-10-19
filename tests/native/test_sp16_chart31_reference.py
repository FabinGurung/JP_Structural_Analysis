"""Primary SP16:1980 p.116 Chart31 bounded direct visual checks.

Source measurements are independently authored in registry JSON; the
numerical solver must not supply or rewrite their expected values.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
import pytest
from jp_structural.solvers.native.sp16_chart31_reference import (
    FIXTURE, build_chart31_comparison,
)


def test_sp16_chart31_original_image_two_direct_visual_spotpoints():
    out=build_chart31_comparison()
    assert out["all_sampled_points_agree"] is True
    assert len(out["points"])==2
    assert all(x["absolute_normalized_error"]<=x["visual_uncertainty_absolute_normalized_moment"]
               for x in out["points"])
    assert all(x["independent_worked_example_error"]<.002 for x in out["points"])
    assert out["historical_code_basis"]=="IS456:1978"
    assert not out["full_sp16_chart31_curve_digitization_complete"]
    assert not out["code_edition_reconciliation"]["full_edition_parity_verified"]
    assert not out["engineering_approval"]


def test_chart31_wrong_original_axis_ordinate_does_not_silently_pass():
    fixture=json.loads(FIXTURE.read_text(encoding="utf-8"))
    fixture["points"][0]["chart_read_mu_over_fck_bD2"]=.16
    with pytest.raises(ValueError,match="outside primary chart visual uncertainty"):
        build_chart31_comparison(fixture)


def test_chart31_invalid_claim_of_full_chart_or_edition_parity_is_rejected():
    raw=json.loads(FIXTURE.read_text(encoding="utf-8"))
    for flag in ("full_chart_curves_digitized","IS456_1978_to_2000_clause_parity_verified","engineering_approval"):
        fixture=copy.deepcopy(raw)
        fixture["acceptance"][flag]=True
        with pytest.raises(ValueError,match="acceptance flags"):
            build_chart31_comparison(fixture)
