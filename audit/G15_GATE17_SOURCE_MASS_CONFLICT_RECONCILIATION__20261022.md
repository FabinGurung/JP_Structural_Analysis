# Gate17 source reconciliation closeout evidence

Read-only Drive inventory confirmed reference source PDF and editable DOCX report, the Gate08 derived ZIP, but no currently verified native ETABS EDB/E2K for THIS building. Other-project E2K files (notably Narayani) are not used or repackaged. Files were not moved or deleted.

New auditable facts:
- 125mm sample slab ×25kN/m³ = 3.125kPa, printed round-off 3.13kPa; 20kN/m³ summary would yield 2.5kPa. No validation of globally assigned actual ETABS density.
- General slab schedule prints 120mm, sample 125mm, full area geometry unverified; ground architectural commercial label contradicts generalized residential report narrative without known eligible live load.
- Table first modal period 0.618 sec vs nearby narrative 0.185 sec; 90% horizontal UX/UY reached in mode5, RZ by mode6; narrative "90% in exactly 6 modes" is ambiguous and must be checked, not silently corrected.
- Original source 6831.9109kN; G08 6059.877983371731kN gap 772.032916628269kN; G10_EDGE_COMM contains unverified adjustments, residual remains positive. Subtotal rounded component sums may vary <0.001kN; this is not the large unexplained mass discrepancy.
- F3 original source fails one-way shear. CI must keep rejection flags true.
- New source observation registry and deterministic Python audit, 3 new regression tests, public Project Lab dashboard, machine-readable P0/P1 gate statuses. Only SOURCE AUDIT documentation debt advanced; structural source and acceptance debt still open.
