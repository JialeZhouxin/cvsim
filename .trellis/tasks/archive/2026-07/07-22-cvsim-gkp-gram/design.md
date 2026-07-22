# Design · δ3 Gram

## Core helpers

```python
def _gauss_overlap(V, r_i, r_j) -> complex:
    # real means → real ov; formula match 1d/2d cases

def _build_gram_state(peaks, V, c) -> BosonicState:
    # peaks: list of real rbar (2,)
    # c: amplitudes >0
    # S_ij = overlap(V, r_i, r_j)
    # Z = c @ S @ c
    # diag + full pairs ± complex centers (generalize 1d pair helper to 2d Δr)
```

Generalize `_append_cross_pair` from (x0,x1) to full `r0,r1` vectors:

```text
m = (r0+r1)/2
d = (r0-r1)/2   # real vector
r̄± = m + (±i) d   # elementwise? 
# 1d was: r=(m_x, ±i d_x) with d_x=(x0-x1)/2
# 2d: r = m + i * sign * d  (complex vector in C^2)
```

## Wiring

- 1d full/nn → call shared builder with 1d peaks  
- 2d none → existing diag  
- 2d full → same builder with 2d peaks  

## Overlap teaching

Diagonal-peak approximation for two GKP states with same V:

```text
ov = (c† T d) / sqrt(Z0 Z1)
T_ij = ⟨g_i^{0}|g_j^{1}⟩
```

Export `gkp_logical_overlap(a, b)` using components with **real rbar only** (diag peaks) as the c-basis; honesty in docstring.

## Files

- `cvsim/bosonic/gkp.py`
- `cvsim/bosonic/__init__.py`
- `tests/test_bosonic_gkp_gram.py`
- docs
