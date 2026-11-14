"""R6.25 Narayani: source-linked element register from the actual drawing repository.

This module DOES NOT produce an engineer-approved building FE model. It
reuses pinned ORIGINAL-DXF-derived column/footing/strip evidence from the
CAD repo, preserves all conflicts and the adopted geotechnical evidence,
and reports exactly what is and is not fit for independent OpenSees input.

No ETABS solver output or ETABS numerical parity is required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
from typing import Any

SCHEMA = "jp.structural.r6p25.narayani_source_register.v0.1"
CAD_SHA = "259d11e1543e4ba7040373a752b823396e12d7f8"
CAD_REPO = "FabinGurung/jp-drawing-coordination"
PROJECT_ID = "PRJ-000007"
DWG_DIR = Path("public/data/projects/narayani-parajuli")
SOIL_WAREHOUSE_FILE = "13y0b0v8BiL2ooMXy0BFn2dtdSHWNOg2N"
SOIL_LINKED_SOURCE_FILE = "1PtkCjcWjWtYi9D2-GG4_O3P6KKW9S7B8"
SOURCE_STRUCTURAL_SHA256 = "55a4b9828f569ece9c78063a60d56484c71e13563d9e73faf76a701bc182d1cf"
SOURCE_ARCHITECTURAL_SHA256 = "077e7b4ffd5ce3c5c9789f9d040ef32ee661175aedd5f2d1059dbbe18176e124"
REQUIRED = (
    "aad-building-v1.json",
    "MODEL_QA_MANIFEST_v2.json",
    "aad-ground-floor-model.json",
    "aad-first-floor-model.json",
    "aad-second-floor-model.json",
    "aad-source-gf-review-v1.json",
    "source-axis-register.v1.json",
    "aad-m30-original-dxf-full-source-index.json",
    "aad-m32-beam-strip-source-register.json",
    "aad-m34-owner-geometry-reconciliation-20261101.json",
    "aad-engineering-current-register.json",
)


class IntakeHold(ValueError):
    """Refuse to invent missing load-bearing geometry, support, or source identity."""


def need(condition: bool, detail: str) -> None:
    if not condition:
        raise IntakeHold("R6.25 ENGINEERING HOLD: " + detail)


def sha(data: Any) -> str:
    return hashlib.sha256(json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False
    ).encode("utf-8")).hexdigest()


def load_sources(cad_root: Path) -> tuple[dict, dict]:
    folder = cad_root.resolve() / DWG_DIR
    need(folder.is_dir(), "pinned Narayani drawing project directory not found")
    sources, hashes = {}, {}
    for name in REQUIRED:
        file = folder / name
        need(file.is_file(), "required drawing-source file unavailable: " + name)
        raw = file.read_bytes()
        try:
            value = json.loads(raw)
        except (ValueError, UnicodeError) as ex:
            raise IntakeHold("Unparseable drawing register: " + name) from ex
        need(isinstance(value, dict), "drawing source not a JSON object: " + name)
        sources[name] = value
        hashes[name] = hashlib.sha256(raw).hexdigest()
    return sources, hashes


def check_git_checkout(cad_root: Path) -> None:
    """CLI refuses moving CAD refs when the supplied folder is a git checkout."""
    if (cad_root / ".git").exists():
        p = subprocess.run(
            ["git", "-C", str(cad_root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True
        )
        need(p.stdout.strip() == CAD_SHA,
             "drawing checkout changed; re-review and repin source SHA")


def normalize(cad_root: Path) -> dict:
    sources, file_sha = load_sources(cad_root)
    bld = sources["aad-building-v1.json"]
    mf = sources["MODEL_QA_MANIFEST_v2.json"]
    gf = sources["aad-source-gf-review-v1.json"]
    axis = sources["source-axis-register.v1.json"]
    m30 = sources["aad-m30-original-dxf-full-source-index.json"]
    m32 = sources["aad-m32-beam-strip-source-register.json"]
    m34 = sources["aad-m34-owner-geometry-reconciliation-20261101.json"]
    debts = sources["aad-engineering-current-register.json"]

    for name, item in sources.items():
        if "projectId" in item:
            need(item["projectId"] == PROJECT_ID, "project ID mismatch: " + name)
    need(bld.get("projectId") == mf.get("project_id") == axis.get("projectLogicalId") == PROJECT_ID,
         "CAD building, drawing QA and axis registers must refer to Narayani only")
    need(bld.get("coordinateSystem", {}).get("units") == "m",
         "unknown architectural model units")
    need(axis.get("coordinateFrame", {}).get("unit") == "mm" and
         axis["coordinateFrame"]["sameFloorCrossLevelValidated"] is False,
         "source native axes or survey frame unexpectedly changed")
    need(axis["sourceFileSha256"] == SOURCE_STRUCTURAL_SHA256,
         "native source DXF identity changed")
    need(gf["sourceAuthority"]["structural"]["sha256"] == SOURCE_STRUCTURAL_SHA256,
         "original structural source fingerprint conflict")
    need(gf["sourceAuthority"]["architectural"]["sha256"] == SOURCE_ARCHITECTURAL_SHA256,
         "original architectural source fingerprint conflict")
    need(m30["originals"]["structure"]["sha256"] == SOURCE_STRUCTURAL_SHA256 and
         m30["originals"]["architecture"]["sha256"] == SOURCE_ARCHITECTURAL_SHA256,
         "M30 originals do not match GF source review")
    need(m34["originalStructuralDxfSha256"] == SOURCE_STRUCTURAL_SHA256,
         "owner geometry correction not based on original drawing")
    need(debts.get("constructionStatus") == "ENGINEERING_HOLD_NOT_FOR_CONSTRUCTION",
         "drawing repo changed its engineering approval status; do not auto-promote")
    need(m34["questions"]["Q1"]["ownerDecision"] == "DRAWN_BEAM_LINES_MEET_NOT_NEW_G2_COLUMN",
         "G2 junction geometry decision changed")
    need(axis["workingException"]["originalAxis"] == "I4" and
         axis["workingException"]["workingAxis"] == "I3",
         "original I4 / owner working I3 distinction lost")

    raw_columns = axis.get("members", [])
    need(len(raw_columns) == len(gf.get("columns", [])) == 23,
         "23 GF drawing-source column marks not reconciled")
    original_by_id = {r[0]: r for r in gf["columns"]}
    need(len(original_by_id) == 23 and
         {x["sourceElementId"] for x in raw_columns} == set(original_by_id),
         "raw columns changed from source evidence")
    columns = []
    for row in raw_columns:
        element = row["sourceElementId"]
        native = row["sourceNativeXYmm"]
        need(all(math.isfinite(float(native[k])) for k in ("x", "y")),
             "nonfinite GF column source point " + element)
        original = original_by_id[element]
        need(original[1] == row["sourceAxisRef"] and
             original[2] == row["sourceColumnFamily"] and
             math.hypot(native["x"]-original[3],native["y"]-original[4]) < .002,
             "GF source axis and original drawing do not reconcile: " + element)
        candidate = {
            "source_id": element,
            "source_axis": row["sourceAxisRef"],
            "working_axis": row["workingAxisRef"],
            "source_column_family": row["sourceColumnFamily"],
            "source_position_mm": {"x": native["x"], "y": native["y"]},
            "source_column_handle": row["columnEntityHandle"],
            "source_footing_handle": row["footingEntityHandle"],
            "working_position_m": None,
            "source_layer": "ORIGINAL_STRUCTURAL_DXF_GF_COLUMN_MARK",
            "status": "SOURCE_COLUMN_MARK_ONLY_NO_VERIFIED_3D_CONNECTIVITY",
        }
        if row["sourceAxisRef"] != row["workingAxisRef"]:
            need(row["sourceAxisRef"] == "I4" and row["workingAxisRef"] == "I3",
                 "unauthorized source column relocation " + element)
            candidate["working_position_m"] = axis["workingException"]["workingCenterAadM"]
            candidate["status"] = "OWNER_WORKING_I3_EXCEPTION_NOT_SOURCE_RELOCATION"
        columns.append(candidate)

    foot_rows = gf.get("footings", [])
    need(len(foot_rows) == 21 and len({f[1] for f in foot_rows}) == 21,
         "GF footing source outlines are not 21 unique handles")
    footings = []
    for f in foot_rows:
        need(len(f) >= 8, "unknown footing source row length")
        fid, handle, family, cx, cy, dx, dy, refs = f[:8]
        need(family in {"IF1", "IF2", "IF3", "IF4", "CF1"},
             "unrecognized footing source family")
        need(all(math.isfinite(float(v)) for v in (cx,cy,dx,dy)) and dx > 0 and dy > 0,
             "invalid drawn foundation outline")
        footings.append({
            "source_id": fid,
            "original_DXF_handle": handle,
            "source_footing_family": family,
            "source_center_mm": [cx,cy],
            "drawn_plan_size_m": [dx,dy],
            "source_column_refs": [s.strip() for s in refs.split(",")],
            "status": "SOURCE_FOOTING_PLAN_ONLY_NO_VERIFIED_GEOTECH_REACTION_CAPACITY",
        })
    need(sum(x["source_footing_family"] == "CF1" for x in footings) == 2,
         "GF contains two combined footing outlines; treat as separate source evidence")
    need(set(c["source_footing_handle"] for c in columns) <=
         set(f["original_DXF_handle"] for f in footings),
         "column-to-original-footing handle mapping incomplete")

    def proximity(xmm: float, ymm: float) -> dict:
        candidate = min(columns,
            key=lambda r: math.hypot(r["source_position_mm"]["x"]-xmm,
                                      r["source_position_mm"]["y"]-ymm))
        delta = math.hypot(candidate["source_position_mm"]["x"]-xmm,
                           candidate["source_position_mm"]["y"]-ymm)
        return {"column_axis_candidate":candidate["source_axis"],
                "distance_mm":round(delta, 6),
                "within_250mm":bool(delta <= 250),
                "connection_verified":False}

    raw_beams = gf.get("beams", [])
    need(len(raw_beams) == 32, "original GF pair of beam/wall source edges changed")
    beams=[]
    for row in raw_beams:
        need(len(row) == 7, "GF source-beam candidate row shape changed")
        element,handles,x0,y0,x1,y1,width = row
        need(width > 0 and all(math.isfinite(float(v)) for v in (x0,y0,x1,y1)),
             "invalid ground-floor strip geometry")
        need(math.hypot(x1-x0,y1-y0) > 50,
             "source strip missing meaningful span")
        beams.append({
            "source_id":element, "original_DXF_handles":handles.split(","),
            "endpoints_native_mm":[[x0,y0],[x1,y1]],
            "source_width_m":width,
            "nearest_columns_source_proximity_only":[proximity(x0,y0),proximity(x1,y1)],
            "status":"UNVERIFIED_GF_PAIRED_EDGE_CANDIDATE_NOT_STRUCTURAL_BEAM",
        })

    source_strips=[]
    for level in ("gf","ff","sf"):
        floor=m32["floorSource"][level]
        pair=floor["pairedHandles"]
        need(len(pair) == 17 and
             len(floor["nearestTextHandles"]) == 17,
             "strict source strip records changed for "+level)
        for i,(handles,txt) in enumerate(zip(pair,floor["nearestTextHandles"])):
            need(len(handles)==2 and handles[0]!=handles[1],
                 "invalid original DXF line pair")
            source_strips.append({
                "source_id":f"{level.upper()}_M32_STRICT_{i+1:03d}",
                "level":level,
                "paired_original_DXF_handles":handles,
                "nearest_annotation_HANDLE_proximity_only":txt,
                "axis_sheet_relative_m":m32["commonStrictSheetNormalizedAxesM"][i],
                "status":"ORIGINAL_DXF_PARALLEL_WALL_LINE_CANDIDATE_NOT_VERIFIED_BEAM",
            })
    need(len(source_strips) == 51 and
         sum(x["level"]=="ff" for x in source_strips)==17,
         "three-floor source strip candidates incomplete")

    levels=[]
    expected = {"gf":205.16,"ff":200.67,"sf":175.62}
    for level in bld["levels"]:
        fl=level["id"]
        need(fl in expected, "unexpected proposed Block B level")
        p=sources[f"aad-{'ground' if fl=='gf' else 'first' if fl=='ff' else 'second'}-floor-model.json"]
        m=next(q for q in mf["levels"] if q["id"]==fl)
        need(abs(m["planned_area_m2"]-expected[fl])<.001 and
             abs(level["sourceArea"]-expected[fl])<.001,
             "architectural reported floor area changed")
        need(abs(m["model_area_m2"]-expected[fl])<.02,
             "architectural AI contour was not area-calibrated")
        graph=p.get("floorGraph",{})
        need(len(graph.get("nodes",[]))>=4 and graph.get("perimeter"),
             "level floorGraph missing dimensional source evidence")
        levels.append({
            "id":fl,"architectural_scheduled_floor_area_m2":expected[fl],
            "cad_semantic_contour_area_m2":m["model_area_m2"],
            "source_dimension_notes":m["source_measurements"],
            "source_graph": {"nodes":graph["nodes"],
                            "perimeter":graph["perimeter"],
                            "walls":graph.get("walls",[]),
                            "openings":graph.get("openings",[])},
            "cad_level_elevation_m":level["elevation"],
            "cad_height_m":level["height"],
            "cad_level_status":level["status"],
            "structural_source_verification":
                "GF_ONLY_COLUMN_SOURCE_MARKS" if fl=="gf" else
                "FF_SF_VERTICAL_SUPPORTS_NOT_REGISTERED",
            "release_to_open_sees_shell":False,
            "note":"Source-area-aligned AAD outline remains inferred; stair/opening/slab support "
                   "corners require source DXF and verified registration",
        })
    need({x["id"] for x in levels} == set(expected),
         "three proposed Block B floor areas must remain distinct")

    return {
        "schema":SCHEMA,
        "project_id":PROJECT_ID,
        "location":"Pokhara Metropolitan City-15, Kaski, Nepal",
        "source_repository": {
            "name":CAD_REPO,"commit_sha":CAD_SHA,
            "path_prefix":str(DWG_DIR),
            "file_SHA256":file_sha,
            "structural_original_DXF_SHA256":SOURCE_STRUCTURAL_SHA256,
            "architectural_original_DXF_SHA256":SOURCE_ARCHITECTURAL_SHA256,
            "source_register_types":"DERIVED_PUBLIC_SOURCE_CANDIDATES_ONLY",
        },
        "approved_basis": {
            "seismic_code":"NBC 105:2025",
            "seismic_code_status":"USER_APPROVED_CODE_EDITION_2026_11_14",
            "project_location":"Pokhara",
            "concrete_grade":"M20_DRAWING_DECLARED",
            "reinforcement_grade":"Fe500_DRAWING_DECLARED",
            "concrete_unit_weight_kN_m3":20.0,
            "concrete_unit_weight_status":"USER_APPROVED_SOURCE_REPORT_VALUE_2026_11_14",
            "elastic_modulus_kN_m2":None,
            "elastic_modulus_status":"NOT_YET_VERIFIED_FOR_REAL_SHELL_FE",
            "load_occupancies":"UNVERIFIED_PER_FLOOR_NBC103",
        },
        "soil": {
            "report_found":True,
            "warehouse_GDrive_file_id":SOIL_WAREHOUSE_FILE,
            "original_user_linked_file_id":SOIL_LINKED_SOURCE_FILE,
            "report_title":"FINAL G R OF RESIDENTIAL BUILDING OF MRS. NARAYANI PARAJULI, RAMBAZAR, PMC-15, KASKI.pdf",
            "report_origin":"Pokhara Soil Testing and Engineering Services Pvt. Ltd.",
            "three_boreholes_depth_m":20.0,
            "report_reference_NBC105_edition":"2020",
            "report_site_class":"B_MEDIUM_SOIL_SITE",
            "older_structural_report_site_class":"D",
            "NBC105_2025_site_class":"NOT_YET_RECLASSIFIED_FROM_ORIGINAL_BOREHOLES",
            "approved_conservative_provisional_q_kPa":160.0,
            "reference_table_q_kPa_B1p5_Df1p5":166.0,
            "reference_table_allowable_conditions":
                "Square isolated footing 1.5 m x 1.5 m, depth 1.5 m, 25mm permissible settlement",
            "reference_table_greater_widths":
                [{"width_m":2.0,"depth_m":1.5,"q_kPa":177.0},
                 {"width_m":2.25,"depth_m":1.5,"q_kPa":184.0},
                 {"width_m":2.5,"depth_m":1.5,"q_kPa":190.0}],
            "foundation_load_and_geometry_specific_check_pending":True,
            "CF1_rectangular_4_by_1p5_direct_table_value":None,
            "soil_bearing_and_liquefaction_status":"SOURCE_REVIEWED_PROVISIONAL_NOT_DESIGN_APPROVED",
        },
        "building":{
            "scope":"PROPOSED_BLOCK_B_ONLY_NOT_EXISTING_BLOCK_A",
            "levels":levels,
            "architectural_scheduled_floor_area_total_m2":581.45,
            "architectural_and_structural_shared_survey_datum":"NOT_VERIFIED",
            "cad_source_ground_floor_column_marks":columns,
            "cad_source_ground_floor_footing_outlines":footings,
            "cad_source_ground_floor_edge_strip_candidates":beams,
            "cad_source_three_floor_strict_line_pair_candidates":source_strips,
            "cad_17_common_sheet_axes_not_proof_of_identical_frame_design":m32["commonStrictSheetNormalizedAxesM"],
            "owner_G2_junction":"BEAMS_MEET_NO_EXTRA_COLUMN_SOURCE_ONLY",
            "owner_C6_F6_strip016":"ORTHOGONAL_WORKING_INTENT_NOT_VERIFIED_SUPPORT",
            "original_I4_vs_owner_working_I3":"PRESERVED_SEPARATE_COORDINATES",
            "historical_16_frozen_GF_IFC_beams":
                "HISTORICAL_WORKING_MODEL_NOT_NEW_SOURCE_ENGINEER_VERIFIED_2026_11",
            "cross_floor_column_member_and_foundation_support_links_verified":False,
            "r6p23_r6p24_FE_input_ready":False,
        },
        "holds":[
            "GF drawing source axes in original structural DXF millimetres are NOT a surveyed architectural-to-structural datum",
            "Upper FF/SF structural columns and designed load paths cannot be inferred merely by repeating GF DXF linework",
            "M32 paired source wall lines or MTEXT proximity are NOT actual load-bearing beam identities or sections",
            "AAD floorGraph boundaries and openings are semantically inferred and area-calibrated, not accepted structural shell contours",
            "G2 is a beam-line junction; no fabricated G2 column; C6-F6 and strip 016 are only owner-approved working orientation",
            "I4 original source column and I3 owner working correction must remain separate; CF1 reactions, eccentricity and detailing unresolved",
            "G1 drawn 1.8x1.8m versus scheduled 2.1x2.1m footing conflict; no automatic final size",
            "Geotechnical report NBC105:2020 Type B versus old structural report Type D, 2025 site-class reconciliation required",
            "160kPa user-approved conservative assumption is NOT a blanket approval of every footing, bearing, settlement or one-way shear",
            "R6.23 research engine only accepts source-verified rectilinear floor grids; actual Narayani geometry is irregular and not yet modelable within this contract",
            "Historical F3 NOT SAFE IN ONE WAY SHEAR remains unresolved, distinct from CAD F3 owner selection-label question",
            "Full code seismic/wind, cracked stiffness, real material modulus, soil foundation, slab-punching, beams/joints/rebar and engineer approval incomplete"
        ],
        "engineering_approval":False,
        "construction_release":False,
        "final_SAR_complete":False,
        "next_gate":"DRAWING_NATIVE_COORDINATE_REGISTRATION_AND_GF_TO_FF_SF_MEMBER_CONTINUITY",
    }


def emit(model: dict, output_dir: Path) -> dict:
    need(model["schema"] == SCHEMA and model["engineering_approval"] is False and
         model["building"]["r6p23_r6p24_FE_input_ready"] is False,
         "source model must not imply full building FE/engineering approval")
    output_dir.mkdir(parents=True,exist_ok=True)
    f=output_dir/"R6P25-NARAYANI-SOURCE-REGISTER-UNAPPROVED.json"
    raw=json.dumps(model,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+"\n"
    f.write_text(raw,encoding="utf-8")
    manifest={
        "schema":"jp.structural.r6p25.source_receipt.v0.1",
        "project_id":PROJECT_ID,
        "cad_source_sha":CAD_SHA,
        "source_model_sha256":hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "filename":f.name,
        "engineer_approval":False,
        "site_soil_pdf_included":False,
        "final_building_analysis_ready":False,
    }
    (output_dir/"R6P25-SOURCE-RECEIPT.json").write_text(
        json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    return manifest


def verify(output_dir:Path) -> dict:
    mf=json.loads((output_dir/"R6P25-SOURCE-RECEIPT.json").read_text())
    need(mf["schema"]=="jp.structural.r6p25.source_receipt.v0.1" and
         mf["cad_source_sha"]==CAD_SHA and
         mf["engineer_approval"] is False and
         mf["final_building_analysis_ready"] is False,
         "R6.25 receipt authorization/source mismatch")
    source=(output_dir/mf["filename"]).read_bytes()
    need(hashlib.sha256(source).hexdigest()==mf["source_model_sha256"],
         "normalized source JSON failed SHA256 integrity check")
    obj=json.loads(source)
    need(obj["source_repository"]["commit_sha"]==CAD_SHA and
         obj["engineering_approval"] is False and
         not obj["building"]["r6p23_r6p24_FE_input_ready"],
         "R6.25 model source or design approval changed")
    return mf


def main() -> None:
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--cad-root",type=Path,required=True)
    cli.add_argument("--output-dir",type=Path,required=True)
    args=cli.parse_args()
    check_git_checkout(args.cad_root)
    model=normalize(args.cad_root)
    result=emit(model,args.output_dir)
    verify(args.output_dir)
    print(json.dumps({
        "project_id":model["project_id"],"source_cad_sha":CAD_SHA,
        "gf_columns":len(model["building"]["cad_source_ground_floor_column_marks"]),
        "gf_footings":len(model["building"]["cad_source_ground_floor_footing_outlines"]),
        "gf_edge_candidates":len(model["building"]["cad_source_ground_floor_edge_strip_candidates"]),
        "three_level_strict_strip_candidates":len(model["building"]["cad_source_three_floor_strict_line_pair_candidates"]),
        "approved_concrete_unit_weight_kN_m3":20,
        "NBC_105_2025_approved":True,
        "soil_report_found_in_warehouse":True,
        "ready_for_real_building_FE":False,
        "engineering_approval":False,
        "source_digest":result["source_model_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
