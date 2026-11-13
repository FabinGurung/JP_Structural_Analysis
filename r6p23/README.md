# R6.23 — Independent multi-floor 3D shell/frame analysis and openings

**Source owner:** JP Structural Analysis · **Classification:** research software, no professional design approval.

R6.23 is a self-contained first-party OpenSeesPy package. It is designed to run on the full research branch **and** as an opt-in, isolated checked module on the lightweight `main` branch, without replacing the existing Pages-dispatch/showcase or pretending that the complete engineering product has been released.

## Capabilities implemented

1. **Actual multi-floor 3D FE model:** per-floor ShellMITC4 quad elements, frame `elasticBeamColumn` members, explicit four corner supports, columns between floor levels, and common shell/beam/column node identities. No proximity joining or ETABS-generated analysis joints.
2. **Two-way behavior:** real plate/shell bending and in-plane membrane stiffness, not an assumed tributary split. Source-declared rectangular orthogonal plan grid only, with optional internal full-span beams.
3. **Slab openings:** explicit interior cells removed from the shell mesh **and** their pressure/volume/mass proxy. The free edges of holes are shell edges; no fictitious plate stiffness is created inside a void.
4. **Diaphragms:** independent `FLEXIBLE_SHELL` and `RIGID_INPLANE_MPC` modes; the latter ties floor **Ux, Uy, Rz** with a retained master node, preserving shell **Uz, Rx, Ry** so a rigid in-plane assumption does not artificially eliminate vertical plate bending.
5. **Gravity source conservation:** concrete slab and finish pressures → consistent four-corner equal nodal loads per rectangular shell cell; beam selfweight counts *additional downstand below the slab* only, vertical column dead weight uses full-span axial OpenSees element loading, walls use net gross length×height less openings and line-load supported beam segments. This is a **source-bounded approximation**, not verified joint-zone volume takeoff.
6. **Numerical results:** each case is separately solved; extract shell 24-DOF nodal forces, signed beam/column I/J actions and support reactions. Check global six-component Fx, Fy, Fz, Mx, My, Mz equilibrium; independently check linear signed superposition of slab and frame dead-load cases. Verify both perpendicular beam families receive shell-load actions.
7. **Artifact integrity:** machine JSON of all cases/forces, HTML summary, CSV floor-node displacements, SHA256 manifest/readback. Case/floor/source provenance and engineering HOLD status are retained.
8. **Fail-closed geometry:** rejects unsupported exterior-edge holes, duplicate openings, invalid material values, impossible geometry, duplicate wall sources and unsupported/unknown combinations, without silently placing artificial restraints.

## Input and status boundary

`jp.structural.r6p23.rectilinear_multifloor_shell.v0.1` takes an explicit source-qualified grid, levels, floor thickness/pressure/opening cells, source material elastic modulus/unit weight, beam/column sizes, wall and lateral load sources, and *source-labelled* combination coefficients. The model does **not** infer building geometry from incomplete drawings. The reference is a **synthetic two-floor** study, not the Pokhara G+1.5 design.

This increment is restricted to small-deformation linear elastic rectilinear buildings with simple rectangular internal cell openings and global four-corner base supports. It does not automatically approve actual plan irregularities, load-bearing walls, transfer slabs, cracked stiffness, end releases, staircases, beams curved/out of plane, irregular floor offsets or openings cutting exterior edges.

ShellMITC4 is an actual finite element, but **numerical force balance alone does not prove mesh convergence** or a physically correct building load path. Member stiffness, in-plane diaphragm choice, load occupancy and site assumptions must be independently sourced. Vertical column distributed loads use exact axial body-force equivalent in the supported 3D elasticBeamColumn, but joint-zone volume overlap remains a bounded approximation.

**Open engineering items:** building-specific mass and diaphragms, verified NBC seismic and wind actions, first/second-order analysis, drift, cracked/nonlinear material behavior, shear walls, slab flexure/shear/punching, beams, columns, joints, staircases, actual soil/support stiffness and all footing design checks. The historical adverse finding **F3 NOT SAFE IN ONE WAY SHEAR** remains unresolved; this code does not reverse or certify it. A complete SAR/PDF and professional site-specific structural review remain future work.

## Reproducible synthetic reference

```bash
python -m pip install openseespy pytest
python -m pytest -q r6p23/test_engine.py
python -m r6p23.runner --reference --output-dir build/r6p23
```

For private real-source inputs, both the input JSON and output directory must be **outside the public repository**:

```bash
python -m r6p23.runner \
  --input /secure/project/r6p23-input.json \
  --output-dir /secure/project/r6p23-analysis
```

Do not upload actual client drawings or analyses to public Actions, artifacts, main, or Pages.

### Manual reference totals (synthetic 4m×4m / two floors)

- 31m² net active shell area (16m² lower + 15m² upper, **1m² void**).
- Slab plus finish dead = 31×(0.12×25 + 1.5) = **139.50 kN**.
- Perimeter beam excess concrete below slab = 32m × 0.30m × (0.45−0.12)m × 25 kN/m³ = **79.20 kN**.
- Four columns × two 3m storeys × 0.40×0.40m × 25 kN/m³ = **96.00 kN**.
- Single masonry run on first floor, one opening = (2.5×4−1.0) × 0.15×18 = **24.30 kN**.
- **Total DL = 339.00 kN**; live = 31×2 = **62.00 kN**.
- These are computed source takeoffs and real OpenSees load magnitudes, not ETABS values or NBC design certifications.

### Algorithm and solver references

- OpenSeesPy ShellMITC4 element and 4-node bilinear bending/membrane formulation:
  https://openseespydoc.readthedocs.io/en/latest/src/ShellMITC4.html
- OpenSees 3D `eleLoad` uniform local `Wy,Wz,Wx`, supporting gravity on beams and axial columns:
  https://opensees.github.io/OpenSeesDocumentation/user/manual/model/pattern/PlainPatternloadcommands/eleLoad.html
- OpenSees 3D in-plane `rigidDiaphragm 3` geometry and small-rotation caveat:
  https://opensees.github.io/OpenSeesDocumentation/user/manual/model/mp_constraint/rigidDiaphragm.html
- NAFEMS verification case for shell mesh convergence (future independent benchmarking):
  https://openseesdigital.com/nafems/le6/

## Branch and release governance

R6.23 is installed in the research branch with full regression tests; an identical isolated runnable subtree may be included on `main` **as a development/preview component** with a dedicated CI job and README pointer. Main/Pages release content and engine default branch must not be silently repinned or tagged. Engineering approval and the complete-engine milestone remain **HOLD** until independent project-specific calculations and professional review are complete.
