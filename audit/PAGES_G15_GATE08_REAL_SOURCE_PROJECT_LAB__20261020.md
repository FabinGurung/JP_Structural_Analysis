# G15 Gate08 real-source Project Lab publication — 20 October 2026

## Execution and evidence
- Private report SHA256: f122904444a2e2f75230d9d4e41da0093d050da25c6e8140c86d466b7e37cc52; private Drive original remains the authority.
- Gate08 private summary SHA256: 37d3ab85d96953a74a773358fb9d56de1858ed163c896bb99de8e43844ee0a48.
- Gate08 private reproducibility ZIP SHA256: c237a8a0f99bff0400969afaa77dd9c02ce77ba0718f2a5a294e522e7e5dda15.
- Original 16 private FE variants x 51 signed linear static cases = 816 cases; 134640 member end records, private QA readback pass.
- Cumulative Gate05–08 project cases: 1192. Gate05–07 historic subtotal remains 376.
- Gate08 Google Drive authority checkpoint: https://docs.google.com/document/d/11O_3Sbj7vOExy-L5WES9mI0R3JygGWN6J65z0LGlHHw/edit
- Development/source CI successful: https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/39409863795 ; 278 tests pass, public-data safety PASS, site QA PASS, JS syntax PASS.
- The private ZIP is retained in personal Library; direct Drive ZIP transfer not confirmed.

## Published surface
- Existing Pages URL: https://fabingurung.github.io/JP_Structural_Analysis/project-lab.html#lab-gate08
- Newly pinned source commit: `1fd723d97100e5501d23a5ec6c2e589e259d9dab` from `site/g15-gate08-source-reconcile-20261020`.
- Previous published source commit (rollback): `125cbc1f26ce2ae66e0bdb464d9575048348a725`.
- Previous main Pages dispatcher commit: `43acbebf5c3352e390e3363105ed8cbdec80e0c9`.
- Public Gate02–08 7-stage journal; source/assumption deltas, floor polygon limitation, 16 numeric scenario rows, ULS/SLS flexural and diaphragm alternatives, mass accounting, F3 unsafe source finding and open approvals.
- The public build runs generated scripts for real-source de-identified ledger and Gate08 aggregates, checks count/algebra/source hashes/HOLD. The private 816 FE runs are not rerun by public Actions and are NOT reconstructed from public data.

## Engineering acceptance boundaries
- 23 grid points convex hull area 224.375 m² versus source captions 218.68, 212.09, 188.11 m² and bounding rectangle 263.13 m². Neither proxy is a verified physical floor outline.
- ETABS W 6831.91 kN, conditional wall reconstructed W 6059.88 kN, residual 772.03 kN. Hypothetical full wall perimeter still leaves 218.57 kN. Wall proposals NOT admitted as field evidence.
- ULS flexible rectangle proxy drift screen 0.037140857 >0.025; convex-hull proxy screen 0.02481773 <0.025. Neither establishes building pass/fail because diaphragm, wall/load paths and mass source remain unverified.
- F3 one-way shear is source FAIL. No source geometry, private member IDs, ETABS vectors, personal identities or drawings are published. PR #4 and frozen Seq9 remain untouched.

## Rollback
Restore `main:.github/workflows/pages.yml` checkout ref from `1fd723d97100e5501d23a5ec6c2e589e259d9dab` to `125cbc1f26ce2ae66e0bdb464d9575048348a725`, reverse versioned G15 ledger build output and remove only Gate08 aggregate step + script syntax check. Trigger Pages workflow and confirm prior site build/deploy. Existing Git tags/releases and history are immutable.

Deployment remains to be verified from a separate successful public Pages build-and-deploy run after this dispatcher commit.
