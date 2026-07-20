# Design · B condition complex likelihood

## Formula (per component)

Same as G but `r̄` complex:

```text
v = V u,  σ = uᵀVu,  μ = u·r̄
V' = V − vvᵀ/σ
r̄' = r̄ + v (outcome − μ)/σ
L = (2πσ)^{-1/2} exp(−(outcome−μ)²/(2σ))
w' ∝ w L ;  renorm ∑w'=1
```

Real `r̄` path: μ,L real → **identical** to current A + G.

## Implementation

**Do not** call `g_homodyne_condition` for complex (it casts real).  
Inline update for all components (or branch: real → reuse G; complex → inline).  
Simplest: **always inline** 5 lines (avoid dual path drift); real case still matches G numerically.

Remove drop-cross loop; remove `imag_tol` or ignore.

```python
def homodyne_condition(state, mode, phi, outcome) -> BosonicState:
    u = ...
    for c in components:
        v = c.V @ u
        sigma = float(u @ v)
        mu = complex(u @ c.rbar)  # or (u @ c.rbar)
        L = (2*pi*sigma)**(-0.5) * np.exp(-0.5*(outcome-mu)**2/sigma)
        Vn = c.V - outer(v,v)/sigma
        rn = c.rbar + v * ((outcome-mu)/sigma)
        keep Component(Vn, rn, w*L)
    renorm
```

## Test rewrites

| Old | New |
|-----|-----|
| cat: no complex, K=2 | cat: may K=4; has complex; +w > −w |
| all-complex raises | all-complex OK, ∑w=1 |
| single ≡ G | keep |

## Files

- `cvsim/bosonic/observables.py`
- `tests/test_bosonic_condition.py`
- quality + README
