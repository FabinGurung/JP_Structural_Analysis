# Post-Seq9: first-party Structural Analysis Report without E2K

**Status: candidate post-frozen Seq9 workstream. The immutable Seq9 SHA `f7c2f8ad7d06ec18b750835b311748b129f39a36` remains unchanged. These functions are elementary algebra, NOT an adopted NBC 105:2025 design module or professional approval.**

## Separation of authority

- **JP Structural Analysis:** first-party canonical model (PK/FK/units), numeric solver adapters, results, equation registry, checks, tests and analysis-run provenance.
- **JP Research & Development:** reusable LaTeX, document schema, report-rendering code and PDF layout in `templates/enterprise/structural-analysis-report/v0.1/`.
- **Google Drive / private runtime:** original architectural/geotechnical data, real model/attachments, project calculations and final reports.
- **GitHub Actions:** public-safe synthetic model tests, solver installation and numerical regression; no confidential projects.
- **GitHub Pages:** public-safe documentation and sanitized demonstration. **A7 is a read-only catalogue.**

## Main numerical pipeline

```text
First-party CAD/BIM + site/soil facts (PRIVATE)
  -> normalized model / schema / IDs / units / provenance
  -> model topology, loads and independent mass reconstruction
  -> pre-solve QA (no model drift, fail-closed)
  -> OpenSeesPy frame/shell as supported, modal, static, response spectrum
  -> independent PyNite / Frame3DD / XC / CalculiX comparisons (when implemented)
  -> code-edition-pinned seismic + RC/member/foundation checks
  -> normalized result/check IDs + figures + source manifest
  -> R&D LaTeX template -> draft PDF -> licensed engineer review
```

No E2K is required for the first-party model. The existing E2K importer is retained **solely as an optional legacy audit/benchmark adapter**. The report supplied by the user explicitly describes ETABS frames, SAFE foundations and Excel slab/stair worksheets. That precedent alone does not prove E2K use.

## Mathematics and implementation status

| Calculation | Formula or numerical task | Status |
|---|---|---|
| Frame statics | `K u = F`, local/global stiffness, reactions | Bounded OpenSees 3D frame and native stiffness already implemented; releases/offsets/shell parity remain gaps |
| Vibration modes | `K phi = lambda M phi`, `T=2*pi/sqrt(lambda)` | Bounded OpenSees modal mass/participation at Seq9; independent benchmarks incomplete |
| Period candidate | `T = a*kt*H**p` | New first-party **parameterized algebra only**; authority-supplied code coefficients needed |
| Elastic/ULS/SLS coefficients | `C = Ch*Z*I`; `Cu=C/(R*OmegaU)`; `Cs=s*C/OmegaS` | New generic arithmetic helper; normative edition/references must be separately verified |
| Floor forces | `Fi = V*Wi*hi**k / sum(Wj*hj**k)` | New unit-neutral helper with conservation test; valid mass-source/diaphragm physics still needed |
| Spectrum | `Sa(T)`, modal response and combination | Seq9 SRSS and equal-damping CQC in canonical_seismic.py |
| Drift | `(ui-u(i-1))/hi` | Bounded explicit response points; accepted limits need governed code version |
| Torsion | opposite-edge displacement checks, accidental eccentricity | Seq9 probes ONLY; code irregularity acceptance NOT implemented |
| RC beam/column | P-M interaction, flexure/shear/torsion/joints/detailing | **NOT IMPLEMENTED / DESIGN HOLD** |
| Slab/footing/stair | plate FE, punching, bearing/settlement, stairs and bar details | **NOT IMPLEMENTED / DESIGN HOLD** |

The new `native/equivalent_lateral.py` functions accept **all** empirical coefficients and seismic distribution bounds from a verified external code registry. No hardcoded claim that private report constants are the actual current Nepal code. Synthetic unit tests verify arithmetic, equilibrium and rejection of bad inputs, not regulatory compliance.

## Top five engines (one primary, four independent candidates)

1. OpenSeesPy — primary structural earthquake solver; https://openseespydoc.readthedocs.io/en/latest/ (commercial redistribution license review required).
2. PyNite — elastic structural/modal/plate benchmark; https://github.com/JWock82/PyNite (MIT).
3. Frame3DD — separate frame static/modal solver; https://github.com/hpgavin/frame3dd (GPL).
4. XC — broader civil structural FE; https://github.com/xcfem/xc (GPL).
5. CalculiX — independent shell/solid/local FE; https://github.com/Dhondtguido/CalculiX (GPL).

Only OpenSees adapter plus limited native kernels currently exist. The four other adapters are registry stubs, **NOT implemented or validated**. External solver executables should be installed/version-pinned as dependencies, not copied wholesale into Git; observe upstream licensing. Do not force equivalence between incomparable elements or modeling assumptions.

## Mandatory future completion gates

1. Author standalone JSON/SQL model without E2K, with true geometry, line/area loads, diaphragms, mass and boundary conditions.
2. Add compatible shells, releases/offsets, mass reconstruction and modal/force independent comparison.
3. Freeze current applicable NBC/IS code editions and verify every adopted factor, threshold and analysis acceptance independently.
4. Implement and benchmark column, beam, slab, footing, stair and detailing modules. A numerical frame solution alone cannot design the building.
5. Generate and audit **all** source-report section families and figures from typed data, not screenshots.
6. Private pilot: compare against source calculations and alternative hand/FE checks, then receive qualified engineering signoff. CI passing != construction permit.

**Source privacy:** no uploaded report text/tables/images/identifiable fields or client model can be committed into public GitHub.
