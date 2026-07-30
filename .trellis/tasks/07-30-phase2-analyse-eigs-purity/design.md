# Design: F-ANALYSE-1 symplectic_eigenvalues + purity

## 目的
锁定两个函数的算法、签名、边界 guard、测试对账点，作为实现前提。

## 文件改动
| 文件 | 动作 |
|------|------|
| `cvsim/gaussian/analyse.py` | 新增 `symplectic_eigenvalues` + `purity`（保留现有 `is_physical` / `validate_state`） |
| `cvsim/gaussian/__init__.py` | 导出两个新函数 |
| `tests/test_analyse.py` | 新建（或扩展，若已有则 append） |

## API 签名

```python
def symplectic_eigenvalues(
    state: GaussianState | np.ndarray,
    *,
    atol: float = 1e-10,
) -> np.ndarray:
    """Return m symplectic eigenvalues ν_j ≥ 1/2 (ascending, float64).

    Williamson decomposition via Cholesky path (Serafini / Weedbrook).
    Accepts GaussianState or bare covariance V (2m×2m).
    Does NOT call validate_state; clips ν ≥ 0.5 for float64 roundoff.
    """

def purity(
    state: GaussianState | np.ndarray,
) -> float:
    """Return μ = 1 / (2^m √det V). Pure Gaussian → 1.

    Uses slogdet for numerical stability (vision §7).
    Raises ValueError if det(V) ≤ 0 (sign ≤ 0 from slogdet).
    Accepts GaussianState or bare covariance V.
    """
```

## 算法：Cholesky-Williamson (锁定)

```
Input: V (2m × 2m real symmetric PSD)
1. V ← ½(V + Vᵀ)                         # symmetrize (vision §7)
2. try: K = chol(V)                       # V = K Kᵀ
   except LinAlgError:
       K = chol(V + 1e-14 · I)            # jitter for near-singular pure states
3. A = Kᵀ Ω K                             # skew-symmetric
4. λ = eigvals(i A)                       # real ±ν pairs
5. ν_all = sort(|Re(λ)|)                  # length 2m, pairs
6. ν = ν_all[::2]                         # take one per pair → length m
7. ν = maximum(ν, 0.5)                    # clip roundoff below vacuum
8. return ν.astype(float64)
```

**关键陷阱（实测）**：`ν_all[m:]`（取上半）对 thermal product `[0.8,0.8,1.5,1.5]` 错取成 `[1.5,1.5]`。必须用 `[::2]`。

**cite**：Serafini, *Quantum Continuous Variables* §3.2; Weedbrook et al., RMP 84, 621 (2012) §II.B.

## 算法：purity (锁定)

```
Input: V (2m × 2m)
1. m = V.shape[0] // 2
2. sign, logdet = slogdet(V)
3. if sign ≤ 0: raise ValueError("det(V) ≤ 0: non-physical or singular")
4. return exp(-0.5 * logdet) / 2^m
```

**交叉验（测试用，非公开 API）**：$\mu = \prod_j 1/(2\nu_j)$。单测可对照两条路径。

## 输入归一化 helper（内部）

```python
def _as_cov(state: GaussianState | np.ndarray) -> np.ndarray:
    if isinstance(state, GaussianState):
        return np.asarray(state.V, dtype=float)
    V = np.asarray(state, dtype=float)
    if V.ndim != 2 or V.shape[0] != V.shape[1] or V.shape[0] % 2 != 0:
        raise ValueError(f"covariance must be even square, got {V.shape}")
    return V
```

与 `is_physical` 的 isinstance 分支对齐，抽 helper 避免三处重复。

## 测试对账点 (atol=1e-10 默认, 与 is_physical 一致)

| Case | symplectic_eigenvalues | purity |
|------|------------------------|--------|
| vacuum(1) | `[0.5]` | 1.0 |
| vacuum(3) | `[0.5, 0.5, 0.5]` | 1.0 |
| thermal(nbar=0.5, m=1) | `[1.0]` | 0.5 |
| thermal(nbar=2.0, m=1) | `[2.5]` | 1/5=0.2 |
| TMSV(r=0.6, m=2) pure | `[0.5, 0.5]` | 1.0 |
| TMSV(r=0.6)+loss(T=0.8) | all ≥ 0.5, length 2 | < 1 |
| product(thermal(0.3), thermal(1.0)) | `[0.8, 1.5]` | $1/(1.6·3)=0.2083$ |
| bare ndarray vacuum V | same as vacuum(1) | 1.0 |
| non-PD V (e.g. -I) | — | raise ValueError |

## 导出

`cvsim/gaussian/__init__.py` 现有导出列表追加：
```python
from cvsim.gaussian.analyse import (
    is_physical,
    validate_state,
    symplectic_eigenvalues,  # NEW
    purity,                  # NEW
)
```

## 风险与回滚

| 风险 | 缓解 |
|------|------|
| 纯态 chol 奇异（det V = (1/4)^m 近 0 for large m） | jitter $10^{-14}I$；m≤10 教学场景足够 |
| `[::2]` vs `[m:]` 取错 | 单测 thermal product 不同 nbar 锁死 |
| slogdet sign=0 边界 | raise 明确；测试覆盖 |
| 与 is_physical 的 isinstance 分支漂移 | 抽 `_as_cov` helper 统一 |

## 不做
- 不重构 `det_cov`（保持 `np.linalg.det`）
- 不在函数内调 `validate_state`
- 不实现下游 entropy_vn / log_neg / fidelity / partial_trace
