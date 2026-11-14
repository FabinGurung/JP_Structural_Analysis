"""R6.25 source-derived, explicitly hypothesized Narayani connectivity QA on Pages.

Source drawing footprints and original DXF handles from pinned CAD repo.
Assumption: all 23 GF original column marks continue vertically at the same
plan position across three storeys. Upper floor strips are floor-specific
M32 source candidates; they are not certified member identities. Candidate
endpoints are routed to nearest columns for visual QA only. A "connection"
in this graph NEVER becomes an OpenSees support or design load path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path

from r6p25.narayani_intake import (
    CAD_SHA, IntakeHold, check_git_checkout, normalize, need
)

HERE=Path(__file__).resolve().parent
SCHEMA="jp.structural.r6p25.narayani_assumed_connections_public_qa.v0.1"
ORIGIN_X_MM=762364.891  # owner M34 source-sheet C6 x -1.459853m
ORIGIN_Y_MM=-116000.0
THRESHOLD_M=0.75

def relative(x_mm:float,y_mm:float)->tuple[float,float]:
    return (round((x_mm-ORIGIN_X_MM)/1000,6),
            round((ORIGIN_Y_MM-y_mm)/1000,6))

def build(cad_root:Path)->dict:
    check_git_checkout(cad_root)
    source=normalize(cad_root)
    b=source["building"]
    original_columns=b["cad_source_ground_floor_column_marks"]
    columns=[]
    for col in original_columns:
        xy=col["source_position_mm"]
        x,y=relative(xy["x"],xy["y"])
        columns.append({
            "id":col["source_id"],"source_axis":col["source_axis"],
            "working_axis":col["working_axis"],
            "x":x,"y":y,"family":col["source_column_family"],
            "original_DXF_handle":col["source_column_handle"],
            "footing_DXF_handle":col["source_footing_handle"],
            "source_status":"ORIGINAL_GF_DXF_SOURCE_MARK",
            "vertical_extension_status":"ASSUMED_GF_TO_FF_TO_SF_TO_ROOF",
            "i3_exception":col["source_axis"]!=col["working_axis"],
        })
    need(len(columns)==23 and len({c["source_axis"] for c in columns})==23,
         "drawing-source unique GF column count changed")

    footings=[]
    for foot in b["cad_source_ground_floor_footing_outlines"]:
        x,y=relative(*foot["source_center_mm"])
        footings.append({
            "id":foot["source_id"],"handle":foot["original_DXF_handle"],
            "family":foot["source_footing_family"],"x":x,"y":y,
            "width_m":foot["drawn_plan_size_m"][0],
            "depth_m":foot["drawn_plan_size_m"][1],
            "source_columns":foot["source_column_refs"],
            "status":"GF_SOURCE_FOOTING_PLAN_NO_REACTION_OR_DESIGN_VERIFIED",
        })
    need(len(footings)==21,"drawing-source footing count changed")
    def closest(x:float,y:float)->dict:
        col=min(columns,key=lambda c:math.hypot(x-c["x"],y-c["y"]))
        distance=math.hypot(x-col["x"],y-col["y"])
        return {
            "column_id":col["id"],"column_axis":col["source_axis"],
            "distance_m":round(distance,5),
            "plan_near_750mm":distance<=THRESHOLD_M,
            "status":"ASSUMED_COLUMN_JOINT_PROXIMITY_ONLY" if
                distance<=THRESHOLD_M else
                "HIGH_GAP_HYPOTHESIS__DO_NOT_USE_AS_3D_SUPPORT",
            "engineer_verified":False,
        }

    beams=[]
    for strip in b["cad_source_ground_floor_edge_strip_candidates"]:
        p1,p2=strip["endpoints_native_mm"]
        x1,y1=relative(*p1);x2,y2=relative(*p2)
        beams.append({
            "id":strip["source_id"],"level":"GF",
            "source_type":"ORIGINAL_DXF_PAIRED_EDGE_GROUND_FLOOR",
            "original_DXF_handles":strip["original_DXF_handles"],
            "section_width_source_m":strip["source_width_m"],
            "section_depth_m":None,
            "endpoints":[[x1,y1],[x2,y2]],
            "assumed_endpoint_joints":[closest(x1,y1),closest(x2,y2)],
            "status":"ORIGINAL_GF_SOURCE_CANDIDATE__BEAM_CONNECTION_ASSUMED",
        })
    need(len(beams)==32,"drawing-source GF original candidate count changed")

    for level in ("FF","SF"):
        strips=[s for s in b["cad_source_three_floor_strict_line_pair_candidates"]
                if s["level"]==level.lower()]
        need(len(strips)==17, "source specific upper floor strip count changed")
        for strip in strips:
            x1,yy1,x2,yy2=strip["axis_sheet_relative_m"]
            y1=round(yy1+ORIGIN_Y_MM/1000,6)
            y2=round(yy2+ORIGIN_Y_MM/1000,6)
            x1,x2=round(x1,6),round(x2,6)
            beams.append({
                "id":strip["source_id"],"level":level,
                "source_type":"ORIGINAL_DXF_SOURCE_SHEET_PAIRED_WALL_LINE",
                "original_DXF_handles":strip["paired_original_DXF_handles"],
                "nearest_annotation_HANDLE_proximity_only":
                    strip["nearest_annotation_HANDLE_proximity_only"],
                "section_width_source_m":None,"section_depth_m":None,
                "endpoints":[[x1,y1],[x2,y2]],
                "assumed_endpoint_joints":[closest(x1,y1),closest(x2,y2)],
                "status":"SOURCE_UPPER_FLOOR_LINE_PAIR__STRUCTURAL_CLASS_AND_JOINTS_ASSUMED",
            })
    need(len(beams)==66,"source strip count changed")

    level_info=[]
    for index,f in enumerate(b["levels"]):
        level_info.append({
            "id":f["id"].upper(),
            "name":{"gf":"Ground floor","ff":"First floor","sf":"Second floor"}[f["id"]],
            "architectural_reported_area_m2":f["architectural_scheduled_floor_area_m2"],
            "source_graph":f["source_graph"],
            "declared_aad_elevation_m":f["cad_level_elevation_m"],
            "elevation_status":"ASSUMED_AAD_LEVEL_ELEVATION_NOT_VERIFIED_SURVEY",
            "structural_column_vertical_continuity":"23_REPEATED_GF_SOURCE_AXES_ASSUMED",
            "shelled_floor_outline_certified":False,
        })
    # NOTE: The floor perimeter in AAD is a source-related, AI-fitted plan
    # graph. Do not place it onto the structural DXF frame without a surveyed
    # transform. Render source-derived columns/strips only, with this hold.
    need(sum(x["level"]=="GF" for x in beams)==32,"GF beams were truncated")
    need(sum(x["level"]=="FF" for x in beams)==17,"FF source evidence truncated")
    need(sum(x["level"]=="SF" for x in beams)==17,"SF source evidence truncated")
    near=sum(j["plan_near_750mm"] for beam in beams
             for j in beam["assumed_endpoint_joints"])
    far=2*len(beams)-near

    return {
        "schema":SCHEMA,
        "project_id":"PRJ-000007",
        "project":"Narayani Parajuli — proposed Block B",
        "location":"Pokhara Metropolitan City-15, Kaski, Nepal",
        "classification":"ORIGINAL_DXF_SOURCE_DERIVED_WITH_ASSUMED_UNVERIFIED_CONNECTIONS",
        "cad_repository":"FabinGurung/jp-drawing-coordination",
        "cad_source_sha":CAD_SHA,
        "original_structural_dxf_sha":source["source_repository"]["structural_original_DXF_SHA256"],
        "source_register_digest":hashlib.sha256(json.dumps(
            source,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest(),
        "review_frame":{
            "origin":"SOURCE_STRUCTURAL_DXF_GF_LOCAL_REFERENCE__NOT_SURVEY",
            "axis_x":"source X shifted by 762364.891 mm",
            "axis_y":"-source Y shifted by -116000 mm",
            "source_upper_floor_sheet_alignment":
                "M32 native source sheet translation, repeated axes working hypothesis",
            "unit":"m","full_architectural_common_datum_verified":False,
        },
        "basis":{
            "seismic_code":"NBC 105:2025",
            "code_edition_user_approved":True,
            "city":"Pokhara",
            "concrete_unit_weight_kN_m3":20.0,
            "concrete_weight_user_approved":True,
            "drawing_concrete_grade":"M20",
            "drawing_steel_grade":"Fe500",
            "assumed_column_joint_behavior":"CONTINUOUS_RIGID_RC_MOMENT_FRAME_IDEALIZATION__NOT_DETAIL_VERIFIED",
            "assumed_ground_floor_column_continuity_through_three_storeys":True,
            "assumed_candidate_beam_joints":"NEAREST_COLUMN_GAP_METRIC_ONLY__NOT_PHYSICAL_CONSTRAINT",
            "assumed_storey_height_m":3.0,
            "assumed_diaphragm_model":"NOT_ASSIGNED__SLAB_SOURCE_SHELLS_NOT_VERIFIED",
            "soil_bearing_working_kPa":160.0,
            "geotechnical_report_table_reference_kPa":166.0,
            "geotechnical_reference":"https://drive.google.com/file/d/13y0b0v8BiL2ooMXy0BFn2dtdSHWNOg2N/view",
            "geotechnical_reference_conditions":
                "isolated square 1.5m footing at 1.5m depth, 25mm settlement",
            "site_class_2020_soil_report":"B",
            "site_class_old_structural_report":"D",
            "site_class_2025":"NOT_YET_CLASSIFIED",
            "standards_references":[
                {"label":"DUDBC Nepal Building Code directory",
                 "url":"https://dudbc.gov.np/pages/building-code/"},
                {"label":"Official Nepal NBC 105:2025 seismic design PDF",
                 "url":"https://giwmscdnone.gov.np/media/files/NBC_105_2025_Seismic%20Design%20of%20Buildings%20in%20Nepal_lqqvx6a.pdf"},
                {"label":"OpenSees forceBeamColumn modeling",
                 "url":"https://opensees.github.io/OpenSeesDocumentation/user/manual/model/elements/forceBeamColumn.html"},
            ],
            "assumption_rationale":
                "Provisional 3D node/beam frame hypothesis for QA: RC frame columns "
                "continuously stacked at each of the GF original source axes and moment "
                "frame joints treated as rigid for exploration. FF/SF paired source line "
                "segments are compared against the GF grid by the M32 drawing translation. "
                "A nearest-column diagnostic does not prove a structural joint. NBC105 "
                "requires code-appropriate seismic system/detailed member and joint checks; "
                "the assumptions are not code acceptance.",
        },
        "columns":columns,
        "footings":footings,
        "beams":beams,
        "floors":level_info,
        "assumed_vertical_segments":23*3,
        "summary":{
            "source_GF_column_marks":len(columns),
            "source_footing_outlines":len(footings),
            "source_GF_beam_candidates":32,
            "source_FF_strips":17,
            "source_SF_strips":17,
            "total_candidate_beam_segments":len(beams),
            "assumed_endpoints_within_750mm_of_source_column":near,
            "high_gap_endpoint_hypotheses":far,
            "3d_member_connectivity_engineer_verified":0,
            "actual_FE_solved_cases":0,
        },
        "critical_holds":[
            "DATA IS FOR QA; DO NOT USE ASSUMED CONNECTIONS FOR STRUCTURAL DESIGN, CONSTRUCTION OR PERMIT",
            "Only GF source column axes are directly registered; three-level vertical continuation is assumed",
            "Upper-level beam candidate line pairs may be walls or schematic/copied base linework; not certified members",
            "Nearest-column endpoints can be multiple metres from actual columns; no fictitious member is assigned support in OpenSees",
            "Source AAD architectural perimeters/holes are AI-area-calibrated, not structurally surveyed or physically meshed",
            "Original I4 vs working I3 are distinct frames: show I4 source marker, hold I3 site placement",
            "No extra column at G2; the G2 beam junction requires separate load-path and joint design",
            "CF1 eccentricity and support approval pending; G1 size 1.8x1.8 vs scheduled 2.1x2.1 unresolved",
            "Geotechnical NBC105:2020 Type B vs old report Type D must be reclassified to NBC105:2025 with VS30/site evidence",
            "160 kPa is an assumed conservative working scenario, not universal soil/foundation approval",
            "Historical F3 'NOT SAFE IN ONE WAY SHEAR' remains adverse",
            "No real-project OpenSees FE solution or verified gravity/seismic/wind/member/rebar/soil design was produced",
        ],
        "actual_independent_FE_run":False,
        "engineering_approval":False,
        "construction_release":False,
    }

def emit(data:dict,site:Path)->dict:
    need(data["engineering_approval"] is False and not data["actual_independent_FE_run"],
         "Cannot publish source assumption as approved FE result")
    site.mkdir(parents=True,exist_ok=True)
    folder=site/"data";folder.mkdir(exist_ok=True)
    target=folder/"r6p25-narayani-qa.json"
    raw=json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n"
    target.write_text(raw,encoding="utf8")
    for src,dst in (("qa.html","r6p25.html"),("qa.css","r6p25.css"),("qa.js","r6p25.js")):
        shutil.copyfile(HERE/src,site/dst)
    for name in ("index.html","r6p23.html","report.html","more.html"):
        page=site/name
        if not page.exists():continue
        html=page.read_text(encoding="utf8")
        if 'href="r6p25.html"' in html:continue
        anchor='href="r6p23.html"'
        need(anchor in html, "expected existing R6.23 project navigation link missing on "+name)
        # Keep menu text compact on narrow phones.
        html=html.replace(anchor, 'href="r6p25.html">Narayani QA</a><a '+anchor,1)
        page.write_text(html,encoding="utf8")
    manifest={
        "schema":"jp.structural.r6p25.narayani_public_qa_receipt.v0.1",
        "cad_source_sha":CAD_SHA,
        "assumed_connections":True,
        "engineering_approval":False,
        "real_project_FE_result":False,
        "files_sha256":{
            name:hashlib.sha256((site/name).read_bytes()).hexdigest()
            for name in ["r6p25.html","r6p25.css","r6p25.js","data/r6p25-narayani-qa.json"]
        },
    }
    (folder/"r6p25-pages-receipt.json").write_text(
        json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf8")
    return manifest

def verify(site:Path)->dict:
    m=json.loads((site/"data/r6p25-pages-receipt.json").read_text())
    need(m["cad_source_sha"]==CAD_SHA and
         m["engineering_approval"] is False and m["real_project_FE_result"] is False,
         "R6.25 public QA receipt source or approval mismatch")
    for name,digest in m["files_sha256"].items():
        need(hashlib.sha256((site/name).read_bytes()).hexdigest()==digest,
             "R6.25 publication SHA256 mismatch "+name)
    data=json.loads((site/"data/r6p25-narayani-qa.json").read_text())
    need(data["schema"]==SCHEMA and not data["engineering_approval"] and
         not data["actual_independent_FE_run"],
         "R6.25 source preview misrepresented as accepted structural analysis")
    need(len(data["columns"])==23 and len(data["footings"])==21
         and len(data["beams"])==66,"R6.25 public source counts drifted")
    return m

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cad-root",type=Path,required=True)
    p.add_argument("--site-dir",type=Path,required=True)
    args=p.parse_args()
    model=build(args.cad_root)
    m=emit(model,args.site_dir)
    verify(args.site_dir)
    print(json.dumps({"schema":SCHEMA,"source":CAD_SHA,
       "GF_columns":len(model["columns"]),"source_beam_candidates":len(model["beams"]),
       "near_joint_hypotheses":model["summary"]["assumed_endpoints_within_750mm_of_source_column"],
       "distant_joint_hypotheses":model["summary"]["high_gap_endpoint_hypotheses"],
       "design_approved":False,"real_FE_solved":False,
       "publication_source_sha256":m["files_sha256"]["data/r6p25-narayani-qa.json"]}))

if __name__=="__main__":
    main()
