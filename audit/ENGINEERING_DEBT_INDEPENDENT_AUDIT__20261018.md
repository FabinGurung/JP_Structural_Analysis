# A9 / JP Structural Analysis — independent debt audit and verified closeout

**Audit:** 2026-10-18 (Nepal). **Base:** `5702cf1b3fffce01908abc1f5fbac10595261355` on `feature/post-seq9-first-party-no-e2k-20261015`. **Seq9 frozen:** `f7c2f8ad7d06ec18b750835b311748b129f39a36`.

## 1. What was actually closed
- Google Drive source-of-truth Local Library `SyncState`: Seq9 **9/9** SYNCED; `SyncDelivery`: reciprocal ACK 9; Main `LocalLibraryRegistry`: **9/9 VERIFIED_SYNCED**. Seq9 historical ledger debt **NONE**. Prior GitHub Seq9 POST file was an in-progress snapshot; the later Drive terminal closure is authoritative and should not be falsified or rewritten.
- Corrected false torsion rotation from a longitudinal two-node gradient: probes now require the excitation-transverse lever arm, node-geometric agreement and correct signed global Rz equation. Y excitation with X-separated nodes supported; X excitation with X-separated nodes rejected.
- Orthogonal spectral response envelopes now require matching numerical model hashes and units, not merely a matching display model ID.
- Before model building, an assembled gravity/mass result is independently checked for source identities, weight conservation, nodal masses, gravity, storey centre of mass, source/FE coordinate agreement, and inadmissible added rotational inertia.
- NBC 105:2025 modal participation screening requires a declared X/Y direction, not a mixed-axis scalar.
- Added Annex A beam reinforcement-face / spacing numerical guards, separate from completed capacity-design shear.
- MDM original stored reactions are **internally contradictory** with their own final member moments (even though whole-system 60kN global force equilibrium is satisfied). AB stored 38.75/21.25 vs independently implied 33.75/26.25 kN; BC stored 1.25/-1.25 vs implied 3.75/-3.75 kN. The OpenSees reactions align with the member-moment-implied results. Original data preserved, state remains FAIL pending source decision.

## 2. Source basis cross-check
- Government Nepal NBC 105:2025: https://ebps.kathmandu.gov.np/UploadFiles/NBC_105_2025_Sesmic_Design.pdf . §5.2 seismic weight, §5.5.1/5.5.3 design displacement/drift, §5.6 eccentricity, §7.3 mass participation and Annex A §4.1 mandatory RC beam limits.
- IS 456:2000: https://wriddodoti.gov.np/uploads/blog/20230331071217_IS-456-with-all-ammendments.pdf . Published BIS code, not yet replaced by proposed fifth revision as of this audit. Amendment No.6: https://www.services.bis.gov.in/tmp/CED19013804_03062024_1.pdf , Gazette establishment June 2024.
- IS 13920:2016 remains listed with its 2017/2020 amendments in BIS. **Applicability of Indian detailing provisions never overrides the Nepal code basis automatically.**

## 3. Unresolved design and evidence debt
Machine-readable details in `registry/engineering-debt-audit.v0.1.json`; distinguish:
- Original benchmark source-data contradiction (P0, source owner/authority).
- Private project-specific model geometry, loads, geotechnics/zone, accepted boundary conditions, and verified actual nonlinear/FE response demand (P0).
- RC M08 complete seismic beam shear/torsion/bar detailing; M09 column biaxial interaction; M10 joint and M12 footings; M11 slab, M13 Winkler, M14 stairs (P0/P1 engineering backlog).
- Missing-mass correction, applied accidental torsion and full seismic irregularity checks (P1).
- Independent real-building report reproduction and signoff (P1).
- Prior public Git audit files contain some private Google Drive IDs (metadata pointers); public history cannot be erased simply by editing current files. Privacy classification/authorization review required if history rewriting contemplated.
- Pages dispatcher intentionally pinned to an older *tested* branch snapshot and must remain so until the engineering release is approved.

## 4. Acceptance boundary
GitHub Actions success, static public-data scan, synthetic sample artifacts and math regression tests are **necessary but not sufficient** for a project Structural Analysis Report approval. Do not set `engineering_approval=true`, `full_RC_design_complete=true` or release M08/M09 purely because CI passes. No user input needed to keep implementing bounded mathematical modules, but actual building/soil evidence and signoff remain separate gates.

**Governed outputs:** development branch only; no Seq10 transaction, no frozen release mutation, no current public Pages mutation. Updated draft PR #4 is the traceable work record.
