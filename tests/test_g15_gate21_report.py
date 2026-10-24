"""Run real OpenSees SAR and assert open provenance and structural safety holds."""
import csv,hashlib,json,math
import pytest
from scripts.build_g15_gate21_report import calculate,export,get_inputs,default

@pytest.fixture(scope="module")
def output():return calculate()

def test_real_five_solved_cases_and_source_conditional_mass(output):
 d,v=output
 assert d["schema"]=="jp.structural.g15.gate21.open_reproducible_sar.v0.1"
 assert d["counts"]["members"]==165 and d["case_count"]==5 and len(v)==825
 assert d["signed_end_action_count"]==825
 assert d["ESM"]["W_kN"]==pytest.approx(6831.910791783,abs=1e-6)
 assert abs(d["ESM"]["conditional_weight_gap_kN"])<.0002
 assert {p["id"] for p in d["provenance"]}==set(default())-{"schema"}
 assert next(x for x in d["provenance"] if x["id"]=="C_design")["class"]=="ASSUMED"
 assert not d["engineering_approval"] and d["F3_verdict"]=="NOT SAFE IN ONE WAY SHEAR"

def test_equilibrium_chords_and_signed_forces(output):
 d,v=output
 assert [c["name"] for c in d["cases"]]==["GRAVITY","EQ_PLUS_X","EQ_MINUS_X","EQ_PLUS_Y","EQ_MINUS_Y"]
 assert all(c["force_residual_kN"]<.001 and c["moment_residual_kNm"]<.001 for c in d["cases"])
 assert all(len(c["story_chord_metrics"])==3 for c in d["cases"])
 assert all(not s["NBC_drift_evaluated"] for c in d["cases"] for s in c["story_chord_metrics"])
 assert len({x["member"] for x in v})==165
 assert all(math.isfinite(x["Ni"]) and math.isfinite(x["Mzi"]) for x in v)
 assert not d["modal_performed"] and not d["p_delta_performed"] and not d["member_rebar_design_performed"]

def test_export_print_html_csv_markdown_json_integrity(output,tmp_path,monkeypatch):
 import scripts.build_g15_gate21_report as engine
 monkeypatch.setattr(engine,"calculate",lambda request_file=None:output)
 d,m=export(tmp_path)
 assert len(m["files"])==4 and not m["engineering_approval"]
 for name,s in m["files"].items():
  assert hashlib.sha256((tmp_path/name).read_bytes()).hexdigest()==s["sha256"]
 html=(tmp_path/"g15-gate21-calculation-report.html").read_text()
 assert "Print / Save PDF" in html and "NOT SAFE IN ONE WAY SHEAR" in html and "OpenSeesPy" in html
 with (tmp_path/"g15-gate21-signed-member-actions.csv").open() as f:
  rows=list(csv.DictReader(f))
 assert len(rows)==825 and "Mzj" in rows[0]
 md=(tmp_path/"g15-gate21-calculation-report.md").read_text()
 assert all("## "+str(i)+"." in md for i in range(1,8))

def test_custom_request_requires_all_citations(tmp_path):
 p=tmp_path/"case.json"
 p.write_text(json.dumps({"solver_request":default(),"provenance":{}}))
 with pytest.raises(ValueError,match="provenance"):get_inputs(p)
