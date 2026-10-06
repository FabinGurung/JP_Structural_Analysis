# Changelog

## Unreleased — engine/opensees-sar-v0.1
- Established A9 bootstrap PRE on main.
- Created dedicated structural-engine development branch.
- Added governed repository, provenance, schema, QA and architecture foundation.
- Added deterministic legacy-E2K → canonical schema v0.1 bridge with stable IDs and source-preserving provenance.
- Expanded fail-closed pre-solve QA for connectivity, supports/DOFs, diaphragms, releases, rigid offsets, local axes, response-spectrum inputs, P-Delta declarations and shell-mesh verification boundaries.
- Added canonical OpenSees Phase-B 3D elastic-frame translation for supported rectangular frame sections.
- Added explicit nodal-mass assignment and rigid-diaphragm execution semantics without silently deriving either from incomplete source meaning.
- Added OpenSees modal/eigen execution with normalized period, frequency, generalized-mass and translational effective-modal-mass participation results.
- Added sanitized Phase-B regression tests and explicit failure cases for unresolved nodal mass and diaphragm semantics.
