# Design · Bosonic condition Homodyne (A)

## Flow

```text
for each component k:
  if max|Im r̄_k| > tol: skip
  else:
    (V', r̄') = gaussian-like update (real)
    L_k = gauss_pdf(outcome; μ_k, σ_k)
    keep (V', r̄', w_k * L_k)
renorm ∑w = 1
```

## Reuse

Prefer call into G formula without wrapping full GaussianState if r̄ complex-as-real:

```python
# build temporary GaussianState(V, rbar.real) for condition
# then Component(V', rbar'.astype(complex), w*L)
```

Or duplicate 5 lines of V/r update — OK if shorter; **prefer** reuse:

```python
from cvsim.gaussian.observables import homodyne_condition as g_cond
from cvsim.gaussian.state import GaussianState
st_g = g_cond(GaussianState(V=c.V, rbar=c.rbar.real), mode, phi, outcome)
L = ... from pre-update μ,σ on c
```

Need μ,σ **before** update → compute with same `_homodyne_u` as G (real).

## API

```python
def homodyne_condition(
    state: BosonicState,
    mode: int,
    phi: float,
    outcome: float,
    *,
    imag_tol: float = 1e-12,
) -> BosonicState: ...
```

Export from `cvsim.bosonic`.

## Edge

| 情况 | 行为 |
|------|------|
| all complex | ValueError |
| σ ≤ 1e-14 | ValueError（同 G） |
| only one real peak | survives with w=1 |

## Tests

prd AC-C*。cat α=0.8, outcome=+√2*0.8.
