#!/usr/bin/env python3
"""R6.5 revision: user-selected ETABS 21 ULS/SLS source pair, fail-closed physical audit.

Raw E2K files are never committed/uploaded or emitted in public outputs. The
default mode validates only public-safe hashes and observations; --uls/--sls
performs PRIVATE byte-for-byte/model-source inspections before emitting the
same de-identified, safe aggregate. A valid user source selection must never
be confused with a solver result, original report numerical agreement,
responsible-engineer approval or site/footing safety.
"""
from __future__ import annotations
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "registry/r6p5_etabs21_governing_pair.v0.1.json"
SECTION = re.compile(r"^\\$ ([A-Z][A-Z0-9 /()_-]*)\\s*$")
GR = re.compile(r'GRID\\s+"[^"]+"\\s+LABEL\\s+"([^"]+)"\\s+DIR\\s+"([XY])"\\s+COORD\\s+(-?\\d+(?:\\.\\d+)?)')
MLOAD = re.compile(r'^MASSSOURCELOAD\\s+"[^"]+"\\s+"([^"]+)"\\s+(-?\\d+(?:\\.\\d+)?)')
LC = re.compile(r'\\bLC\\s+"([^"]+)"')
MOD = re.compile(r'\\bI[23]MOD\\s+(?:\\d+(?:\\.\\d+)?)')
EXPECTED_COUNTS = {
    "POINT COORDINATES": 127, "LINE CONNECTIVITIES": 97,
    "AREA CONNECTIVITIES": 80, "LINE ASSIGNS": 199,
    "AREA ASSIGNS": 115, "FRAME OBJECT LOADS": 107,
    "SHELL OBJECT LOADS": 230,
}
LEVELS = ["TF", "FF", "GF", "Plinth level"]


class SourceError(ValueError):
    pass


def load_registry(path=REGISTER):
    data = json.loads(Path(path).read_text(encoding="utf8"))
    if data.get("schema") != "jp.structural.r6p5.etabs21_user_designated_governing_pair.v0.1":
        raise SourceError("Invalid governing source register")
    decision = data["decision"]
    if decision["state"] != "USER_CONFIRMED_CURRENT_GOVERNING_ETABS21_ULS_SLS" or not decision["selected_model_takes_precedence_over_report_for_future_RECONCILIATION"]:
        raise SourceError("Source authority changed unexpectedly")
    m = data["model_pair"]
    for role in ("ULS", "SLS"):
        if not re.fullmatch(r"[0-9a-f]{64}", m[role]["sha256"]):
            raise SourceError("Invalid governing model digest")
        if m[role]["etabs_version"] != "21.0.0" or int(m[role]["size_bytes"]) <= 0:
            raise SourceError("Invalid version or file length")
    if data["historical_report_comparison"]["report_seismic_weight_kN"] != 6831.9109:
        raise SourceError("Old report weight must not be silently rewritten")
    holds = data["admission_gates"]
    for field in ("native_ETABS_solution_and_mass_per_story_tables_reproduced",
                  "physical_component_mass_independently_reconciled",
                  "geotechnical_and_parcel_engineer_approved",
                  "F3_one_way_shear_safe", "MRSM_scaling_executed", "engineering_approval"):
        if holds[field] is not False:
            raise SourceError("Physical or engineering acceptance cannot be claimed")
    return data


def sections(text):
    result = {}
    current = None
    for line in text.splitlines():
        m = SECTION.match(line.strip())
        if m:
            current = m.group(1)
            if current in result:
                raise SourceError("Repeated E2K section")
            result[current] = []
        elif current and line.strip():
            result[current].append(line.strip())
    return result


