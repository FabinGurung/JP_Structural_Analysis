# Gate16 Pages release and rollback — 22 October 2026

- **CI-tested immutable source:** `a36e790b062250be4972ddfa5a6de46dc02030e5`, [333 passing tests](https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/39749594943).
- **Previous working Pages pin:** `15ea84a59ce1f15c8c21598f414b5c1cd6f1e8c0` (Gate15), preserved as rollback.
- **Prior main release:** `3e1e9b656ed5307f85cdf81e2e9f1c8d3bf3e386`.
- **New route:** `project-lab.html#lab-gate16`. Pages generates `site/data/g15-gate16-source-mesh.v0.1.json` from precisely the above pinned immutable source and reruns full regression/public safety/site checks before deployment.
- **Source register:** `registry/g15-gate16-drawing-mass-review.v0.1.json`, based on SHA-256-verified source PDF architectural pages 9–11 and material pages 4/6. Original PDF still in existing Drive; no original/private pages published.
- **Numerical changes:** 36 real OpenSees FE cases, sample-bay shell meshes 2×2 (8 shells), 4×4 (32), 8×8 (128) on two assumed levels and earlier hypothetical 4×4 opening (24). Matched signed X/Y eccentricity scenarios and same-source-member `COL-F1-L0-1` Mzi comparisons.
- **Engineering HOLD:** original ETABS mass 6831.9109kN vs G10 trial 6116.443223kN unresolved (715.467677 kN gap); competing report unit weights 20 vs 25 kN/m³ unresolved; complete floor/terrace slabs and openings unverified; no seismic design acceptance; F3 **NOT SAFE IN ONE WAY SHEAR**.
- **Release acceptance:** both Pages BUILD and DEPLOY must complete successfully before user-facing live release claim.
