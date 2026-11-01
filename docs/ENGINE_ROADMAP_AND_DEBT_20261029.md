# JP Structural Analysis — execution roadmap & governed debt, 2026-10-29

## Operating boundary

**Engine-first:** independent analysis/design rules and numerical QA are product truth; original G+1.5 revised SAR provides seven-chapter TOC and a known conflicting building-specific example. Do **not** condition progress on missing original native ETABS/soil evidence. Release an engine module when reproducibly tested; release a verified building model only after separate real-project evidence. No false source acceptance, no invented completion or construction approval.

**Authoritative references:** `registry/report-template-contract.v0.2.json` (7-chapter ordered TOC); `registry/report-calculation-coverage.v0.1.json` (M01–M16/S17–S18); NBC105:2025 governmental PDF https://ebps.kathmandu.gov.np/UploadFiles/NBC_105_2025_Sesmic_Design.pdf ; IS456:2000 government-hosted text https://wriddodoti.gov.np/uploads/blog/20230331071217_IS-456-with-all-ammendments.pdf . Source material original G+1.5 revised PDF Drive `1TpWUmOdrcQqOpkN6qvmhZ12KrYaNABBM`, SHA-256 `f122904444a2e2f75230d9d4e41da0093d050da25c6e8140c86d466b7e37cc52`. Internal source titles, status and examples are not official permits.

## Milestones — with actual state labels

| Phase | Description | Evidence / state |
|---|---|---|
| R0 | Canonical IDs/model normalization, source intake, provenance and staged source audit | **IMPLEMENTED_BOUNDED**, independent E2K authority for original building unresolved |
| R1 | Independent static/dynamic OpenSees modules, signed end forces, member equilibrium; seismic load/mass base | **IMPLEMENTED_BOUNDED**, no full original-building equivalence |
| R2 | Report-first chapters 1–6, Annex evidence registry, 15 physical source proof obligations | **DEPLOYED AND TESTED**; 0/15 original building physical source gates accepted |
| R3 | Reusable original-TOC seven-chapter report contract, M01–M16/S17–S18 manifest and bounded synthetic ESM/RC/isolated-footing case | **DEPLOYED V0.2**, 7 limited numerical module groups, 24 provisional footing comparisons |
| R4 | Source-identified signed FE static analysis → M08/M09/M10 design check → 7-chapter report and full I/J action CSV | **V0.3 TESTED AND DEPLOYED**, independent synthetic D2 static frame; no original-building parity or signed modal source |
| R5 | Generalize canonical arbitrary 3D frame/area model inputs, member/diaphragm/wall/area load placement, verified weight/mass trace, real signed ULS/SLS combinations | **PARTIAL R5.1–R5.4 SOURCE-BOUNDED IMPLEMENTATION**, real 3D signed static beam forces, exact horizontal member UDL, member span V/M and assumed one-way panel routes; shell/diaphragm FE, actual tributaries, code-governed ULS/SLS remain OPEN |
| R6 | Complete structural dynamics: NBC105 ESM/MRSM, modal participation, accidental eccentricity, effective stiffness, diaphragm response, drift/torsion/P–Delta, stiffness/soft-storey/mass irregularity with independent benchmarks | **OPEN ENGINE DEBT** |
| R7 | Complete RC member design: longitudinal and transverse steel, beam negative/positive moment/torsion/anchorage, columns biaxial/second-order/confinement, joint shear/SCWB, slabs, stairs, CF1/F3 footings including eccentric contact/settlement and foundation FE where relevant | **OPEN ENGINE DEBT** |
| R8 | Independent numerical comparison, guarded QA, IFC/DXF/ETABS imports as supported, signed data/provenance, report figures, annexes, PDF/HTML/CSV/JSON packaging, municipality/jurisdiction-specific submission contract | **OPEN ENGINE AND VERIFICATION DEBT**, not approved SAR |

## Prior work verified before this stage

- Original source SHA, report sections and 15 evidence requirements indexed; source error F3 `NOT SAFE IN ONE WAY SHEAR` preserved.
- Multiple synthetic and source-bounded actual OpenSees cases executed, signed end-action and force/moment equilibrium modules tested. Different model generations must not be misrepresented as one original building model.
- Independent bounded IS456 beam, column and joint code/design kernels, anchored source/edition tests, SP16 table/partial chart checks.
- F3 12 geometry-demand sensitivity scenarios, source-conflict ledger, and independent 24-candidate footing checks across two synthetic/source-bounded v0.2 inputs; a provisional mathematical pass is not a physically accepted footing.
- v0.2 report prints seven original-TOC chapters, JSON/CSV/HTML/Markdown and SHA-256 output manifest. Development CI 417 pass; GitHub Pages successful run `40786078082`. Sources pinned and preserved.

## Current R5 engineering increments — recorded 2026-10-31

