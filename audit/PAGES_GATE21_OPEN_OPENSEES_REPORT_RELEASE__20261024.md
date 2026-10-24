# Gate21 executable OpenSees SAR release / 2026-10-24

- Tested G15 OpenSees source SHA `6e1ecbb2036b10337e933b4af158d7ead3634b6a`, [GitHub Actions 355 tests PASS](https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/40049927892); original Gate20 source `7abc1c1e4bcb6923254c485526469427c8bfeba8` and prior main `c9c404109a0e3f2ae771910204144918b1b51965` retained intact for rollback.
- Executable code uses existing actual 3D OpenSees solver to generate all five cases on 165-member assumed source-derived public grid. Numerical outputs delivered as HTML Print-to-PDF, Markdown, JSON, CSV with 825 signed 12-component local member force records, SHA256 integrity manifest.
- Inputs: conditional source PDF mass table Wi=270076.47,274062.74,152521.81 interpreted *conditionally* kg and converted by 9.80665/1000. W=6831.910791783kN vs original report 6831.9109kN. This is not original ETABS element mass-source composition.
- Working estimates explicitly cited, NOT verified as original: T=.493s, Cd=.131, E=22360.6798MPa, ULS EI factors, hypothetical two connectors, fixed supports, and gravity equal-distributed equivalent seismic floor weights.
- Real FEM force/moment global equilibrium residuals <0.001; same-grid elastic story chord ratios are NOT code-accepted drift. The signed end-force vectors are open and inspectable, no black-box output.
- Original report structure inspired seven chapters. This numeric report is NOT a complete 68-page report substitute: full site hazard, sections, dead/live source loads, slabs/diaphragm, modal, torsion, PDelta, steel design/footing geotechnics and source-verified ULS/SLS remain unverified/absent.
- Source F3 **NOT SAFE IN ONE WAY SHEAR** retained, no design/construction approval. No original private source PDF or DOCX copied into public pages.
- Pages BUILD and DEPLOY both must finish success before public access claimed.
