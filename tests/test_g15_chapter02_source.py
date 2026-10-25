"""Original report 2.1–2.4 versus independent Python arithmetic and original source holds."""
from __future__ import annotations
import math,json
from pathlib import Path
from scripts.build_g15_chapter02_source_audit import build
ROOT=Path(__file__).resolve().parents[1]
def test_source_scoped_arithmetic_and_safety():
 d=build(); s=d["source_findings"]
 assert d["schema"]=="jp.structural.g15.chapter02.source_audit.v0.1"
 assert d["source_record_count"]==21 and d["gate_open_count"]==8
 assert d["gate_accepted_count"]==0
 assert d["engineering_approval"] is False
 assert d["actual_member_load_assignments_verified"] is False
 assert d["original_F3_verdict"]=="NOT SAFE IN ONE WAY SHEAR"
 assert math.isclose(s["independent_formula_E_MPa"],5000*math.sqrt(20),rel_tol=1e-13)
 assert s["source_modulus_difference_MPa"]>2600
 assert s["source_printed_steel_E_MPa"]==200
 assert s["steel_modulus_admitted_for_design"] is False
 assert sorted(s["material_density_conflict_kN_m3"])==[20,24,25]
def test_source_alternative_member_weights_not_applied_to_project():
 d=build(); rows=d["illustrative_square_member_alternatives"]
 assert len(rows)==6
 assert len({(v["square_side_m"],v["gamma_kN_m3"]) for v in rows})==6
 for v in rows:
  assert math.isclose(v["trial_member_weight_kN"],
   v["square_side_m"]**2*3.048*v["gamma_kN_m3"],rel_tol=1e-14)
  assert v["member_or_node_id"] is None
  assert v["not_project_selfweight"] is True
 assert rows[0]["square_side_m"]==.3556
 assert rows[-1]["square_side_m"]==.4
def test_report_clear_cover_is_checked_as_original_source_not_adopted_code():
 d=build()
 for x in d["cover_formula_examples"]:
  dia=x["bar_diameter_mm"]
  assert x["source_beam_cover_mm"]==max(25,dia)
  assert x["source_slab_cover_mm"]==max(20,dia)
  assert x["compliance_status"].endswith("NOT_VERIFIED_DETAIL")
def test_public_page_chapter_order_and_solver_provenance():
 h=(ROOT/"site/report.html").read_text()
 a=h.index('id="chapter-02"');b=h.index('id="chapter-03"')
 c=h[a:b]
 assert "g15-chapter02-source-audit.v0.1.json" in c
 for n in ("2-1","2-2","2-3","2-4","2-5"):assert c.count('id="toc-'+n+'"')==1
 assert [c.index('id="toc-'+n+'"') for n in ("2-1","2-2","2-3","2-4","2-5")]==sorted(c.index('id="toc-'+n+'"') for n in ("2-1","2-2","2-3","2-4","2-5"))
 assert "NOT SAFE IN ONE WAY SHEAR" in h
 assert "Source-based arithmetic" in c
