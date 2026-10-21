# Private G15 3D studio — development implementation

Status: SOURCE-CONNECTED DEVELOPMENT CODE, DEPLOYMENT BLOCKED — no authenticated live URL verified.

The public structural repository contains **application code only** under `secure-studio/`. It NEVER contains the private model, private source PDFs, full G15 JSON data, passwords, or Vercel credentials.

## Source contract
Private archive: `G15_GATE08_PRIVATE_EXECUTION_v0.1.zip`, SHA-256 `c237a8a0f99bff0400969afaa77dd9c02ce77ba0718f2a5a294e522e7e5dda15`, governed Drive file `1YmnTl7Osg9fIhK9FnHCCp7r1ddrD8Itw`.
ZIP is loaded at runtime on trusted server only. It contains Gate03 source-derived working model (92 nodes, 165 members, 23 source-grid positions) and private Gate08 3D linear frame solver.
ZIP extraction rejects unsafe paths. SHA-256 and node/member counts are checked before work.

## Implemented controls
- Single authenticated model status endpoint; fail closed without `JP_STUDIO_SERVER_TOKEN` (length >=32) and `JP_G15_PRIVATE_ZIP_PATH` pointing to a checksum-matched server-only archive.
- A restricted same-origin studio page with a nonpersistent access credential. In production put the entire site behind identity-provider SSO, HTTPS and server-side request throttling; no bearer secret in public source.
- User adjustments: assumed beam width and Ec, ULS/SLS/gross effective stiffness, flexible/rigid trial diaphragms, candidate walls, footprint proxy, two tentative beam connectors.
- Calls the actual independent **private** 3D solver rather than the synthetic 2D frame. Uses 51 working-frame load cases, global equilibrium guards and an equal-case governing member-end force table.
- F3 source failure remains `NOT SAFE IN ONE WAY SHEAR` regardless of model changes; no as-built or NBC compliance claim.
- Every run is ephemeral until private versioned persistence is implemented. Exports response JSON on demand only.
- The backend is Python+SciPy; **not** claimed to be the OpenSees engine. Cross-solver comparison is an outstanding numerical validation.

## Installation and deployment prerequisites
1. Obtain Vercel team permission **for the existing connected scope**. On 21 Oct 2026 the `create_git_project` request was denied HTTP 403; no Vercel application was created.
2. Use private/server-only runtime filesystem (or authenticated object storage) to supply the ZIP file and set `JP_G15_PRIVATE_ZIP_PATH`; checksum verified at request time.
3. Configure `JP_STUDIO_SERVER_TOKEN` as protected encrypted server secret, not in repository, publicly visible JS, or build logs.
4. Require HTTPS, SSO and rate limits before production use. Runtime needs CPU, memory and enough execution time for 51 sparse 3D analyses; Vercel Hobby short-function limits may be unsuitable. A dedicated authenticated Python service may be required.
5. Install `pip install -r secure-studio/requirements.txt`; launch `cd secure-studio && uvicorn api:app --host 127.0.0.1 --port 8765` in a trusted environment, then front through protected HTTPS proxy.
6. Confirm GET /api/status with correct token, run /api/analyze and check 165 members, 51 source-case solutions, 165 same-case signed force records, archive SHA, F3=FAIL and numerical balance; preserve old public Pages version.

## Exclusions
No project-authenticated deployed URL yet. No automatic private Drive sync, durable job queue, full drawing model editor, slab meshing, modal CQC/response spectrum, or engineer-approved design. Existing GitHub Pages remains the real-case de-identified journal.
