# R6.16 — First-party structural report reproducibility and acceptance audit

## Three separate meanings of "reproduce"

1. **Software repeatability**: Given a deterministic model version and specified assumptions, GitHub Actions can execute the first-party Python/OpenSees engine and generate consistent numerical reports, diagrams, data and provenance manifests. This works within bounded scope.
2. **Governing source/model equivalence**: The independently constructed model must represent the complete selected ETABS21 ULS and SLS source semantics, including actual analysis joints, shell/frame compatibility, real boundary conditions, stiffness, releases, offsets, masses, load transformations and load combinations. Not established. 12 of 115 source shell objects lack a source-graph base path and remain excluded from the present coarse research trial.
3. **Complete design/report reproduction**: Every historical report calculation, seismic and serviceability result, member/footing design and appropriate code check is reproduced with independent benchmarks, source input traceability and qualified professional engineering acceptance. Not achieved; historical PDF mixes ETABS20 references with ETABS21 excerpts, and the original F3 remains NOT SAFE IN ONE WAY SHEAR.

Do **not** interpret green software tests as (2) or (3).

## Current source chain

- Private Google Drive: original governing ULS/SLS ETABS21 E2K revisions, old report PDF, geotechnical and original construction drawings. Drive is an evidence authority; no authorization is inferred to publish raw source or change it.
- GitHub repository: private-source-derived, versioned/public-safe input snapshot and calculation functions.
- GitHub Actions: pinned source SHA, Python/OpenSees engine, regression checks and browser tests. The current main Pages workflow does not fetch E2K from Drive live; it rebuilds the pinned GitHub snapshot.
- GitHub Pages: read-only public results, diagrams, source limitations, report-level claims and QA links. It does not run ETABS or update its own model from Drive.
- Historical PDF: reported values to cross-check, NOT a current analysis solver output from the selected E2K pair.

Authoritative versioned implementation coverage is registry/report-calculation-coverage.v0.1.json, currently 18 requirements: 2 IMPLEMENTED_BOUNDED, 11 PARTIAL, 4 MISSING, 1 DRAFT_UNVALIDATED. These classifications are conservative and must be intentionally reviewed as new engine features arrive. A bounded solver feature does not automatically become project-verified.

## Independently verified work

- A real OpenSees Gate21 report executes 5 source-derived/hypothetical frame load cases and exports 825 signed member-end action records, with a SHA256 manifest, HTML, Markdown and CSV. That model deliberately lacks complete authentic slab/wall source loading, ETABS21 result parity, modal solution in that particular Gate21 run, P-Delta, full RCC design, and accepted footing demand.
- R6.10 analyzes only 103 originally source-connected shell objects in a nonconforming coarse FE trial; 12 original unsupported shells are withheld.
- R6.12 checks arithmetic and contradictions in the historical PDF, not original ETABS21 solver equilibrium.
- R6.13 publishes 165 source-member bounded actions with independent provenance.
- R6.14 reconciles 25 four-full-beam-edge geometric rectangles only. R6.15 measures all 77 incomplete-perimeter source slabs and 308 edges; neither stage promotes physical supports or modifies FE member actions.
- Original F3 one-way shear verdict remains unsafe throughout.

## Staged plan to a true complete report

P0-1 **Canonical building model**: Draw/approve a first-party complete XYZ graph with joints, edges, shell mesh, column-footing anchors, support degrees of freedom, diaphragm master/slave logic and openings. Missing source evidence means an *assumed alternate design model* can be analyzed but cannot be claimed identical to ETABS21. Provide explicit geometry/building drawings for engineer review; do not infer a fixed slab corner solely from coincidence.

P0-2 **Independent source load/mass book**: material grades, concrete and steel densities, original wall and roof loads, live load by actual use, soil profile and true source load patterns. Reconcile mass/weight per storey and global equilibrium, retaining the difference from historical 6831.9109 kN instead of calibrating away the residual.

P0-3 **Whole-model actions and seismic**: source ULS/SLS stiffness, reliable shell-to-beam load paths, modal and spectrum checks under Nepal's controlling NBC105:2025 edition, full torsion/accidental eccentricity, P-Delta, signed load combinations, design envelopes, serviceability and wind screening.

P0-4 **Concrete and foundation design**: complete geometry, actual material and steel detailing, beam flexure/shear/torsion, column P-M-M and slenderness, ductile joints, slab flexure/serviceability, stairs, footings including bearing/one-way shear/punching, and structural load-path continuity. Solve original F3 adverse condition; do not replace original result with an assumed "SAFE" value.

P0-5 **Numerical and professional validation**: independent benchmarks for gravity, modal, shear-force distributions, member demand and footing reactions; convergence and model sensitivity; code clause/edition provenance; signed engineering review.

P1-6 **Report and governed publishing**: report section-by-section typed-data source map, full numbered equations/figures, calculations, bar schedules and drawing source, approved complete PDF export, immutable run manifest and explicit GDrive revision synchronization or reviewed intake queue. Keep original Drive authority and GitHub derived public-safe data split.

## No data-hiding or acceptance shortcuts

- Generated-joint coordinates, original mesh and reactions unavailable ≠ zero, and missing E2K outputs do not prevent a correctly labelled first-party *alternate research model*.
- R6.14/R6.15 geometric proximity cannot establish physical slab support, mass or load transfer.
- Bounded example analyses and report arithmetic cannot become "ETABS equivalent" through similar base shear or story-weight totals.
- GitHub Pages publication verified by GitHub's live readback confirms delivery of a pinned artifact, not field/site validation.
- Green browser tests on simulated viewport sizes are not physical-device UX certification.
- Source credentials and private original files stay in Drive; no live publisher to Drive exists in the current workflow.

**Engineering HOLD remains** until a qualified structural engineer approves and signs the full model and checks.
