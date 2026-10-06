# Analysis methodology

OpenSees/OpenSeesPy is the primary solver for supported workflows.

Phase A: controlled 2D elastic frame.

Phase B: canonical 3D elastic frame, diaphragms, mass and modal/eigen analysis. The current bounded implementation now includes a legacy-E2K-to-canonical bridge plus fail-closed representation QA. Canonical OpenSees translation, diaphragm constraint execution, governed mass mapping and modal participation normalization remain incomplete.

Phase C: Nepal-relevant seismic/response-spectrum workflow, base-shear checks, storey displacement/drift and torsional reporting.

Phase D: P-Delta and nonlinear/fiber analysis only after separate validation.

## Pre-solve QA boundary

Pre-solve QA now checks, where represented:

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

Analysis output is not member/code design. Design checks require separate benchmarked modules.
