# R6.20 — Independent OpenSees / Python SAR engine: governing acceptance contract

**Status:** development scope correction, 2026-11-12. **No engineering approval and no release/tag from this document.**
**Supersedes:** ETABS-native parity as a mandatory completion criterion in the R6.16–R6.19 research discussions. R6.19 provenance checker remains available **only for an optional ETABS-input benchmark/intake path**, not as a prerequisite for generating an independent final report.

## Owner decision

JP Structural Analysis is an **independent first-party engineering application**. Its output is a source-cited structural analysis report generated from independently normalized project geometry, materials, actions and support conditions, solved using OpenSees/OpenSeesPy and verified Python calculations. It is **not** required to reproduce ETABS-generated joints, mesh, member numbers, seismic mass, signed reactions, or historical report values.

ETABS and the original E2K/archived reports are optional **precedent/reference/benchmark evidence**. Their reported values shall not be copied as our computed answers or used to tune an independent model toward a numerical match. Difference from ETABS is acceptable if our inputs, assumptions, physics, code checks, and numerical verification justify the result.

**Never infer a building's real loads, support restraints, member sizes, slab edge condition, foundation system, reinforcement, soil bearing/settlement or site parameters merely because source drawings/E2K files are incomplete.** Distinguish a fully verified design from a clearly labelled preliminary calculation.

## Actual independent first-party pipeline

1. **Input/provenance:** read the authoritative drawings, site specification, materials and design requirements from governed Drive; normalize units, coordinate frame, floors/levels, columns, beams, shell polygons, openings and connection conditions. ETABS E2K may be an *optional* geometry reference, not solver authority. Maintain source citations and decision provenance.
2. **Structural semantics:** model actual load-bearing beams, columns, slabs/diaphragms, walls, base support/foundation arrangement, releases/offsets/constraints. Build a *conforming, connected* model from justified engineering geometry. Inspect the geometry behind each suspect/disconnected shell instead of forcibly preserving the **115/103/12** research trial as a permanent physical model.
3. **Load/mass:** generate dead, finishes, masonry, imposed, wind and seismic mass from geometry, densities, occupancies, code-prescribed factors and source-identified assumptions. Distinguish characteristic/service/factored states; no adjustment to match the old ETABS mass figure.
4. **Solve:** run genuine gravity, wind/earthquake, eigenmodal, code-defined spectral and applicable second-order cases through OpenSees; extract signed forces/moments/displacements/support reactions and project-specific envelopes with correct combined-case treatment.
5. **Independent numerical verification:** force **and moment** global equilibrium, mechanism/ill-conditioning screening, support path consistency, mesh convergence with relevant *local* results, material/section sanity, benchmark comparisons with published hand solutions and a distinct independent method where practicable. No blind 5% of total gravity proxy as proof of per-footing convergence.
6. **Design:** applicable NBC105:2025 seismic, NBC103 imposed, NBC104 wind, NBC110 concrete and verified relevant adopted RC code clauses (and NBC205:2024 only if eligible) to check beam/column/slab/joint/stair/foundation flexure, shear, punching, reinforcement, ductile detailing and serviceability. Capture actions and capacities from the *same* validated independent model and compatible code/load combinations.
7. **Report:** reproducible G+1.5 SAR with original/source inputs, drawings/3D, analytical assumptions, code editions and clauses, model and solver SHA/version, actions/combinations, calculation sheets, real tables/plots, member/foundation designs, pass/fail/hold schedule, and authored HTML/PDF report. No template placeholder presented as a completed design.
8. **QA and milestone:** integrated reruns + browser/document/print QA + benchmarks + artifact checksums and readback. Release as **independent software milestone** only for accurately stated functional scope; never label it site/construction/engineering approval without qualified independent human verification.

## What is *not* a release blocker

- Exporting **native ETABS21 analysis joints or meshes** solely to imitate ETABS.
- Producing exact historical seismic weight, modes, base reactions, member forces or layouts.
- Mapping **21 research support points** to **27 old E2K restraint IDs** just to reproduce the legacy solver.
- Retaining **all 115 historical E2K shell IDs** in the independently authored model when drawing-grounded load paths support a different mesh or representation.
- Clearing the legacy R6.19 ETABS-native-topology gate when the independent-source path does not use that export.

Those remain useful optional research/benchmark tasks, not mandatory engine features.

## What still matters in the independent route

The **physical building** still needs grounded geometry, support continuity and loads. Previously identified 12 unsupported legacy shells are **source-conflict investigation items**, not automatically 12 physically unsupported slabs and not automatically irrelevant. If the drawing-grounded independent model contains an unresolved slab/load path, that specific slab must remain on HOLD.

Likewise the historical **F3 NOT SAFE IN ONE WAY SHEAR** stays a visible *legacy adverse finding*. The independent model must check the actual footprint, soil, reactions, depth, load combinations, one-/two-way shear and reinforcement. A passing *new* F3 (possibly after redesign) requires an auditable new demand/capacity calculation and revision identity; it cannot be auto-passed merely because legacy ETABS is no longer the numerical source.

## Practical module backlog (based on the existing 18-module coverage register)

- Existing bounded kernels: M04 3D elastic frame response and signed forces, M05 modal/spectrum; several partial geometry/load/seismic/member/footing kernels (M01–M03, M06–M12, S17). **Do not overstate these as an integrated complete 3D building design engine.**
- Advance **M02/M04/M06** for actual independent shell-to-frame load paths, conforming shell mesh and complete signed case/combination recovery.
- Advance **M03/M05/M07** for site-specific NBC105:2025 spectrum/mass/eccentricity, displacement/drift, modal combinations and relevant P–Delta checks.
- Complete **M08–M12** for per-member/per-foundation designs, connected detailing and F3 replacement/recheck.
- Implement **M14 stair** and **M16 wind** when applicable to this project; **M13 raft** only if raft/soil spring behavior is applicable, **M15 lift/equipment** only for such actual source equipment. Other requirements must be scoped by project applicability, never universalized.
- Complete **S17 reproducibility/source verification** and **S18 native SAR/HTML/PDF report output**.
- Keep professional engineering acceptance distinct from software CI and from tag creation.

## Verification source catalogue

- OpenSees beam element and member actions:
  https://opensees.github.io/OpenSeesDocumentation/user/manual/model/elements/dispBeamColumn.html
- OpenSees eigen analysis:
  https://opensees.github.io/OpenSeesDocumentation/user/manual/analysis/eigen.html
- OpenSeesPy 3D ShellMITC4:
  https://openseespydoc.readthedocs.io/en/latest/src/ShellMITC4.html
- OpenSeesPy response-spectrum/modal actions:
  https://openseespydoc.readthedocs.io/en/latest/src/responseSpectrumAnalysis.html
- Nepal Government DUDBC national building code library:
  https://dudbc.gov.np/pages/building-code/
- NBC 105:2025 official government text:
  https://giwmscdnone.gov.np/media/files/NBC_105_2025_Seismic%20Design%20of%20Buildings%20in%20Nepal_lqqvx6a.pdf
- DUDBC RCC structural analysis/design compliance checklist:
  https://dudbc.gov.np/content/13317/nbc-compliance-check-list-on-structural-analysis/

**This contract corrects a mistaken dependency. It does not assert that the remaining project-specific engineering and report work is already complete.**