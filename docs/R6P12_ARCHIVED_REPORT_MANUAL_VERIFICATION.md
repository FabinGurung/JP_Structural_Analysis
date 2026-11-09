# R6.12 — Manual check of the archived G+1.5 structural report

**Source:** original revised report PDF in governed Drive (file `1TpWUmOdrcQqOpkN6qvmhZ12KrYaNABBM`), SHA-256 `f122904444a2e2f75230d9d4e41da0093d050da25c6e8140c86d466b7e37cc52`. Historic ETABS20 headings contain ETABS21 design snippets. The *current* engineering inputs remain the registered ULS/SLS ETABS21 pair, not these historical results.

**Method:** Recalculate printed arithmetic from explicitly printed inputs; retain the historical report values verbatim in the source register. Distinguish a numerical match from a solved, safe or approved structural model. This audit does **not** create missing ETABS outputs, material test results, seismic mass validation, or geotechnical approval. All 12 unsupported shells remain excluded. Footing F3 is **NOT SAFE IN ONE WAY SHEAR**.

## Hand calculations and source comparisons

| PDF section | Substitute / recalculate | Result and qualification |
| --- | --- | --- |
| §2.1 concrete modulus | 5000 × √20 | **22,360.68 MPa**, versus early printed 25,000 MPa. Later ETABS21 excerpt prints 22,360.68; source inconsistency. |
| §2.6 period | 1.25 × 0.075 × 9.144^0.75 | **0.492973 s**; printed 0.493 s reproduced. Not fundamental eigenperiod. |
| §2.6 ULS coefficient | (0.35 × 2.25 × 1)/(4 × 1.5) | **0.13125** versus report's **0.131** adopted coefficient. |
| §2.6 SLS coefficient | (0.35 × 2.25 × 0.2)/1.25 | **0.126** reproduced. |
| §§5.1, 5.10 source mass | (270,076.47 + 274,062.74 + 152,521.81) × 9.80665/1000 | **6,831.910792 kN**, consistent with historical 6,831.9109 within mass rounding. Original mass units not printed; **kg is an inference**, not verified ETABS21 mass. The printed base entry 18,434.33 is excluded. |
| §§5.1, 5.12 ULS base shear | 6,831.910792 × 0.131 | **894.980314 kN** reproduces printed 894.9803 kN. Using unrounded 0.13125 instead gives **896.688291 kN**, a **+1.707978 kN** arithmetic difference. |
| §§5.1, 5.12 SLS base shear | 6,831.910792 × 0.126 | **860.820760 kN**, reproduces 860.8208 kN. Static base-shear arithmetic is not native reaction output. |
| §2.6 / §5.1 level distribution | Fᵢ=V×Wᵢhᵢ/ΣWⱼhⱼ; k=1; h=3.048, 6.096, 9.144 m | Conditional ULS: **189.4649, 384.5227, 320.9927 kN**, summing to 894.9803 kN. **Not original ETABS floor forces.** |
| §5.5 90% modal participation | Compare printed cumulative UX/UY across rows | At **mode 5** UX=0.9297 and UY=0.9538, already both over 90%. Narrative says six modes. This is a *text/table discrepancy*. |
| §5.5 period and frequency | 1/0.185 | **5.405405 Hz**, matches narrative 5.405 Hz but table lists mode 6 T=0.187 s and mode 1 T=0.618 s. A sixth-mode period is not a fundamental period. |
| §5.6 ULS displacement limit | 0.025/4 × 9.144 × 1000 | **57.150 mm**. Reported 22.9069 mm / limit = **0.40082**; inequality only, not reproduced displacement. |
| §5.6 SLS displacement limit | 0.006 × 9.144 × 1000 | **54.864 mm**. Reported 12.846306 mm / limit = **0.23415**; inequality only. |
| §5.7 ULS drift | 0.00288 / 0.00625 | **46.08%** of report's cited limit; reported response, not independent solution. |
| §5.7 SLS drift | 0.002174 / 0.006 | **36.23%** of report's cited limit; reported response, not independent solution. |
| §5.8 torsion example | Story 3 ULS EQY 22.907 / 19.146; EQX 18.765 / 17.779 | **1.19644** and **1.05546**, matching displayed 1.20 and 1.06. Other rows need to preserve their original source labels. Not a full torsion validation. |
| §5.9 soft-storey example | X K1/K2=210,766.538/105,412.441; K2/K3=105,412.441/58,488.585 | **1.99945** and **1.80227**. Y ratios **1.76885, 1.52557**. These reproduce comparisons of printed stiffnesses; no current-model stiffness established. |
| §5.10 mass irregularity | (274,062.74 − 152,521.81)/274,062.74 | **44.35%** lower top mass relative to story 2. Actual mass-classification and light-roof exceptions require engineer/code review. |
| §5.15 eccentricity sample | 100×abs(9.9295−10.0517)/19.90, 100×abs(5.2078−4.9616)/11.10 | Ground-floor **0.614% X, 2.218% Y**, reproducing rounded 0.61% and 2.22%. This is not an accidental-eccentricity response calculation. |
| §6.1 C1 steel | 8×π×16²/4 / (400×400) ×100 | **1.0053%**, reported 1.00%, subject to rounding. Other C1–C4 schedules are already generated in Chapter 6 arithmetic ledger. |
| §6.2 B46 combined design moment | −99.4853 − 14.7682 | **−114.2535 kN·m**, matches excerpt; cannot recover its actual original FEM demand from printed summary. |
| §6.2 B19 combined design moment | −60.1122 − 19.4579 | **−79.5701 kN·m**, matches excerpt, not independently analysed member action. |
| §6.3 slab self-weight | 0.125×25 | **3.125 kPa**, reported 3.13. General 120 mm vs sample 125 mm unresolved. |
| §6.3 slab design pressure | 1.5×(3.125+1+1+2) | **10.6875 kPa**, reported 10.69. |
| §6.3 slab 8 mm @150 steel | π×8²/4×1000/150 | **335.103 mm²/m**; spacing/area arithmetic only. |
| §6.4 F3 foot pressure | 1.5×571/(2.1×2.1) | **194.2177 kPa**, reproduces printed 194.22; does **not** establish shear safety. |
| §6.4 F3 total-load sensitivity | 1.5×600/(2.1×2.1) | **204.0816 kPa**, if the printed *selfweight-inclusive* 600 kN were also factored. PDF's printed 194.22 follows 571 kN instead; do not silently choose one. |
| §6.4 F3 service average pressure | 600/(2.1×2.1) | **136.0544 kPa**. Source allowable bearing 160 kPa is not independently verified; average pressure omits moment and local maxima. |
| §6.4 F3 effective depth scenario | 450−50−12/2 | **394 mm**, versus printed **423.46278 mm**; section assumptions conflict. **F3 remains unsafe in one-way shear.** |
| §6.4 F3 12 mm @150 steel | π×12²/4×1000/150 | **753.982 mm²/m**. This does not fix F3 one-way shear. |
| §6.4 CF1 average bearing | 501/(4.0×1.5) | **83.5 kPa**, average only; not corner pressure, punch, shear or soil settlement verification. |
| §6.5 stair flight | 1.5×11.41 | **17.115 kPa** versus report's rounded 17.11. Multiplying 17.11 by 1.2 m gives 20.532 kN/m versus 20.53. |
| §6.5 stair 12 mm @127 steel | π×12²/4×1000/127 | **890.530 mm²/m**, versus one worksheet's stated **995.26 mm²/m**. Verify worksheet steel math. |
| §6.5 waist depth | 150 mm general schedule vs 127 mm design worksheet | **23 mm conflict**, unresolved. |

## Not independently reproduced

Complete ETABS21 FEM member end actions, response-spectrum/modal participation, support/joint reactions, frame stiffness and drift, actual shell load transfer, footing shear capacities, slab/stair strength and deflection checks, geotechnical bearing/settlement and the current building's full design code acceptance. Published historic graphics and member examples remain *source-reported* results only.

## Governance

- The original archived PDF and raw ETABS21 files remain in their prior Drive locations; do not republish raw sources.
- Do not silently equate historical ETABS20/ETABS21 report results with the current selected ETABS21 ULS/SLS pair.
- Keep the 12 source-unanchored shells excluded and all active issue #7 source/design holds open.
- Original F3 one-way shear **NOT SAFE IN ONE WAY SHEAR**.
- Software validation, numerical arithmetic and a professional engineering sign-off are distinct activities.
