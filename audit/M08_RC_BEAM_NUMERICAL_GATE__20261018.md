# Post-Seq9 M08 beam calculation gate — October 18, 2026

## Code and source
BIS currently lists IS 456:2000 as the published standard (reviewed 2025). Official Amendment No. 6 June 2024: https://www.services.bis.gov.in/tmp/CED19013804_03062024_1.pdf ; reviewed modifications do not change section 26.5.1.1/5/6, clause 38.1, Table 19/20 or clause 40.4; torsion clause 41.3.2 changed and remains excluded.
Government-hosted full text: https://wriddodoti.gov.np/uploads/blog/20230331071217_IS-456-with-all-ammendments.pdf .
PRIVATE sources: consult Drive local source registry; original private Drive file IDs are not published.

## Delivered executable engine (PARTIAL M08)
- `src/jp_structural/solvers/native/rc_beam_strength.py`: rectangular singly reinforced positive moment flexure, 0.36/0.42 stress block, neutral-axis limit by steel grade, minimum/maximum steel, inverse area sizing via bounded bisection, explicit kN/mm/MPa units. Reject over-reinforced and unsafe numerical sections.
- Vertical stirrup preliminary shear from factored Vu, source Table 19 percentage-versus-grade, source Table 20 concrete max shear, 26.5.1.5 maximum stirrup spacing and 26.5.1.6 minimum steel. New Table19 adapter uses the lower-or-equal steel-percentage row to avoid unconservative interpolation.
- Earlier external manual tau_c route returns HOLD unless real source lookup was machine-validated.
- `tests/native/test_rc_beam_strength.py` covers independent equation fixtures, min/max and invalid inputs, table row lookups, fail-closed unsafe examples, inverse steel sizing.

## Remaining critical gates
1. Verify actual source report beam factored force combinations and member mappings in private Drive.
2. Apply NBC105:2025 capacity-design shear and special ductile beam/joint detailing in addition to the base flexure/shear checks.
3. Add negative moment, top reinforcement, doubly/flanged beams, torsion, bar development, lap, curtailment, serviceability and constructability.
4. Independently benchmark against worked RC examples and at least one existing report without copying historical UNSAFE worksheet PASS states.
5. Only approved full-design outputs may feed a project-specific SAR; current public Pages snapshot is older and not automatically advanced.

## Governance
Frozen Seq9 unchanged. Development PR #4 remains DRAFT and is not merged. Site is NOT deployed from this new M08 branch. No private engineering model/binary is published.
