# RUN-ANALYSIS MVP — controlled GitHub Pages publication — 20 October 2026

## Deployed functionality
- Site route: https://fabingurung.github.io/JP_Structural_Analysis/analysis-studio.html
- Tested source snapshot: `8d804ec4df1a6052b7acfe2fda4a738a2bb4d1ca`, branch `site/interactive-analysis-mvp-20261020`.
- CI: https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/39417453730 — 290 tests PASS, OpenSees 3-case regression sample PASS, browser JS syntax PASS, six-page navigation PASS, public-safety scan PASS.
- Browser: editable 3-storey single-bay 2D hypothetical frame properties, 3 independent weight inputs, NBC105:2025 Cd and Fi instant preview, frame diagram, local JSON export.
- Authenticated backend handoff: pre-filled GitHub issue `[JP Frame MVP]`, owner `FabinGurung` only; default branch workflow `.github/workflows/portal-frame-analysis.yml` on issue opened and manual workflow dispatch.
- Engine: numerical OpenSeesPy elasticBeamColumn 2D, three independent signed cases GRAVITY, ESM_PLUS_X, ESM_MINUS_X; 9 frame members each, signed end actions, reactions, drift-screen and explicit engineering HOLD.
- Output: GitHub Actions JSON artifact, synthetic only, and owner-submitted issue success comment with job link. OpenSees issue submission itself requires an authenticated GitHub action; Pages cannot call GitHub Actions directly without a server or credentials, so this avoids tokens embedded in the public site.
- Result is not the 165-member project frame; actual source building geometry stays in private Drive.

## Safety
- Public issue cannot run for other authors; runner enforces owner identity, exact whitelisted numeric fields, tight model constraints, no URLs, no private source uploads and source-code injection.
- GitHub runner checkout uses immutable source SHA and `persist-credentials: false`. Workflow permissions scoped; no user-supplied shell interpolations.
- No raw client plans, report PDF or private 816-case force dataset in Pages.
- NBC105 static arithmetic runs locally and is source-labelled; OpenSees actual solver is run by authenticated workflow only.
- Structural certification, 3D torsion, complete real project analysis and F3 source footing remain HOLD.

## Rollback
- Old source pin `0379b1e5ecf048c07c019fc9b784e9fb95cd8304`, new source pin `8d804ec4df1a6052b7acfe2fda4a738a2bb4d1ca`.
- Previous main dispatcher commit `c9d323306b0ea383dbd084d6ccafd01902a16c4e`. Restore `.github/workflows/pages.yml` checkout ref to old source, remove generated portal-reference-frame step, redeploy. Disable portal-frame-analysis workflow to stop issue queue if rolling back product.
- Frozen Seq9, PR #4 and private Gate08 evidence are not modified.

## Deployment
After commit, verify Pages deployment jobs and route from server. The web route's source and tests exist; independent public-browser readback may be unavailable.
