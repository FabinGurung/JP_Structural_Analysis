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
