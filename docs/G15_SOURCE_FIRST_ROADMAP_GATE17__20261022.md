# JP Structural Analysis · P0→P3 decision roadmap (Gate17)

Status as of 22 October 2026. This is not an approved building design.

## Stage already built — governance, engine and publication
- Original source PDF SHA-256 recorded and checked, report observations traceable to exact PDF text source markers.
- Source-derived frame topology: 23 coordinate positions, 165 original physical frame member segments; not a verified native ETABS model. Working editor and signed 3D OpenSees cases functioning.
- Gate08 historic provisional 1,192 scenarios; Gate12 rigid/flexible signed FE; Gate13 one actual assumed shell bay; Gate14 matched two-floor shell trial; Gate15 three hypothetical opening/mesh alternatives; Gate16 real 2x2/4x4/8x8 shell sensitivity (36 cases).
- Current GitHub Pages release is immutable-source pinned; full 333 regression tests passing Gate16, with Gate17 adding three pure-source tests and audited JSON.
- Previous Gate11–16 tests, explicit global force+moment equilibrium and signed local actions preserved.

## Stage now active — P0: authenticated source-to-model reconciliation
1. Obtain **this G+1.5 building's** original ETABS binary `.edb` or text `.e2k`; export model area/line assignments and Mass Source settings. A public report is NOT the editable ETABS model. Do not use the unrelated E2K files found in other building projects.
2. Reconcile 6831.9109 kN ETABS seismic weight with actual element mass, slabs, finishes, wall segments, eligible live loads and source story weights. Current Gate08 gap 772.032917 kN, current G10_EDGE_COMM gap approximately 715.467677 kN (both not source-accepted). Never fill with invented generic partitions.
3. Resolve 20 vs 25 kN/m³ concrete source conflict, reported sample slab 125 mm vs general schedule 120 mm, commercial ground floor label vs residential report classification, first mode 0.618s vs narrative 0.185s. Local sample slab 125 mm×25 = 3.125 kPa ≈ 3.13 kPa is internally consistent; this alone does not determine ETABS material mass.
4. Trace actual structural slabs/terrace/voids, wall load paths and diaphragm to source ETABS frame/area object IDs. Supersede convex hulls and imaginary sample floor repetition only after geometry is verified.

## Next — P1: approved engineering analysis and design correction
5. Reanalyze independently on source-matched geometry, site parameters and mass: gravity combinations, signed seismic eccentricities, ULS/SLS drift (real interstorey displacements), irregularity, P–Delta, member/connection actions, structural durability/detailing.
6. Redesign failed isolated footing F3 based on verified bearing, load and detailing; source worksheet **NOT SAFE IN ONE WAY SHEAR** persists. Independent specialist review needed.

## Later — P2 product maturation, P3 reusable template
7. Versioned arbitrary editor geometry, source/case imports, controlled roundtrip from Actions artifact to website; avoid unreviewed source-data mutation.
8. Source-approved project Structural Analysis Report, audited reproducible calculation archive, and last a reusable LaTeX/CAD/report template.

### Engineering admission rule
CI, material/sample mass identities, plausible three-level shells, or matching seismic weights NEVER constitute construction safety approval. Source ETABS mass definitions and footing F3 approval are independent hard gates.
