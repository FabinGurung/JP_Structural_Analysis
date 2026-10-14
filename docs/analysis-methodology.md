# Analysis methodology

OpenSees/OpenSeesPy is the primary solver for supported workflows.

Phase A: controlled 2D elastic frame.

Phase B: canonical 3D elastic frame, explicit rigid diaphragms, explicit nodal mass and modal/eigen analysis. The bounded Phase-B adapter translates canonical rectangular elastic frame members, applies support restraints, assigns explicitly normalized node masses, applies rigid-diaphragm constraints only when their execution semantics are explicit, executes OpenSees eigen analysis, and serializes modal periods/frequencies plus translational effective-modal-mass participation.

Phase B is fail-closed about missing engineering meaning. In particular, mass-source load factors are **not** silently converted to nodal masses, diaphragm labels alone do **not** imply rigid-diaphragm execution, and shells/end releases/rigid offsets remain outside this bounded solver adapter until separately implemented and validated.

Phase C: Nepal-relevant seismic/response-spectrum workflow, base-shear checks, storey displacement/drift and torsional reporting.

Phase D: P-Delta and nonlinear/fiber analysis only after separate validation.

## Pre-solve QA boundary

Pre-solve QA checks, where represented:

- units, coordinates, duplicate/coincident nodes and zero-length members;
- material/section/member references;
- support references and DOF tokens;
- unsupported or disconnected frame components;
- diaphragm references and conflicting memberships;
- end-release and rigid-offset references;
- unresolved local-axis definition for non-axis-aligned members;
- mass-source load-pattern references;
- response-spectrum series, damping and modal-case references;
- P-Delta load-state declarations;
- shell-mesh verification status;
- design-basis resolution.

These checks are fail-closed gates. They do not prove global stability, local-axis equivalence, release mechanisms, rigid-zone equivalence, shell adequacy or code compliance. Those require solver execution and independent validation.

## Phase-B modal result boundary

Normalized Phase-B modal results include, for each requested mode:

- eigenvalue;
- circular frequency;
- frequency;
- period;
- generalized mass;
- X/Y/Z participation factors;
- X/Y/Z effective modal masses;
- modal and cumulative translational participation ratios.

The result set also records solver/version, canonical-model digest, deterministic run/result IDs, source-reference IDs, explicit implementation scope and warnings. These outputs are analysis evidence, not reinforced-concrete design or professional approval.

Analysis output is not member/code design. Design checks require separate benchmarked modules.


## Phase-C response-spectrum core boundary

The bounded Phase-C core consumes an **explicit acceleration response spectrum** and the Phase-B canonical frame/modal model. The engine does not manufacture spectrum ordinates, damping, unit conversions or code coefficients.

Implemented in the current bounded slice:

- deterministic spectrum validation, sorting and linear interpolation inside the supplied period domain;
- fail-closed rejection of period extrapolation;
- explicit damping and unit-consistency metadata;
- one-direction modal response-spectrum evaluation for X, Y or Z;
- SRSS modal combination and equal-damping CQC modal correlation/combination selected explicitly by the caller;
- modal and combined base-shear response;
- storey displacement only when the caller explicitly maps a storey to a canonical response node;
- inter-storey drift from those explicit response-node mappings;
- optional numerical design-limit evaluation only when a governing code/source reference and numerical limits are supplied by the governed caller;
- deterministic result/run IDs, model digest and spectrum provenance.

The implementation deliberately does **not** infer or claim:

- modal-combination methods beyond the implemented SRSS and equal-damping CQC paths;
- accidental-eccentricity load application;
- implicit/code-specific orthogonal-direction factors; the bounded orthogonal envelope helper requires a caller-supplied factor;
- Nepal-code numerical coefficients or limits that were not supplied as governed inputs;
- shell/end-release/rigid-offset equivalence that remains outside the Phase-B frame adapter;
- source-software equivalence, professional approval or reinforced-concrete design.

Explicit two-node storey torsional-response probes are available when canonical node IDs and a positive physical separation are supplied by the caller. These probes are response quantities, not torsional-irregularity acceptance checks. Accidental-eccentricity execution and dedicated torsional-irregularity acceptance remain future work. Therefore this Phase-C core is a reproducible analysis capability, not a completed seismic code-compliance certification.


## Seq9 bounded combination and torsional-response extension

The OpenSees Phase-C extension retains the explicit canonical inputs and provenance of Seq8 while adding:

- `modal_combination="CQC"` for equal-damping complete quadratic combination. The supplied spectrum damping ratio is mandatory; modes are coupled using their computed circular frequencies. `SRSS` remains selectable.
- Optional `torsion_points`: one explicit pair of distinct, same-storey canonical node IDs plus a positive physical separation per storey. Modal differential displacement over that separation yields an approximate storey rotation in radians; this is **not** accidental eccentricity or a torsional-irregularity code check.
- `combine_orthogonal_direction_results(first, second, orthogonal_factor=...)`: a caller-supplied factor in [0, 1] produces absolute-response envelopes for the two distinct directions. No code-specific 100/30 or similar combination is inferred. The postprocessor does not reconstruct signed simultaneous responses.

All quantities and thresholds requiring normative meaning remain caller-supplied. Results are bounded computational evidence and must not be treated as Nepal-code acceptance, professional sign-off, or equivalence with ETABS. Numerical test and CI evidence must be verified separately before Seq9 is recorded as closed.
