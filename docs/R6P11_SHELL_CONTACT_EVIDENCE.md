# R6.11 — source corner contacts, NOT verified vertical supports

Source: the SHA-256-registered, de-identified, original ETABS21 ULS/SLS inputs in
`registry/r6p5_etabs21_governing_pair.v0.1.json`. Parent R6.10 source:
`fc74b1459a9d049d5bc9e90f7287ea8526ca5896`.

**Geometry-only finding:** ten original wall corners near three candidate receiving
edges, evaluated in 3D to **0.001 mm**. Four are on the GF:F56 edge
(56 to 75), four on FF:F56 (56 to 75), and two near FF:B27
(26 to 27), which borders FF:F7 and FF:F30. Coordinates,
fractions along the receiving edge, and separation are derived at build time;
the script does not snap or reposition any ETABS point.

## Evidence gate — currently OPEN

An overlapping source coordinate is **not** an ETABS21 generated joint and
does **not** demonstrate a vertical support, joint constraint, or load path.
Keep the original **12 shell objects excluded** from all independent trial
calculations. Do not alter the 103 supported research shells or original
six disconnected restraints merely to make an input graph connected.

The following matching **ULS and SLS** exports are needed for *each* candidate:

1. Generated ETABS21 analysis joint coordinates and source-object mapping.
2. Generated shell and frame mesh/element connectivity and releases.
3. Applied point/edge joint constraints and UZ-degree-of-freedom coupling.
4. Signed gravity reactions and balanced vertical member/shell force transfer,
   demonstrating actual nonzero force carried into a restrained base.
5. Engineer review of source identity, loads, support behaviour and safety.

Preserve raw ETABS21 model revisions and analysis results in restricted Drive;
only release de-identified, checked projections through GitHub and Pages.

**Still HOLD:** unreconciled total seismic mass, accidental eccentricity,
native mesh equivalence and full design compliance. F3: **NOT SAFE IN ONE WAY
SHEAR**. No construction or structural engineering approval.
