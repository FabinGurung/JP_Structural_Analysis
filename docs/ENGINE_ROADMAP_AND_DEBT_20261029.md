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
| R4 | Source-identified signed FE static analysis → M08/M09/M10 design check → 7-chapter report and full I/J action CSV | **V0.3 IMPLEMENTATION UNDER CI**, independent D2 synthetic frame, not project-linked; no modal action transfer |
| R5 | Generalize canonical arbitrary 3D frame/area model inputs, member/diaphragm/wall/area load placement, verified weight/mass trace, real signed ULS/SLS combinations | **OPEN ENGINE DEBT**, do not combine independent case IDs |
| R6 | Complete structural dynamics: NBC105 ESM/MRSM, modal participation, accidental eccentricity, effective stiffness, diaphragm response, drift/torsion/P–Delta, stiffness/soft-storey/mass irregularity with independent benchmarks | **OPEN ENGINE DEBT** |
| R7 | Complete RC member design: longitudinal and transverse steel, beam negative/positive moment/torsion/anchorage, columns biaxial/second-order/confinement, joint shear/SCWB, slabs, stairs, CF1/F3 footings including eccentric contact/settlement and foundation FE where relevant | **OPEN ENGINE DEBT** |
| R8 | Independent numerical comparison, guarded QA, IFC/DXF/ETABS imports as supported, signed data/provenance, report figures, annexes, PDF/HTML/CSV/JSON packaging, municipality/jurisdiction-specific submission contract | **OPEN ENGINE AND VERIFICATION DEBT**, not approved SAR |

## Prior work verified before this stage

- Original source SHA, report sections and 15 evidence requirements indexed; source error F3 `NOT SAFE IN ONE WAY SHEAR` preserved.
- Multiple synthetic and source-bounded actual OpenSees cases executed, signed end-action and force/moment equilibrium modules tested. Different model generations must not be misrepresented as one original building model.
- Independent bounded IS456 beam, column and joint code/design kernels, anchored source/edition tests, SP16 table/partial chart checks.
- F3 12 geometry-demand sensitivity scenarios, source-conflict ledger, and independent 24-candidate footing checks across two synthetic/source-bounded v0.2 inputs; a provisional mathematical pass is not a physically accepted footing.
- v0.2 report prints seven original-TOC chapters, JSON/CSV/HTML/Markdown and SHA-256 output manifest. Development CI 417 pass; GitHub Pages successful run `40786078082`. Sources pinned and preserved.

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
