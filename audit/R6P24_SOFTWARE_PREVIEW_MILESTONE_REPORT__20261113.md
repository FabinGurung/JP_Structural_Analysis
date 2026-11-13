# R6.24 Milestone Report — Independent OpenSees structural research software

**Report date:** 13 November 2026 (Asia/Kathmandu)  
**Milestone:** `r6.24-preview` — *software-only prerelease, ENGINEERING HOLD*  
**Product:** JP Structural Analysis (MOD-STRUCT-001)  
**Immutable, QA-verified tag target:** `c9a4ad136ee70e000150026d0f0e1c049ff143df` on `main`  
**Research baseline:** `2c4d4d1791c788376087e116c71a6e41e2cf49f6`  
**Public workbench:** https://fabingurung.github.io/jp-structural-analysis/r6p23.html  
**Current structural research approval:** **NOT APPROVED FOR BUILDING DESIGN OR CONSTRUCTION**.

## Executive summary

R6.24 is ready for a **bounded research-software prerelease** because the independent R6.23 shell/frame solver and R6.24 two-grid numerical sensitivity screen are committed, reproducible, and published to GitHub Pages with passing automated checks. The site also preserves the older project reports. This is not a project-specific structural design, certified Nepal Building Code analysis, or permit-ready structural-analysis report.

The synthetic two-floor numerical example has **31 coarse ShellMITC4 panels**, **124 refined panels**, **31 m² net slab area** (a **1 m² opening** removed on the upper floor), **339.00 kN** dead gravity and **62.00 kN** imposed gravity. Physical dimensions and load sources remain the same between the two meshes. Those figures are model-generated **synthetic benchmark values**, not the Pokhara G+1.5 project's physical design actions.

Independent OpenSeesPy is the computational engine. Reproducing or agreeing with ETABS output is **not** a prerequisite for this software milestone. Correct physical inputs, numerical verification and structural code checks are distinct responsibilities still to be completed for the actual building.

## 1. Implemented software by stage

