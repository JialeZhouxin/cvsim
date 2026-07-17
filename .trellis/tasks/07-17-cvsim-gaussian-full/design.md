# Design · Gaussian 全流程

## 1. Scope

| 内 | 外 |
|----|----|
| `homodyne_condition` | 删模 condition、采样 |
| `loss(T)` | 热浴放大、F/B |
| G 测 + README | PNRD |

## 2. Architecture

```text
cvsim/gaussian/observables.py  # + homodyne_condition (or measure.py — prefer observables)
cvsim/gaussian/channels.py     # NEW: loss  (thin; avoid stuffing into gates)
cvsim/gaussian/__init__.py
tests/test_g1_homodyne_condition.py
tests/test_g2_loss.py
```

`channels.py` 新文件：通道 ≠ 门；YAGNI 但目录清晰。

## 3. Physics

### 3.1 条件 Homodyne（理想，ħ=1 xxpp）

`u` 长 `2m`，仅 `u[mode]=cosφ`，`u[m+mode]=sinφ`。

\[
\sigma = u^{\mathsf T} V u,\quad
\mu = u\cdot \bar r,\quad
v = V u
\]

\[
V' = V - \frac{v v^{\mathsf T}}{\sigma},\qquad
\bar r' = \bar r + v\frac{\mathrm{outcome}-\mu}{\sigma}
\]

要求 `σ > ε`（否则 raise `ValueError`）。

不删模 → `V'` 在 `u` 方向奇异；符合理想投影。

### 3.2 光子损失

选模集合 `S`（单模或全体）：

- 对 `i∈S`：`X` 在 `x_i,p_i` 对角 √T；`Y` 同位置 `(1-T)/2`
- 其余模：`X=I`，`Y=0`

\[
V' = X V X^{\mathsf T} + Y,\qquad \bar r' = X \bar r
\]

## 4. API

```python
def homodyne_condition(
    state: GaussianState, mode: int, phi: float, outcome: float
) -> GaussianState: ...

def loss(
    state: GaussianState, T: float, mode: int | None = None
) -> GaussianState: ...
```

## 5. Slice plan

1. **G1** condition + tests AC-C*
2. **G2** loss + tests AC-L*
3. README + quality 合同
4. 全量回归

## 6. Trade-offs

| 选择 | 原因 |
|------|------|
| 不删模 | API 稳、实现短 |
| `channels.py` | 与 gates 分离 |
| `Y=(1-T)I/2` | 对齐 `V_vac=I/2` |

## 7. Tests

见 prd AC-C* / AC-L*。
