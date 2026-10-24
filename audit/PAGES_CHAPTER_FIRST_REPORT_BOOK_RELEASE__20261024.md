# Release: chapter-first continuous-scroll master report / 2026-10-24

Tested immutable engineering source `c62a11fa60bb97ae81e9a59b56ed106918ac5e25`, source CI [359 tests passed](https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/40076443216). Prior Pages main `02a218c0e4a63584a75f2f996502663a44b4a17c` and old source pin `6e1ecbb2036b10337e933b4af158d7ead3634b6a` preserved for rollback.

The former Report Codex was restructured into `site/report.html` as a continuous scroll from cover and table of contents through seven ordered chapter sections. Sticky navigator, full input citation table, actual Gate21 OpenSees floor-force distribution, five-case reactions, same-grid elastic story-chord output, design readiness and report download panels are now embedded at their proper chapter positions. Existing M09, D2, Gate05, Gate06 and Gate21 secondary evidence modules are preserved as expandable panels within relevant chapters. Responsive print layout, source citation links and private-source separation unchanged.

GitHub Actions builds the same deterministic Gate21 numerical report on deploy; script reads machine JSON and explicitly rejects false design approval, wrong schema, missing cases and F3 status changes. Browser scrolling is only navigation, not a live FEM computation or new engineering result.

No source model, material properties, code numerical result, design acceptance, private report or frozen release rewritten. G15 original model source verification remains missing, 15 source proof gates open, F3 **NOT SAFE IN ONE WAY SHEAR**, no engineer certification.

Pages deployment needs both build and deploy success before being called live.
