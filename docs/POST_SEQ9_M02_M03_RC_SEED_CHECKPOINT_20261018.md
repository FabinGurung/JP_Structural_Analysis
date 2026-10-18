# POST-SEQ9 progress checkpoint — M02/M03/M06 and RC bounded seed
Date: 2026-10-18 NPT. Branch: `feature/post-seq9-first-party-no-e2k-20261015`.

## Frozen authority and releases
- Frozen tag: `a9-seq9-phase-c-20261015` commit `f7c2f8ad7d06ec18b750835b311748b129f39a36`.
- NO merge into `engine/opensees-sar-v0.1` or `main`. Hold issue #2 remains OPEN, PR #4 remains DRAFT.
- Old CI red runs in this branch were regression-test development debt and corrected by later green runs; do not claim red run itself passed.
- No confidential DOCX/PDF, client geometry, screenshots or project data added to public GitHub.

## M02 — gravity and mass
- Explicit source identifiers prevent duplicate load consumption. Each known component's assigned node fractions must sum to unity.
- Computes nodal gravity, effective seismic weight, mass in kN*s²/m, centre of mass, and independent source-to-assembly conservation.
- Opens a bounded canonical OpenSees static case using same verified source coordinates and an explicit unit contract, creates nodal masses and gravity forces, solves and checks Rz/Mx/My global equilibrium.
- **Limit:** Actual wall/area geometry tributaries, frame/area distributed load FE translation and validated client model response remain OPEN. A reaction equilibrium check is necessary not sufficient.

## NBC105:2025 source
Official government PDF: https://ebps.kathmandu.gov.np/UploadFiles/NBC_105_2025_Sesmic_Design.pdf
The code functions admit ESM and MRSM spectral shapes only for 0<T≤6s; actual soil classification/Z/importance are not invented.
Implements §5.2 live participation, RC MRF §5.1 period and factors, §6.2 base shear and §6.3 vertical distribution, §5.6 eccentricity ACTIONS, design-drift §5.5.3, modal 90%/33Hz gate and MRSM §7.5 force-only scale.
Source-to-function map in `registry/nbc105-verified-rule-inventory.v0.1.json`.
Particularly: §7.5 NEVER scales drift or displacement. High-frequency missing mass merely evidenced by an ID is not claimed solved.

## RC priority
`registry/rc-design-engine-execution-queue.v0.1.json` ranks M08 beams, M09 columns, M10 seismic joints, M12 footing, M11 slab, M14 stair, M13 subgrade. Annex A prechecks are scoped to dimension, selected bars, column ratio and strong-column / weak-beam hierarchy only. **Full capacity/shear/flexure P-M-M member design remains unfinished.** Failed source footing shear cannot be overridden by an adopted design summary.

## Reproducibility
Run `python -m pytest -q`, `python scripts/check_public_safety.py`, and `python scripts/build_calculation_coverage.py --check`.
Latest verified CI and exact SHA are recorded in draft PR #4 after provider readback; do not record an assumed future CI success.
