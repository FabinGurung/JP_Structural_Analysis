#!/usr/bin/env python3
"""R6.19 source-bounded engineering debt register; NEVER publish native exports.

The default invocation consumes already generated R6.17/R6.18 sanitized
derived artifacts. A private native ETABS21 export may be supplied at runtime,
but is not copied, archived, or echoed into a public site artifact. Existence
of a topology candidate never clears engineer review or F3 design holds.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from jp_structural.validation.native_support_evidence import (
    build_readiness, public_receipt
)

CANONICAL = ROOT / "site/data/r6p17-canonical-3d-source-graph.json"
RESEARCH = ROOT / "site/data/r6p18-fe-connection-mesh-foundation-audit.json"
PUBLIC = ROOT / "site/data/r6p19-native-source-support-readiness.json"
RECEIPT = ROOT / "site/reports/r6p19-native-source-support-receipt.json"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--canonical", type=Path, default=CANONICAL)
    p.add_argument("--research", type=Path, default=RESEARCH)
    p.add_argument("--native-export", type=Path,
                   help="PRIVATE input, NEVER copied to the repository/site")
    p.add_argument("--output", type=Path, default=PUBLIC)
    p.add_argument("--receipt", type=Path, default=RECEIPT)
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    canonical = json.loads(args.canonical.read_text(encoding="utf-8"))
    research = json.loads(args.research.read_text(encoding="utf-8"))
    native = (json.loads(args.native_export.read_text(encoding="utf-8"))
              if args.native_export else None)
    result = build_readiness(canonical, research, native)
    receipt = public_receipt(result)

    for target, data in ((args.output, result), (args.receipt, receipt)):
        body = json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.check:
            if not target.is_file() or target.read_text(encoding="utf-8") != body:
                raise SystemExit(f"Stale/absent R6.19 generated output: {target}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")

    print(json.dumps({
        "schema": result["schema"], "counts": result["counts"],
        "engineering_approval": result["engineering_approval"],
        "native_export_supplied": result["native_export_supplied"],
        "release_authorised": result["release_authorised"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
