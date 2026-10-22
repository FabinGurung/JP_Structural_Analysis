# GitHub Pages Gate15 release — 22 October 2026

- Tested source SHA `15ea84a59ce1f15c8c21598f414b5c1cd6f1e8c0`; branch Gate15 CI https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/39710843042 (329 passing pytest checks).
- Previous deployed immutable Gate14 source SHA `830c5ec006c192330b0c371fb8ab43585c0188ad` retained for rollback. Prior main release `1643bb680cf19b9967e20e747d95533ca313e286`.
- Site section: `project-lab.html#lab-gate15`, data generated from this exact source: `site/data/g15-gate15-mesh-opening.v0.1.json`.
- 27 real FEM cases: 2×2 full patch vs 4×4 full patch and hypothetical center aperture (8,32,24 shell elements across two assumed levels); signed actions and force/moment equilibrium maintained.
- Hypothetical aperture reduces modelled two-patch gravity 45.84681 kN and conditionally reduces assumed seismic mass; mass-source physicality remains unverified; do not treat numerical recalibration as observed ETABS mass.
- Preserved structural HOLD: no actual full-floor slab polygons or aperture/terrace location, no full convergence study, no verified wall/diaphragm/source ETABS mass definition; **F3 NOT SAFE IN ONE WAY SHEAR**.
- Release acceptance requires green Pages build and deploy for the new main commit. No design approval.
