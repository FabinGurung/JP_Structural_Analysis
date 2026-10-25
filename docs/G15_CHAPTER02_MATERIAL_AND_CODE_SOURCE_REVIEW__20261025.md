# Chapter 2 · Source-derived materials and code basis — 25 Oct 2026

Original authority: private revised G+1.5 report (Drive ID 1TpWUmOdrcQqOpkN6qvmhZ12KrYaNABBM, SHA-256 f122904444a2e2f75230d9d4e41da0093d050da25c6e8140c86d466b7e37cc52), exact source §§2.1–2.4. Real report values have not been silently overwritten by standard textbook values.

- Actual source §2.1 M20 concrete and printed formula 5000×√20 = 22,360.679775MPa conflicts with printed 25,000MPa. Source RC density 25, plain 24, competing executive 20 kN/m³. Poisson=0.2.
- Actual source §2.2 Fe500 for main/stirrups; reported steel modulus printed "200 Mpa" (not auto-corrected to 200GPa); cited IS1786 1985 vs IS1786 2008 edition mismatch; no authenticated code edition.
- Actual source §2.3: footing 50mm all faces; column 40mm; secondary beam 25mm; beam max(25mm,bar diameter); slab max(20mm,bar diameter). Only original source transcription; full NBC/IS detailing source proof pending.
- §2.4 original code lists NBC105:2025, IS875, IS456, IS1786, IS13920, others. This is not a complete NBC compliance engine. Codes must be separately clause-indexed and validated.
- Original reported 14x14in (=355.6mm) versus later 400x400mm column assignments not reconciled. This release calculates a cross-product of six **separate illustrative** square-column scenarios (two size interpretations × 20/24/25 kN/m³) using original 3.048m height. ZERO physical column IDs or source masses are assigned, and no finite-element model input is changed. It reuses native verified material_properties and gravity_loads kernels with independent hand identities and negative-case tests.
- Source-provenance ledger has 21 entries and 8 chapter-specific open/blocked acceptance gates. These are not the same as 15 Gate20 source/model gates; neither set is approved. Original unsafe footing F3 remains **NOT SAFE IN ONE WAY SHEAR**.
- Site presentation moved source subsections 2.1, 2.2, 2.3 and 2.4 into true TOC order before 2.5. Python builder emits source-checked JSON consumed by fail-closed public reader and CI/Pages. Scope is Chapter 2.1-2.4 **arithmetically audited**, not a physical engineering acceptance.
Next: §2.5 source geometry ledger/object IDs and §2.6 authentic loads and location graph after receiving source native floor/wall/ETABS material assignments; do not fill gap with invented walls.
