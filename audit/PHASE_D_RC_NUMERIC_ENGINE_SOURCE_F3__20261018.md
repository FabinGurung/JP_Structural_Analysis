# Phase D: actual numerical RC report engines and source F3 reconstruction
Date: 2026-10-18 NPT

This changes engineering calculations, **not merely governance**. Bounded source-linked mathematical kernels:
- `M08` NBC105:2025 Annex A 4.1.3 seismic capacity shear: max linear-analysis action or gravity +/- 1.4(end plastic hinge capacities)/clear span, enveloped at both ends. Requires actual independently determined hinge strengths and member-end signed FE actions.
- `M09` IS456:2000 §39.6: Puz, alpha_n, minimum eccentricity, short-column check and biaxial utilization. Actual uniaxial capacities presently require a source-linked SP16 or independent section solver, which remains a genuine missing numerical engine.
- `M10` NBC105:2025 Annex A 4.4.1 joint nominal shear coefficient/area and interior/exterior horizontal shear. Computes additional joint reinforcement *demand* but does not yet close confinement and anchorage.
- `M12` IS456:2000 footing rigid concentric interior soil pressure, strip bending, two one-way shears, d/2 punching against ks·0.25√fck; settlement/combined/eccentric footings not implemented.

Reference example from IITGN's 400×500 section, Pu1475, Mx252/My29.5, Mux1/Muy1=272/340. Beam, joint, footing geometry are synthetic assumptions; sample outputs are NOT a consistent actual building.

Original private precedent `new nbc2025 report REVISED(1).pdf`, §6.4.2, F3: explicit `NOT SAFE IN ONE WAY SHEAR` and contradictory IF3 2100×2100 adopted footing schedule. Printed F3 numbers include 571kN column load, 600kN including self-weight, 160kPa claimed SBC, D=450mm, 12mm@150 reinforcement, M20 Fe500. The historical upward pressure 194.22kPa equals 1.5×571/(2.1²), not 1.5×600/(2.1²). Reconstructed d=394mm is an ASSUMPTION based on cover 50mm and bar radius 6mm. Source remains unsafe even if reconstructed arithmetic checks pass. No source overwrite.

**Release gates:** member-level FE force recovery and envelope mapping, verified soil and steel schedules, uniaxial P–M interaction generator, ductile confinement, bar layout/anchorage, settlement and independent real-building validation. Frozen Seq9/Pages main unchanged. CI generates two distinct machine JSON artifacts: assumed RC calculations and historical F3 unsafe reconciliation.
