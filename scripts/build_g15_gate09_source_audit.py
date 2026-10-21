#!/usr/bin/env python3
"""Gate09 source-backed *single* slab panel and unresolved seismic mass audit.

Never extrapolate a single sample panel to the building's entire slab area,
and never convert conditional wall lengths to as-built mass assignments.
Physical source figures and ETABS mass-source object tables remain absent.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"registry/g15-gate09-panel-mass-source.v0.1.json"
GRID=ROOT/"site/data/g15-working-grid.public.v0.1.json"

def point_on_segment(p,a,b,tol=.002):
    """Coordinates in metres. Verify both collinearity and segment bounds."""
    dx,dy=b[0]-a[0],b[1]-a[1]
    cross=(p[0]-a[0])*dy-(p[1]-a[1])*dx
    if abs(cross)>tol*max(1,math.hypot(dx,dy)):
        return False
    dot=(p[0]-a[0])*(p[0]-b[0])+(p[1]-a[1])*(p[1]-b[1])
    return dot<=tol**2

def polygon_area(vertices):
    return abs(sum(
        vertices[i][0]*vertices[(i+1)%len(vertices)][1]-
        vertices[(i+1)%len(vertices)][0]*vertices[i][1]
        for i in range(len(vertices)))/2.)

def build():
    reg=json.loads(SOURCE.read_text(encoding="utf-8"))
    grid=json.loads(GRID.read_text(encoding="utf-8"))
    assert reg["schema"]=="jp.structural.g15.gate09.source_register.v0.1"
    assert reg["source_pdf_sha256"]=="f122904444a2e2f75230d9d4e41da0093d050da25c6e8140c86d466b7e37cc52"
    assert len(grid["column_positions_mm"])==23 and len(grid["beam_edges"])==32
    P={x[0]:(x[1]/1000.,x[2]/1000.) for x in grid["column_positions_mm"]}
    assert all(x in P for x in ("F1","F2","G1","G3","H2"))
    # G2 is explicitly NOT a column; it is at the F-G / 1-2 beam-line intersection.
    assert "G2" not in P
    P["G2"]=(P["G1"][0],P["F2"][1])
    panel=reg["source_sample_panel"]
    ordered=panel["mapped_grid_polygon"]
    assert ordered==["F1","G1","G2","F2"]
    xy=[P[x] for x in ordered]
    actual_long=math.dist(P["F1"],P["G1"])
    actual_short=math.dist(P["F1"],P["F2"])
    assert abs(actual_long-panel["reported_long_span_m"])<=.01
    assert abs(actual_short-panel["reported_short_span_m"])<=.01
    # Each geometric boundary sits on an existing source-derived candidate
    # beam LINE; this says nothing about physical as-built verification.
    beams=grid["beam_edges"]
    source_line_support=[]
    for i in range(4):
        a,b=xy[i],xy[(i+1)%4]
        candidates=[]
        for u,v in beams:
            aa,bb=P[u],P[v]
            if point_on_segment(a,aa,bb) and point_on_segment(b,aa,bb):
                candidates.append([u,v])
        assert candidates, f"Unrepresented sample-panel supporting beam line {ordered[i]}->{ordered[(i+1)%4]}"
        source_line_support.append({"edge":[ordered[i],ordered[(i+1)%4]],
                                    "candidate_source_grid_beam_line":candidates[0],
                                    "actual_beam_as_built_verified":False})
    area=polygon_area(xy)
    assert math.isclose(area,actual_long*actual_short,abs_tol=.0001)
    assert abs(area-17.874)<=1e-6
    sw=reg["source_wall_assembly"]
    computed_main=sw["wall_material_unit_weight_kN_m3"]*(sw["wall_height_m"]-sw["beam_depth_m"])*sw["main_brick_thickness_m"]*(1-sw["main_opening_allowance_pct"]/100)
    computed_partition=sw["wall_material_unit_weight_kN_m3"]*(sw["wall_height_m"]-sw["beam_depth_m"])*sw["partition_thickness_m"]*(1-sw["partition_opening_allowance_pct"]/100)
    assert abs(computed_main-sw["reported_main_wall_kN_m"])<.02
    assert abs(computed_partition-sw["reported_partition_wall_kN_m"])<.02
    # Sample-panel ledger is an illustrative constituent of the preexisting
    # area-load inventory and MUST NOT be appended to the whole-building W.
    self_25=area*(panel["reported_slab_thickness_mm"]/1000)*25
    sample_dead=area*panel["reported_total_dead_kN_m2"]
    sample_live=area*panel["reported_residential_live_kN_m2"]
    source_self=area*panel["reported_slab_selfweight_kN_m2"]
    mass=reg["report_mass"]
    subtotal=(mass["gate08_member_self_weight_kN"]+mass["gate08_floor_added_dead_kN"]+
      mass["gate08_seismic_live_share_kN"]+mass["gate08_conditional_wall_load_kN"])
    assert math.isclose(subtotal,mass["gate08_reconstructed_weight_kN"],abs_tol=.001)
    unbalanced=mass["report_ETABS_seismic_weight_kN"]-mass["gate08_reconstructed_weight_kN"]
    assert math.isclose(unbalanced,mass["report_minus_reconstructed_kN"],abs_tol=.001)
    assert unbalanced>0 and not mass["source_mass_source_definitions_available"]
    diag_main_per_level=unbalanced/(2*sw["reported_main_wall_kN_m"])
    diag_partition_per_level=unbalanced/(2*sw["reported_partition_wall_kN_m"])
    # Both *inverse* lengths are algebraic sensitivities, NOT verified walls.
    assert not any(reg["governance"][k] for k in
       ("add_sample_panel_to_gate08_mass","complete_physical_slab_polygon_set",
        "wall_locations_verified","full_seismic_mass_reconciled",
        "full_3D_loading_accepted","engineering_approval"))
    assert reg["governance"]["original_F3_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"
    out={
     "schema":"jp.structural.g15.gate09.sample_panel_and_mass_audit.v0.1",
     "status":"ONE_SOURCE_TEXT_PANEL_MAPPED_OTHER_GEOMETRY_OPEN",
     "source_pdf_sha256":reg["source_pdf_sha256"],
     "source_register_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
     "source_locations":reg["references"],
     "panel":{
       "name":panel["title"],"grid_vertices":ordered,
       "vertices_xy_m":[{"grid":name,"x":p[0],"y":p[1]} for name,p in zip(ordered,xy)],
       "area_m2":area,
       "derived_spans_m":{"long":actual_long,"short":actual_short},
       "reported_spans_m":{"long":panel["reported_long_span_m"],"short":panel["reported_short_span_m"]},
       "discrepancies_m":{"long":actual_long-panel["reported_long_span_m"],
                          "short":actual_short-panel["reported_short_span_m"]},
       "candidate_beam_line_support":source_line_support,
       "structural_supports_verified":False,"story_verified":False,
       "actual_slab_openings_verified":False,"whole_building_polygon_coverage":False,
       "illustrative_panel_loads":{
          "reported_dead_kN":sample_dead,"reported_live_kN":sample_live,
          "source_reported_slab_selfweight_kN":source_self,
          "thickness_times_assumed_25_density_kN":self_25,
          "additional_weight_to_gate08_reconciliation_kN":0,
          "reason_zero":"Already represented inside Gate08 assumed floor-area load allowance; adding again double counts mass."
       }
     },
     "source_floor_area_captions_m2":reg["source_floor_area_captions_m2"],
     "wall_rates":{
       "computed_main_wall_kN_m":computed_main,
       "source_main_wall_kN_m":sw["reported_main_wall_kN_m"],
       "computed_partition_wall_kN_m":computed_partition,
       "source_partition_wall_kN_m":sw["reported_partition_wall_kN_m"],
       "source_parapet_wall_kN_m":sw["reported_parapet_kN_m"],
       "verified_wall_segments":0,
       "wall_topology_source":"MISSING_LOCATION_EVIDENCE"
     },
     "mass_reconciliation":{
       "reported_ETABS_W_kN":mass["report_ETABS_seismic_weight_kN"],
       "working_member_selfweight_kN":mass["gate08_member_self_weight_kN"],
       "working_area_dead_kN":mass["gate08_floor_added_dead_kN"],
       "working_seismic_live_kN":mass["gate08_seismic_live_share_kN"],
       "conditional_prior_wall_trial_kN":mass["gate08_conditional_wall_load_kN"],
       "source_supported_new_mass_kN":0,
       "working_trial_W_kN":subtotal,
       "unexplained_W_kN":unbalanced,
       "unexplained_pct_source_W":100*unbalanced/mass["report_ETABS_seismic_weight_kN"],
       "main_wall_equivalent_missing_length_each_of_two_floors_m":diag_main_per_level,
       "partition_equivalent_missing_length_each_of_two_floors_m":diag_partition_per_level,
       "missing_wall_length_is_verified":False,
       "ETABS_mass_source_definition_verified":False,
       "source_mass_reconciled":False,
       "source_report_uls_coefficient":mass["source_report_auto_seismic_coeff_uls"],
       "source_report_sls_coefficient":mass["source_report_auto_seismic_coeff_sls"],
       "assumed_mass_difference_is_approved_extra_load":False
     },
     "unresolved_evidence":reg["governance"]["next_evidence"],
     "source_F3_status":reg["governance"]["original_F3_one_way_shear"],
     "engineering_approval":False,
     "real_building_acceptance":False
    }
    return out

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    result=build()
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
    print("GATE09_SOURCE_PANEL_MATCH_P0_PARTIAL_AND_MASS_UNRECONCILED_P1_HOLD",
          result["panel"]["area_m2"],result["mass_reconciliation"]["unexplained_W_kN"])

if __name__=="__main__":main()
