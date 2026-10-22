# Gate13: bounded actual shell slab and assumed masonry wall load path

Date: 2026-10-22. Approved assumption-based development, **not an approved structural design**.

- Tested source commit: `e9ec188412ca5a1b4d18ecd977bb8f8803819b24`. Prior Pages source/rollback: `b0eba2743dbfb7fae8552ea23adc371302432eb0`.
- CI: https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/39696622232 — **323 automated tests passed**, safety scan, real 27-case OpenSees FE, site QA.
- Live new route: https://fabingurung.github.io/JP_Structural_Analysis/project-lab.html#lab-gate13
- Source-referenced example slab F–G/1–2: 4.965m × 3.600m / 17.874m²; 125mm slab; 5.13kPa reported sample dead load. Its level-two assignment is **assumed**.
- One trial slab patch: four connected 3D ShellMITC4 quadrilaterals with plate-fiber section. A slab center mesh node receives gravity and transfers load via beam-edge mesh.
- 165 original source frame segments become **171 computational beam segments** where continuous members are subdivided at panel boundary/junctions. No new physical beams are claimed.
- Seven specifically named **assumed** masonry wall beam lines from Gate10, rate 9.24kN/m, trial levels 1 and 2. OpenSees 3D beamUniform applies load directly to beam members.
- 27 comparable elastic solves = 9 signed gravity/±X±5%, ±Y±5% cases × frame baseline, slab-shell patch and full rigid-floor MPC. Support force/moment equilibrium and signed local 12-component member actions are tested. Full data archived in Actions. Beam wall weights are kept separate from lateral mass ledger to avoid double counting.
- Incomplete building: source slab level, wall positions, openings, actual diaphragm properties and ETABS mass source are not verified. Shell patch is only one bay, **not an entire floor diaphragm**. P–Δ, codal drift and source grounding remain open. F3 source footing result: **NOT SAFE IN ONE WAY SHEAR**.
- Full-building seismic mass gap remains 772.032917kN for Gate08 baseline; the altered Gate10 weight is explicitly hypothetical. Preserve unfinished engineering issue #7, draft PR #4, frozen Seq9 and all prior versions. To rollback, restore previous Pages pinned source and remove the Gate13 generated JSON/JS build steps, then redeploy.
- OpenSees reference: https://openseespydoc.readthedocs.io/en/latest/src/ShellMITC4.html and https://opensees.github.io/OpenSeesDocumentation/user/manual/model/pattern/PlainPatternloadcommands/eleLoad.html
