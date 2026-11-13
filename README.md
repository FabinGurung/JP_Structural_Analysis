# JP Structural Analysis

**Public showcase:** https://fabingurung.github.io/jp-structural-analysis/

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

[Open the live showcase](https://fabingurung.github.io/jp-structural-analysis/) ·
[Browse the engine branch](https://github.com/FabinGurung/JP_Structural_Analysis/tree/engine/opensees-sar-v0.1)

## Federated repository boundary — A7 is an index, not this product's template owner

**This repository owns** its domain-specific source, templates, workflows, documentation, tests and release history: OpenSees/OpenSeesPy structural-analysis code, model/benchmark contracts, SAR validation and engineer review states. The catalogue at [A7](https://github.com/FabinGurung/JP_A7_System_Registry_and_Knowledge_Graph) is only the **federated service directory / metadata index** of where repositories, websites, version pointers, statuses and cross-module relationships are found. A7 is **not** a parent codebase, shared template writer, or administrator of this module's content.

**Agent and automation rule:** Never create, update, synchronize or “repair” A7 code, policy, templates, catalogue records, READMEs, website or history as a side effect of work in this repository. An A7 modification requires a **separate task explicitly authorized by the user for A7**, with its own versioning and review. If an A7 listing appears stale, leave A7 unchanged and note a pending pointer correction **locally**. Resolve this repository's own live sources and approvals; do not duplicate its canonical domain files into A7. The CAD/AAD design-and-drawing template is owned by [CAD/AAD](https://github.com/FabinGurung/JP_Computer-Aided-Drawings/tree/main/governance/aad), never by A7. Existing independent domain and private-provider authorities still apply.



## R6.23 independently runnable multi-floor structural FE preview (development only)

The user-authorized R6.23 integration is available **on `main` as an isolated,
source-controlled numerical research component**, independently of the older
publication/Pages dispatcher:

- [R6.23 module and calculation documentation](r6p23/README.md)
- [Independent OpenSeesPy multistorey shell engine](r6p23/engine.py)
- [Source-safe command line report generator](r6p23/runner.py)
- [Numerical/geometry/manifest regression tests](r6p23/test_engine.py)
- [R6.23 standalone verification workflow](.github/workflows/r6p23-preview.yml)

It computes connected 3D ShellMITC4/beam/column systems over multiple rectangular
floors, actual shell openings, source-dependent gravity/line loads and both
flexible-shell / rigid in-plane diaphragm branches, with signed support and
member actions. It is a **synthetic, bounded research feature**, not an
accepted actual-building structural design, permit, full SAR engine release,
or professional approval. The previous F3 one-way-shear FAIL is unresolved.

Run `python -m r6p23.runner --reference --output-dir build/r6p23` after
installing `openseespy==3.8.0.0`; actual source-derived models, drawings
and reports must stay out of this public repository.

This integration **does not** merge/release the rest of the research branch,
repin Pages, change the canonical governed working branch, or tag V0.1.

## R6.23/R6.24 published independent OpenSees explorer

The separate R6.24 numerical/publishing QA passed and the existing GitHub
Pages workflow publishes a synthetic, source-hashed independent structural
shell/frame viewer at:

https://fabingurung.github.io/jp-structural-analysis/r6p23.html

The interface allows per-floor, per-case and per-diaphragm viewing of actual
OpenSees-solved beam and shell force components, base reactions and a 4x4
versus 8x8 mesh-sensitivity screen. It is based on the self-contained main
r6p23 package, checked out at the invoking commit; the historic pinned
full engine, existing report pages and navigation remain preserved.

Only synthetic calculations are published. Static Pages cannot run arbitrary
Python/OpenSees input from visitors, and this integration is NOT a certified
engineering design, project-specific SAR, full engine release or approval.
The original F3 one-way shear unsafe finding remains visible and unresolved.

## R6.24 governed software-preview milestone

- [Software-only R6.24 prerelease with Engineering HOLD](https://github.com/FabinGurung/jp-structural-analysis/releases/tag/r6.24-preview)
- [Consolidated R6.10–R6.24 milestone report and limitations](audit/R6P24_SOFTWARE_PREVIEW_MILESTONE_REPORT__20261113.md)
- [R6.24 release notes](audit/R6P24_SOFTWARE_PRERELEASE_NOTES__20261113.md)
- [One-shot verified release workflow](.github/workflows/r6p24-software-prerelease.yml)

The release tag freezes the tested source commit `4f3bacd7e32ce057fd6c8c3542d410747de40066`; subsequent audit/report/workflow commits do not rewrite that tag. A software prerelease is not a complete independent structural design, a project-specific accepted SAR, or professional/municipal approval. The original F3 one-way-shear adverse finding is preserved.
