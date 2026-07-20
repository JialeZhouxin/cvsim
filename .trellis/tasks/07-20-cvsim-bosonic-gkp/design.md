# Design · gkp0（A 档）

## Formula

```text
Δ = √(2π)
for k in -N … N:
  r̄ = (k Δ, 0)
  V  = 0.5 * diag(ε, 1/ε)
  w̃_k = exp(−π ε k²)
w_k = w̃_k / ∑ w̃
```

## Files

```text
cvsim/bosonic/gkp.py      # gkp0
cvsim/bosonic/__init__.py
tests/test_bosonic_gkp.py
README + quality
```

## Honesty note

对角实权重 = 混合/对角近似齿梳，非完整纯态 GKP 的 4-方向交叉。文档 docstring 写明。

## Tests

prd AC-G*。
