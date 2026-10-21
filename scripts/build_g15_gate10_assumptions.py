#!/usr/bin/env python3
"""Reproducible but UNVERIFIED G15 floor outlines, wall paths and seismic-mass trials.

The source gives 23 grid marks, three area CAPTIONS, and one sample slab bay.
No fitted polygon or trial wall edge here is claimed to be surveyed.
ETABS mass-source alternatives follow CSI's documented categories; numeric
calibration to source weight is never evidence of correct physical assignment.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
GRID=ROOT/"site/data/g15-working-grid.public.v0.1.json"
REG=ROOT/"registry/g15-gate09-panel-mass-source.v0.1.json"
CAPTIONS=[218.68,212.09,188.11]
PRIMARY=[("A1","A2"),("A1","C1"),("C1","F1"),("F1","G1"),
         ("G1","H1"),("H1","H2"),("H2","H3")]
ASSUMED_GRAVITY=9.81

def area(poly):
    return abs(sum(poly[i][0]*poly[(i+1)%len(poly)][1]
      -poly[(i+1)%len(poly)][0]*poly[i][1] for i in range(len(poly)))/2)

def hull_of(pts):
    pts=sorted(set(pts))
    def cross(o,a,b):
        return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower=[]
    for p in pts:
        while len(lower)>=2 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
        lower.append(p)
    upper=[]
    for p in reversed(pts):
        while len(upper)>=2 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
        upper.append(p)
    return lower[:-1]+upper[:-1]

def build():
    d=json.loads(GRID.read_text())
    r=json.loads(REG.read_text())
    assert d["safety"]["engineering_approval"] is False
    assert r["source_plan_occupancy_conflict"]["ground_floor_room_label"]=="COMMERCIAL SPACE"
    points={g:(x/1000.,y/1000.) for g,x,y,_ in d["column_positions_mm"]}
    assert len(points)==23
    hull=hull_of(points.values())
    hull_area=area(hull)
    assert abs(hull_area-224.3750125)<.001, hull_area
    center=(sum(p[0] for p in hull)/len(hull),
            sum(p[1] for p in hull)/len(hull))
    floor_polygons=[]
    for i,requested_area in enumerate(CAPTIONS):
        scale=math.sqrt(requested_area/hull_area)
        vertices=[[center[0]+(p[0]-center[0])*scale,
                   center[1]+(p[1]-center[1])*scale] for p in hull]
        assert math.isclose(area(vertices),requested_area,abs_tol=1e-8)
        floor_polygons.append({
          "hypothetical_floor":i+1,
          "source_caption_area_m2":requested_area,
          "scaled_convex_hull_outline_xy_m":vertices,
          "area_preserved":True,
          "scale_about_hull_vertex_mean":scale,
          "drawing_polygon_verified":False,
          "opening_holes_verified":False,
          "supports_on_perimeter_verified":False,
          "occupancy_and_diaphgram_verified":False,
          "method":"AREA_FITTED_CONVEX_HULL_NOT_PHYSICAL_SLAB"
        })
    all_edges={frozenset(e) for e in d["beam_edges"]}
    assert all(frozenset(e) in all_edges for e in PRIMARY)
    assumed_walls=[]
    for a,b in PRIMARY:
        length=math.dist(points[a],points[b])
        assumed_walls.append({"between":[a,b],"length_m":length,
           "floor_levels":[1,2],"assembly":"MAIN_WALL_TRIAL",
           "source_verified_wall":False,"actual_openings_verified":False})
    assumed_length=sum(x["length_m"] for x in assumed_walls)
    src=r["report_mass"]
    roof=r["source_plan_occupancy_conflict"]
    W_src=src["report_ETABS_seismic_weight_kN"]
    W_trial=src["gate08_reconstructed_weight_kN"]
    base=list([2050.,2050.,W_trial-4100.])
    assert math.isclose(sum(base),W_trial,abs_tol=1e-6)
    main=src["gate08_conditional_wall_load_kN"]/(src["wall_trial_levels"]*src["wall_trial_length_m_per_level"])
    assert abs(main-9.24)<1e-8
    partition=r["source_wall_assembly"]["reported_partition_wall_kN_m"]
    extra_wall=2*main*(assumed_length-src["wall_trial_length_m_per_level"])
    room_area=math.prod(roof["nominal_ground_commercial_dimensions_mm"])/1e6
    # Ordinary nonstorage effective live-load participation 0.30 for NBC105:2025;
    # exact use category and ground-floor actual floor diaphragm are NOT verified.
    commercial_delta=room_area*(3.-2.)*.30
    # Alternative 120 mm (source conflicting schedule) vs sample 125 mm:
    # density=25 kN/m^3 remains an independent assumed material value.
    thin_slab_delta=sum(CAPTIONS)*(.120-.125)*25.
    residual=W_src-W_trial
    assert residual>0 and abs(residual-772.0329166282687)<.001
    cases=[]
    def case(key,title,change,distribution,classification,explanation):
        floors=[base[i]+distribution[i] for i in range(3)]
        total=sum(floors)
        assert math.isclose(total,W_trial+change,abs_tol=1e-6)
        cases.append({
         "id":key,"label":title,"classification":classification,
         "hypothetical_mass_change_kN":change,
         "floor_weights_kN":floors,
         "trial_seismic_weight_kN":total,
         "source_minus_trial_kN":W_src-total,
         "absolute_gap_pct_of_source":abs(W_src-total)/W_src*100.,
         "verified_source_mass_match":False,
         "seismic_mass_accepted":False,
         "explanation":explanation})
    case("G08_BASE","Gate08 conditional wall baseline",0,[0,0,0],
      "PREVIOUS_PROVISIONAL",
      "Existing source-calibrated assumed loading with 29.188 m/floor main-wall trial; not source-confirmed.")
    case("G10_EDGE7","7 source-grid candidate wall edges",extra_wall,
      [extra_wall/2,extra_wall/2,0],"NEW_WALL_ASSIGNMENT_HYPOTHESIS",
      "Replace prior 29.188m/floor inferred walls with seven specifically named beam-edge wall candidates; none verified.")
    case("G10_COMMERCIAL","Commercial-label +1 kPa live assumption",commercial_delta,
      [commercial_delta,0,0],"NEW_OCCUPANCY_HYPOTHESIS",
      "Change one nominal 14.54x11.54m room's live load from 2 to 3 kPa at assumed 30% seismic participation; ground level assignment unverified.")
    case("G10_EDGE_COMM","Candidate edge walls + occupancy alternative",
      extra_wall+commercial_delta,[extra_wall/2+commercial_delta,extra_wall/2,0],
      "COMBINED_HYPOTHESES","Combine two separate unverified changes, excluding duplicate wall selfweight.")
    case("G10_THIN_SLAB","120mm vs 125mm source thickness sensitivity",
      thin_slab_delta,[thin_slab_delta*x/sum(CAPTIONS) for x in CAPTIONS],
      "ALTERNATIVE_SOURCE_SCHEDULE",
      "Scale all caption-area slabs from reported sample 125mm to conflicting 120mm schedule; actual slab areas unverified.")
    for length in [20.,45.,70.]:
        v=2*length*partition
        case("G10_PARTITION_"+str(int(length)),f"Additional {length:g} m/floor partition trial",
          v,[v/2,v/2,0],"UNVERIFIED_PARTITION_LENGTH",
          "Extra partition lengths on two levels are generic sensitivity only, not observed walls; risk of overlap with partition-area allowance.")
    inverse=residual/(2*partition)
    case("G10_INVERSE_FIT","Algebraic residual-fit partitions",residual,
      [residual/2,residual/2,0],"INVERSE_NUMERICAL_FIT_NOT_EVIDENCE",
      "An algebraic partition length chosen to make source W equal trial W; this is NOT a physical load path or mass-source reconciliation.")
    # ETABS supports distinct origins of mass. Their identities cannot be
    # discovered merely by matching total seismic weight.
    etabs=[
     {"id":"ELEMENT_SELF_PLUS_ADDITIONAL_LOADS","member_self_kN":src["gate08_member_self_weight_kN"],
      "load_pattern_included_selfweight":False,"additional_dead_kN":src["gate08_floor_added_dead_kN"]+src["gate08_conditional_wall_load_kN"],
      "seismic_live_kN":src["gate08_seismic_live_share_kN"],
      "trial_W_kN":W_trial,"double_count_flag":False,"actual_ETABS_setting_known":False},
     {"id":"LOAD_PATTERN_ONLY_WITH_SELFWEIGHT","member_self_kN":0,
      "load_pattern_included_selfweight":True,"additional_dead_kN":src["gate08_member_self_weight_kN"]+
       src["gate08_floor_added_dead_kN"]+src["gate08_conditional_wall_load_kN"],
      "seismic_live_kN":src["gate08_seismic_live_share_kN"],
      "trial_W_kN":W_trial,"double_count_flag":False,"actual_ETABS_setting_known":False},
     {"id":"DOUBLE_COUNT_ERROR_SENSITIVITY","member_self_kN":src["gate08_member_self_weight_kN"],
      "load_pattern_included_selfweight":True,"additional_dead_kN":src["gate08_member_self_weight_kN"]+
       src["gate08_floor_added_dead_kN"]+src["gate08_conditional_wall_load_kN"],
      "seismic_live_kN":src["gate08_seismic_live_share_kN"],
      "trial_W_kN":W_trial+src["gate08_member_self_weight_kN"],
      "double_count_flag":True,"actual_ETABS_setting_known":False}
    ]
    assert all(math.isclose(q["trial_W_kN"],q["member_self_kN"]+
       q["additional_dead_kN"]+q["seismic_live_kN"],abs_tol=.001) for q in etabs)
    assert sum(1 for c in cases if math.isclose(c["source_minus_trial_kN"],0,abs_tol=1e-8))==1
    assert all(c["seismic_mass_accepted"] is False for c in cases)
    return {
      "schema":"jp.structural.g15.gate10.assumption_sensitivity.v0.1",
      "status":"REPRODUCIBLE_FLOOR_AND_WALL_ASSUMPTIONS_NOT_VERIFIED_DESIGN",
      "source_report_pdf_sha256":r["source_pdf_sha256"],
      "assumption_basis":["G15 Gate09 original architectural floor-area captions and revised report brick load rates",
        "NBC105:2025 section 5.2/table 5-1 for 0.30 eligible nonstorage occupancy seismic live fraction (not roof)",
        "CSI ETABS Mass Source and Analysis Reference: mass derived from element mass/additional mass/load patterns; avoid doubled selfweight"],
      "footprints":{"method":"SOURCE_CAPTION_AREA_FITTED_CONVEX_HULL",
       "grid_hull_area_m2":hull_area,"assumed_per_floor":floor_polygons,
       "all_physical_slab_boundaries_verified":False,"real_terrace_openings_verified":False,
       "ground_commercial_use_verified":False},
      "wall_candidates":{"method":"EXPLICIT_HYPOTHETICAL_BEAM_EDGE_SELECTION",
       "edges":assumed_walls,"trial_length_per_level_m":assumed_length,
       "prior_G08_assumed_length_per_level_m":src["wall_trial_length_m_per_level"],
       "line_rate_kN_m":main,"wall_locations_verified":False,
       "potential_overlap_partition_allowance_unresolved":True},
      "occupancy_trial":{"drawn_commercial_room_nominal_area_m2":room_area,
       "assumed_delta_live_intensity_kPa":1.,
       "assumed_eligible_seismic_live_fraction":.30,
       "additional_seismic_weight_kN":commercial_delta,
       "ground_room_actual_level_assignment_verified":False,
       "roof_eligible_live_share":0,
       "commercial_source_live_intensity_verified":False},
      "slab_thickness_trial":{"assumed_125_to_120_mm_weight_change_kN":thin_slab_delta,
       "assumed_concrete_density_kN_m3":25.,
       "source_actual_slab_thickness_unambiguous":False},
      "etabs_mass_source_alternatives":etabs,
      "model_cases":cases,
      "inverse_length_partitions_each_two_floors_m":inverse,
      "actual_etabs_mass_source_observed":False,
      "source_seismic_W_kN":W_src,
      "baseline_working_W_kN":W_trial,
      "seismic_mass_source_reconciled":False,
      "source_F3_one_way_shear":"NOT SAFE IN ONE WAY SHEAR",
      "diaphragm_verified":False,
      "engineering_approval":False
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    obj=build()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(obj,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("G15_GATE10_ASSUMED_SCENARIOS_VALIDATED_NOT_APPROVED",len(obj["model_cases"]),
        obj["baseline_working_W_kN"],obj["inverse_length_partitions_each_two_floors_m"])
if __name__=="__main__":main()
