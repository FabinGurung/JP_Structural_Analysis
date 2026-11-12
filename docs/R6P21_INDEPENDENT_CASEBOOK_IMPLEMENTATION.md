# R6.21 — Parameterized independent OpenSees SAR casebook (research implementation)

**Status:** Executable bounded software integration. Not full building FE/design/permit
acceptance; no release tag, no change to published Pages or original Drive files.

## Purpose

Replace one-off hardwired ETABS report matching with a reusable computational
path. This R6.21 stage is deliberately **elastic 3D frame static only** and
connects the existing canonically normalized model → source-identified nodal
load cases → actual OpenSeesPy solves → same-case *signed* load-combination
actions → M08/M09/M10 RC capacity screens → report tables, HTML and SHA-256
manifest.

The input is an explicit JSON case, **not** the original ETABS solver output.
The original ETABS/archived SAR can be used as optional checking precedent, not
as a numerical target.

## Commands

Inside the governed research branch with Python >= 3.11 and development stack
installed (`pip install -e '.[test,opensees]'`):

```bash
# Fully deidentified reference; safe synthetic case inside repo build/
python scripts/build_r6p21_independent_sar.py --reference --output-dir build/r6p21-independent-sar

# Test the actual FE -> check -> report and public-file boundaries
python -m pytest -q tests/test_r6p21_independent_casebook.py

# Project-source case input + output must live outside checkout, for example
python scripts/build_r6p21_independent_sar.py \
    --input /secure/project/canonical-case.json \
    --output-dir /secure/project/independent-sar
```

For source-derived work, the CLI rejects project-source input or output paths
inside the public repository. Do not attach real private model/report artifacts
to GitHub PRs, Actions, Pages, issues or public artifact storage.

## Input contract

`jp.structural.independent_sar_input.v0.1`, fields:

- `case_id`: safe stable identifier.
- `classification`: `SYNTHETIC_REFERENCE` or
  `PROJECT_SOURCE_DERIVED_UNVERIFIED`. No "approved" input mode.
- `provenance`: explicit source/assumption IDs for geometry, materials,
  supports, loads, reinforcement and design code.
- `model`: supported normalized canonical 3D frame JSON including nodes,
  member geometry/sections/materials, supports and original/source registry.
- `cases`: separately source-labelled signed static nodal or supported uniform
  beam loads, with explicit force/moment units.
- `combinations`: source-labelled algebraic case factors. The engine **does
  not auto-assert that this list covers all code-governing combinations**.
- `design_bindings`: lists `beams`, `columns`, `joints` with explicit
  relevant member IDs, source-identified geometry/rebar and design assumptions.
- `code_references`: edition/source HTTPS references; citing a code is not
  proof that every clause was checked.

Anything without a justified physical meaning is rejected or visibly unresolved.
This first stage does **not** accept shell elements, unsupported frame offsets
and end releases, in-model duplicate live load patterns or unproven mass.
Those require next-stage FE adapters, not implicit approximation.

## Generated artifacts

- `independent-sar.json`: exact run result, all signed OpenSees member I/J
  actions, checked member IDs, M08/09/10 bounded results and incomplete design
  statuses.
- `independent-sar.html`: seven-chapter source-TOC casebook with 18-module
  registry/this-run status comparison, actual numerical RC check summaries,
  force/moment tables, case provenance, missing code/design gates and links
  to adopted standards.
- `independent-sar-member-ends.csv`: every source case/combination and I/J
  member end with N, Vy, Vz, T, My, Mz **signed**.
- `independent-sar-manifest.json`: deterministic SHA256 artifact receipt.

The code independently recomputes the SHA256 of the model+case+combination
inputs and verifies the signed FE-to-RC handoff from the *same OpenSees model*.
It requires independent 3-force/3-moment global equilibrium and hash readback.
A SHA256 manifest is an integrity aid, not proof of model adequacy.

## Scope/limits and next work

Current test example: synthetic two-column/two-beam-segment frame, five nodes
and two static cases, with two algebraic combinations. It intentionally
screens only BM1, COL1, and one joint T1; the other beam and column remain
explicitly `NOT_EVALUATED`. The example is **not** the Pokhara G+1.5
building.

The next essential engineering work is **real project-grounded first-party
geometry and loads** followed by conforming shell/frame FE, verified
diaphragms, eigen/seismic/wind cases, numerical mesh convergence, all relevant
code combinations, complete RC member/slab/stair/footing checks and report
production. The historical F3 one-way-shear adverse result remains visible
until independently checked/revised with verified actual inputs and
geotechnical evidence. Building design acceptance requires qualified
independent professional engineering review.

Do not tag a complete-engine milestone from R6.21.
