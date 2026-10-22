# Gate14 · Two-level source-bay ShellMITC4 numerical sensitivity

- **Starting baseline:** tested Gate13 source `1cc18b552b01f51190bb9e3168ed909bf612379a` and 323 passing tests.
- **Geometry:** F–G / 1–2 source dimensional sample, 4.965 m × 3.600 m (17.874 m²). Assumed repeated at elevated levels 1 and 2, **not physical evidence** of those slab levels, slab outline, openings or diaphragm.
- **FE models:** 165 preserved source physical frame segments. Computational splits at two levels produce 177 OpenSees elastic frame pieces, with 8 real ShellMITC4 elements in the shell alternative. Equal load-path variants: flexible frame corner tributary reference, shell pair, ideal rigid MPC.
- **Gravity:** 5.13 kPa floor-dead assumption × 17.874 m² × 2 patches = **183.38724 kN** (not extra seismic mass). Seven hypothetical external wall beam edges at 9.24 kN/m, same on levels 1 and 2.
- **Case matrix:** 3 structural alternatives × (1 gravity + 8 signed X/Y ±5% accidental-eccentricity cases) = 27 actual FE solves.
- **Numerical QA:** all frame local signed 12-component end actions archived; applied and support reaction forces/moments must balance to 0.001 engineering units; gravity load applied identically across alternatives.
- **Mass:** unchanged Gate10 G10_EDGE_COMM floor seismic weights; no insertion of additional fictitious matching mass. Original 6,831.9109 kN versus Gate08 6,059.877983 kN gap remains unresolved.
- **Unresolved:** actual slab polygons, topography/openings, gravity floor assignment, shell mesh refinement convergence, wall locations, occupancy, actual ETABS mass-source settings, NBC drift, full P–Δ and full-floor diaphragm.
- **Critical design HOLD:** F3 one-way shear remains **NOT SAFE IN ONE WAY SHEAR**. No construction approval.
- **Rollback:** prior published Gate13 immutable source `1cc18b552b01f51190bb9e3168ed909bf612379a` remains unchanged.
- **Release:** publish only after new branch CI passes, then pin immutable tested SHA via `.github/workflows/pages.yml` on `main`.
