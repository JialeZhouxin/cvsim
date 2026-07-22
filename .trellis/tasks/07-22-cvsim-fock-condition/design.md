# Design · Fock condition

## Core

```python
# observables.py
def _fock_x_eigen_amps(cutoff, outcome, phi) -> np.ndarray:
    # phase-rotated HO basis at x=outcome → amps, L2 renorm
    ...

def homodyne_condition(state, mode=0, phi=0.0, outcome=...) -> FockState:
    _require_1mode_homodyne(state, mode)
    amps = _fock_x_eigen_amps(state.cutoff, outcome, phi)
    return FockState(amps=amps)

def homodyne_sample_and_condition(...):
    o = homodyne_sample(...)
    return o, homodyne_condition(state, mode, phi, o)
```

Reuse `_ho_basis_x`, `_amps_for_phi` patterns from sample.

Note: post-state **independent of state amps/rho** (projective).  
Still take `state.cutoff` so truncation matches input.

## Export

`fock/__init__.py`

## Tests

`tests/test_fock_condition.py`

- vacuum → cond(0.5) mean≈0.5  
- coherent prior same post mean (independence smoke)  
- var after < 0.5  
- sample_and_condition seed path  
- nmode=2 raises  

## Docs

USER_ACCEPTANCE / README / optional 01 one line pure theory
