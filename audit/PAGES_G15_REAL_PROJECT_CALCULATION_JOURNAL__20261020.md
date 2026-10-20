# G+1.5 real-project calculation journal publication — 20 October 2026

## Outcome and controlled branch

Site: https://fabingurung.github.io/JP_Structural_Analysis/project-lab.html
Engine source branch: `site/g15-project-calculation-ledger-20261020`
Pin: `125cbc1f26ce2ae66e0bdb464d9575048348a725`
Source CI: https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/39377286608
Validation: 272 unit/regression tests PASS; public-data safety PASS; five-page navigation QA PASS; both page JS syntax checks PASS.
Previous public source pin: `fdcfc27ff1d80026b759d8ac337a3610a368ad9f`.

## Audience and authority

User asked to **show the actual-source project workflow**, not just a synthetic engine demo. The new page `site/project-lab.html` is a **de-identified numeric summary of that real report workflow**, not a generic example, not an as-built model, and not an engineering signoff.

The private source report, floor drawings, model grids, the Gate06 raw 12-component member-end action arrays and the Gate07 source-frame executable remain private in governed Google Drive or conversation attachments. The publication is a curated projection `registry/g15-public-case-ledger.v0.1.json` transformed deterministically to `site/data/g15-project-ledger.v0.1.json` at deploy. Source hashes enable authorized private reconciliation without disclosing private Drive IDs. The public projection should not be mistaken for a recreation from zero of every private analysis run.

## Presentation

Navigation unified across existing Overview, Calculations, Report, More and the new Project Lab. Current light RPG Guild theme is preserved.
- Six interactive gates G02–G07 with evidence/status explanations.
- Seismic mass reconciliation figure with explicit source, reconstructed, conditional wall scenario, and residual.
- Roof response comparison between G06 gross/ULS/SLS and G07 flexible/rigid hypothetical diaphragm alternatives.
- Full local table of eight detailed Gate06 signed-eccentricity scenarios and four Gate07 diaphragm alternatives.
- Twelve calculation families with provisional/warning/fail statuses and links to existing M09, D2, SP16 and report sections.
- Client-side private file inspector accepts authorized extracted `GATE06_*_FULL_ANALYSIS_PRIVATE.json` from the user's own computer. It reads the selected file locally, lets user select exact source case and member, and displays all 12 signed local action components without network upload, persistence, or server endpoints. Loading the private file in-browser is **not independent rerun**.

## Source-derived Gate07 numerical record

Prior source W=6831.9109 kN, reconstructed G06 W≈5520.4837 kN, gap≈1311.4272 kN. Conditional line-wall weight≈539.3942 kN at a source-derived 9.24 kN/m across seven unverified grid-hull segments on two trial levels. Remaining gap≈772.0329 kN, still unresolved.
Four independent additional Gate07 scenario bundles × 51 load cases = 204 new solves. Source-derived run history Gate05 19 + Gate06 153 + Gate07 204 = 376. Gate07 flexible cracked-EI ULS roof≈72.317 mm, design chord drift≈.040331; hypothetical rigid MPC ULS roof≈28.452 mm, drift≈.015824; hypothetical rigid SLS roof≈17.576 mm, drift≈.002429. Actual floor/diaphragm/wall locations are **not** confirmed. The ESM seismic inertia vector in those comparison cases was deliberately held at its historical-report trial W; extra wall weight does not imply an independently recalibrated seismic force. Residual source mass shortfall remains OPEN.

Source footing F3 continues `NOT SAFE IN ONE WAY SHEAR`; no model assumption, frontend code or public display may clear the source FAIL. Provisional C24 longitudinal bar schedule remains unmapped. Actual project seismic hazard, diaphragm and mass closure, real ETABS/FE parity, modal/second-order effects, and professional approval all remain HOLD.

## Rollback

Edit only `main:.github/workflows/pages.yml` to checkout immutable old source `fdcfc27ff1d80026b759d8ac337a3610a368ad9f`, and remove the public project ledger generator/new script checks, then verify Pages builds/deploys. No source history was deleted.
PR #4 and frozen Seq9 are independent and must remain untouched.

## Numerical ledger correction and final release pin
Public M04 calculation count label reconciled to 153 Gate06 + 204 Gate07 = **357**, plus Gate05 19 = **376** across all three gates. No model calculations changed; this corrects only the human-readable label. Final corrected source CI: https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/39377788381 — SUCCESS, code/QA/public safety all pass. Exact Pages source pin updated to `125cbc1f26ce2ae66e0bdb464d9575048348a725`.

The full private Gate07 reproducibility ZIP was subsequently uploaded to governed private Google Drive with provider-read filename, parent folder and 45,951-byte size; full ZIP remains excluded from this public site and source tree. Private checkpoint holds the authenticated Drive link and SHA256.
