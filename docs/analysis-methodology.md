# Analysis methodology

OpenSees/OpenSeesPy is the primary solver for supported workflows.

Phase A: controlled 2D elastic frame.
Phase B: 3D elastic frame, diaphragms, mass, modal/eigen analysis.
Phase C: Nepal-relevant seismic/response-spectrum workflow, base-shear checks, storey displacement/drift and torsional reporting.
Phase D: P-Delta and nonlinear/fiber analysis only after separate validation.

Analysis output is not member/code design. Design checks require separate benchmarked modules.
