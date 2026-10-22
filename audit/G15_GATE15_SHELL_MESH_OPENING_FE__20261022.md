# Gate15 source-bounded mesh refinement and aperture hypothesis

- **Tested baseline:** published Gate14 source `830c5ec006c192330b0c371fb8ab43585c0188ad`. All old gates preserved.
- **Source facts:** F–G/1–2 reported sample slab 4.965 × 3.600 m, nominal 125 mm, 5.13 kPa dead; base frame has 165 source-grid frame member segments. Actual floor, slab opening and terrace topology are NOT source-known.
- **Three actual FE models:** real ShellMITC4: 2×2 no hole (8 quads across two assumed levels), 4×4 no hole (32 quads), 4×4 with unverified centered void occupying 25% of bay area (24 quads across two levels). Boundary nodes connect through subdivided original beam lines. Opening unsupported trim edges remain structurally unverified.
- **27 solves:** 3 models × 9 matched gravity and ±X/Y, ±5% eccentricity scenarios, with explicit conditional reduction of gravity and lateral floor-weight trial in the void model only. 2×2 vs 4×4 full-bay modes share the same imposed floor weights.
- **Loading:** the full two-patch gravity total is 183.38724 kN; hypothetical 25% void decreases it by 45.84681 kN. The subtraction from G10 seismic mass is illustrative ONLY IF that historical assumed mass includes this precise patch, which has not been confirmed. No ETABS inverse-mass fitting.
- **Validation gates:** global force/moment equilibrium <0.001, signed 12-component frame end actions, mesh CCW orientation and element area checks, 3-mode case matrix, no accidental double body gravity.
- **Engineering HOLD:** two meshes do not establish convergence; unknown floor shells, opening trim, terrace, actual walls, wall opening reductions, columns, site/drift combinations, P–Δ, ETABS mass-source definition, and **F3 NOT SAFE IN ONE WAY SHEAR**. No engineering approval.
