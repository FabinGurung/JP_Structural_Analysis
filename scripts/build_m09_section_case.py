#!/usr/bin/env python3
"""Reproducible assumed M09 section-capacity JSON, not a client design."""
import argparse
import hashlib
import json
import math
from pathlib import Path

from jp_structural.solvers.native.rc_column_section import (
    ENGINE_ID, biaxial_interaction_from_bars, uniaxial_pm_curve, STEEL_MODEL, STEEL_TABLE_SOURCE,
)


def build():
    # Eight D25 bars: 3 at each short face, 1 on each long-side mid-height.
    area = math.pi * 25**2 / 4
    bars = [{"x_mm": x, "y_mm": y, "area_mm2": area}
            for x, y in ((50, 50), (200, 50), (350, 50),
                         (50, 450), (200, 450), (350, 450),
                         (50, 250), (350, 250))]
    inp = dict(width_mm=400, depth_mm=500, fck_MPa=25, fy_MPa=415,
        bars=bars, Pu_kN=1200, Mux_kNm=80, Muy_kNm=40,
        clear_height_mm=2600, effective_length_x_mm=2800,
        effective_length_y_mm=2800,
        source_id="SYNTHETIC_400X500_M25_FE415_8D25_NO_REAL_PROJECT")
    normal = biaxial_interaction_from_bars(**inp)
    overload = biaxial_interaction_from_bars(
        **(inp | {"Mux_kNm": 100000, "Muy_kNm": 100000}))
    if overload["status"] != "FAIL":
        raise RuntimeError("M09 unsafe-case regression failed")
    curves = [uniaxial_pm_curve(width_mm=inp["width_mm"], depth_mm=inp["depth_mm"],
        fck_MPa=inp["fck_MPa"], fy_MPa=inp["fy_MPa"], bars=bars, axis=axis,
        compression_face=face, source_id=inp["source_id"], points=65,
        target_axial_kN=inp["Pu_kN"])
        for axis in ("X", "Y") for face in ("START", "END")]
    result = {
        "schema": "jp.structural.m09_column_section.v0.1",
        "case_id": "ASSUMED-M09-SECTION-001",
        "engine": ENGINE_ID,
        "published_code": "IS 456:2000",
        "provenance": "All geometry/bars/forces are synthetic. No private client data.",
        "assumptions": {
            "geometry": "400 x 500 mm; eight 25 mm bars with 50 mm centre offsets",
            "materials": "M25 concrete; Fe415 nominal steel",
            "load_case": "Pu=1200 kN, Mux=80 kNm, Muy=40 kNm",
            "steel_law": STEEL_MODEL,
            "critical_limit": "SP16 Table A interpolated steel points tested; full column interaction-chart parity NOT established",
            "other_exclusions": "Confinement, slenderness second order, code detailing, signed FE actions, SP16 independent full-column chart benchmarking"
        },
        "steel_table_reference": STEEL_TABLE_SOURCE,
        "pm_curves": curves,
        "valid_case": normal,
        "intentionally_unsafe_case": overload,
        "engineering_approval": False,
        "report_accepted": False,
    }
    raw = json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False)
    result["case_payload_sha256"] = hashlib.sha256(raw.encode("utf8")).hexdigest()
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    opts = p.parse_args()
    result = build()
    opts.output.parent.mkdir(parents=True, exist_ok=True)
    opts.output.write_text(json.dumps(result, indent=2, sort_keys=True,
                                       allow_nan=False) + "\n", encoding="utf8")
    print("M09_NUMERIC_SECTION_EQUILIBRIUM_BUILT_NOT_APPROVED", opts.output)
    print("Axial kN", result["valid_case"]["face_capacities"][0]["section_resultants"]["axial_kN"])
    print("Section Mux1 kNm", result["valid_case"]["chosen_conservative_Mux1_kNm"])
    print("Section Muy1 kNm", result["valid_case"]["chosen_conservative_Muy1_kNm"])


if __name__ == "__main__":
    main()
