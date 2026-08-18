# B3 Design — homodyne CDF 网格反演精确采样

> 物理/策略事实源：vision §2.3 + ADR-0006 决策 1。本文件记工程边界、数学实现、坑。

## 1. 边界

- 改动文件：`cvsim/bosonic/observables.py`（`homodyne_sample` 重写 + 新增 `homodyne_pdf` + `homodyne_sample_and_condition` 升级）；`cvsim/bosonic/measure.py`（re-export 不变，docstring 同步去"teaching cut"）；`cvsim/bosonic/__init__.py`（+`homodyne_pdf` 进 `__all__`）；`pyproject.toml`（+`phaseB3` marker）；`tests/test_public_api.py`（BOSONIC_PUBLIC +`homodyne_pdf`）；新增 `tests/test_b3_bosonic_homodyne_exact.py`。
- 不动：`homodyne_condition` / `homodyne_mean` / `homodyne_var`（已是精确闭式）。
- `homodyne_condition` 现在已是精确 Born-rule 闭式（复 r̄/复 w，L may be complex），B3 sample 升级后 `sample_and_condition` 自动走精确路径。

## 2. 数学

### 2.1 单分量 x_φ 边缘高斯

对分量 k，x_φ = x cosφ + p sinφ，投影向量 `u = (cosφ, sinφ)`（xxpp 取 mode 块）：
- `μ_k = u · r̄_k`（复，因 r̄ 可复）
- `σ²_k = uᵀ V_k u`（实，V 对称）
- `p_k(x) = (2π σ²_k)^{-1/2} · exp(−(x − μ_k)² / (2 σ²_k))`

注意 `μ_k` 可复 → `p_k(x)` 可复 → `S(x) = Σ_k w_k p_k(x)` 可复。厄米共轭对闭合保证 `Im(S) ≈ 0`；`is_hermitian`（B2）兜底。取 `P(x) = max(Re S(x), 0)`。

### 2.2 网格自动规则

- σ_min = min over k of `sqrt(σ²_k)`（最窄峰）
- σ_max = max over k of `sqrt(σ²_k)`（最宽峰，定范围）
- 质心 `x̄ = Re(Σ_k w_k μ_k) / Re(Σ_k w_k)`（归一化质心）
- `δx = σ_min / 5`
- 范围 = `[x̄ − 6·σ_max, x̄ + 6·σ_max]`
- `n_grid = ceil((2·6·σ_max) / δx) + 1` = `ceil(60·σ_max/σ_min) + 1`
- override：`n_grid`/`lim` 非 None → `np.linspace(-lim, lim, n_grid)`

### 2.3 CDF 反演采样

1. 算 `P = homodyne_pdf(state, mode, phi, n_grid, lim)` → `(xs, P)`
2. `cdf = np.cumsum(P) * dx`，归一化 `cdf /= cdf[-1]`
3. `u = rng.uniform(0, 1, shots)`
4. `idx = np.searchsorted(cdf, u)`，clamp 到 `[0, n_grid-1]`
5. 返回 `xs[idx]`（shape `(shots,)`）

### 2.4 Born 一致性解析核验（判据 2）

网格上每个 x：
- `ρ_post(x) = homodyne_condition(state, mode, phi, x)`（现有精确闭式，复权重重加权）
- `P(x)·ρ_post(x) = Σ_k w_k p_k(x) ρ_k(x)`（condition 内部已除以 P，乘回来抵消）
- `Σ_x P(x)·ρ_post(x)·δx ≈ ρ`（梯形积分）
- atol=1e-7 验证梯形积分精度

## 3. API 契约

### 3.1 `homodyne_sample`

```python
def homodyne_sample(
    state: BosonicState,
    mode: int = 0,
    phi: float = 0.0,
    *,
    rng: np.random.Generator | None = None,
    n_grid: int | None = None,
    lim: float | None = None,
    shots: int = 1000,
) -> np.ndarray:
    """Sample homodyne outcomes via CDF grid inversion (exact edge distribution).

    P(x) = Σ_k w_k p_k(x) computed on a grid; complex weights handled via
    Re(S) with hermitian-pair closure (is_hermitian guard). Negative Re(S)
    values clipped to 0 (non-physical, warns).

    Grid auto: δx ≤ σ_min/5, range = centroid ± 6σ_max.
    Override n_grid/lim to force a specific linspace.
    """
```

