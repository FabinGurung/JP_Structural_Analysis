# R6.14 — Slab-to-beam tributary source reconciliation

## Provenance and purpose

Source authority: exact approved **ETABS21 governing ULS and SLS E2K input pair**, identified by immutable SHA-256 values in `registry/r6p5_etabs21_governing_pair.v0.1.json`. This stage consumes only the existing de-identified R6.8 source catalogue and R6.10 original shell graph/source geometry. The governing raw E2K originals stay in restricted Drive.

**Not a structural engineering acceptance step.** Geometrically coincident shell/beam source coordinates do not prove generated ETABS analysis joint identity, frame/shell edge compatibility, actual gravity reactions or professional design approval. The twelve R6.11 candidate-contact shells must not be admitted into the R6.10 numerical model by this audit.

## Decision rules

1. Keep the original 115 shell source objects, their kind, story, original corner IDs, assigned load patterns and true-area material selfweight proxy. The original 103/12 topology division is preserved.
2. Only original `FLOOR` shell types are considered. Non-floor panels are withheld without attempting floor tributary assignment.
3. Each original edge is compared against structural `BEAM` elements on the *same source storey* using real XYZ positions and a strict **0.001 mm perpendicular / end-containment geometric tolerance**. An exact two-point source-ID pair is distinguished from a beam that merely occupies the same geometric edge. Lines without a structural beam section are **not** treated as concrete beams.
4. Record each **full** same-storey edge match, each partial collinear match and any missing or ambiguous matches. A point-only touch is not an edge match. No implicit snapping, new support, slab meshing or constraint is added.
5. A conditional geometric tributary area is produced **only** when the floor shell is horizontal, truly rectangular in plan, part of the original source-graph connected group, and each of its four edges is fully covered by **exactly one distinct original beam**. Missing, partial and ambiguous perimeter edges cause withholding, not a forced redistribution to the remaining beams.
6. For that *idealized four-edge rectangular two-way plate case only*, let `a >= b` be planar dimensions in metres. Each short edge is assigned `b²/4` m²; each long edge `ab/2 - b²/4` m². Four edge areas sum to `ab`. Source shell true-area selfweight (as an explicit *gross proxy*) and original applied shell pattern resultants are split in those exact area fractions. The rule is an assumed two-way 45-degree *geometric distribution*, not original ETABS21 reactions. The load along each edge is generally triangular/trapezoidal, **not** necessarily uniformly applied. No new design line load or beam end-force is invented.
7. For each beam, **conditionally** sum candidate areas and source resultants from fully accepted *geometry-only* slabs; keep original direct wall load assignments separate. Never add these to existing R6.10 finite-element solver actions (which already include shell loads), because that would double-count loads.
8. Publish both complete candidates and withheld reason/status. Keep `approved_beam_load_kN=null`, `verified_vertical_load_transfer=false`, and original `F3_one_way_shear_unsafe=true`. The published R6.13 member-action workbook remains unchanged.

### Important modelling qualifications

The 45-degree two-way method applies to idealized supported rectangular two-way slab behavior; actual slab moment distribution, edge fixity, geometry, openings, cantilevers, frame offsets, differential stiffness, load placement, shell-to-beam connectivity and source-mesh resultants are not captured. A slab with fewer than four matched frame edges is not forcibly interpreted as a one-way/cantilever case. Native ETABS21 solver-generated joints, shell/frame connectivity and signed supported reactions are still required to prove physical transfer.

The source shell concrete gross selfweight is a geometric proxy and can double-count overlaps if treated as BOQ; it is not a verified seismic story-mass schedule. Original non-sectioned wall-carrying LINE loads and slab-to-shell load transfers are **outside** this direct slab-to-beam table; they remain under prior R6.10 controlled source investigation.

## Verification

`python -m pytest -q tests/test_r6p14_tributary_reconciliation.py`

`python scripts/build_r6p14_tributary_reconciliation.py`

The source identity, 115 objects, 103/12 graph split and force/area conservation on each provisional full-perimeter slab are asserted. Any missing approved source input, changed fingerprint, invalid negative source loading or changed engineer-hold gate must not become an accepted design load. Chromium tests verify both desktop/mobile source browsing and the original report navigation.

## Engineering boundary

- No native ETABS21 numerical solver is claimed to have run.
- No shell contact is promoted to load-bearing status.
- No member strength envelope, rebar requirement, footing reaction, foundation capacity or design approval is computed here.
- Original F3 remains **NOT SAFE IN ONE WAY SHEAR**.
- Issue #7 remains OPEN pending engineering evidence.
