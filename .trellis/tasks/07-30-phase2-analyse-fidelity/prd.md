# F-ANALYSE-4: fidelity

## Goal

`fidelity(state1, state2) -> float`：两高斯态 Uhlmann 保真度 $F\in[0,1]$。

## Math (locked)

- 文献：Banchi–Braunstein–Pirandola, PRL 115, 260501 (2015)；实现对齐 thewalrus `fidelity`（Brask arXiv:2102.05748 Eq.112 的平方形式）。
- 约定：ħ=1，xxpp，`V_vac=I/2`。thewalrus 路径：先把 cov/means 归一到 hbar=1（`σ=V/ħ`），再算。
- 对账 freeze：
  - 相同态 → 1
  - 相干态：$F=\mathrm{e}^{-|\alpha-\beta|^2}$
  - 热态：$F=[\sqrt{(n+1)(m+1)}-\sqrt{nm}]^{-2}$
  - 压缩真空 vs 真空：$F=\mathrm{sech}(r)$

## API

```python
def fidelity(
    state1: GaussianState,
    state2: GaussianState,
    *,
    rtol: float = 1e-5,
    atol: float = 1e-8,
) -> float:
```

只接 `GaussianState`（需要 `rbar` + `V`）；模态数须一致。

## Out of scope

- Heterodyne
- 不改现有 analyse API
