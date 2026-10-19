# SP16 original acquisition and D2 code evidence — public Pages promotion (2026-10-19)

- Public: https://fabingurung.github.io/JP_Structural_Analysis/
- New immutable publication source: `2349678ff60f8f69d24643b62709b4e6d1207e1b` (branch `site/sp16-d2-evidence-20261019`).
- Source build and site checks: https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/39238063830 ; **215 tests PASS**, generated M09, real OpenSees signed D2 synthetic case, corrected Table A rounded elastic strain, public privacy scan and website QA PASS.
- Previous rollback source: `d10f82518c2a0afc2e5179b8a75e6f90fa6a0c5a` and previous deploy dispatcher `f9d6b0e120fa1995167fde8127e5006ded5e0f40`. Rollback: pin `main:.github/workflows/pages.yml` back to previous SHA, remove the signed-D2 generator and separate `site/d2.js` JS syntax check, rerun deployment.
- Original SP16:1980 PDF (255 physical pages) original SHA-256 `d2a6246a5dc7504568f4e55f310dd4be9d925fb1a8b04b6d7f5132c93f66c76e` preserved in private Google Drive source ingestion; full extracted source SQLite, JSONL, 92-chart inventory, all 255 page images, Table A and integrity manifest uploaded separately to Drive. No raw standards PDF or client data exposed in public GitHub.
- Verified first-party Table A: 12 rows, Fe415 and Fe500, printed page 6 / physical page 29. Original Chart 31 visually inspected printed p116 / physical p139, fy415 d'/D=.05, two opposite bar faces. Original chart ordinate digitization and reconciliation between SP16:1980/IS456:1978 and IS456:2000/current amendments **remain HOLD**, not silently passed.
- D2: true OpenSees static elastic member I/J local signed force recovery; six-component global equilibrium; signed concurrent combination arithmetic; M08 beam, M09 column P-M-M and M10 joint adverse shear bound. Synthetic test column utilization ~0.7614, **not** an approved structural-design utilization for a real building.
- Public light RPG/Engineering Guild interface and existing four-page navigation preserved.
- Main dispatcher only; PR #4 and frozen Seq9 release remain untouched and must not be merged.
- Public Pages publication success must be verified from the new dispatcher run, not assumed from source CI success.
