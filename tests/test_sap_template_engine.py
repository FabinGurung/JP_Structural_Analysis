"""Reusable structural template contract, source provenance and fail-closed submission QA."""
from pathlib import Path
import copy,json,pytest
from scripts.build_sap_template_case import assess,render_md,InputError,ROOT,CONTRACT

@pytest.fixture
def case():
    return json.loads((ROOT/"examples/sap_template/reference_case.v0.1.json").read_text())

def test_7_chapter_contract_from_source_toc():
    c=json.loads(CONTRACT.read_text())
    assert c["schema"]=="jp.structural.sap.template.v0.1"
    assert [x["chapter"] for x in c["chapters"]]==["01","02","03","04","05","06","07"]
    assert c["chapters"][5]["source_outline"]==["6.1 Column","6.2 Beam","6.3 Slab","6.4 Foundation","6.5 Stair"]
    assert len(c["standards"])>=6
    assert c["status"]=="T0_IMPLEMENTED_SUBMISSION_NOT_READY"

def test_reference_gravity_and_combination_values(case):
    r=assess(case)
    c=r["calculations"]
    assert c["slab_selfweight_kPa"]==pytest.approx(3.125)
    assert c["dead_area_total_kPa"]==pytest.approx(5.125)
    assert c["cases"][0]["total_vertical_force_kN"]==pytest.approx(92.25)
    assert c["cases"][1]["pressure_kPa"]==pytest.approx(10.6875)
    assert c["cases"][1]["total_vertical_force_kN"]==pytest.approx(192.375)
    assert all(not x["is_code_approved_combination"] for x in c["cases"])
    assert not r["approval"]["submission_ready"]
    assert len(r["required_design_modules"])==12
    assert all(x["design_pass"] is False for x in r["required_design_modules"])
    assert not r["source_custody"]["verified"]

@pytest.mark.parametrize("key,val",[
    ("slab_thickness_m",-1),("concrete_density_kN_m3",0),
    ("area_m2",float("nan")),("live_area_kN_m2",float("inf")),
    ("dead_area_kN_m2",False)])
def test_bad_numeric_inputs_fail_closed(case,key,val):
    case["inputs"][key]=val
    with pytest.raises(InputError):assess(case)

def test_no_implicit_seismic_analysis(case):
    case["load_cases"][0]["type"]="SEISMIC"
    with pytest.raises(InputError,match="unsupported load type"):assess(case)

def test_no_unreviewed_unknown_code_edition(case):
    case["code_edition"]="NBC 105:2099"
    with pytest.raises(InputError,match="unregistered"):assess(case)

def test_missing_source_provenance_rejected(case):
    case["source_custody"]={}
    with pytest.raises(InputError):assess(case)

def test_markdown_has_seven_sections_and_submission_warning(case):
    s=render_md(assess(case))
    assert all(f"## {i}." in s for i in range(1,8))
    assert "Submission ready: NO" in s
    assert "full analysis" not in s.lower() or "NOT" in s

def test_engineering_report_example_not_real_project():
    sample=json.loads((ROOT/"examples/sap_template/reference_case.v0.1.json").read_text())
    assert sample["source_custody"]["verified"] is False
    assert sample["engineer_review"]["signed"] is False
    assert "HYPOTHETICAL" in sample["site"]
