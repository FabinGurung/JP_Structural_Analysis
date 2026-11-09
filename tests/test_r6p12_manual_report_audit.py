"""R6.12 manual archived-report audit: arithmetic cannot become engineering acceptance."""
import json
import math
from pathlib import Path
from scripts.build_r6p12_manual_report_audit import calculate, export

def test_historical_report_scope_and_adverse_engineering_hold():
    x=calculate()
    assert x["schema"]=="jp.structural.r6p12.manual_historical_report_audit.v0.1"
    assert x["historical_report_sha256"]=="f122904444a2e2f75230d9d4e41da0093d050da25c6e8140c86d466b7e37cc52"
    assert not x["source_model_solver_reproduced"]
    assert not x["engineering_approval"]
    assert x["unsupported_source_shells_excluded"]==12
    assert x["F3_one_way_shear_unsafe"]
    assert len(x["checks"])>=40
    assert x["counts"]["CONFLICT"]>=6
    assert x["counts"]["NOT_REPRODUCED"]>=5
    assert x["counts"]["ENGINEERING_HOLD"]==1
    assert all(not a["current_etabs21_solver_result"] for a in x["checks"])

def test_historical_report_key_arithmetic_and_critical_mismatch():
    x=calculate()
    by={z["subject"]:z for z in x["checks"]}
    assert by["ULS coefficient"]["calculated"]==.13125
    assert by["First mode achieving 90% in both axes"]["calculated"]==5
    assert abs(by["Seismic weight from three printed mass entries"]["calculated"]-6831.9109)<.0002
    assert abs(by["ULS static base shear with printed rounded coefficient"]["calculated"]-894.9803)<.0002
    assert by["F3 cover-based effective depth scenario"]["calculated"]==394
    assert by["F3 cover-based effective depth scenario"]["status"]=="CONFLICT"
    assert abs(by["Stair 12 mm at 127 mm provided steel"]["calculated"]-890.5302)<.001
    assert by["F3 one-way shear status"]["status"]=="ENGINEERING_HOLD"

def test_generated_report_is_inspectable_and_preserves_project_navigation():
    x=export()
    p=Path("site/projects/pokhara-g15/manual-verification.html")
    j=Path("site/data/r6p12-manual-report-audit.json")
    assert p.is_file() and j.is_file()
    content=p.read_text(encoding="utf-8")
    assert "Manual verification of the archived structural report" in content
    assert "F3 remains NOT SAFE IN ONE WAY SHEAR" in content
    assert "Back to project report" in content
    assert len(json.loads(j.read_text())["checks"])==len(x["checks"])