返回 `np.ndarray` shape `(shots,)`。

### 3.2 `homodyne_pdf`

```python
def homodyne_pdf(
    state: BosonicState,
    mode: int = 0,
    phi: float = 0.0,
    *,
    n_grid: int | None = None,
    lim: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Exact edge density P(x_φ) = Σ_k w_k p_k(x) on a grid.

    Returns (xs, P) where P = max(Re S, 0), S = Σ_k w_k p_k(x).
    Hermitian-pair closure ensures Im(S) ≈ 0; is_hermitian guards.
    Negative Re(S) clipped to 0 with a warning (non-physical leak).
    """
```

### 3.3 `homodyne_sample_and_condition`

```python
def homodyne_sample_and_condition(
    state: BosonicState,
    mode: int = 0,
    phi: float = 0.0,
    *,
    rng: np.random.Generator | None = None,
    n_grid: int | None = None,
    lim: float | None = None,
    shots: int = 1,
) -> tuple[np.ndarray, BosonicState]:
    """Sample via CDF inversion then condition (exact path). Returns (outcomes, posterior)."""
```

取 `outcomes[0]` 调 condition（单态返回）。shots>1 时只 condition 首个。

## 4. 坑

- **σ²_k ≤ 0**：V 非正定（数值漂移）→ 抛错（对齐 B1 `_SIG_EPS` 检查）。
- **复 r̄ 的 μ_k**：`p_k(x) = exp(−(x−μ_k)²/(2σ²))` 中 `(x−μ_k)` 可复，结果可复。必须用 complex dtype 全程。
- **lim 太小截断尾**：6σ 已保守，但 GKP ε 小时 σ_max 可能仍大 → override 需要时调。
- **searchsorted 边界**：`u` 接近 1 时 `idx` 可能 = n_grid，clamp。
- **warnings.warn 与 filterwarnings**：cvsim 模块 warning 会触发 `error:cvsim.*`。负 Re(S) warn 用 `warnings.warn(..., stacklevel=2)` 但需确认是否被过滤——若触发 error，改用 `logging.warning` 或测试 `pytest.warns`。**决策**：负 Re(S) 是数值泄漏，应可见 → 用 `warnings.warn`，测试用 `pytest.warns` 捕获；若 `filterwarnings` 报错则 spec §5 纪律下用 docstring 标注 + 不发 warning（静默 clip）。

## 5. 测试设计

新增 `tests/test_b3_bosonic_homodyne_exact.py`，标 `@pytest.mark.phaseB3`：

1. **cat 交叉核对（判据 1）**：even_cat/odd_cat，Bosonic `homodyne_pdf` vs Fock cutoff=30 `_pdf_from_amps`，同 lim+n_grid，逐点 atol=1e-7。
2. **GKP 定性对齐（判据 1）**：gkp0 `homodyne_pdf` 峰位/周期 vs Fock 高 cutoff 定性比（峰位匹配，不锁严格 atol）。
3. **Born 一致性（判据 2）**：cat/相干/热态，网格上 `Σ_x P(x)·ρ_post(x)·δx ≈ ρ`，atol=1e-7。比较 `Component(V, rbar, w)` 的 V/rbar/w。
4. **采样直方图（判据 3）**：cat 态 10⁴ shots，固定种子，分箱直方图 vs `homodyne_pdf` 归一化密度，bin 级相对误差 < 5%。
5. **K=1 Gaussian 对齐**：单高斯态（from_gaussian）`homodyne_pdf` 退化为单高斯密度，与解析高斯密度 atol=1e-12。
6. **回归**：现有 `test_b1_bosonic_measures.py` / `test_bosonic_condition.py` 中 `homodyne_sample` 调用适配新返回类型（float → ndarray，取 `[0]` 或首元素）。
