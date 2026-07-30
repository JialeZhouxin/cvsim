# Design: entropy_vn + partial_trace

## API

```python
def entropy_vn(
    state: GaussianState | np.ndarray,
    *,
    validate: bool = False,
) -> float:
    """Von Neumann entropy S = Σ g(ν_j) in nats (ħ=1)."""

def partial_trace(
    state: GaussianState,
    keep: int | Iterable[int],
) -> GaussianState:
    """Reduce to subsystem `keep` (logical mode indices). No measurement collapse."""
```

## g(ν) — bosonic thermal entropy (nats)

With mean occupation $n = \nu - 1/2$:

$$
g(\nu) = (n+1)\ln(n+1) - n\ln n
$$

Equivalent form:

$$
g(\nu)=(\nu+\tfrac12)\ln(\nu+\tfrac12)-(\nu-\tfrac12)\ln(\nu-\tfrac12)
$$

At $\nu=1/2$ ($n=0$): $g=0$ by continuity. Implement via $n=\max(\nu-1/2,0)$ and mask $n\le\varepsilon$.

## partial_trace (xxpp)

- Normalize `keep` → sorted unique list of ints in `0..m-1`.
- Empty keep → `ValueError`.
- Out of range → `IndexError`.
- Index map: for each kept mode $k$, keep axes $k$ (x) and $m+k$ (p).
- `V_out = V[np.ix_(idx,idx)]`, `r_out = rbar[idx]`.
- Return `GaussianState(V=V_out, rbar=r_out)`.

Note: not the same as mid-circuit measure+`remove_mode` when conditioning on outcomes; docstring must say so.

## Tests

| case | expect |
|------|--------|
| vacuum any m | S=0 |
| thermal nbar | closed form |
| TMSV whole | S=0 |
| TMSV → keep [0] | S = S_thermal(sinh²r) |
| product two thermals | S = S1+S2 |
| ptrace keep all | equal V,rbar |
| ptrace drop uncorrelated mode | matches remove_mode chain |
| bad keep | raise |
| entropy validate=True on 0.4I | raise |
