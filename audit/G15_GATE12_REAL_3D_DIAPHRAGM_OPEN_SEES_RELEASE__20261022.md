# Gate12 controlled release: Actual 3D OpenSees diaphragm model comparison (22 Oct 2026)

## Verified source and deployment
Source branch `site/g15-gate12-opensees-diaphragm-20261022` pinned source SHA `b0eba2743dbfb7fae8552ea23adc371302432eb0` (prior source `181852bcfdce91db7c5d61101608c00d2c1a15f3`).
Source CI https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/39690579931: **319 tests PASS**, 18 FE cases; 9 flexible and 9 rigid MPC, 32 trial algebraically signed member combinations. Full 165-member 12-component actions for each model/case uploaded to a GitHub artifact. Public source safety and site QA PASS.
Pages route `https://fabingurung.github.io/JP_Structural_Analysis/project-lab.html#lab-gate12` publishes numerical summary and signed governing end moments with human-selectable case comparisons.
Hosted action `.github/workflows/g15-diaphragm-fe-analysis.yml` supports authenticated owner/contributor-prefilled GitHub issues `[JP G15 G12]`, carrying only whitelisted Gate10 scenario ID and stiffness. Users view/edit Pages without login; GitHub issues need authenticated contributor, no embedded PAT.

## Exact engineering scope and qualifications
The original source-derived 23-position, 165-member, 92-node 3D beam-column frame is solved in OpenSees with identical lateral nodal forcing between flexible and rigid alternatives. Rigid idealization uses OpenSees rigidDiaphragm(3) at the area-fitted assumed floor centroid, constraining Ux,Uy,Rz; flexible model leaves individual plan nodes. Each three-storey scenario: GRAVITY plus X and Y, +/- direction, +/- 5% accidental eccentricity = 9 load cases/diaphragm, 18 FE solves total. Total force and moment equilibria both pass. Recorded vector roof and interstorey chord displacement, source-specific signed member actions, governing end moments, 32 illustrative 1.2G+E and .9G+E member-wise signed combinations. These assumed factors are NOT confirmed governing NBC105:2025 load combinations and cannot be used for engineering acceptance.

**This does NOT include physical slab shells, independently verified diaphragm stiffness, verified wall geometry, actual ETABS mass source, measured site hazards, P-Delta, modal dynamic analyses, full code drift factors, reinforcement checking or footing redesign.** Original source F3 is `NOT SAFE IN ONE WAY SHEAR`. Trial differences are engineering sensitivity evidence, not proof that rigid assumption is correct.

## Source authority/rollback
P0/P1 original ETABS W 6831.9109 kN versus Gate08 conditional W 6059.87798 kN / residual 772.0329 kN still source-unreconciled. Gate10 wall+commercial trial W 6116.44322 kN is hypothetical.
Preserve prior Gate02–11 data and site deep links. PR #4 remains draft and Seq9 frozen untouched.
To roll back, restore `main:.github/workflows/pages.yml` checkout ref to `181852bcfdce91db7c5d61101608c00d2c1a15f3`, remove Gate12 site generation and JS check, and disable `g15-diaphragm-fe-analysis.yml`. Do not delete raw evidence.
