# Design · B2 Homodyne（Gaussian 边缘矩）

## 1. Scope

| 内 | 外 |
|----|----|
| Gaussian `homodyne_mean` / `homodyne_var` | 条件更新、采样 |
| 单/多模按 `mode` 选 (x,p) 槽 | Bosonic/Fock Homodyne |
| pytest AC-H1–H4 | PNRD / 通道 / S₂ |

## 2. Architecture

```text
cvsim/gaussian/observables.py   # + homodyne_mean, homodyne_var
cvsim/gaussian/__init__.py      # export
tests/test_b2_homodyne.py       # AC
```

无新包。不碰 `symplectic.py`（除非发现 helper 必要——本切片不需要）。

## 3. Physics（ħ=1, xxpp）

Mode `i`：

\[
x_\phi = x_i\cos\phi + p_i\sin\phi
\]

均值：

\[
\langle x_\phi\rangle = \bar r_i\cos\phi + \bar r_{m+i}\sin\phi
\]

方差（中心）：

\[
\mathrm{Var}(x_\phi) = \mathbf u^\top V \mathbf u
\]

其中 `u` 为全零向量，仅 `u_i=\cos\phi`，`u_{m+i}=\sin\phi`。

等价展开：

\[
\cos^2\phi\, V_{xx} + \sin^2\phi\, V_{pp} + 2\sin\phi\cos\phi\, V_{xp}
\]

真空：`V=I/2` → 任意 φ 方差 `1/2`。  
挤 `S(r)` 后对角：`V_xx=½e^{-2r}`，`V_pp=½e^{2r}`。

位移与 B1 一致：`d_x=√2 Reα`，`d_p=√2 Imα` →

\[
\langle x_\phi\rangle = \sqrt2\,(\mathrm{Re}\alpha\cos\phi + \mathrm{Im}\alpha\sin\phi).
\]

## 4. API

```python
def homodyne_mean(state: GaussianState, mode: int = 0, phi: float = 0.0) -> float: ...
def homodyne_var(state: GaussianState, mode: int = 0, phi: float = 0.0) -> float: ...
```

- `phi=0` → x；`phi=π/2` → p  
- mode 越界 → `IndexError`（与 gates 一致）

## 5. Trade-offs

| 选择 | 原因 | 代价 |
|------|------|------|
| 仅边缘矩 | B2 最短可验收 | 无后选态 |
| 双函数非 dict | 测试直接 | 多一处 export |
| 无采样 | 确定性 AC | demo 无直方图 |

## 6. Test strategy

- 解析恒等式 AC-H1–H3  
- H4：与 `uᵀVu` 直接算对照  
- 回归全量 pytest