- **R5.1:** source-explicit horizontal panel and wall-line magnitude calculations; nodal allocation and separately audited seismic source mass, no undocumented automatic tributary inference.
- **R5.2:** native OpenSees 3D full-span horizontal beam uniform element loads replace wall source end-lumping. Closed-form fixed-ends benchmark and signed I/J source end forces preserved.
- **R5.3:** actual signed static beam end actions integrated into span Vz/My distributions, 20 source/case-member diagrams with exact stationary positions and J-end equilibrium; no nonlinear/section recorder claim.
- **R5.4 (implementation staged with CI/Pages gates):** `one_way_panel_to_beams.py` explicitly routes each source horizontal rectangular panel to **two opposite full-length beam edges** under the user-supplied `ONE_WAY_SIMPLY_SUPPORTED` scheme. Exact panel source intensity and geometry derive equal tributary widths; routing must conserve the source Fz and X/Y first moments. Retain the same audited seismic mass source, keep the wall load as its own source, apply all panel and wall gravity to the native beam elements without duplicate panel nodal forces, and carry the resulting signed cases into the bounded member checks and seven-chapter SAR. Synthetic 4 × 3m example has two pressure source entries (DL and LL), four panel-to-beam load entries and one independent wall line load; total gravity remains 128kN, seismic-eligible weight remains 111.2kN. These are assumed numerical reference quantities, NOT building facts.
- R5.4 does **NOT** infer one-way/two-way behavior from geometry alone, derive real support conditions from drawings, calculate plate/shell stiffness, address openings/cantilevers, verify slab steel, or approve actual physical building loading. These are explicit open tasks, not old software debt marked resolved.
- Reproducible source paths: `examples/sanitized/r5_oneway_slab_routes.v0.1.json`, `src/jp_structural/solvers/native/one_way_panel_to_beams.py`, `scripts/build_r5_oneway_panel_beam_case.py`, `tests/test_r5_oneway_panel_beam.py`. The latest live CI/Pages run and milestone commit must be read before claiming deployment complete.
- Original F3 source remains **NOT SAFE IN ONE WAY SHEAR**; original physical source acceptance remains **0/15**; professional signoff and municipality submission remain unaccepted.

## R5.5 connected shell-frame extension — CI-tested and Pages-deployed 2026-11-01

The new independent **synthetic rectangular source model** uses compatible, physically shared nodes at all edges between actual OpenSees `ShellMITC4` four-node quadrilateral shells, subdivided `elasticBeamColumn` perimeter beams, and four column supports. Meshes **2×2, 4×4 and 8×8** are solved for **source-defined DL, LL and HX cases** (9 distinct static OpenSees runs); the original load/mass source SHA and assumed 111.2 kN seismic-eligible weight are preserved across refinements. Dead panel 72 kN plus independent beam wall 32 kN, and separate live panel 24 kN, reproduce the synthetic 128 kN gravity source. Transverse pressure acts on the compatible four-node shell element mesh, not the previous user-declared one-way strip load; the shell shares actual FE nodes with surrounding beam elements. Six-component external/reaction equilibrium, signed member I/J local forces, actual shell-centre displacement, and monotonic displacement-difference reduction across the tested three meshes are governed QA.

This does **not** represent a full original building, real floor diaphragm seismic comparison, actual reinforced slab design, code-verified load combinations, any professional signoff, or the missing 15 physical source acceptances. In particular **F3 remains NOT SAFE IN ONE WAY SHEAR**. New bounded files are `scripts/build_r5_connected_shell_frame.py`, `scripts/build_r5_connected_shell_report.py` and `tests/test_r5_connected_shell_frame.py`. **Verified release:** immutable tested source `ad7db779a469fbdab664c7d76c28ab15469f2c04` passed **494 regression tests** in [Actions #41283131373](https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/41283131373). Production main release `29f94b533ca5dbb02410353f850148fc961d7e05` pinned that tested SHA, and [Pages build and deploy #41283258386](https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/41283258386) both succeeded. Master report Annex M `report.html#annex-r5p5-connected-shell` and hashed standalone HTML, JSON and CSV package were generated. These release facts do not amend any real-building approval, source evidence or F3 status.

**Next open design/solver debt:** source-authenticated floor opening/topology and nonrectangular 2D/3D shell geometry, explicit MPC-versus-flexible diaphragm comparison, selfweight/source mass reconciliation, signed combinations/true concurrent design action transfer in the same shell model, independent mesh convergence benchmarks for plate displacement/stresses, NBC ESM/MRSM/drift/P-Delta, complete RC detailing/foundation checks, and jurisdictional submission. Do not silently mark them closed.

## Remaining source/physical debt — intentionally distinct

1. Authenticate native ETABS/model source or independently reproduce and survey actual as-built member/grid/loads.
2. Obtain actual floor/terrace/slab/void/wall data, loads, verified use/occupancy, concrete weights and seismic mass mapping; reconcile original ETABS 6831.9109kN (old model variants retain 715–772kN conditional gaps).
3. Obtain site-specific hazard/soil investigation, footing service/ultimate signed reactions, F3 geometry/cover/reinforcement and foundation settlement/bearing data.
4. Recheck original F3 failed one-way shear and all other code checks with real physical evidence; professional verification needed before any construction design declaration.

## GitHub governance

- Code GitHub; static reporting GitHub Pages; CI/QA in Actions; Google Drive retains private source records.
- Development work uses separate source branches; production `.github/workflows/pages.yml` **pins a fully tested immutable commit**. Do not overwrite old verified source or frozen A9 Seq9 milestone.
- Report explicit PRE/POST/manifest audit where modifying live authorities; never mark a task complete before CI and Pages readback.
- [Engineering source & engine issue](https://github.com/FabinGurung/JP_Structural_Analysis/issues/7) remains open for real engineering gaps; [interface roadmap](https://github.com/FabinGurung/JP_Structural_Analysis/issues/9) remains open; [frozen A9 history](https://github.com/FabinGurung/JP_Structural_Analysis/issues/2) is NOT G15 active debt.
