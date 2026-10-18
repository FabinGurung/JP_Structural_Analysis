## PHASE D numerical update — 18 October 2026

**Executed rather than merely described:** Native Python numerical engines `rc_report_kernels.py` now evaluate NBC105:2025 M08 capacity-design beam shear, IS456:2000 M09 column biaxial interaction (using independently sourced uniaxial capacities), NBC105:2025 M10 joint shear and additional joint shear reinforcement, and IS456:2000 M12 concentric isolated/rigid eccentric combined footings.

Two specific worksheets from the private revised structural report were reconstructed:
- F3: the original `NOT SAFE IN ONE WAY SHEAR` persists even when assumed d=394mm computations produce different checks. Concrete M20, Fe500, 2.10m square, 12mm@150, P571/600 kN, q_u historical 194.22kPa are source-derived; effective depth and soil assumptions explicit.
- CF1: columns 46/409kN, separation1.5m, alleged A property-line offset0.45m treated as hypothetical centreline coordinate; footing4.0×1.5m, total501kN after 46kN inferred uniform footing load. Resultant at 1.816866m, service contact q(left)=106.4375kPa, q(right)=60.5625kPa, factored max moment ~287.133kNm. Geometric coordinate is an assumption; shear/punching/settlement still HOLD.

Machine outputs generated in GitHub CI artifacts, not full certificate:
`assumed-rc-numerical-calculations-not-approved`, `report-f3-source-conflict-not-safe`, `report-cf1-combined-footing-calculations-not-approved`.
No ETABS/E2K is required by these numeric kernels.

**Still genuine**: independent uniaxial P–M capacity section solver, NBC complete ductile rebar/combined torsion, full foundation shear/punching and settlement, real structural-member mapping and full compiled SAR; no private client payload pushed or release merged.

Sources: https://ebps.kathmandu.gov.np/UploadFiles/NBC_105_2025_Sesmic_Design.pdf and https://wriddodoti.gov.np/uploads/blog/20230331071217_IS-456-with-all-ammendments.pdf ; IIT example https://www.iitk.ac.in/nicee/IITGN-WB/EQ06.pdf .
