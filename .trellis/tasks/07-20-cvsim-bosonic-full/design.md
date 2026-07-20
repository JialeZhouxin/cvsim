# Design · Bosonic 矩闭环

## 1. Scope

| 内 | 外 |
|----|----|
| vacuum、加权 ⟨n⟩ / Homodyne | loss、GKP、Wigner |
| 既有门 + cat 回归 | 改 F/G |

## 2. Files

```text
cvsim/bosonic/state.py       # + vacuum [, from_gaussian]
cvsim/bosonic/observables.py # + mean_photon, homodyne_*
cvsim/bosonic/__init__.py
tests/test_bosonic_full.py
```

门文件基本不动。

## 3. Physics

单组件高斯（ħ=1 xxpp）：

\[
\langle n_i\rangle_k=\frac12\bigl(V_{x_ix_i}+r_{x_i}^2+V_{p_ip_i}+r_{p_i}^2-1\bigr)
\]

多组件（准概率权重 \(w_k\)，可复）：

\[
\langle O\rangle=\sum_k w_k\langle O\rangle_k
\]

Homodyne \(x_\phi=u\cdot r\)：

\[
\mu=\sum_k w_k\,(u\cdot\bar r_k)
\]

\[
\langle x_\phi^2\rangle=\sum_k w_k\bigl(u^{\mathsf T}V_k u+(u\cdot\bar r_k)^2\bigr)
\]

\[
\mathrm{Var}=\langle x_\phi^2\rangle-\mu^2
\]

实现：全程 complex 累加，返回 `float(x.real)`；`|Im|` 过大可 warn/raise（默认 atol 1e-8 仅测）。

## 4. API

```python
BosonicState.vacuum(nmode: int = 1) -> BosonicState

def mean_photon(state, mode: int | None = None) -> float: ...
def homodyne_mean(state, mode: int = 0, phi: float = 0.0) -> float: ...
def homodyne_var(state, mode: int = 0, phi: float = 0.0) -> float: ...
```

`from_gaussian`：可选一行工厂。

## 5. Tests

见 prd AC-B*。AC-B2 用 Gaussian 对照位移/挤压。

## 6. Trade-offs

| 选择 | 原因 |
|------|------|
| 取实部返回 float | 与现 API 一致 |
| 不重写 cat | 权重合同已锁 |
| 不实现 loss | D2=A |
