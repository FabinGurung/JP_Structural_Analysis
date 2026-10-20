# Pages Gate05 source-backed numerical update — 20 October 2026

## Code and publication authority
- Existing site: https://fabingurung.github.io/JP_Structural_Analysis/
- Source CI run: https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/39356508853
- Source CI verified 241 Python tests, public-data safety PASS, calculation-coverage QA PASS, site navigation PASS and synthetic ESM JSON generation PASS.
- Published source snapshot pinned in `main:.github/workflows/pages.yml`: `3517c78efdedc84f102ba1c86372674ee35c4cfd`.
- Source branch: `site/gate05-preview-20261020` (not merged into frozen engine).
- Previous Pages source rollback: `017e3bc0ee07956319f34941d522960888869b83`.
- Previous Pages dispatcher main commit: `43ffe2757bcd404725b0ce949282e5c9eeb900ab`.

## Public site scope
The Calculations and Report pages add bounded, native NBC 105:2025 ESM calculation data, not client's input. The public example is a freshly authored synthetic three-level reference (1200 kN seismic weight, abstract elevations). Its outputs are regenerated during every Pages build. The same limited formulas and guarded statuses are tested in GitHub Actions.

## NBC105:2025 code boundaries
- §6.1: Cd,ULS=C(T)/(RμΩu); Cd,SLS=Cs(T)/Ωs.
- §6.2: V=Cd×W.
- §6.3: Fi=V×Wi×hi^k / Σ(Wj×hj^k); k=1 up to T=.5s, k=2 from T=2.5s and linearly interpolated between.
- §5.5.1: ULS design drift multiplies linear elastic displacement by Rμ. SLS uses unscaled elastic drift.
- §5.5.3: ULS ratio .025 and SLS ratio .006, with effective member stiffness per §3.4.
- §5.6: accidental ±.05b eccentricity must be addressed in actual design.
- §5.2: authentic seismic mass and occupancy live load factors remain critical.

## Private G+1.5 hypothesis access boundary
The specific approved-for-exploration hypothesis uses two unverified connector-beam assumptions and a selected, unverified source reinforcement schedule. Private geometry, source member labels, actual design loads and numerical building results were **not** committed to public GitHub and **not** exposed on Pages. Its exact report, signed action results, full reproducibility package, manifested evidence and unresolved engineering checks remain in private Google Drive.

## Engineering acceptance
The public site remains numerical demonstration only. Actual soil Vs30/zoning, signed source axes, full diaphragm and slab layout, source-to-model mass equality, accidental eccentricity, effective stiffness, P-Delta, complete nonlinear/modal checks, construction-safe foundation and reinforcement detailing are not verified. The source F3 footing unsafe shear finding is retained privately as OPEN. No professional acceptance is claimed.

## Exact rollback
Change `main:.github/workflows/pages.yml` checkout `ref` to the previous immutable source `017e3bc0ee07956319f34941d522960888869b83` and remove only the new NBC105 ESM generation step. Trigger the Pages workflow; verify the previous report-first site passes. Never merge or rewrite the frozen Seq9 engine branch, its release tag or PR #4 to roll back a website.

## Deployment verification
Separate from CI preflight. Confirm the final GitHub Pages `deploy-pages` build and deploy jobs; update this audit with the run URL if needed in a separate versioned follow-up.
