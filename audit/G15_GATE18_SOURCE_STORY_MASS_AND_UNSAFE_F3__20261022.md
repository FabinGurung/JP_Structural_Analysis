# Gate18 actual source-storey weight identity and unsafe F3 source worksheet — 22 October 2026

## Source finding: significant resolution of a **previously unrecognized aggregate arithmetic identity**
The original revised report PDF (private Drive `1TpWUmOdrcQqOpkN6qvmhZ12KrYaNABBM`, SHA-256 `f122904444a2e2f75230d9d4e41da0093d050da25c6e8140c86d466b7e37cc52`) was read AND its physical p.34 mass table visually inspected. It prints **Story 3 152521.81; Story 2 274062.74; Story 1 270076.47; Base 18434.33**, column title **MASS X or Y**, **no unit printed**.

- Sum three storey values: **696661.02**. If the units are kg (inference), conversion by standard gravity **9.80665 m/s²** gives **6831.910791783 kN**, versus the separate source auto-seismic table reported **6831.9109 kN**.
- Error report minus reconstructed **+0.000108217 kN**; worst-case rounding uncertainty with 3×0.01 mass displayed, 0.0001 W displayed: **±0.00019709975 kN**. The agreement is stronger than required by printed precision. **Do not replace source W or round/placehold to force a match**.
- Including Base 18434.33 at same inferred mass units gives **7012.6898140775 kN**, which does not match; this only demonstrates its exclusion from the matched total, NOT proof of original ETABS mass-source exclusion setting.
- This is source *reported total arithmetic reconciliation*, not actual ETABS selfweight/dead/eligible live component reconstruction. Gate08 gap **772.032917 kN** and Gate10 hypothesis gap **715.467677 kN** are still unresolved and cannot be patched to story masses without material, area, wall and source unit evidence.

## Source F3 critical failure
Rendered physical PDF p.61 F3 worksheet; source verdict exact **NOT SAFE IN ONE WAY SHEAR**. Effective depth printed **423.46278 mm**, whereas prior M12 reconstruction assumed **394 mm**. Printed allowable and nominal shear stress both **0.2** (rounded) yet verdict FAIL. Source pressure **194.22 kPa**, P=571kN and with-selfweight=600kN, SBC claim=160kPa. Do not infer success from rounded pressures or any bounded one-way shear precheck.

Added four conditional effective depth/mass load screens D=450/500/550/600, carrying their own extra hypothetical concrete selfweight and factored demand. Results are strictly numerical sensitivities; settlement, soil quality, seismic load path, reinforcement anchorage, real source footing geometry and design approval remain BLOCKED. A qualified structural/geotechnical redesign of F3 remains required.

## Software execution and source governance
- Existing Gate17 source auditing, Gate16 36 real FE cases, rollback pins, original PDF, Drive references and legacy issue data unchanged.
- Gate18 source register, deterministic report calculation, dedicated regression tests, verified static site QA and human-readable Project Lab new Gate18 section.
- External native .edb/.e2k for this specific building was not found in a fresh scoped Drive search (other buildings' .e2k excluded). No source copied or deleted.
- Public numerical aggregate and redacted findings only; original private PDF stays in Drive.
- Hard HOLD: `mass_source_reconciled=false`, `engineering_approval=false`, `f3_current_design_accepted=false`.
