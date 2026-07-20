# Design · Fock 独立全流程（2 模 + Kerr + PNRD）

## 1. Scope

| 内 | 外 |
|----|----|
| 1–2 模 `FockState` | m≥3 |
| Kerr、BS、PNRD | loss、Homodyne |
| 单模 D/R/S 兼容 | Bosonic |

## 2. State

```python
# amps.ndim == 1 → single mode, shape (N,)
# amps.ndim == 2 → two mode, shape (N, N)  # c[n0, n1]
class FockState:
    amps: np.ndarray
    @property
    def cutoff(self) -> int: ...
    @property
    def nmode(self) -> int:  # 1 or 2
    @classmethod
    def vacuum(cls, cutoff, nmode=1): ...
```

构造校验：ndim∈{1,2}；2 模方阵。

## 3. Gates

### 3.1 Single-mode on mode k

- 1 模：现有 matrix × vector
- 2 模 mode=0：`U @ amps` 按 axis 0；mode=1 按 axis 1  
  `np.tensordot` / `einsum`

### 3.2 Kerr

对角：`phase_factor[n] = exp(1j * chi * n**2)`，沿目标轴乘。

### 3.3 BS (2-mode only)

物理：`a0' = c a0 + e^{iφ} s a1`，`a1' = -e^{-iφ} s a0 + c a1`（与 Gaussian U 一致）。

实现（最小可正确）：

1. 建两模 ladder 于 ℂ^{N²}（ravel 序 `n0*N+n1`）  
2. `G = θ * (e^{iφ} a0† a1 - e^{-iφ} a1† a0)` 或标准 BS 生成元  
   - 常用：`BS(θ,φ) = exp(θ(e^{iφ} a0† a1 - h.c.))` 且 50:50 时 θ=π/4  
3. `expm(G) @ vec(amps)` reshape 回 `(N,N)`

注意：截断下 ladder 非精确对易；小 N 有误差——AC 用 cutoff≥8 与解析对比。

可选更轻：固定 θ=π/4 的 binomial 填充（但缺一般 θ）→ **用 expm 统一**。

## 4. Observables

```python
def pnrd_probs(state, mode=None) -> np.ndarray:
    p = np.abs(state.amps) ** 2
    if state.nmode == 1:
        return p.real  # or p
    if mode is None:
        return p  # joint
    # marginal
    return p.sum(axis=1 if mode == 0 else 0)

def norm(state): ...
def mean_photon(state, mode=None): ...
```

## 5. Files

```text
cvsim/fock/state.py      # ndim 1|2
cvsim/fock/gates.py      # +kerr, +beamsplitter, mode= for 1-body
cvsim/fock/observables.py # +pnrd_probs; multi mean_photon
tests/test_fock_full.py  # or split
```

## 6. Compatibility

- `vacuum(N)` 仍单模；`vacuum(N, nmode=2)` 两模
- 旧 demos/tests 只碰单模 → 无改调用

## 7. Tests

见 prd AC-F*。
