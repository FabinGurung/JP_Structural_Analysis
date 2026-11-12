# R6.18 — Source-bounded 3D FE mesh and original-base reaction audit

Engineering disposition: RESEARCH MODEL; incomplete native ETABS21 model parity; F3 original footing NOT SAFE IN ONE WAY SHEAR.

## Source and numerical scope
- Original selected ETABS21 ULS/SLS E2K inputs remain private and unchanged in governed Google Drive.
- 165 original structural frames and 115 shell records; 103 source-graph-connected shells in the research OpenSees model; 12 excluded.
- Original 27 declared base restraints, 21 connected numerical support nodes, six not mapped to connected frame/shell research graph.
- Two comparable nonconforming shell meshes: 103 x 4 = 412 ShellMITC4 elements (2x2), and 103 x 16 = 1648 elements (4x4).
- Eight genuine previous 2x2 gravity research solves (ULS/SLS by Dead, Live, WALL LOAD, FLOOR FINISH) with 21 signed six-DOF source point reactions per case, plus independent 4x4 solves at ULS Dead and SLS Live.

## Actual verification
1. Preserve original point identity plus storey in canonical node/frame/shell source graph. Audit rounded-XYZ node collisions separately. Never treat geometric coincidence as the evidence required to join previously distinct nodes.
2. For each original source structural frame endpoint on an admitted shell boundary, record original source ID correspondence, geometric separation and whether a generated 2x2 or 4x4 research grid node actually aligns. Original ETABS21 generated joint, mesh, frame offsets/releases and shell-edge constraints remain unknown even when points coincide.
3. Accumulate original source uniform beam and discrete nodal wall/shell force resultants; compute global source gravity force and moment about the original model origin. Sum each support signed reaction force and its moment-arm plus signed support bending/torsion moments. Reject differences exceeding an explicit numerical tolerance on all three force and all three moment axes.
4. For two independently solved 4x4 cases compare all 21 signed vertical support reactions against the earlier 2x2 case. Report the peak absolute change and its ratio to source-applied gravity. A 5 percent research numerical stability screen is NOT full mesh convergence or code design acceptance.
5. Publish eight-case per-original-support foundation reaction books. Original footing IDs, especially the historical F3/CF1 correspondence, remain unknown (null) and no research value is an approved footing design reaction.
6. Preserve twelve original unanchored shell exclusions without automatic shell mesh ties or added base restraints.

## Source files, reproducibility and browser QA
- scripts/build_r6p18_fe_mesh_foundation.py — deterministic report generator and numerical acceptance checks
- scripts/run_r6p10_connected_shell_gravity.py — six-axis force/moment accumulation and existing signed support reactions
- tests/test_r6p18_fe_mesh_foundation.py — source coverage, genuine FE refinement, corrupted-reaction and engineering-hold tests
- site/projects/pokhara-g15/fe-mesh-audit.html — filtered shell–frame interface and source-footing research response explorer
- site/r6p18-fe-mesh.js and site/r6p18-fe-mesh.css — responsive visualization
- tests/browser/r6p18_fe_mesh_smoke.py — Chromium desktop/mobile QA
- site/data/r6p18-fe-connection-mesh-foundation-audit.json — full numerical evidence
- site/reports/r6p18-first-party-fe-convergence-receipt.json — SHA256 output and source counts

## Remaining gates before the complete independent real-building report
- Authenticate actual building support and shell/frame constraints from drawings and original numerical mesh, or establish an explicitly approved alternate structure.
- Resolve twelve original source unsupported shells on evidence; do not silently reconnect them.
- Verify physical source loads/mass, seismic/torsional/P-Delta actions and complete governing ULS/SLS combinations.
- Perform further mesh and response convergence for displacement and peak frame/shear demands, not merely two reaction grids.
- Match original column/base IDs with actual foundation plan and geotechnical capacities; redesign the F3 unsafe one-way shear case and complete all RCC member/foundation strength and serviceability checks.
- Obtain independent professional engineering review and signoff for any construction use.

R6.18 is a software + bounded numerical study, not the complete certified original ETABS21 model or approved structural report.
