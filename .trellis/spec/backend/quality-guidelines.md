# Quality Guidelines

> Standards for `cvsim` and related backend code.

---

## Overview

MVP stack: **Python + uv + numpy + scipy**. No quantum libraries (DeepQuantum, Strawberry Fields, etc.) as implementation deps.

Acceptance is numeric: analytic identities and cross-representation trends, not “imports without error”.

---

## Forbidden Patterns

| Pattern | Why |
|---------|-----|
| Bind DeepQuantum/API into theory `*.md` | Notes are pure physics |
| Homodyne/PNRD/Hafnian in MVP without new PRD | Out of scope for three-simulators MVP |
| Early Circuit / backend abstraction with one use | YAGNI; three reps may share later |
| Treat Fock truncated-unitary `norm==1` as “no truncation error” | Truncated U is still unitary on ℂ^N; true deficit needs high-N evolve then project |

---

## Required Patterns

### Physics contracts (`cvsim`)

| Item | Value |
|------|--------|
| ħ | `1` |
| Quad order | `xxpp`: `(x_1..x_m, p_1..p_m)` |
| Vacuum | `V = I/2`, `r̄ = 0` |
| Pure single-mode Gaussian | `det V = 1/4` |
| Vacuum squeeze mean photon | `⟨n⟩ = sinh² r` |

### Fock truncation checks

1. Scan cutoff: `⟨n⟩(N)` approaches `sinh² r`.
2. For **norm deficit**: evolve at high cutoff, **project** amplitudes to low `N`, then `1 - ∑|c|² > 0`.

### Bosonic cat weights

Even/odd cat uses **4 components** (2 diagonal + 2 cross). Cross weights include overlap  
`ov = exp(-2α²)` (real α). After normalize: `∑ w_k = 1`.  
Wrong: set cross weight equal to diagonal without `ov`.

### Gaussian squeeze (xxpp, mode `i`)

- `x_i → e^{-r} x_i`, `p_i → e^{r} p_i`
- Vacuum single-mode: `V = ½ diag(e^{-2r}, e^{2r})`

---

## Testing Requirements

- Each milestone: pytest under `tests/` **and** `python -m cvsim.demos.m*_...` green.
- New observable/gate: at least one analytic or cross-backend assert.
- Commands:

```bash
uv pip install numpy scipy pytest
python -m pytest tests -q
python -m cvsim.demos.m1_gaussian_squeeze
python -m cvsim.demos.m2_fock_cutoff_scan
python -m cvsim.demos.m3_cat_weights
```

---

## Code Review Checklist

- [ ] Conventions match `conventions.py` (no silent ħ/order mix)
- [ ] No quantum-lib dependency added without PRD change
- [ ] Theory MD unchanged re: API bindings
- [ ] Fock error claims use projection or ⟨n⟩ trend, not only `norm(Uψ)`
- [ ] Cat `∑w` and cross/diag structure covered by test
