# JP Structural Analysis

Governed, reproducible structural-analysis and Structural Analysis Report (SAR) engine.

```text
source evidence -> inventory/provenance -> normalized model -> pre-solve QA
-> OpenSees primary analysis -> independent benchmarks -> result QA
-> government-style SAR -> HTML/PDF + machine-readable results + audit trail
```

Development occurs on `engine/opensees-sar-v0.1`. `main` remains the governed bootstrap baseline until release criteria are met and merge/release is explicitly authorized.

This repository is public. Do not commit client/government source files, ETABS project models, private drawings, signatures, credentials, tokens, private Drive links, or unsanitized evidence.

OpenSees/OpenSeesPy is the primary computational engine where supported. Analysis and member/code design are separate modules. CI success is not professional approval, code compliance, or government approval.
