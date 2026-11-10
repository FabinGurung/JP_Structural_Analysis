# R6.15 — 77 original incomplete/ambiguous slab-perimeter cases

**Source baseline:** R6.14 audited 115 original ETABS21 shell source objects: 25 complete four-edge geometric candidates; 77 source-connected FLOOR shells with incomplete/ambiguous beam perimeters; 13 others (9 non-floor and 4 unsupported FLOOR). All 12 original source-graph unanchored objects remain excluded from the numerical research case.

**Authority:** the same registered immutable ULS/SLS ETABS21 E2K input pair, through the R6.8 de-identified source catalog and R6.14 shell/beam edge audit. This is NOT a new native solver run, and original generated-joint, mesh and signed-reaction exports are unavailable.

## Reproducible geometry review

For **all 77 source slabs and all four original XYZ edges**:

1. Preserve exact source shell key, storey, corner IDs, section and applied source loads.
2. Compare 3D-collinear same-storey structural BEAM segments only, within 0.001 mm perpendicular/geometric tolerance. Record each source-beam interval along the slab boundary.
3. Merge beam intervals and measure covered length, uncovered gaps, and double-overlap length. Distinguish a unique full beam, contiguous segmented chain, partial chain gap, overlapping chain, competing full/partial beams, multiple full beams and absent frame edge.
4. Separately record touching FLOOR shell geometry and unsectioned original LINE geometry. Neither is proven vertical support; LINE is not silently promoted to frame stiffness.
5. Assign an exhaustive review group per slab. Retain R6.14's original withheld decision, regardless of clean geometric edge overlap.
6. Present purely **hypothetical** one-way/cantilever scenarios for idealized horizontal rectangular source geometry ONLY:
   - Two opposite fully aligned beam edges and the other two without competing source beam segments: one-way A/2 area and W/2 source-resultant examples per edge. Real continuity and reactions unverified.
   - Exactly one clean aligned beam edge, three other unaligned beam edges and no recorded adjoining FLOOR shell: cantilever illustration with uniform source load W, projection L, root resultant W and idealized root bending moment W*L/2. Root fixity and slab anchorage unverified.
   - Partial, ambiguous, nonrectangular or neighbouring-floor-conflicted configurations withhold simplified clean scenarios. The raw source-edge measurements remain visible for each of these cases.

## Engineering boundary

The published accepted support and beam load values are **null (unknown), not zero**. Hypothetical per-edge resultants are never applied to the R6.10 OpenSees research model or R6.13 member force study; double-counting shell loads would be invalid. No original ULS/SLS E2K source is changed; the original R6.14 geometry-only allocations remain intact and no previously unsupported shell is admitted.

Footing F3 remains explicitly **NOT SAFE IN ONE WAY SHEAR**. R6.15 does not verify member strength, slab serviceability, footing bearing, design load envelopes, engineer approval, or reinforcement. Physical load paths still require generated joint IDs, native shell/frame mesh connectivity, supported restraints/releases and signed equilibrated gravity reactions from the selected original revisions.

## Inspect and verify

Python audit source: scripts/build_r6p15_incomplete_edge_audit.py

All-source and synthetic geometry tests: tests/test_r6p15_incomplete_edge_audit.py

Interactive Pokhara report page: site/projects/pokhara-g15/incomplete-edges.html

Generated source ledger: site/data/r6p15-incomplete-slab-edge-audit.json

Generated evidence receipt: site/reports/r6p15-incomplete-slab-edge-receipt.json

Desktop/mobile Chromium: tests/browser/r6p15_incomplete_edge_smoke.py

All 77 shell keys and all 308 edges must be represented. Classification and review-group counts must conserve this scope. Regression and live Pages readback guard the 115/103/12 graph, 25+77+13 baseline, source hashes, source action immutability, null approved transfers, F3 unsafe and engineering HOLD.

Original Google Drive records and the R6.10 frozen prerelease remain untouched. R6.15 is a research software milestone and not construction approval.
