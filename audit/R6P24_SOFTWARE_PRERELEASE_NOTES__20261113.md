# R6.24 — Independent OpenSees Shell/Frame + Mesh Sensitivity (Software Preview)

**STATUS: RESEARCH SOFTWARE PRERELEASE · ENGINEERING HOLD · NOT FOR CONSTRUCTION**

**Frozen, QA-passed software commit:** `c9a4ad136ee70e000150026d0f0e1c049ff143df` (`main`)  
**Validated research lineage:** `2c4d4d1791c788376087e116c71a6e41e2cf49f6`

### Delivered in this prerelease

- **R6.21:** reusable signed OpenSees analysis-to-bounded-RC-casebook pipeline, actual static frame actions, HTML/JSON/CSV and SHA256 results.
- **R6.22:** geometry/material-derived slab, wall, beam and column gravity, explicit one-way beam load paths and source-conserving checks.
- **R6.23:** genuine multi-floor 3D elastic ShellMITC4 + beam/column FE, shared node connectivity, actual internal slab openings, flexible versus rigid in-plane diaphragms, signed shell/member forces and base reactions.
- **R6.24:** source-equivalent 2× mesh refinement, per-case numerical displacement/reaction differences and source-preserving artifact validation.
- **Mobile UI QA:** corrected long-source-digest horizontal overflow, added permanent real Chromium desktop/mobile test gates and screenshots, and keyboard-accessible beam inspection.
- **GitHub Pages:** publicly visible, read-only, interactive R6.23/R6.24 workbench with floor/case/diaphragm controls, clickable shell/beam force results, support reactions and mesh sensitivity; earlier published structural reports preserved.

The synthetic two-floor benchmark has **31 coarse shells → 124 refined shells**, 31 m² actual slab area after an internal 1 m² opening, **339.00 kN DL** and **62.00 kN LL**. These are **synthetic calculation values, not the Pokhara building's verified design loads.**

### Verified build and deployment

- [Research CI: 697 established + 29 dedicated tests passed](https://github.com/FabinGurung/jp-structural-analysis/actions/runs/43398308287)
- [Real desktop/mobile Chromium UI regression](https://github.com/FabinGurung/jp-structural-analysis/actions/runs/43436691680)
- [Independent main numerical/preview QA](https://github.com/FabinGurung/jp-structural-analysis/actions/runs/43436881971)
- [Successful Pages deployment with both new and legacy live verification](https://github.com/FabinGurung/jp-structural-analysis/actions/runs/43436881758)
- [Live independent workbench](https://fabingurung.github.io/jp-structural-analysis/r6p23.html)
- [Canonical report and review issues](https://github.com/FabinGurung/jp-structural-analysis/issues/7)
- [Full consolidated R6.24 milestone report](https://github.com/FabinGurung/jp-structural-analysis/blob/main/audit/R6P24_SOFTWARE_PREVIEW_MILESTONE_REPORT__20261113.md)

### Critical limitations — engineering HOLD

This code does **not** certify actual project-source geometry, completeness of historical building shell/support connectivity, nonlinear/cracked behavior, mass/seismic/wind/drift and full load cases, multi-resolution convergence, RC member/slab/stair/footing design, soil bearing, or professional structural approval. **Historical F3: NOT SAFE IN ONE WAY SHEAR** remains adverse. Do not use the synthetic forces, sample mass, displayed 5% screen, or software CI as construction authorization or as a complete engineering SAR.

The code independently uses OpenSeesPy and manual source-derived equations. ETABS result parity is not a required gate.

**Next priority:** private actual-building source normalization, multi-level mesh convergence, site-specific structural actions/code design checks and an engineer-reviewed complete SAR. The main Pages showcase remains separate from the governed research engine.
