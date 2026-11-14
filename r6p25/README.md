# R6.25 — Narayani source-verified element intake (not yet an FE model)

This is the **first real-project intake and source qualification stage** for the
independent structural-analysis engine, using the separate, live
[FabinGurung/jp-drawing-coordination](https://github.com/FabinGurung/jp-drawing-coordination)
GitHub repository as the source for geometries already traced to the
**original Narayani DXF**. The drawing repository's canonical URL was changed
from `JP_Computer-Aided-Drawings` to `jp-drawing-coordination`.

**Pinned source checkout:** `259d11e1543e4ba7040373a752b823396e12d7f8`  
**Project identity:** `PRJ-000007`, proposed Block B, Pokhara Metropolitan City-15  
**Building design / construction approval:** **HOLD**

## What is copied versus what is calculated

The importer reads original-DXF-derived data directly from the pinned CAD
repository. It **does not copy/alter** source CAD drawings, use ETABS result
numbers, or promote an AI-inferred outline into a real structural slab.

The normalized register includes:

- Source GF **23 column marks** with individual original DXF entity handles
  and native X/Y coordinates in millimetres. The owner-working **I3** correction
  remains separate from the **original I4** source location.
- GF **21 footing outlines**, including two `CF1` combined footings, with
  original handles and plan sizes. Foundation depth, soil reactions,
  eccentricity, bearing, punching and one-way shear are **not calculated**.
- GF **32 paired-edge source candidates** with endpoint coordinates and
  *diagnostic nearest-column distances only*. A close source endpoint is not
  automatically a supported beam-to-column junction.
- GF/FF/SF **17 strict parallel-line candidates per level** (51 records),
  with paired DXF handles and candidate axes. The sources were drawn/copy-
  translated at different sheet offsets. This is **not** 51 accepted load-
  bearing members or evidence of upper-floor structural continuity.
- The three architecturally scheduled proposed Block B areas:
  **205.16, 200.67, 175.62 m²** (total **581.45 m²**). AAD floor contours
  are source-related but contain expressly **area-fitting/inferred geometry**,
  so they are **not direct FE shell or opening data**.
- Existing Block A is excluded from this proposed Block B model.

## Approved basis and geotechnical evidence

**User decisions 14 November 2026:** Pokhara; **NBC 105:2025** seismic
edition; concrete design self-weight **20 kN/m³** rather than silently imposing
a general default; preliminary **160 kPa** soil bearing assumption. The
concrete *grade* M20 and steel Fe500 are drawing-stated.

**Authentic geotechnical report** is already preserved in the canonical
Narayani Drive warehouse `02 Original Source Files/05_GEOTECHNICAL`,
file ID `13y0b0v8BiL2ooMXy0BFn2dtdSHWNOg2N`. The user-linked original file
`1PtkCjcWjWtYi9D2-GG4_O3P6KKW9S7B8` has the same title, byte size and
extracted text. Do **not** overwrite or duplicate this governed copy.

The geotechnical report table, p. 21, states **166 kPa** at **B=L=1.5 m,
Df=1.5 m** for a square isolated footing (25 mm permissible settlement).
The user-approved **160 kPa** input is marginally more conservative for
this case; it is **not** a blanket approval of 1.8–2.4 m footings or 4×1.5 m
rectangular combined footing CF1. The table varies bearing pressure with
width/depth.

**Critical soil-class disagreement:** geotechnical report p. 22 labels site
**Type B under NBC 105:2020**, older structural report states **Type D**.
Adopting the **2025 code** does not resolve this conflict automatically.
Original borehole records and applicable NBC 105:2025 classification rules
must decide seismic site class; do not invent a classification.

## Geometry and independent OpenSees gate

The drawing repository **explicitly preserves** the following engineering
unverified states:

- source GF beam/column drawing registration is **sheet-relative**, not a
  surveyed architectural/structural shared control datum;
- real FF/SF vertical member identity/continuity is **not verified**;
- G2 is an owner-confirmed **beam-line junction**, **not** an extra column;
- C6–F6/strip 016 is an owner-authorized *orthogonal drawing-intent overlay*
  and does not prove junction capacity;
- I4 original and I3 owner-working positions are not silently merged;
- the G1 footing has **drawn 1.8×1.8 m** versus a **scheduled 2.1×2.1 m**
  dimension conflict;
- the archived **F3 one-way shear NOT SAFE** from the SAR investigation
  is still adverse and distinct from a CAD F3 dropdown/selection issue;
- the current R6.23 engine requires a small rectangular, regular source-
  verified multi-floor shell mesh; the Narayani outlines and actual joints
  must not be coerced into that synthetic contract.

Hence **R6.25 produces an evidence-indexed real-project element register,
not a complete connected FE input nor any design approval**.

## Reproduce pinned-source intake

```bash
git clone https://github.com/FabinGurung/jp-drawing-coordination.git drawing-source
git -C drawing-source checkout 259d11e1543e4ba7040373a752b823396e12d7f8
R6P25_CAD_ROOT=drawing-source python -m pytest -q r6p25/test_narayani_intake.py
python -m r6p25.narayani_intake --cad-root drawing-source \
  --output-dir /tmp/r6p25-narayani-source
```

Both output files carry project/source fingerprint information and an
**ENGINEERING HOLD**. The CLI rejects a moving Git checkout. The dedicated
GitHub Actions job runs with the exact pinned drawing repo commit and
checks a source-SHA256 receipt; **no soil PDF, client-origin CAD source files,
or full real project model is uploaded as a public workflow artifact**.

The next step is model source mapping across GF→FF→SF and section/load
schedule validation, after which a source-backed *irregular* structural FE
mesh (and at least three physically equivalent resolutions) can be
evaluated. There is no ETABS numerical-parity requirement.
