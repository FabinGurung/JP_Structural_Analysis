#!/usr/bin/env python3
"""Deterministic public projection of curator-checked real-source Gate08 aggregates.

No private FE model, node coordinates, member IDs or exact 12-force vectors.
These are 16 independently solved PRIVATE scenario summaries, not a CI rerun
of 816 FE solves (private sources cannot be copied to public GitHub).
"""
from __future__ import annotations
import argparse,hashlib,json,math
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
SOURCE=BASE/"registry/g15-gate08-source-aggregates.v0.1.json"
def build():
    raw=SOURCE.read_bytes()
    d=json.loads(raw)
    assert d["schema"]=="jp.structural.g15.gate08.source_aggregate.v0.1"
    assert d["original_source_pdf_sha256"]=="f122904444a2e2f75230d9d4e41da0093d050da25c6e8140c86d466b7e37cc52"
    assert d["gate07_archive_sha256"]=="35989464a2b1be37322ea2915a69295bb3c294849fbb8ba8783f0bc5cdd9b4ff"
    assert d["gate08_private_summary_sha256"]=="37d3ab85d96953a74a773358fb9d56de1858ed163c896bb99de8e43844ee0a48"
    assert d["public_view_only"] is True and d["engineering_approval"] is False
    assert d["exact_slab_edges_verified"] is False
    assert d["grid_hull_used_as_slab_geometry"] is False
    assert d["seismic_mass_reconciled"] is False
    assert d["original_report_as_built_model_verified"] is False
    assert d["f3_source_failure"]=="NOT SAFE IN ONE WAY SHEAR"
    assert d["c24_true_rebar_to_grid_mapping_verified"] is False
    m=d["mass_kN"]
    assert math.isclose(m["source_ETABS_W"]-m["with_wall_hypothesis"],
       m["remaining_residual"],abs_tol=1e-5)
    assert math.isclose(m["without_walls"]+m["hypothesized_wall_weight"],
       m["with_wall_hypothesis"],abs_tol=1e-5)
    assert math.isclose(m["remaining_residual"]-m["hypothetical_extra_mass_if_completed_kN"],
       m["hypothetical_residual_after_full_perimeter_kN"],abs_tol=1e-5)
    assert m["remaining_residual"]>0 and m["hypothetical_residual_after_full_perimeter_kN"]>0
    assert m["full_grid_perimeter_wall_not_applied"] is True
    assert math.isclose(d["equivalent_missing_wall_length_per_level_m"]*2*d["source_wall_rate_kN_m"],
       m["remaining_residual"],abs_tol=1e-4)
    assert len(d["source_floor_caption_m2"])==3
    assert d["column_convex_hull_area_m2"]<d["grid_bbox_area_m2"]
    assert d["cohort"]=={
      "variants":16,"cases_per_variant":51,"solved_cases":816,"signed_member_end_action_records":134640}
    cases=set()
    for s in d["scenarios"]:
        tup=(s["limit_state"],s["diaphragm"],s["footprint"],s["wall"])
        assert tup not in cases
        cases.add(tup)
        assert s["limit_state"] in ("ULS","SLS")
        assert s["diaphragm"] in ("FLEXIBLE","RIGID_TRIAL")
        assert s["footprint"] in ("GRID_BBOX","COLUMN_CONVEX_HULL")
        assert s["wall"] in (True,False)
        assert all(math.isfinite(s[x]) and s[x]>0 for x in ("roof_mm","drift_ratio","max_member_end_moment_kNm"))
        assert s["design_approved"] is False
        limit=.025 if s["limit_state"]=="ULS" else .006
        s["numerical_drift_screen_limit"]=limit
        s["numerical_drift_screen_exceeded"]=s["drift_ratio"]>limit
    assert len(cases)==16
    assert any(s["numerical_drift_screen_exceeded"] for s in d["scenarios"])
    assert any(not s["numerical_drift_screen_exceeded"] for s in d["scenarios"])
    d["source_registry_sha256"]=hashlib.sha256(raw).hexdigest()
    d["public_generator_integrity"]="ARITHMETIC_SCENARIO_QUALITY_AND_SOURCE_HASH_VERIFIED_NOT_PRIVATE_FE_RERUN"
    d["schema"]="jp.structural.g15.gate08.public_source_reconciliation.v0.1"
    d["report_accepted"]=False
    body=json.dumps(d,allow_nan=False,ensure_ascii=False)
    for token in ("drive.google.com/","@gmail.com","LOCAL_GRID_NODE","PRIVATE_FE_MEMBER"):
        if token in body:raise ValueError("private record leakage")
    return d
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    d=build()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(d,indent=2,allow_nan=False,ensure_ascii=False)+"\n")
    print("G15_GATE08_PUBLIC_PROJECTION_VALIDATED_WITH_SOURCE_HOLD",len(d["scenarios"]))
if __name__=="__main__":main()
