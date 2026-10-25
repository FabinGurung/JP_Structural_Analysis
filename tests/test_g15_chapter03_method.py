"""Original §3 procedure, real OpenSees 3D numerical workflow and fail-closed admission."""
from pathlib import Path
import math,pytest
from scripts.build_g15_chapter03_method import build
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope="module")
def result():return build()

def test_source_method_real_opensees_actions_and_equilibrium(result):
 d=result;n=d["real_OpenSees_numerical_snapshot"]
 assert d["schema"]=="jp.structural.g15.chapter03.method_execution.v0.1"
 assert n["nodes"]==92 and n["members"]==165
 assert n["case_count"]==5 and n["signed_member_end_action_records"]==825
 assert n["signed_local_components_per_record"]==12
 assert n["case_labels"]==["GRAVITY","EQ_PLUS_X","EQ_MINUS_X","EQ_PLUS_Y","EQ_MINUS_Y"]
 assert n["max_equilibrium_force_residual_kN"]<.001
 assert n["max_equilibrium_moment_residual_kNm"]<.001
 assert all(math.isfinite(n[x]) for x in ("max_abs_member_axial_kN","max_abs_member_shear_kN",
               "max_abs_member_bending_kNm","max_abs_member_torsion_kNm"))
 assert n["max_abs_member_bending_kNm"]>0
 assert len(n["model_grid_SHA256"])==64 and len(n["solver_request_SHA256"])==64

def test_method_is_not_approved_site_or_real_member_design(result):
 assert len(result["stages"])==12
 assert [x["id"] for x in result["stages"]]==["M"+str(i).zfill(2) for i in range(1,13)]
 assert all(x["physical_building_accepted"] is False for x in result["stages"])
 assert result["accepted_engineering_method_stages"]==0
 assert result["source_gates_open"]==15
 assert result["original_native_ETABS_model_authenticated"] is False
 assert result["source_floor_loads_and_mass_authenticated"] is False
 assert result["actual_structural_member_design_completed"] is False
 assert result["engineering_approval"] is False
 assert result["original_F3_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"

def test_original_program_and_code_citation_conflicts_preserved(result):
 programs={x["program"] for x in result["original_programs"]}
 assert {"ETABS v20.0.0","SAFE 2016","Excel worksheets"}<=programs
 code={x["printed"] for x in result["source_code_citation_conflicts"]}
 assert "NBC 150:2025" in code and "IS456:2000+1392:2016" in code
 assert result["reported_SBC_kPa"]==160
 assert result["reported_settlement_mm"]==25
 assert result["source_geotechnics_authenticated"] is False
 assert any(x["member"]=="Floor Slab" and "120 mm" in x["reported_size"] for x in result["original_member_schedule"])
 assert any("300" in x["reported_size"] and x["source_status"]=="SOURCE_STRING_UNIT_CONFLICT" for x in result["original_member_schedule"])

def test_report_reading_order_links_source_method_and_results():
 h=(ROOT/"site/report.html").read_text()
 a=h.index('id="chapter-03"');b=h.index('id="chapter-04"')
 ch=h[a:b]
 for mark in ("chapter-03-procedure","chapter-03-source-programs","chapter-03-stages",
              "chapter-03-real-results","chapter-03-open-holds"):
  assert ch.count('id="'+mark+'"')==1
 assert "g15-chapter03-method.v0.1.json" in ch
 assert "original source" in ch.lower()
 assert "NOT SAFE IN ONE WAY SHEAR" in ch
 assert "more.html#guide-fem-triad" in ch
 assert "reports/g15-gate21-calculation-report.html" in ch
