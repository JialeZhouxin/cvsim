# Design · gkp1

## Tooth set

Match |0| diagonal count style:

```text
N = grid_size
|0| none: k=-N..N          → K=2N+1
|1| none: k=-N..N-1        → K=2N     peaks at (k+1/2)Δ
```

Or use k=-N..N with (k+1/2)Δ → K=2N+1 same as gkp0 (prefer **same K** for UI).

**Lock: same K as gkp0** — k=-N..N, x_k=(k+½)Δ.

nn: pairs of neighbouring teeth still spacing Δ; K_nn = 6N+1 same formula as gkp0.

## Code

`cvsim/bosonic/gkp.py`:

- factor shared builder `_gkp_comb(offsets, ...)` OR thin `gkp1` copy-paste with half shift
- prefer **shared helper** to avoid drift:

```python
def _gkp_x_comb(epsilon, grid_size, x_of_k, cross):
    ...
def gkp0(...):
    return _gkp_x_comb(..., x_of_k=lambda k, d: k*d, ...)
def gkp1(...):
    return _gkp_x_comb(..., x_of_k=lambda k, d: (k+0.5)*d, ...)
```

## Tests

`tests/test_bosonic_gkp1.py`

## Export

`bosonic/__init__.py`
