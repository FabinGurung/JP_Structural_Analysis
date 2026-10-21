# G15 Engineering debt cleanup: source and deployment audit (21 Oct 2026)

## Completed and source-verified
1. Existing public G15 3D Studio, source-derived 23 column positions and 165 working frame members, 5 signed source-labelled OpenSees cases.
2. Default 3D solver's maximum roof displacement now uses `max(hypot(Ux,Uy))`, not the prior `|Ux|+|Uy|` upper estimate. Chart labels remain source-bounded.
3. Added reaction+applied **3D global moment** equilibrium for all five independent load cases, beyond prior global force equilibrium only. Regressions fail closed on either.
4. User can select extracted JSON from a completed GitHub Actions job within the webpage, inspect the custom signed same-case member-end actions, then restore the published reference. Result files are parsed locally by the browser, never transmitted to a third-party site. Imported JSON requires correct schema, 92-node source, 159/165 elements, 5 cases, 12 finite local-action components/member, moments and forces balanced, and F3/engineering HOLD. Older output schemas must be rerun.
5. GitHub Actions CI `https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/39570657493` PASS **302 tests**, privacy scan PASS, native OpenSees source case PASS and site QA PASS.
6. Page deployment pin upgraded from `c4353c564a256c49fe0d2680f68d89814bef16a0` to verified immutable source `7e9ee03194710ea4ae06d82214fc72ed6aa2d8b0` on `main`; G15 3D hosted issue workflow pinned to the same reviewed source.

## Already verified historical baseline
- Full public GitHub 3D issue-run/handoff: `https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/39529648914` successful; Actions 165-member signed JSON artifact, GitHub issue #6 closed completed.
- Initial public 3D Pages deployment `https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/39529620629` successful.
- Project Lab source-derived Gates02–08 and retrospective 1,192 scenario solves are *not* a single consistent as-built model; no uplift into certified design is implied.
- GitHub Pages public 3D and interactive viewer: `https://fabingurung.github.io/JP_Structural_Analysis/g15-3d.html`.
- Vercel integration/secure-service issue #5 was retired by user choice; no Vercel dependency.
- Draft PR #4 and frozen Seq9 remain unmodified.

## Unresolved engineering debt — deliberately not auto-cleared
- Traced slab and wall polygons/load paths; reference grid topology and diaphragm physicality remain hypothetical.
- Original ETABS seismic weight W 6831.9109 kN vs trial with conditional line wall 6059.878 kN: **772.0329 kN (11.3%)** unexplained. New generic public model load inputs are independent and not a reconciliation of this mismatch.
- Historical flexible floor variants flagged drift-limit exceedances; rigid diaphragm trial favorable results cannot be assumed physical.
- Required complete NBC105 site hazard/soil and signed action checks, P-delta, eccentricity and source member detailing outstanding.
- Source footing F3 one-way shear is **NOT SAFE**. Never waive this FAIL from a passing website CI run.
- Client-specific full-model input and original third-party documents have not all been reproduced publicly; the user authorized publishing their own technical source, not third-party secrets or credentials.

## Roadmap and issue tracking
Primary engineering reconciliation P0–P3 is GitHub issue #7:
`https://github.com/FabinGurung/JP_Structural_Analysis/issues/7`
P0 exact source geometry & seismic mass; P1 diaphragm, torsion, drifts, C24, F3;
P2 editable full 3D authoring, round-trip case catalog and solver interoperability;
P3 freeze SAR/LaTeX template only after model/contracts accepted.
Do not close #7 until the relevant source/engineering evidence is read back.

## Rollback
Undo both `main:.github/workflows/pages.yml` and `main:.github/workflows/g15-open-3d-analysis.yml` source pins to `c4353c564a256c49fe0d2680f68d89814bef16a0`, redeploy Pages. The old published baseline and historical Actions artifacts remain available.
