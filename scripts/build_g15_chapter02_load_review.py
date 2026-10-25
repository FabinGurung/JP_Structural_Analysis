#!/usr/bin/env python3
"""Original report wall-load arithmetic readback: NEVER assign inferred geometry or loads to building."""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
from jp_structural.solvers.native.gravity_loads import wall_line_dead_load
ROOT=Path(__file__).resolve().parents[1]
def build():
 src=json.loads((ROOT/"registry/g15-chapter02-load-facts.v0.1.json").read_text())
 assert src["schema"]=="jp.structural.g15.chapter02.load_rate_sources.v0.1"
 p=src["reported_dimensions"]
 G=p["wall_unit_weight_kN_m3"];H=p["wall_gross_floor_height_m"];D=p["beam_deduction_m"]
 main=p["main_thickness_m"];part=p["partition_thickness_m"]
 calc=[
 wall_line_dead_load(G,H,0,main,D)["line_load_kN_m"],
 wall_line_dead_load(G,H,p["main_opening_fraction"],main,D)["line_load_kN_m"],
 wall_line_dead_load(G,H,0,part,D)["line_load_kN_m"],
 wall_line_dead_load(G,H,p["partition_opening_fraction"],part,D)["line_load_kN_m"],
 wall_line_dead_load(G,p["parapet_height_m"],0,p["parapet_thickness_m"],0)["line_load_kN_m"]
 ]
 assert len(src["reported_line_rates"])==5 and len(src["reported_live_load_rates"])==3
 rows=[]
 for index,(x,rate) in enumerate(zip(src["reported_line_rates"],calc)):
  diff=rate-x["printed_kN_m"]
  assert math.isfinite(rate) and math.isfinite(diff) and rate>0
  rows.append({"id":x["id"],"source_label":x["label"],
    "printed_kN_m":x["printed_kN_m"],"computed_from_source_inputs_kN_m":rate,
    "computed_minus_source_kN_m":diff,
    "absolute_discrepancy_over_0p01":abs(diff)>src["checks"]["absolute_discrepancy_threshold_kN_m"],
    "formula":x["formula"],"citation":x["citation"],
    "actual_wall_segment_id":None,"target_beam_id":None,
    "source_assignment_verified":False})
 assert abs(calc[0]-11.7024)<1e-10
 assert abs(calc[1]-9.244896)<1e-9
 assert abs(calc[2]-5.5968)<1e-10
 assert abs(calc[3]-4.47744)<1e-10
 assert abs(calc[4]-2.1888)<1e-10
 assert len([x for x in rows if x["absolute_discrepancy_over_0p01"]])==2
 assert src["acceptance"]["accepted_project_load_members"]==0
 assert src["acceptance"]["source_F3_verdict"]=="NOT SAFE IN ONE WAY SHEAR"
 live=[]
 for d in src["reported_live_load_rates"]:
  live.append({**d,"target_area_id":None,"load_pattern_id":None,"assigned_area_m2":None,
    "actual_element_load_verified":False})
 return {
  "schema":"jp.structural.g15.chapter02.load_review.v0.1",
  "source_pdf_sha256":src["original_pdf_sha256"],
  "wall_load_arithmetic":rows,
  "reported_live_load_rate_register":live,
  "source_geometry":src["geometry_source"],
  "source_wall_height_vs_storey_height_gap_m":p["wall_gross_floor_height_m"]-p["report_general_storey_height_m"],
  "numeric_screen_discrepancies_count":sum(x["absolute_discrepancy_over_0p01"] for x in rows),
  "member_load_assignments_accepted":0,
  "source_mass_reconciliation_complete":False,
  "source_geometry_verified":False,
  "private_ETABS_load_assignment_verified":False,
  "original_F3_verdict":"NOT SAFE IN ONE WAY SHEAR",
  "engineering_approval":False,
  "limitations":["No original wall segments/plan polygons modelled","No line/area loads assigned to project FE elements",
  "Reported residence occupancy conflicts with other original source locations","Original source reported values preserved without forced matching"],
 }
def main():
 a=argparse.ArgumentParser();a.add_argument("--output",default="site/data/g15-chapter02-load-review.v0.1.json")
 p=Path(a.parse_args().output);p.parent.mkdir(parents=True,exist_ok=True)
 d=build();p.write_text(json.dumps(d,sort_keys=True,indent=2)+"\n")
 print("G15_CHAPTER02_WALL_LOAD_SOURCE_CHECK_PASS",len(d["wall_load_arithmetic"]),d["numeric_screen_discrepancies_count"],"ASSIGNED_ZERO_UNAPPROVED")
if __name__=="__main__":main()
