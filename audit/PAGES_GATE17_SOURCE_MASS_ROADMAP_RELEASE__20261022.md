# Gate17 release · immutable source and safety holds

- Tested source SHA `64e36e367ea4a551236e103d54b35f49892063b2` [GitHub Actions](https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/39765136730), full regression 336 passed in 6.12s, source-audit 3 regression checks.
- Previous source fallback `a36e790b062250be4972ddfa5a6de46dc02030e5` (Gate16). Previous main dispatcher commit `9aa1f7c4e8475330b20ab661d7e9c6dd9800d863`.
- Site anchor `project-lab.html#lab-gate17`; generated from exact tested source `scripts/build_g15_gate17_source_audit.py`, no private report content published, source observation/roadmap registers immutable via SHA.
- Report sample selfweight internal check 125mm×25kN/m³=3.125kPa, rounded printed 3.13 kPa. Source summary 20kN/m³, general floor 120mm unresolved.
- Gate08 original residual 772.032917kN. G10_EDGE_COMM residual ~715.468kN, both not closed; no reverse fit. Source ETABS native model not identified, no floor polygons or wall assignments verified.
- Modal narrative/source table period inconsistency tracked; commercial/residential occupancy mismatch tracked; F3 original **NOT SAFE IN ONE WAY SHEAR** retained, no structural approval.
- Website release requires successful separate BUILD and DEPLOY jobs, not only green development CI.
