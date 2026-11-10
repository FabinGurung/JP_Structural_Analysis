# R6.15 CI verification branch

The existing R6.15 source branch is under PR #23. This SHA-frozen QA branch is
created solely to trigger the repository's established site/** push CI, because
the PR event did not launch GitHub Actions after the current GitHub/Vercel
integration context. It contains the exact R6.15 audit code and tests from
source commit 6a687e3af5997f8ae47ce5b5f1043132f7f125f5; this extra text file does not affect calculations.

Gate: full Python regressions, generated report, Chromium desktop/mobile,
original 77/308 evidence scope, 12 unsupported shells, and F3 shear HOLD.

Do not merge, publish, or claim structural safety based on Vercel's unrelated
rate-limit check or a generated branch without its successful CI evidence.
