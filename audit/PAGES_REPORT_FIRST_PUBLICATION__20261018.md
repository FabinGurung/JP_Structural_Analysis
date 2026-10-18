# Report-first GitHub Pages deployment — dispatcher-only update

Date: 2026-10-18 Nepal time
Public website: https://fabingurung.github.io/JP_Structural_Analysis/
Public release baseline: `a9-seq9-phase-c-20261015` / `f7c2f8ad7d06ec18b750835b311748b129f39a36` (unchanged and on hold).

## Narrow scope
The `main` branch is only the GitHub Pages dispatcher. It checks out **exact immutable site snapshot** `443b6b8c7d92b0885cd03cad350496d8af61fc46` from a reviewed, successful CI run https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/39087509543 . This is **not** a merge of the experimental engine into `main`, not a structural-analysis product release, and not approval of any private report.

## Pages output
Four pages with unified compact stylesheet and app script:
- `/index.html`: concise source→load→solve→design→report workflow
- `/calculation-coverage.html`: searchable modules, state sourced from registry generated JSON projection
- `/report.html`: report chapter/output stages and R&D LaTeX link
- `/more.html`: legacy benchmark, Actions, frozen release, source/history

The sanitized mathematical benchmark remains at `/demo/SAR.html`, now de-emphasized under More. Its result package is a separate report artifact, not general site navigation. Old hero/screens and historical layout remain retrievable in Git history at `f91224b4...`.

## Deployment gating
Pages checkout fixed SHA → `pytest -q` → privacy scanner → generated sanitized SAR → coverage projection checker → static site link/theme checker → Node JS syntax checker → write build metadata → Pages artifact → deploy.

Legacy `SAMPLE_MDM_001` reactions discrepancy remains a HOLD. The full RC analysis/design and a real-project SAR are not completed. Client files stay in private Drive. Site content shows bounded/draft/missing calculations without claiming full code or professional acceptance.

## Future update rule
Never checkout a moving experimental branch from Pages. Every website promotion requires successful exact SHA CI and a new `main` dispatcher pin. Do not modify A7 or the frozen Seq9 tag.
