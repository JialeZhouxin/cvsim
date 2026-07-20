# Design · Homodyne sample B

## G

```python
def homodyne_sample(state, mode=0, phi=0.0, *, rng=None) -> float:
    rng = rng or np.random.default_rng()
    mu = homodyne_mean(...)
    var = homodyne_var(...)
    if var <= eps: raise
    return float(rng.normal(mu, sqrt(var)))
```

## B

```python
def homodyne_sample(state, mode=0, phi=0.0, *, rng=None, imag_tol=1e-12) -> float:
    # pool real peaks with Re(w)>0
    # p ∝ Re(w); k = rng.choice
    # mu = u·rbar.real; var = uᵀVu
    # return rng.normal(mu, sqrt(var))
```

## Files

| File | Change |
|------|--------|
| `cvsim/gaussian/observables.py` | +sample |
| `cvsim/bosonic/observables.py` | +sample |
| `cvsim/*/ __init__.py` | export |
| `tests/test_homodyne_sample.py` | AC-S* |

## Tests

- seed=0 固定
- cat：N=200，数左右邻域 counts
