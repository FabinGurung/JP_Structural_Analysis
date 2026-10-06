# A9 PRE — Phase C modal/directional combination + torsional response / lane seq9

Date: 2026-10-07 NPT
Repository: FabinGurung/JP_Structural_Analysis
Branch: engine/opensees-sar-v0.1

## Prior closed boundary

- Seq8 bounded response-spectrum core: FINAL_CLOSED_PASS
- prior engine head / Seq8 POST: 67407b3a02d1475f143b10ea81be565435d5191e
- structural Local/Main Library: 8/8 SYNCED / VERIFIED_SYNCED
- A9 debt through Seq8: NONE
- broader Phase C: IN_PROGRESS / NOT COMPLETE
- Engine V0.1: IN_PROGRESS / NOT RELEASED
- main remains unmerged

## Snapshot-before-edit evidence

- Seq9 history folder: 1v3zglGATHEV0D0KqD8XCpw-D7IJBhG2j
- PRE Local Library: 1Z5Mu7rs2et_-Ni6azh6lEi3vv_XjD9h64PfWXHVWDAc
- PRE Main Library: 1a3hNG4dDY5prdEGYDPxorc1kHEIrL2ReS6J_fJvOmXU
- PRE Local ReadFirst: 1hDL-6mp2rkj6z8dIV9F0uYNwAcHynVdAYa9xdRkNiMk

All PRE objects were provider-read before material mutation.

## Bounded Seq9 scope

This sequence may extend the public-safe canonical Phase-C response-spectrum core only with:

- equal-damping Complete Quadratic Combination (CQC) modal correlation/combination, using the explicit spectrum damping ratio;
- deterministic modal-combination selection between existing SRSS and the new bounded CQC path;
- explicit two-node storey torsional-rotation response, where node pair and positive lever-arm/separation are provided by the caller;
- explicit orthogonal-direction envelope combination using a caller-supplied factor, without hard-coding a code-specific ratio;
- deterministic serialization and sanitized regression tests;
- documentation of implementation and limitations.

## Fail-closed exclusions

This sequence does NOT authorize or claim:

- accidental-eccentricity loading/execution;
- a hard-coded 100/30, 100/40 or other orthogonal factor without governed caller input;
- torsional-irregularity acceptance limits unless separately supplied and governed;
- hard-coded Nepal-code numerical coefficients/limits;
- missing spectrum/damping/unit inference;
- private client evidence in the public repository;
- shell/end-release/rigid-offset equivalence;
- source-software ↔ OpenSees seismic equivalence;
- RC design, professional approval, V0.1 release or merge to main.

No Seq9 completion is claimed by this PRE.
