#!/usr/bin/env python3
"""Export primary-chart spot comparisons; fail closed on numerical disagreement."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from jp_structural.solvers.native.sp16_chart31_reference import build_chart31_comparison


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True,type=Path)
    opts=p.parse_args()
    record=build_chart31_comparison()
    opts.output.parent.mkdir(parents=True,exist_ok=True)
    opts.output.write_text(json.dumps(record,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
    print("SP16_PRIMARY_CHART31_SPOTCHECK_PASS_NOT_APPROVED",len(record["points"]),opts.output)
    for point in record["points"]:
        print(point["point_id"],"chart",point["source_chart_coordinate"]["mu_over_fck_bD2"],
              "engine",round(point["engine_mu_over_fck_bD2"],7),
              "error",round(point["absolute_normalized_error"],7))


if __name__=="__main__":
    main()
