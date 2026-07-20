# Design · GKP nn cross

## Formula

```text
Δ = √(2π)
V = ½ diag(ε, 1/ε)
k = -N … N
a_k ∝ exp(−π ε k² / 2)     # unnormalized
```

### none
`w_k = a_k² / Σ a²`（= 现 `exp(−π ε k²)` 归一，因 a²∝exp(−π ε k²)）

### nn
1. 建对角：`w_k⁰ = a_k²`，`r̄=(x_k,0)`
2. 对 k=-N…N-1：
   - `Δr = (x_k − x_{k+1}, 0) = (−Δ, 0)` 或用 (x_k−x_{k+1})
   - `ov = exp(−⅛ Δrᵀ V⁻¹ Δr) = exp(− Δ² / (4ε) ) = exp(−π/(2ε))`
   - `w_c⁰ = a_k a_{k+1} * ov`
   - 两组件：r̄ = (m, ±i d) with `m=(x_k+x_{k+1})/2`, `d=(x_k−x_{k+1})/2`
3. `w ← w⁰ / Σ w⁰`（所有对角+交叉）

K_nn = (2N+1) + 2·(2N) = **6N+1**

## File

改 `cvsim/bosonic/gkp.py` 仅；导出不变（同 `gkp0`）。

## API

```python
def gkp0(
    epsilon: float = 0.1,
    grid_size: int = 3,
    *,
    cross: Literal["none", "nn"] = "none",
) -> BosonicState: ...
```

`cross` 非法 → ValueError。

## Tests

`tests/test_bosonic_gkp_cross.py` + 旧 `test_bosonic_gkp.py` 默认 none。
