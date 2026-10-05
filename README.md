# JP Structural Analysis

**Public showcase:** https://fabingurung.github.io/JP_Structural_Analysis/

Governed structural-analysis and Structural Analysis Report (SAR) engine with
OpenSees/OpenSeesPy as the primary computational engine, explicit source
provenance, normalized model contracts, fail-closed QA, transparent benchmarks,
validation records, and reproducible reporting.

## Development source

The current governed engine/source branch is:

`engine/opensees-sar-v0.1`

The `main` branch is intentionally a lightweight Pages-dispatch and navigation
surface. Engine/product source has **not** been merged into main as a V0.1
release.

## Public demo

The deployed showcase builds the sanitized two-span benchmark during GitHub
Actions and publishes:

- interactive project/showcase landing page
- sanitized Structural Analysis Report
- analysis results JSON
- validation results JSON
- report manifest

The benchmark preserves its known support-reaction reconciliation discrepancy
as `ENGINEER_REVIEW_REQUIRED`; a successful CI/deployment is not represented
as professional engineering approval.

[Open the live showcase](https://fabingurung.github.io/JP_Structural_Analysis/) ·
[Browse the engine branch](https://github.com/FabinGurung/JP_Structural_Analysis/tree/engine/opensees-sar-v0.1)
