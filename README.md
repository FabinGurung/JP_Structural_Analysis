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

## Federated repository boundary — A7 is an index, not this product's template owner

**This repository owns** its domain-specific source, templates, workflows, documentation, tests and release history: OpenSees/OpenSeesPy structural-analysis code, model/benchmark contracts, SAR validation and engineer review states. The catalogue at [A7](https://github.com/FabinGurung/JP_A7_System_Registry_and_Knowledge_Graph) is only the **federated service directory / metadata index** of where repositories, websites, version pointers, statuses and cross-module relationships are found. A7 is **not** a parent codebase, shared template writer, or administrator of this module's content.

**Agent and automation rule:** Never create, update, synchronize or “repair” A7 code, policy, templates, catalogue records, READMEs, website or history as a side effect of work in this repository. An A7 modification requires a **separate task explicitly authorized by the user for A7**, with its own versioning and review. If an A7 listing appears stale, leave A7 unchanged and note a pending pointer correction **locally**. Resolve this repository's own live sources and approvals; do not duplicate its canonical domain files into A7. The CAD/AAD design-and-drawing template is owned by [CAD/AAD](https://github.com/FabinGurung/JP_Computer-Aided-Drawings/tree/main/governance/aad), never by A7. Existing independent domain and private-provider authorities still apply.

