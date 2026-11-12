# R6.19 — Native connectivity and footing evidence gate (development only)

**Parent implementation:** R6.18 `a754d2cc2306ab87541adeb57ffefa63c5551cf4`.
**State:** software/evidence work in progress; not engineering approval, not a release.

## Purpose

The original ETABS21 ULS/SLS E2K input fingerprints are the governing
registered sources. The R6.17 graph and R6.18 numerical FE study do **not**
provide authenticated ETABS21 generated analysis joint IDs, constraints,
joint-to-shell ties, or actual footing correspondences.

The research solver has 165 structural frame segments and 103 admitted
source-graph-connected shells. Twelve other shells remain excluded. Of 27
declared base restraint IDs, 21 are associated with bounded research reactions.
Those signed six-axis research reactions are *not* final design loads.

R6.19 provides an explicit native-export contract and refuses to clear
source-to-FE connection/footing acceptance by geometric proximity. An
untrusted or incomplete export is rejected. A topologically connected exported
frame-to-original-base path is labelled **candidate for engineering review**,
never accepted as an engineered support, even if the exported path is valid.

## Native export contract (private input only)

Pass a privately handled JSON file with schema
`jp.structural.native_etabs21_topology_export.v0.1`.
It must declare:

- `governing_source_sha256` with the exact ULS and SLS original E2K source
  fingerprints, `source_software: ETABS21`, `length_unit: mm`, an original
  `export_file_sha256`, `export_method`, and `source_receipt_ref`.
- `analysis_joints`: immutable native analysis joint IDs and finite coordinates.
- `original_node_to_analysis_joint`: **story:pointID** to native joint IDs,
  each with its own original export-record citation.
- `explicit_native_joint_merges`: optional exact lists of intentional source
  identities consolidated into one native joint, with the original exported
  merge record. Coordinates alone never authorize this operation.
- `native_element_edges`: native joint pairs of type FRAME, SHELL or
  EXPORTED_CONSTRAINT, each citing the native record and original source
  object. The constraint kind requires a separate native constraint citation.
- `native_base_restraints`: each original base source point linked to
  an actual analysis joint with an original exported restraint record.
- `native_shell_joint_maps`: source shell key, four or more native analysis
  joints, correspondence to each original shell corner identity, and original
  native mesh/area export citation.

All connectivity is traversed through explicit native exported edges.
Finding a mapped fixed base requires at least one actual exported FRAME edge.
The validator does **not** accept a shell/corner merely because coordinates
are close, nor assume that a 2×2/4×4 research node is an ETABS native node.

**No native E2K, private drawing, ETABS export, private receipt or raw source
reactions should be committed to this public GitHub repository.**

## Generate the safe report

First run the existing R6.17 and R6.18 derived artifact builders using the
governed original source register. With those outputs present:

```bash
python scripts/build_r6p19_native_connection_readiness.py
pytest -q tests/test_r6p19_native_support_evidence.py
```

An authenticated export may be supplied only from a trusted private runtime
via `--native-export /secure/path/native-analysis-topology.json`. The builder
serializes only the derived, no-approval summary; it never writes the native
input itself into GitHub Pages. Do not include a private absolute path in
the generated report or public action logs.

## Open engineering gates — remain open until genuine source evidence

1. Resolve the **12 original unsupported shell identities** against the real
   native analysis mesh and original beam/column-to-shell support transfers.
2. Investigate the source-frame endpoint / shell grid **hanging-node encounters**
   by native joint and constraint output, not by rounding or coordinate ties.
3. Map **all 27 declared** original base source points and the currently
   **21 research reaction nodes** to the actual footing or mat schedule. A
   shared footing requires explicit multiple-node correspondence, not a guess.
4. Reconcile full actual mass source, diaphragm, source load assignments,
   torsion eccentricity, seismic/mode combinations, and complete governing
   ULS/SLS signed member demand envelopes.
5. Perform geometry-specific NBC/IS applicable member, joint, reinforcement,
   one-/two-way shear and foundation serviceability/strength checks.
   Historical footing **F3 NOT SAFE IN ONE WAY SHEAR** remains **FAIL** until
   independently validated redesign and matching governing demand evidence.

The native topology evidence gate is necessary but not sufficient for 3D FE
parity: source element releases/offsets, shell meshing, stiffness, mass,
boundary conditions and numerical convergence need separately checked.

## Release boundary

This is a research-branch increment only. The existing main/default bootstrap
and published Pages are not mutated. R6.19 produces an inspectable status and
regression tests; it does not perform the later **full independent QA** and
does not tag/release a milestone. Preserve engineer issue #7 as open.
