# Gate06 NBC105:2025 source-safe site promotion — 20 October 2026

## Tested software and controlled publication
- Public site: https://fabingurung.github.io/JP_Structural_Analysis/
- Source verification: https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/39365767461
- Source CI: **271 passing pytest tests**, public-data safety scan PASS, site navigation PASS, registry QA PASS, source-derived synthetic Gate06 JSON PASS.
- Immutable published branch snapshot: `fdcfc27ff1d80026b759d8ac337a3610a368ad9f` on `site/gate06-nbc105-torsion-mass-20261020`.
- Public content is only code plus separately invented synthetic values: 16 signed horizontal force/couple references, source-member same-combination envelope function, explicit unclosed synthetic seismic mass inventory, NBC 105:2025 §3.4 EI factors, and explicit design HOLD.
- No private C24, F3 calculations, actual building coordinates, 153-case private model trace or source plans are in public GitHub.
- GitHub Pages rebuild runs the generator against the exact pinned SHA, then checks 271 tests, public-data boundary, site QA and JavaScript syntax before deployment.

## Original private project source and status
- Source report and complete assumed frame source evidence live in governed private Google Drive; public GitHub holds no raw private calculations.
- Private Gate06 source artifacts use 153 assumed-model cases (three stiffness variants x 51) and preserve concurrent signed member-end vectors, numerical drift exceedances and source mass reconciliation HOLD.
- User approval permits two hypothesized beam connections and one C24 bar layout as **trial inputs only**, not actual observations or construction acceptance.
- NBC 105:2025 official code primary reference, private Drive ID 1Hlp_E95o3KD4EkiMu2s6_Y20uq-BvETD.
- §3.4 Table3-1: beam/column EI ULS .35/.70, SLS .70/.90; §5.6 eccentricity ±.05b; §5.2 seismic dead plus factored live; §5.5 ductility-scaled ULS drift.
- Modeling caveat: without verified diaphragm, eccentric loads are distributed as nodal moments as a sensitivity approximation, NOT code-verified torsion transfer.
- Outstanding: site hazard/Vs30, 2025 mass model closure, source slab/diaphragm, stiffness and compatibility-torsion classification, nonlinearity, P-Delta, project engineering approval; F3 FAIL remains unresolved.

## Exact rollback
- Prior immutable Pages source = `3517c78efdedc84f102ba1c86372674ee35c4cfd`.
- Prior dispatcher on main = `90fb08e43940aafbd68d0bf1cafced1c4bbea675`.
- To rollback, change only `main:.github/workflows/pages.yml` ref back to prior source SHA and remove only new Gate06 regeneration step; rerun GitHub Pages and verify deploy.
- Preserve current light Engineering Guild/RPG visual design and all existing site routes.
- Existing PR #4, frozen Seq9 branch and release tag must remain untouched.
- Deployment run confirmation is a separate step after committing dispatcher.
