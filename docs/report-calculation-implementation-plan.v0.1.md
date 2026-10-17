# Report-to-Engine Calculation Coverage — governed draft

This is the **single implementation checklist** for the minimum report scope of the two private precedent reports (G+1.5 and G+2.5). Do not implement all algorithms of all five possible solvers; use OpenSeesPy for supported structural FE analyses and focused tested Python functions for code-based design.

- Authority: registry/report-calculation-coverage.v0.1.json (18 requirements: M01-M16 plus verification S17 and rendering S18).
- GitHub Pages candidate: site/calculation-coverage.html, driven by generated site/data/report-calculation-coverage.v0.1.json.
- Builder: python scripts/build_calculation_coverage.py (writes data projection); --check validates exact parity.
- Current main Pages workflow checks out old pinned SHA, so this **branch page is not currently live**.
- Code status reflects verified source files and bounded regression tests, **not** structural design approval.
- Frozen milestone a9-seq9-phase-c-20261015 remains unchanged; feature PR is DRAFT and not merged.
- No client-specific text, source model, diagrams, coordinates, Drive IDs or confidential numbers in this public source.

## Proposed build schedule

1. P0 materials, loads and mass: implement source-parameterized kernels, then load-placement integration and verified unit/mass reconciliation.
2. P0 dynamic/linear frame result completion: force recovery, equilibrium, mass participation and seismic code-source references.
3. P1 ductile RC beams, columns and joints: code-verified design equations and governing combinations.
4. P1 slab, isolated/combined footings, stairs, stability and wind screening: independent hand benchmarks.
5. P2 special G+2.5 foundation/equipment cases; report assembly into R&D LaTeX/PDF with provenance and privacy boundaries.

## Safety rule

Never interpret formula-only functions, registry status, or CI passing as a compliant design. Every design formula needs the exact verified edition, clause/table, unit contract, provenance, regression examples, independent benchmark and professional acceptance. Source conflict flags (e.g. an originally failed footing adopted anyway) stay FAIL until reassessed with evidence.

This checklist must change only through a commit, code diff, tests, and provider CI readback. New material coding goes on the post-Seq9 draft branch, not on the frozen release.