def inspect_raw(path, expected):
    path = Path(path)
    if not path.is_file() or path.stat().st_size != expected["size_bytes"]:
        raise SourceError("Native source size mismatch")
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != expected["sha256"]:
        raise SourceError("Native source digest mismatch")
    try:
        src = content.decode("utf8")
    except UnicodeError as e:
        raise SourceError("Unsupported E2K encoding") from e
    if "$ END OF MODEL FILE" not in src:
        raise SourceError("Truncated E2K source")
    d = sections(src)
    prog = " ".join(d.get("PROGRAM INFORMATION", []))
    if not re.search(r'PROGRAM\\s+"ETABS"\\s+VERSION\\s+"21\\.0\\.0"', prog):
        raise SourceError("Not ETABS21")
    ctrl = " ".join(d.get("CONTROLS", []))
    if 'UNITS  "N"  "MM"  "C"' not in ctrl:
        raise SourceError("Unexpected E2K unit basis")
    stories = d.get("STORIES - IN SEQUENCE FROM TOP", [])
    if len(stories) != 4 or [re.search(r'STORY\\s+"([^"]+)"', x).group(1) for x in stories] != LEVELS:
        raise SourceError("Story identity/sequence differs from selected source")
    if not all("HEIGHT 3048" in x for x in stories[:3]):
        raise SourceError("Story elevations need new review")
    coordinates = {axis:{} for axis in ("X", "Y")}
    for line in d.get("GRIDS", []):
        m = GR.search(line)
        if m: coordinates[m.group(2)][m.group(1)] = float(m.group(3))
    if coordinates["X"].get("I") != 21000 or coordinates["Y"].get("7") != 12550:
        raise SourceError("Grid span differs from confirmed model")
    if coordinates["Y"].get("4") != 7080 or coordinates["Y"].get("3") != 6425:
        raise SourceError("Grid chain changed: between lines 3 and 4 should be 655 mm")
    for sec, count in EXPECTED_COUNTS.items():
        if len(d.get(sec, [])) != count:
            raise SourceError("Connectivity, assignment or load count changed")
    ms = d.get("MASS SOURCE", [])
    if len(ms) != 7 or not ms[0].startswith('MASSSOURCE  "MsSrc1"'):
        raise SourceError("Mass-source definition missing")
    if not all(flag in ms[0] for flag in (
            'INCLUDEELEMENTS "No"', 'INCLUDEADDEDMASS "Yes"',
            'INCLUDELOADS "Yes"', 'LUMPATSTORIES "Yes"')):
        raise SourceError("Mass source participation changed")
    multipliers = {}
    for row in ms[1:]:
        m = MLOAD.match(row)
        if not m: raise SourceError("Mass load pattern malformed")
        multipliers[m.group(1)] = float(m.group(2))
    expected_factors = {"Dead": 1, "Live": .3, "WALL LOAD": 1,
                        "FLOOR FINISH": 1, "TANK": .6, "STAIRCASE LOAD": .3}
    if multipliers != expected_factors:
        raise SourceError("Mass pattern participation changed")
    loads = Counter(LC.search(row).group(1) for sec in
                    ("FRAME OBJECT LOADS", "SHELL OBJECT LOADS", "POINT OBJECT LOADS")
                    for row in d.get(sec, []) if LC.search(row))
    if loads != {"WALL LOAD":107, "FLOOR FINISH":115, "Live":115}:
        raise SourceError("Unexpected load pattern assignments")
    return d, {"sha256": expected["sha256"], "bytes_verified": True,
               "etabs_version": "21.0.0", "grid_extent_mm": [21000,12550],
               "story_count":4, "actual_object_load_pattern_counts": dict(loads),
               "defined_but_no_object_load_rows": ["TANK", "STAIRCASE LOAD"],
               "all_expected_model_sections_verified": True}


def verify_pair(uls, sls, registry):
    u, a = inspect_raw(uls, registry["model_pair"]["ULS"])
    s, b = inspect_raw(sls, registry["model_pair"]["SLS"])
    protected = set(u)|set(s)
    excluded = {"LOG", "FRAME SECTIONS", "LOAD COMBINATIONS", "PROJECT INFORMATION"}
    for sec in protected-excluded:
        if u.get(sec) != s.get(sec):
            raise SourceError("ULS and SLS differ outside expected stiffness/loadcase sections")
    if len(u.get("FRAME SECTIONS", [])) != len(s.get("FRAME SECTIONS", [])):
        raise SourceError("Different frame section counts")
    for p,q in zip(u["FRAME SECTIONS"], s["FRAME SECTIONS"]):
        if MOD.sub("I_MOD _",p) != MOD.sub("I_MOD _",q):
            raise SourceError("ULS and SLS frame section differs beyond I2/I3 modifiers")
    if len(u.get("LOAD COMBINATIONS", [])) != len(s.get("LOAD COMBINATIONS", [])):
        raise SourceError("ULS/SLS combination count mismatch")
    for x, y in zip(u["LOAD COMBINATIONS"], s["LOAD COMBINATIONS"]):
        if re.sub(r'EQ([XY])\\s+(ULS|SLS)', r'EQ\\1 _', x) != re.sub(r'EQ([XY])\\s+(ULS|SLS)', r'EQ\\1 _', y):
            raise SourceError("ULS/SLS load combinations differ unexpectedly")
    return {"ULS": a, "SLS": b,
            "same_geometry_load_assignments_and_mass_source": True,
            "distinct_ULS_SLS_frame_stiffness_and_seismic_combinations": True}


