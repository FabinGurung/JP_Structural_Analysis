# A9 POST — Phase C combination and torsion / lane seq9

Date: 2026-10-15 NPT
Repository: FabinGurung/JP_Structural_Analysis
Governed branch: engine/opensees-sar-v0.1
Status at this GitHub POST: CODE_AND_CI_PASS; LOCAL_MAIN_TERMINAL_CLOSEOUT_PENDING

## Preserved PRE and predecessor
- Prior Seq8 FINAL_CLOSED_PASS at GitHub 67407b3a02d1475f143b10ea81be565435d5191e.
- Seq9 PRE: audit/PRE__PHASE_C_COMBINATION_TORSION_SEQ9__20261007.md.
- Seq9 Drive PRE history folder: 1v3zglGATHEV0D0KqD8XCpw-D7IJBhG2j.
- Seq9 PRE Local snapshot: 1Z5Mu7rs2et_-Ni6azh6lEi3vv_XjD9h64PfWXHVWDAc.
- Seq9 PRE Main snapshot: 1a3hNG4dDY5prdEGYDPxorc1kHEIrL2ReS6J_fJvOmXU.
- Seq9 PRE ReadFirst: 1hDL-6mp2rkj6z8dIV9F0uYNwAcHynVdAYa9xdRkNiMk.
- Local/Main last fully closed synchronization at POST preparation: 8/8 SYNCED / VERIFIED_SYNCED.

## Material changes and provenance
Seq9 source before resumption: 740117cfee14930566e0d1e37d3d6dbf7154c1a3.
- Bounded equal-damping CQC coefficients and modal superposition, selected explicitly against SRSS.
- Explicit two-node, same-storey torsional rotation probes using caller-supplied separation.
- Orthogonal X/Y/Z response-envelope helper with caller-supplied factor and no code-specific inference.
- 19a72e44e993df1a3e322a775603904509f99442: methodology reconciled with actual code.
- f347ff2ec0fffe0ca5d464f86d9ec8612517170b: additional CQC symmetry and negative mapping tests.
- 729bea9fa8f89568c056bd608d34eef9ff64a9e6: changelog material-state update.
- c286122ecd976333f9feec2ffcbf1cb58a352747: durable Seq9 open-work checkpoint.
- Compare Seq8 POST to latest material checkpoint: ahead by 8 commits, no behind divergence. Seven bounded changed paths in code, tests, documents, audit.

## Exact provider-verified GitHub Actions evidence
- CI workflow: structural-engine-ci (.github/workflows/ci.yml).
- Trigger: push.
- Run ID 38584464318; job ID 115922620169.
- Checked HEAD SHA: c286122ecd976333f9feec2ffcbf1cb58a352747.
- Run: COMPLETED / SUCCESS; job test: COMPLETED / SUCCESS.
- Job log: 36 passed in 0.81s.
- Public-data safety scan: PASS.
- Sanitized SAR build: PASS.
- Sanitized SAR artifact upload: PASS.
- Artifact name: sanitized-mdm-two-span-sar.
- Artifact ID: 11903524443.
- Size: 8,814 bytes.
- SHA256: 7e6bd7d59fe8bd8ec6be8678a27b0ee17a9b31d4eb87bb0c64d679397150dcd7.
- Provider run URL: https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/38584464318.

## Engineering/release exclusions
- No accidental-eccentricity loading, dedicated torsional-irregularity acceptance or Nepal-code numerical inference.
- No source-ETABS equivalence, independent solver validation, RC design or government/professional approval.
- SAMPLE_MDM_001 support-reaction discrepancy remains unresolved and not admitted as PASS.
- No private client drawing, model, report or credential was added.
- Main was not merged and Engine V0.1 remains IN_PROGRESS / NOT RELEASED.

## Remaining A9 boundary
This POST is GitHub code and provider CI evidence only.
DO NOT mark Seq9 FINAL_CLOSED_PASS until the exact POST commit CI, Seq9 LocalCatalog/LocalEdges/ChangeLog, bounded Main ArtifactRegistry/ArtifactEdges/LocalLibraryRegistry/RunLog, reciprocal ACK, finite Local/Main/ReadFirst POST snapshots and independent provider readbacks all pass.
No Seq10 is created for Seq9 bookkeeping.
