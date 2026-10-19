# SP16:1980 Chart 31 — two direct original-scan spot checks

## Immutable provenance
Original **SP16:1980** (Design Aids to IS456:1978), 255 PDF physical pages,
source SHA256 `d2a6246a5dc7504568f4e55f310dd4be9d925fb1a8b04b6d7f5132c93f66c76e`.
Original hosted in governed private Google Drive; source PDF and all 255 page
images are **not** published in GitHub.

**Original Chart 31** is printed page 116 / physical PDF page 139, Fe415,
d'/D=0.05, equal reinforcement on two faces. Independent physical-source
manual graph readings use a large ±0.010 (absolute dimensionless normalized
moment) band to acknowledge graph scan/line identification uncertainty.
Source readings are frozen in `registry/sp16_chart31_visual_samples.v0.1.json`,
distinct from the solver's calculated outputs.

The two physical-chart spot estimates:
- Pu/(fck bD) = 0.25; Mu/(fck bD²) ≈ 0.082 ± 0.010
- Pu/(fck bD) = 0.44; Mu/(fck bD²) ≈ 0.030 ± 0.010
Both near independently published worked example values ≈0.081575, 0.028979.

The source chart plots **p/fck = 0.02**, corresponding to 0.4% steel for M20.
One synthetic 400 × 500 mm, 4-bar two-face section is used, with d' 25 mm,
four equal 200 mm² bars. This is **not a building member**.

Run `python scripts/build_sp16_chart31_spotcheck.py --output build/sp16_chart31_spotcheck.json`.
GitHub CI runs `tests/native/test_sp16_chart31_reference.py` and saves
the numerical evidence. Any difference outside the declared scan tolerance
FAILS the build; no alleged exact original chart ordinate claim is made.

## Legacy to current-code decision register

| Topic | Source | Current action | Gate |
|---|---|---|---|
| Concrete compressive block | SP16:1980 printed pages 4, 100–102 | Align numerical peak 0.446fck and .0035 strain | Bounded numeric check |
| Fe415/Fe500 steel | SP16 Table A, printed p6, PDF p29 | Direct 12-value regression against numerical steel knots | Verified at knot values |
| Column interaction | SP16 Chart31, printed p116, PDF p139 | Two coarse direct plotted point cross-checks + external hand examples | Spot agreement only |
| Steel displacement | SP16 printed p102 notes chart's approximation using M20 reference | Current section subtracts actual local concrete stress | Do not require exact chart equality |
| Edition transition | SP16 based on IS456:1978; kernel cites IS456:2000 | Preserve edition fields, explicitly record unresolved changed clauses | **Full equivalence not established** |
| Seismic/ductility | NBC105:2025 | Model load-case/signed FE checks and separate ductile detailing | **Project acceptance HOLD** |

## Engineering safety state

Two successful scans are not all SP16 curves. A chart-derived historical
stress-resultant comparison cannot substitute for modern NBC ductile detailing,
slenderness, second-order P–Delta, member longitudinal bar anchorage, or
project model/source validation. Formal design/signoff remains OPEN.

This record avoids treating missing chart vectorization as a reason to stop
independent regression development and allows additional source-labeled
chart points/grades/shapes to be added incrementally.