def build(registry=None, uls=None, sls=None):
    reg = registry if registry is not None else load_registry()
    if (uls is None) != (sls is None):
        raise SourceError("Both ULS and SLS inputs required for private verification")
    report = {
      "schema": "jp.structural.r6p5.etabs21_governing_audit_public_v0.1",
      "source_authority": reg["decision"]["state"],
      "model_user_designated_governing": True,
      "model_versions": ["21.0.0", "21.0.0"],
      "source_model_hashes": [reg["model_pair"]["ULS"]["sha256"],reg["model_pair"]["SLS"]["sha256"]],
      "source_folder": reg["drive_provenance"]["folder_id"],
      "registered_model_grid_extent_mm": reg["local_inspection_observations"]["grid_extent_mm"],
      "registered_source_mass_patterns": reg["local_inspection_observations"]["source_patterns"],
      "current_model_mass_source_settings_observed": True,
      "current_model_source_binary_verified_in_this_run": False,
      "current_model_ULS_SLS_pair_structurally_compatible": None,
      "historic_report_ETABS_version": 20,
      "historic_report_seismic_weight_kN": reg["historical_report_comparison"]["report_seismic_weight_kN"],
      "historic_report_mass_reproduced_from_current_model": False,
      "historic_772kN_Gate08_residual_not_current_model_deficit": True,
      "current_model_stories_mass_kN": None,
      "current_model_mass_total_kN": None,
      "current_model_mrsm_scale_factor": None,
      "actual_ETABS_modal_run_completed": False,
      "F3_historical_failure_retained": True,
      "geotechnical_parcel_engineer_approval": False,
      "physical_mass_reconciliation": "HOLD_MODEL_RESULTS_REQUIRED",
      "engineering_approval": False,
      "raw_private_model_uploaded_or_published": False
    }
    if uls is not None:
        verified=verify_pair(uls,sls,reg)
        report["current_model_source_binary_verified_in_this_run"]=True
        report["current_model_ULS_SLS_pair_structurally_compatible"]=verified["same_geometry_load_assignments_and_mass_source"]
        report["observed_assigned_load_pattern_counts"]=verified["ULS"]["actual_object_load_pattern_counts"]
        report["defined_but_no_object_load_rows"]=verified["ULS"]["defined_but_no_object_load_rows"]
    return report


def emit(path,uls=None,sls=None):
    d=build(uls=uls,sls=sls)
    out=Path(path)
    out.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(d,indent=2,sort_keys=True,allow_nan=False)+"\\n"
    out.write_text(raw,encoding="utf8")
    (out.parent/(out.stem+"-manifest.json")).write_text(
      json.dumps({"sha256":hashlib.sha256(raw.encode("utf8")).hexdigest(),
                  "raw_private_bytes_in_artifact":False,
                  "engineer_approval":False,
                  "source_registry_sha256":hashlib.sha256(REGISTER.read_bytes()).hexdigest()},
                  indent=2,sort_keys=True)+"\\n",encoding="utf8")
    return d


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--uls",type=Path)
    p.add_argument("--sls",type=Path)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    d=emit(a.output,a.uls,a.sls)
    print("R6P5_ETABS21_GOVERNING_SOURCE_USER_CONFIRMED_PHYSICAL_WEIGHT_AND_F3_HOLD",
          "PRIVATE_VERIFIED" if d["current_model_source_binary_verified_in_this_run"] else "REGISTER_CHECKED_ONLY")


if __name__=="__main__":
    main()
