# G15 public 3D Studio authorized GitHub workflow revision, 21 October 2026
- Previous pinned source: `04de562d6f94d0583c49a2f7907e7d9118444f9c`.
- Revised pinned source: `c4353c564a256c49fe0d2680f68d89814bef16a0`.
- GitHub connection which created audit issue #5 is `Kaksaveksaka`; the issue-runner initially allowed only `FabinGurung`.
- Allow precisely these two repository contributor identities to initiate hosted OpenSees runs. Any GitHub user can still inspect, edit in the browser, download model data, and fork to run the fully open-source code. General-public issues do not spend shared Actions capacity.
- Regression new source: https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/39529452202 (source 165-member FE, author gate test, F3 failure preserved).
- Website source `site/g15-3d.html` is open; GitHub Pages build generates pinned default five-case 3D reference result and checks signed member data.
- Source grade: derived geometry, 96 inferred beam segments, two hypothetical connections, slab/diaphragm/mass unreconciled. Structural engineering approval HOLD.
- This change has no Vercel dependency, no new secrets, no third-party licensed SP16 scans and does not modify frozen Seq9 or PR #4.
