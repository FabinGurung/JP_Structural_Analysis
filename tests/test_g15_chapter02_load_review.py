"""Bounded original report 2.5/2.6 load source checks, not model assignment."""
from __future__ import annotations
import math
from pathlib import Path
from scripts.build_g15_chapter02_load_review import build
ROOT=Path(__file__).resolve().parents[1]
def test_source_wall_load_inputs_and_independent_values():
 d=build()
 assert d["schema"]=="jp.structural.g15.chapter02.load_review.v0.1"
 a=d["wall_load_arithmetic"]
 assert [x["id"] for x in a]==["L-MAIN-GROSS","L-MAIN-OPEN","L-PART-GROSS","L-PART-OPEN","L-PARAPET"]
 for x in a:
  assert x["target_beam_id"] is None
  assert x["actual_wall_segment_id"] is None
  assert x["source_assignment_verified"] is False
  assert math.isfinite(x["computed_minus_source_kN_m"])
 assert d["numeric_screen_discrepancies_count"]==2
 assert abs(a[4]["computed_from_source_inputs_kN_m"]-2.1888)<1e-8
 assert a[4]["printed_kN_m"]==2.10
 assert math.isclose(d["source_wall_height_vs_storey_height_gap_m"],.002,abs_tol=1e-12)
def test_no_actual_load_assignments_or_occupancy_admitted():
 d=build()
 assert d["member_load_assignments_accepted"]==0
 assert not d["source_mass_reconciliation_complete"]
 assert not d["source_geometry_verified"]
 assert not d["private_ETABS_load_assignment_verified"]
 assert not d["engineering_approval"]
 assert d["original_F3_verdict"]=="NOT SAFE IN ONE WAY SHEAR"
 for x in d["reported_live_load_rate_register"]:
  assert x["target_area_id"] is None
  assert x["assigned_area_m2"] is None
  assert x["actual_element_load_verified"] is False
def test_load_report_panel_and_json_contract_present():
 page=(ROOT/"site/report.html").read_text()
 idx=page.index('id="chapter-02"')
 end=page.index('id="chapter-03"')
 ch=page[idx:end]
 assert "c02-wall-audit" in ch
 assert "g15-chapter02-load-review.v0.1.json" in ch
 assert "No individual wall or area load" in ch
 assert "NOT SAFE IN ONE WAY SHEAR" in page