| Stage | Delivered, bounded software functionality | Key evidence |
|---|---|---|
| R6.10 and earlier | Public project/report navigation; synthetic OpenSees shell/diaphragm research studio; existing report chapter/hold records and engine demonstrations | [Previous prerelease](https://github.com/FabinGurung/jp-structural-analysis/releases/tag/r6.10) |
| R6.14–R6.18 | Original-source geometry/support review, research gravity reactions and refinement studies. Historical source gaps are **not** silently repaired or approved | [Engineering issue #7](https://github.com/FabinGurung/jp-structural-analysis/issues/7) |
| R6.19 | Strict native-source support/connectivity evidence gate, preserving unresolved original support and footing relationships; **not** an ETABS parity prerequisite for the new solver | [PR #27](https://github.com/FabinGurung/jp-structural-analysis/pull/27) |
| R6.21 | Reusable independent input → OpenSees 3D frame solve → signed I/J member forces and equilibrium → bounded M08/M09/M10 reinforced-concrete prechecks → seven-chapter HTML/JSON/CSV casebook and SHA-256 receipts | [PR #29](https://github.com/FabinGurung/jp-structural-analysis/pull/29) |
| R6.22 | Source-labelled beam/column/material geometry; volume-derived concrete, finishes, imposed and wall self-weight; full-edge one-way slab beam load paths; source-load conservation and fail-closed support graph | [PR #30](https://github.com/FabinGurung/jp-structural-analysis/pull/30) |
| R6.23 | Independently runnable **multi-floor** elastic `ShellMITC4` + `elasticBeamColumn` finite-element model with common shell/frame/column nodes, source-declared interior openings, flexible shell and rigid in-plane diaphragm alternatives, signed shell/frame forces and base reactions | [Research PR #31](https://github.com/FabinGurung/jp-structural-analysis/pull/31) · [Main PR #32](https://github.com/FabinGurung/jp-structural-analysis/pull/32) |
| R6.24 | Exact 2× orthogonal mesh refinement that preserves physical floor/void/source loads; independently solved DL and HX in both diaphragm modes; original-node displacement and base Fz sensitivity tables, explicit non-convergence caveat; source-hashed interactive website integration | [Research PR #34](https://github.com/FabinGurung/jp-structural-analysis/pull/34) · [Pages PR #33](https://github.com/FabinGurung/jp-structural-analysis/pull/33) · [Live verification correction PR #35](https://github.com/FabinGurung/jp-structural-analysis/pull/35) |

The R6.23/R6.24 package on `main` includes `r6p23/engine.py`, `convergence.py`, `runner.py`, `site_export.py`, `test_engine.py`, `test_convergence.py`, the viewer HTML/CSS/JS and documentation. The main branch deliberately **does not** merge the whole research repository into the historical Pages dispatcher.

## 2. Synthetic calculations and provenance

**R6.22 four-column gravity reference** (earlier, different synthetic model):

| Source | kN |
|---|---:|
| Slab concrete | 36.00 |
| Finishes | 18.00 |
| Imposed load | 24.00 |
| Masonry wall, net of opening | 26.19 |
| Horizontal concrete beams | 47.25 |
| Concrete columns | 60.00 |
| **Sum of applied source gravity** | **211.44** |

The R6.22 model has one-way full-edge beam transfer and a bounded column self-weight approximation. It is not the same model as the R6.23/24 example.

**R6.23–R6.24 two-floor 3D elastic plate/frame reference**:

| Physical/source quantity | Verified synthetic result |
|---|---:|
| Slab area, floor 1 | 16 m² |
| Slab area, floor 2 after opening | 15 m² |
| Net total slab area | 31 m² |
| Coarse/fine shell counts | 31 / 124 |
| Slab + finish dead gravity | 139.50 kN |
| Beam downstand self-weight | 79.20 kN |
| Two-storey RC column weight | 96.00 kN |
| Masonry wall after opening | 24.30 kN |
| **Total dead load** | **339.00 kN** |
| **Total imposed load** | **62.00 kN** |

The pressure and self-weight expressions are based on explicitly declared thickness, section geometry, lengths, material weight and actual active shell areas. No report-derived ETABS reaction forces are input to this solver. The R6.24 comparison only tests one **coarse→fine mesh pair**; a five-percent difference screen cannot establish rigorous multi-level convergence, code compliance, or safe reinforcement/foundations.

## 3. GitHub Pages and UI status

**Latest verified live site:** https://fabingurung.github.io/jp-structural-analysis/  
**Independent solver workbench:** https://fabingurung.github.io/jp-structural-analysis/r6p23.html  
**Research/project report:** https://fabingurung.github.io/jp-structural-analysis/projects/pokhara-g15/report.html

Implemented user-facing features:

- Readable **responsive editorial UI** with cream background, purple/indigo structural elements, coral warning/selection accents, a card layout, and a mobile-width CSS breakpoint.
- Dropdown selection for **floor**, **loading case** and **flexible versus rigid in-plane diaphragm**.
- Floor-by-floor 2D projection of the genuine computed 3D shell/frame mesh, with selectable beam and shell elements, excluded slab opening, and column locations.
- Selected members reveal **signed local I/J force components**; selected plates show the **24-component ShellMITC4 element force vector**.
- Visible source gravity, mesh convergence-screen outcomes and independent signed support reactions.
- Links to the computation JSON, synthetic casebook, SHA-256 manifest and GitHub source.

**UI QA is bounded:** JavaScript syntax, HTML/export structure, numerical source integrity, live HTTP readback and real Chromium desktop/mobile control tests have passed. The mobile test caught and drove a repair for an unbreakable source SHA that previously caused 511 px scroll width on a 390 px viewport. The UI now wraps long hashes and tests keyboard activation, shell/beam selection, floor/case/diaphragm controls and mobile overflow in CI. See [hotfix PR #37](https://github.com/FabinGurung/jp-structural-analysis/pull/37) and [Chromium QA run](https://github.com/FabinGurung/jp-structural-analysis/actions/runs/43436691680). The page is a **read-only inspection interface**, not an arbitrary building-analysis solver running inside the browser. Automated desktop/mobile screenshots are captured; pixel-perfect visual design review, comprehensive screen-reader accessibility certification and real user usability research remain outside current QA; do not claim those checks have been completed.

## 4. Commits, Actions and verification

| Controlled item | Identity / QA |
|---|---|
| `main` software tag target | `c9a4ad136ee70e000150026d0f0e1c049ff143df` |
| Latest research engine at milestone | `2c4d4d1791c788376087e116c71a6e41e2cf49f6` |
| [Research CI](https://github.com/FabinGurung/jp-structural-analysis/actions/runs/43398308287) | **PASS**: 697 established regressions + 29 R6.23/R6.24 regressions; complete broader pipeline |
| [Main numerical-preview CI](https://github.com/FabinGurung/jp-structural-analysis/actions/runs/43436881971) | **PASS**: dedicated numerical, source integrity and preview bundle gates |
| [Final Pages deploy and live QA](https://github.com/FabinGurung/jp-structural-analysis/actions/runs/43436881758) | **PASS**: 75 build steps; actual deploy; R6.23 live asset/source/hold verification; existing site report/source regression |
| [Mobile UI/Chromium regression PR #37](https://github.com/FabinGurung/jp-structural-analysis/pull/37) | Merged; 390 px overflow corrected and made a CI gate |
| [Main integration PR #33](https://github.com/FabinGurung/jp-structural-analysis/pull/33) | Merged |
| [Research integration PR #34](https://github.com/FabinGurung/jp-structural-analysis/pull/34) | Merged |
| [Live URL correction PR #35](https://github.com/FabinGurung/jp-structural-analysis/pull/35) | Merged |

Historical pinned Pages engine source stays separately checked out so the old report remains stable. The added independent R6.23 solver is checked out at the invoking `main` SHA during Pages build and added as a verified synthetic site bundle. GitHub source commits preserve PRE/POST change history. Actual client drawings/models/reports stay in their governed private source provider, not public GitHub. This work has **not** changed the A7 registry.

## 5. Outstanding structural and engineering HOLDs

These restrictions remain **open** after the software prerelease:

1. **Actual building model:** privately sourced project-specific dimensions, column/beam/slab connectivity, openings, diaphragms, loads, material properties, site and soil constraints must be independently verified. The reference models are synthetic.
2. **Original-source historical gaps:** the research source investigation recorded 115 original shells, 12 unsupported shell connectivity cases, 6 base points not mapped into the coarse frame/shell graph, and 77 ambiguous perimeter-support cases. The synthetic R6.23 model does **not** reconcile those as real-building physics.
3. **Analysis completeness:** nonlinear/geometric-second-order effects, cracked stiffness, governing seismic/wind response, site-specific mass, all required loading/code combinations, irregularities, deflection/drift and more than two levels of mesh convergence.
4. **Design and detailing:** comprehensive beam/column/joint capacities, two-way slab shear and punching, walls, stairs, reinforcement anchorage, soil/foundation/footing checks and a complete engineer-reviewable project SAR/PDF.
5. **Adverse footing finding:** historical **F3: NOT SAFE IN ONE WAY SHEAR** must remain visible until a real redesign/check based on verified project inputs is assessed by a qualified structural engineer.

**Release decision:** `r6.24-preview` is appropriate **only as an immutable tested software research prerelease with engineering HOLD**. The complete-engine milestone, certified report and construction authorization are **NOT READY**.

## 6. Recommended next technical task

**R6.25 — Actual project input normalization and independent multi-resolution acceptance.** Build a private, provenance-linked normalized representation of the real building from its authoritative drawings and verified source inputs, explicitly record unconnected objects rather than auto-joining them, and extend two-grid shell numerical checks to at least a third physically equivalent refinement where supported. Then apply independent site-specific loads and code checks before producing a final structural SAR. An ETABS-native calculation or numerical parity target is **not** a dependency.

### Reproducible code entry points

```bash
python -m pip install openseespy==3.8.0.0 pytest
python -m pytest -q r6p23/test_engine.py r6p23/test_convergence.py
python -m r6p23.runner --reference --output-dir build/r6p23-reference
python -m r6p23.site_export --site-dir build/r6p24-site
```

**Release governance note:** this Markdown audit report and release automation can be committed after the frozen, QA-verified tag target. The tagged software source itself must never be mutated; the audit report's existence on the later `main` commit does not change the immutable software tag.
