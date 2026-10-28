"""Reusable seven-chapter report template: actual numerical kernels, source flags and reproducibility."""
from __future__ import annotations
import copy
import csv
import hashlib
import json
import math
from pathlib import Path

import pytest

from scripts.build_structural_template_engine import (
    DEFAULT_CASE, INPUT_SCHEMA, SCHEMA, TemplateInputError,
    build, emit, validate,
)

ROOT=Path(__file__).resolve().parents[1]
F3=ROOT/"examples/sanitized/template_engine_f3_conditional.v0.2.json"

@pytest.fixture(scope="module")
def result():
    return build()

def test_original_seven_chapter_table_of_contents_and_18_requirements(result):
    assert result["schema"]==SCHEMA
    assert len(result["chapters"])==7
    assert [c["chapter"] for c in result["chapters"]]==[f"{i:02d}" for i in range(1,8)]
    headings={h["number"] for c in result["chapters"] for h in c["headings"]}
    for requirement in ("1.1","2.1","2.6.4","2.8","4.1","5.1","5.7","5.15","6.1","6.2","6.3","6.4","6.5"):
        assert requirement in headings
    mids={x["id"] for c in result["chapters"] for x in c["requirements"]}
    assert mids=={f"M{i:02d}" for i in range(1,17)}|{"S17","S18"}
    assert result["modules_calculated"]==["M03","M08","M09","M10","M11","M12","M14"]
    assert result["all_18_modules_complete"] is False

def test_seismic_floor_force_distribution_equilibrium(result):
    x=result["numerical_results"]["M03_ESM"]
    assert x["seismic_weight_kN"]==pytest.approx(2220)
    assert x["base_shear_kN"]==pytest.approx(244.2)
    assert sum(x["floor_forces_kN"])==pytest.approx(x["base_shear_kN"],abs=1e-8)
    assert x["status"]=="NUMERICALLY_BALANCED_DISTRIBUTION_ONLY"
    assert x["accidental_eccentricity_applied"] is False

def test_real_beam_joint_column_slab_stair_kernels_and_approximate_strip_hand_math(result):
    x=result["numerical_results"]
    assert x["M08_beam_flexure"]["formula_id"]=="JP-RC-M08-FLEXURE-001"
    assert x["M08_beam_flexure"]["engineering_approval"] is False
    assert x["M09_biaxial_column"]["engineering_approval"] is False
    assert x["M10_joint_shear"]["engineering_approval"] is False
    slab=x["M11_slab_strip"];stair=x["M14_stair_strip"]
    assert slab["one_m_strip_Mu_kNm_per_m"]==pytest.approx(1.5*(5.13+2)*3.6**2/8)
    assert stair["one_m_strip_Mu_kNm_per_m"]==pytest.approx(1.5*(8.41+3)*2.8**2/8)
    assert slab["provided_As_mm2_per_m"]==pytest.approx(math.pi*8**2/4*1000/150)
    assert stair["provided_As_mm2_per_m"]==pytest.approx(math.pi*12**2/4*1000/125)
    for v in (slab,stair):
        assert v["actual_supports_and_load_path_verified"] is False
        assert v["deflection_shear_development_and_detailing_checked"] is False
        assert v["engineering_approval"] is False

def test_footing_candidate_search_is_bounded_numerically_real_and_noncertifying(result):
    rows=result["M12_footing_candidates"]
    assert len(rows)==3*4*2==result["M12_candidate_count"]
    assert len({x["id"] for x in rows})==len(rows)
    assert result["M12_numeric_candidate_count"]==sum(all(x["checks"].values()) for x in rows)
    assert all(x["design_approved"] is False and x["full_foundation_design"] is False for x in rows)
    assert all(x["calculation"]["engineering_approval"] is False for x in rows)
    assert all(x["verified_site_bearing"] is False and x["verified_footing_reactions"] is False for x in rows)
    x=next(x for x in rows if x["B_mm"]==2200 and x["D_mm"]==450 and x["bar_spacing_mm"]==150)
    assert x["calculation"]["service_pressure_kPa"]==pytest.approx(640/(2.2*2.2))
    assert x["calculation"]["factored_pressure_kPa"]==pytest.approx(960/(2.2*2.2))
    assert x["d_mm"]==450-50-6
    assert x["Ast_mm2_per_m"]==pytest.approx(math.pi*12**2/4*1000/150)

def test_original_unsafe_F3_is_never_cleared_by_any_candidate():
    case=json.loads(F3.read_text())
    out=build(case)
    assert out["source_class"]=="SOURCE_DERIVED_UNVERIFIED"
    assert out["original_unsafe_flags_preserved"]==["NOT SAFE IN ONE WAY SHEAR"]
    assert out["M12_candidate_count"]==24
    assert all(x["design_approved"] is False for x in out["M12_footing_candidates"])
    assert out["engineer_approved"] is False and out["permit_eligible"] is False
    assert out["public_issue_for_construction"] is False

def test_case_provenance_and_geometry_validation_fails_closed():
    base=json.loads(DEFAULT_CASE.read_text())
    for mutate in (
       lambda c:c["provenance"].pop("footing"),
       lambda c:c["footing"].update({"loads_include_footing_and_backfill":False}),
       lambda c:c["footing"].update({"plan_mm":[500,500]}),
       lambda c:c["footing"].update({"cover_mm":800}),
       lambda c:c["seismic"]["stories"].reverse(),
       lambda c:c["material"].update({"fy_MPa":650}),
       lambda c:c.update({"classification":"SOURCE_APPROVED"}),
       lambda c:c["seismic"].update({"period_seconds":float("nan")}),
       lambda c:c["seismic"]["stories"][0].update({"weight_kN":True}),
    ):
        inp=copy.deepcopy(base);mutate(inp)
        with pytest.raises((TemplateInputError,KeyError,ValueError,TypeError)):
            build(inp)
    with pytest.raises(TemplateInputError):
        validate({},json.loads((ROOT/"registry/report-template-contract.v0.2.json").read_text()))

def test_reference_export_is_readable_hashed_reproducible_and_never_claims_approval(tmp_path):
    a=emit(DEFAULT_CASE,tmp_path)
    n="template-engine-reference"
    names=[n+".json",n+".md",n+".html",n+"-footing-candidates.csv"]
    manifest=json.loads((tmp_path/(n+"-manifest.json")).read_text())
    assert set(manifest["files"])==set(names)
    for p in names:
       assert manifest["files"][p]==hashlib.sha256((tmp_path/p).read_bytes()).hexdigest()
    assert (tmp_path/(n+".json")).read_text()==json.dumps(a,indent=2,sort_keys=True,allow_nan=False)+"\n"
    body=(tmp_path/(n+".html")).read_text()
    for s in ("NOT ENGINEERING APPROVED","Chapter 01","Chapter 07","Submission eligibility","NOT APPROVED"):
       assert s in body
    md=(tmp_path/(n+".md")).read_text()
    assert "## Chapter 06" in md and "Original registry status" in md
    data=list(csv.DictReader((tmp_path/(n+"-footing-candidates.csv")).open()))
    assert len(data)==24
    assert all(r["engineering_approval"]=="False" for r in data)
    assert manifest["engineering_approval"] is False

def test_original_report_annex_has_link_to_independent_template_not_f3_pass():
    text=(ROOT/"site/report.html").read_text()
    assert 'id="annex-template-engine"' in text
    assert "reports/template-engine-reference.html" in text
    assert "reports/template-engine-reference-manifest.json" in text
    assert "NOT SAFE IN ONE WAY SHEAR" in text
