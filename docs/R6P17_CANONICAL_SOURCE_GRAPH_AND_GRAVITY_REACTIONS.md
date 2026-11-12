# R6.17 — Source-identity canonical 3D graph and bounded gravity equilibrium

## Scope and original source authority

Original user-selected **ETABS21 ULS/SLS E2K input revisions** remain under restricted Google Drive; GitHub contains de-identified versioned research inputs and derived model registers only. The R6.17 graph is assembled using **original source point ID + storey**, never simple XYZ snapping. It preserves all 165 structural frame objects (beams and columns), all 115 original shell objects and their corner loops, and their original declared point/base restraints. It is not the actual solver-generated ETABS21 mesh or a construction model.

The original E2K input declares **27** fixed-base point IDs. **21** are in the currently connected source frame/shell graph used by coarse research OpenSees. Six original base restraint IDs lack an accessible original frame/shell source graph node. This is not proof that they are physically absent from the actual structure; source-mesh and modelling semantics remain unverified. Five original source components exist, only two with declared original base reachability. Of the 115 shell objects, **103** have original source-identity graph reachability and are included in the R6.10 trial; **12 remain excluded**.

## R6.17 construction

- Preserve the unmodified source point and storey key, XYZ position and source component ID.
- Preserve all original BEAM and COLUMN links and original quadrilateral shell corner loops.
- Distinguish native source adjacency from actual solver meshed-joint compatibility, source offsets/releases/diaphragm constraints and shell-to-frame physical load transfer.
- For **each** of the 12 unanchored shells: retain the original shell ID, source corner IDs, source component, nearest authentic source beam and nearest source-graph connected shell boundaries on the same storey. All proximity findings are geometry diagnostics and **do not add** a source joint, support, shell admission, member release or reaction.
- Reuse R6.10's existing *real OpenSees numerical* coarse 2×2 shell trial, not a new reconstructed ETABS21 native solution, for **4 original gravity patterns × 2 role-specific ULS/SLS stiffness variants = 8 independent bounded gravity cases**.
- Add **all 21 original-source-matched signed six-component OpenSees support reactions per gravity case** (168 signed six-DOF records overall) to the existing solver; reconcile individual sum with the original case-level base reactions and original applied gravity within recorded tolerance.
- Reject duplicate/unknown base IDs, changed source counts/fingerprints, a false unsupported-shell admission, reaction corruption, unknown loads represented as zero, or change in F3 adverse shear verdict.

## Engineering interpretation

The graph's source identity and numerical research reactions are **separate** from full model fidelity. Original ETABS21 automatically generated 8×8 mesh, exact member releases/offsets, shell-to-frame mesh constraints, diaphragm/slab connectivity, source member-end force compatibility, full seismic mass and ULS/SLS load envelopes are not independently validated here. Reachability to a fixed source base ID is necessary for a load path in this graph, but not sufficient for real vertical force transfer. Support reaction records from the assumed/coarse FE model must **not** be used as accepted footing design demands.

F3 original footing remains **NOT SAFE IN ONE WAY SHEAR**. No full RCC slab/beam/column/footing design, soil capacity, revised foundation or professional engineering signoff is implied.

## Generated deliverables

- Machine ledger: `site/data/r6p17-canonical-3d-source-graph.json`
- Source receipt: `site/reports/r6p17-canonical-model-reaction-receipt.json`
- Source topology/equilibrium generator: `scripts/build_r6p17_canonical_source_graph.py`
- Original R6.10 solver extension: `scripts/run_r6p10_connected_shell_gravity.py`
- Individual regression and tamper tests: `tests/test_r6p17_canonical_source_graph.py`
- Interactive browser: `site/projects/pokhara-g15/canonical-model.html`
- Browser JS/CSS: `site/r6p17-canonical.js`, `site/r6p17-canonical.css`
- Browser smoke and saved evidence screenshots: `tests/browser/r6p17_canonical_smoke.py`

## Criteria before considering a future engineering admission

1. Verify all actual source geometry against signed structural drawings, including slab boundaries, beam-column local axes, heights, openings and foundation anchors.
2. Compare generated analysis mesh and joint/connectivity attributes with an independently defined canonical source graph, documenting all inserted nodes, constraint and release equivalence.
3. Preserve physical load and story-mass ledgers, actual boundary conditions, horizontal and vertical force/moment equilibria, convergence and sensitivity checks across mesh refinements.
4. If the user cannot supply original ETABS solver outputs, proceed with **independent first-party engineering research** and reproducible alternate model assumptions; do not misrepresent it as identical to the original ETABS21 solver.
5. Resolve and engineer-review F3 one-way shear and foundation reactions before any accepted final structural report.

Software CI/Pages deployment verifies the declared source snapshot and execution. It is **not** a qualified structural engineer's approval.