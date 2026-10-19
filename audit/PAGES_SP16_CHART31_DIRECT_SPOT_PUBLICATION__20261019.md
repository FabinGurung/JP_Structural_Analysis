# Controlled SP16 Chart31 two-point publication — 19 October 2026

## Verified source and bounded QA
- Public site root: https://fabingurung.github.io/JP_Structural_Analysis/
- Source branch: `site/sp16-chart31-benchmark-20261019`.
- New immutable site snapshot: `017e3bc0ee07956319f34941d522960888869b83`.
- Source CI: https://github.com/FabinGurung/JP_Structural_Analysis/actions/runs/39270401364
- CI verified: 218 pytest tests, source projection PASS, public-data safety PASS, four-page site check PASS, and the generated original-source Chart31 spot-check artifact.
- Source SP16:1980, physical PDF page 139, printed page 116, 255 original pages, SHA256 `d2a6246a5dc7504568f4e55f310dd4be9d925fb1a8b04b6d7f5132c93f66c76e`. Source original and full corpus are in governed **private** Google Drive.
- Reference table original Table A PDF p29, Fe415/Fe500 12 design stress points.
- Original chart is Fe415, d'/D=0.05, two-face reinforcement.
- Source-fixed manual plotted coordinates at Pu/(fck bD)=.25 and .44, Mu/(fck bD²) ≈ .082 and .030 respectively, absolute visual uncertainty .010. The engine's original-source computed values are ≈.0818613 and .0289821. This is a **two-point approximate visual spot-check**, not full curve digitization or code-version approval.
- The original scanned PDF, original graphs and complete page text are not publicly hosted.

## Change surface
- Calculations Chart31 panel now exposes measured / computed spot values and uncertainty.
- Report provides the same source-code distinction and acceptance limitations.
- Every public Pages build regenerates the numeric `site/data/sp16_chart31_spotcheck.v0.1.json` from the registered 1980 source ordinates and column solver. Source CI fails if spot checks disagree.
- `scripts/check_site.py` validates original source SHA256, 2 point pairs, coarse uncertainty and safety-HOLD flags.
- Current light Engineering Guild theme, existing mobile layout, M09 and D2 synthetic displays retained.

## Editions and decisions
- 1980 SP16 design aids derive from IS456:1978; modern engine currently cites IS456:2000. Numeric concrete law and Fe415/500 primary Table A knots have bounded agreement, but whole-clause edition equivalence, source-specific material behavior, NBC105:2025 details, actual building model and professional acceptance remain HOLD.
- SP16 §3.2.3.1 notes using an M20-based approximation of displaced concrete for charts; the first-party fiber solver subtracts local displaced concrete, which can yield small legitimate numeric differences.
- No independent complete SP16 Chart31 curve vectorization, full NBC ductile detailing, real project response-spectrum or P–Delta certification is claimed.

## Exact previous deploy and rollback
- Prior immutable publication source commit: `2349678ff60f8f69d24643b62709b4e6d1207e1b`.
- Prior `main` Pages dispatcher commit: `b10f188a4458e2b9981a227cce7ea74808945039`.
- Restore by editing only `main:.github/workflows/pages.yml` checkout ref to `2349678ff60f8f69d24643b62709b4e6d1207e1b` and removing newly added SP16 generation step; trigger workflow and verify old site artifact.

## Governance
- Existing PR #4 remains draft and unmerged.
- Frozen Seq9 source branch/release remains untouched.
- Neither source PDF nor original Drive extraction nor any private building report was exposed to public GitHub.
- One Pages workflow run must be checked for complete deployment PASS separately from prepublication source CI.
