# Utility & Reference Scripts

Standalone verification/analysis scripts — **not part of the cvsim public API**.

## Contents

| File | Purpose |
|------|---------|
| `_tw_fidelity_src.py` | Reference fidelity implementation from Xanadu `thewalrus` (Apache 2.0). Used during implementation to cross-validate `cvsim.gaussian.analyse.fidelity()`. |
| `_tw_gauss_checks.py` | Reference Gaussian-state property checks from Xanadu `thewalrus` (Apache 2.0). Used to validate covariance matrix tests. |
| `review_f_analyse_3_verify.py` | Independent verification of `log_negativity()` against analytic TMSV formula and cross-checks. |

## Usage

Run from project root:

```bash
python scripts/review_f_analyse_3_verify.py
```

These are **one-shot review scripts**, not continuous validation. The continuous tests live in `tests/`.
