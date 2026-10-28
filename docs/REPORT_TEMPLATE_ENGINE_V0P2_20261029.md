# JP Structural Analysis — report-template engine v0.2

## Purpose and authority

The template is **engine-first**: it derives its seven-chapter report presentation order from the supplied G+1.5 revised SAR source, while calculations accept a separately versioned, source-labelled input case. The original report is a **test precedent**; the engine is not tied to its particular grid, soil, floor layouts or structural model.

- Original source PDF (private Drive): `1TpWUmOdrcQqOpkN6qvmhZ12KrYaNABBM`, SHA-256 `f122904444a2e2f75230d9d4e41da0093d050da25c6e8140c86d466b7e37cc52`.
- Exact metadata and document fragment references are stored in the existing Chapter 1–6 registries. No new private drawings or original PDF contents are copied to this public repository.
- Report TOC and source-ordered headings: `registry/report-template-contract.v0.2.json`.
- Module-level status (M01–M16/S17–S18): `registry/report-calculation-coverage.v0.1.json`.
- Codes and clause discovery: official [NBC 105:2025](https://ebps.kathmandu.gov.np/UploadFiles/NBC_105_2025_Sesmic_Design.pdf), government-hosted [IS 456:2000 with amendments](https://wriddodoti.gov.np/uploads/blog/20230331071217_IS-456-with-all-ammendments.pdf) and [DUDBC code index](https://dudbc.gov.np/pages/building-code/). Identifying a code reference is **not** proof that a corresponding design check is implemented or independently accepted.

## Runnable contract

The package is deterministic and reads a single `jp.structural.template.input.v0.2` case. It requires an explicit source/document class, seven per-domain provenance records and a deliberate source unsafe-flag list. It rejects malformed/nonfinite values, duplicate candidate dimensions, missing floor weights, nonmonotonic storey elevations, unspecified footing loads not including foundation/backfill weight and unsupported material grades. Every output preserves a false engineer-approval flag.

```sh
python -m pip install -e ".[test,opensees]"
python scripts/build_structural_template_engine.py \
  --input examples/sanitized/template_engine_independent.v0.2.json \
  --output-dir site/reports
python scripts/build_structural_template_engine.py \
  --input examples/sanitized/template_engine_f3_conditional.v0.2.json \
  --output-dir build/template_source_f3 \
  --prefix template-engine-f3-conditional
python -m pytest -q tests/test_structural_template_engine.py
```

These runs write `<prefix>.json`, `<prefix>.md`, `<prefix>.html`, `<prefix>-footing-candidates.csv`, and `<prefix>-manifest.json` containing SHA-256 checksums of the four outputs. The independent case is suitable for public GitHub Pages; the conditional original-source example is a separate CI artifact, not a reconstructed original building approval.

## Implemented numerical scope in this runner

| Module | Reused or added calculation | Explicit boundary |
|---|---|---|
| M03 | NBC 105:2025 equivalent-static floor-force distribution and force sum | Caller supplies C_d, T and storey weights; no site hazard or FE model |
| M08 | IS 456:2000 rectangular singly reinforced positive flexure | No torsion, doubly reinforced case, anchorage or complete ductile detailing |
| M09 | Short RC-column biaxial interaction | Uniaxial interaction capacities independently supplied by caller; no member model mapping |
| M10 | NBC 105:2025 Annex A joint shear | No complete anchorage or confinement design |
| M11 | One-way simply supported slab strip flexure | No two-way moment transfer, deflection or actual continuity |
| M12 | 3 plan x 4 depth x 2 bar-spacing centered isolated footing scenarios; bearing, flexure, one-way, punching numerical checks | Soil, settlement, eccentricity, detailing and site actions assumed; conditional precheck is not accepted design |
| M14 | Simply supported stair strip flexure | Horizontal-equivalent uniform load assumed, not independently derived inclined waist/stair geometry |

The underlying repository already supports additional bounded FE, modal, load-combination and member kernels. This orchestrator **does not pretend to have integrated them**. In the TOC each module still reports its current implementation/verification gap.

## F3 source gate

The original revised worksheet says **NOT SAFE IN ONE WAY SHEAR**. The F3 fixture explicitly retains that statement. Its 2100 mm plan, 450 mm thickness, 600 kN worksheet load and 160 kPa listed SBC are source-reported, but the modeled 360 mm square column, 50 mm cover and 1.5 x 600 ultimate load hypothesis are provisional. They are not an authenticated F3 design reaction, governing code combination, footing drawing or geotechnical bearing pressure.

A numerically passing *alternative hypothetical candidate* is neither an F3 replacement nor physical engineering approval. Original Gate20 source-acceptance obligations remain open until authentic source evidence and qualified independent review establish closure.

## Submission preparation and remaining engine work

The engine emits a seven-item NOT ACCEPTED checklist: source/drawing register, site/use/soil data, validated model/load/mass fingerprint, full ULS/SLS signed actions, complete RC/foundation detailing, independent code/numerical QA and professional/authority review.

Next implementation steps, without requiring a particular building's source: 

1. Make the canonical-case schema accept arbitrary verified node/member/area/load data, and connect it to a real full-building OpenSees analysis with signed concurrent end-force combinations.
2. Bring full NBC 105:2025 ESM/MRSM, drift, torsion, accidental eccentricity, P-Delta, mass irregularity, and distinct ULS/SLS design into the template orchestrator.
3. Complete actual RC beam shear/torsion/detailing, axial-biaxial column capacities, joint confinement and bar development, slabs and stairs from real boundary/load models, and isolated/combined footing settlement/eccentric contact checks.
4. Finish wind, raft/subgrade, special/equipment actions where appropriate; add model-to-source independent benchmarks and permit/jurisdiction-specific evidence adapters.
5. Add full issued-for-review/issued-for-construction certification workflow only after source-specific engineering review. Do not create fictitious stamps, signatures, approvals or passing project acceptance flags.

This is a **functional but partial design template engine**, not a finished SAP2000/ETABS replacement or complete government submission.
