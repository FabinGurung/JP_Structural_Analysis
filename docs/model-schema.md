# Canonical model policy

Stable IDs are mandatory; display labels and source labels are not primary keys.

Core families include PROJECT, UNITS, DESIGN_BASIS, CODE_REFERENCE, GRID, STOREY, NODE, FRAME_MEMBER, SHELL_ELEMENT, MATERIAL, SECTION, SUPPORT, CONSTRAINT, DIAPHRAGM, END_RELEASE, RIGID_OFFSET, STIFFNESS_MODIFIER, LOAD_PATTERN, LOAD_CASE, LOAD_COMBINATION, MASS_SOURCE, NODAL_MASS, JOINT_LOAD, FRAME_LOAD, AREA_LOAD, RESPONSE_SPECTRUM, MODAL_CASE, PDELTA_CASE, ANALYSIS_CASE, RESULT_SET, VALIDATION_RUN, REPORT_SECTION and SOURCE_REFERENCE.

## E2K canonical bridge

`jp_structural.normalization.canonical.canonicalize_e2k_model()` converts the existing source-preserving legacy E2K payload into canonical schema `0.1`.

The bridge:

- generates deterministic opaque IDs for canonical entities;
- preserves source labels separately from canonical IDs;
- maps storeys, nodes, frame/shell objects, materials, sections, supports, diaphragms, load patterns/cases/combinations and mass-source factors when the legacy parser exposes enough meaning;
- retains source hashes, source QA warnings and explicit translation-scope limitations;
- never invents releases, rigid offsets, local-axis rotations, response spectra, P-Delta definitions, shell-mesh adequacy, explicit nodal mass or load-combination components that were not parsed from source evidence.

A canonical model is therefore a normalized representation, not an engineering approval. Missing source semantics remain unresolved and are expected to be caught by pre-solve QA.

## Phase-B solver fields

Canonical OpenSees Phase B uses explicit solver-ready fields rather than silently deriving engineering meaning.

For modal execution:

- `units.mass` and `units.time` must be explicit;
- `nodal_masses[]` identifies `node_id` plus `mx/my/mz` and optional `mrx/mry/mrz`;
- a rigid diaphragm must explicitly state `constraint_type: "RIGID"`, `perpendicular_axis`, `retained_node_id`, and `node_ids`;
- `frame_members[]` must resolve to supported elastic frame sections/materials;
- non-axis-aligned members require explicit local-axis meaning before translation;
- shell elements, end releases and rigid offsets are not silently approximated by the bounded Phase-B adapter.

Legacy `mass_source.load_factors` remains source meaning/provenance. It is not itself a solver-ready nodal-mass distribution.
