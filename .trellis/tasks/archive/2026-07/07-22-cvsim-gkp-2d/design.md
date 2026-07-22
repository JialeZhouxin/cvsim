# Design · δ2 2D lattice

## API surface

```python
LatticeMode = Literal["1d", "2d"]

def gkp0(..., cross="none", lattice="1d"):
def gkp1(..., cross="none", lattice="1d"):
```

## Builders

```text
lattice=1d → _gkp_x_comb(...)   # existing
lattice=2d → _gkp_xp_grid(...)
  if cross != "none": raise
  V = (ε/2) I
  for k,l in {-N..N}²:
    rbar = (x_of_k(k), l*Δ)   # gkp1: x_of_k = (k+½)Δ
    w_raw = a[k,l]²
  renorm
```

## Files

- `cvsim/bosonic/gkp.py`
- `tests/test_bosonic_gkp_2d.py`
- USER_ACCEPTANCE / README

## Risk

| 风险 | 缓解 |
|------|------|
| 破 1d | lattice 默认 1d |
| V 约定混淆 | docstring 写清 2d 用 (ε/2)I |
| K 爆炸 | 2d 禁 nn/full |
