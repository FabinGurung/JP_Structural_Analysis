# Public 3D Studio — Github-only deployment, 21 Oct 2026

## User authority and product decision
The user expressly authorized publishing their source-derived G15 structural geometry, results and modelling assumptions to the existing public repository. **No Vercel, private backend or new project required.** Separate credentials, personal/confidential data and third-party proprietary standards texts are not included.

## Engineering/implementation proof
- Source branch `site/g15-open-3d-analysis-20261021`, immutable tested source `04de562d6f94d0583c49a2f7907e7d9118444f9c`.
- GitHub Actions CI https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/39528706299 — passed tests including actual 165-member 3D OpenSees solver and 5-case signed equilibrium QA; public safety scan passes.
- Source geometry in `site/data/g15-working-grid.public.v0.1.json`, reconstructed directly from authorized Gate03: 23 positions, 69 column segments, 96 inferred beam segments (including two approved hypothetical connectors).
- Public 3D editor `site/g15-3d.html`: rotate, inspect, toggle beam connections, edit beam width, Ec, gross/ULS/SLS EI, three floor seismic weights, Cd and T. Live ESM preview. Reference initial numerical output `site/data/g15-open3d-reference.v1.json` is regenerated in Pages build and supports all five case/member signed-force selection.
- GitHub Actions workflow `.github/workflows/g15-open-3d-analysis.yml`: owner-authenticated issue queue or manual workflow dispatch; each run saves full signed source 3D JSON result. Anyone can view/edit in browser and fork open source; only owner issues spend this repository's CI runtime.
- The public FE is a bounded 3D linear frame, not exact historical ETABS reproduction, physical floor slab, as-built geometry or professional structural design. Source ETABS seismic mass remains unreconciled. F3 source one-way shear remains **NOT SAFE**.

## Rollback
Prior Pages source pin `8d804ec4df1a6052b7acfe2fda4a738a2bb4d1ca`, new source pin `04de562d6f94d0583c49a2f7907e7d9118444f9c`. Restore original `main:.github/workflows/pages.yml` pin and remove G15 result build if required. Disable the G15 issue workflow to stop hosted runs. PR #4 and frozen Seq9 are untouched. The historical Gate08 source archive remains stored in Drive.

## Open checks
Direct browser navigation and real owner-issued hosted-job trigger still require independent verification. Build/deploy Actions and regression alone do not establish that a particular user's browser loaded properly.
