# B4 — Bosonic 调和对账分层套件 Design

## 1. 范围

B4 = **analyse 闭式补全** + **R1 分层对账套件**（layer 1 退化 atol + layer 2 GKP 内部恒等式）。
- 新增公共 API：`purity`、`pure_fidelity`（BOSONIC_PUBLIC 39→41）
- `overlap` 不在范围（混合态无闭式，跳过）
- Fock `gkp0` 工厂延后 B7（B4 不扩 GKP 跨包交叉核对）

## 2. 数学

### 2.1 purity（混合态纯度）

Bosonic 态 ρ = Σ_k w_k ρ_k，各 ρ_k 是纯高斯态（det V_k 决定 μ_k）。
- 单分量纯度：`μ_k = Tr(ρ_k²) = 1 / (2^m · √det V_k)`（ħ=1, xxpp, 纯态 det V_k = 1/(4^m) → μ_k=1）
- 混合态纯度：`μ = Σ_k |w_k|² · μ_k`（分量正交时；近似成立因 K 小 + 分量空间分离）
  - **诚实标注**：严格 `Tr(ρ²) = Σ_{i,j} w_i w_j* Tr(ρ_i ρ_j)`，非对角项 `Tr(ρ_i ρ_j)` 非零（Gaussian overlap kernel）。
  - B4 实现取 `Σ |w_k|² μ_k`（对角近似）——**teaching 闭式**，非严格混合态纯度。GKP/cat 分量空间分离时误差极小；强重叠态偏差大。
  - docstring 标注限制 + 指向未来 `overlap`（混合态严格）作为升级路径。

### 2.2 pure_fidelity（纯态保真度，等 V 限制）

`|ψ⟩ = Σ_i c_i |g_i⟩`，`|φ⟩ = Σ_j d_j |g_j'⟩`，两态 **V 相同**。
- Gram 矩阵：`T[i,j] = ⟨g_i|g_j'⟩ = _gauss_overlap(V, r_i, r_j)`
  - `_gauss_overlap` 已存在（gkp.py L27）：`S = exp(−⅛ Δrᵀ V⁻¹ Δr)`，实均值；复 rbar 取 real（teaching，GKP/cat 实均值为主）
- 内积：`⟨ψ|φ⟩ = Σ_{i,j} c_i* d_j T[i,j] = c_aᴴ · T · c_b`（矩阵形式，c = √w）
- `pure_fidelity = |⟨ψ|φ⟩|²`
- **V 不同 → ValueError**（通用双 V 公式留 B7/后续）
- 复权重处理：`c_i = √w_i`（复平方根，保留相位）；`c_aᴴ = conj(c_a).T`

### 2.3 layer 1 退化情形（L1a-L1e）

| # | Bosonic 侧 | 基线 | atol |
|---|-----------|------|------|
| L1a | K=1 squeezed r=0.6 | `from_gaussian` vs `cvsim.gaussian.purity` + `homodyne_var` | 1e-12 |
| L1b | K=1 coherent α=0.7+0.3j | `mean_photon` vs \|α\|² 解析 | 1e-12 |
| L1c | K=2 thermal-like 混合（两 coherent） | `purity` vs `Σ\|w\|²·μ_k` 自洽 | 1e-7 |
| L1d | cat even α=2.0（4 分量） | `mean_photon` vs \|α\|²(1−e^{−2\|α\|²})/2 | 1e-7 |
| L1e | cat even α=2.0 vs `FockState.cat(cutoff=30)` | `homodyne_pdf` 网格点 | 1e-7 |

### 2.4 layer 2 GKP 内部恒等式（L2a-L2e）

| # | 恒等式 | atol |
|---|--------|------|
| L2a | `pure_fidelity(gkp0, gkp0) ≈ 1` | 1e-10 |
| L2b | `pure_fidelity(gkp1, gkp1) ≈ 1` | 1e-10 |
| L2c | `pure_fidelity(gkp0, gkp1)` vs `gkp_logical_overlap(gkp0, gkp1)`（旧 deprecated 法对角峰近似） | 1e-7 |
| L2d | "measure+feedback=untouched"：gkp0 测 x 模 + 位移回格点 → `pure_fidelity(post, gkp0) ≈ 1` | 1e-6 |
| L2e | 单点 loss（γ=0.1）→ `pure_fidelity(lossed, gkp0) < 1` | 定性 |

## 3. API

### 3.1 新增（`cvsim/bosonic/analyse.py`，新文件）

```python
def purity(state: BosonicState, *, validate: bool = False) -> float:
    """混合态纯度近似 μ = Σ_k |w_k|² / (2^m √det V_k)。

    Teaching 闭式（对角近似，非严格 Tr(ρ²)）。强重叠态偏差大。
    严格混合态纯度需 `overlap`（未实现）。
    """

def pure_fidelity(state_a: BosonicState, state_b: BosonicState) -> float:
    """纯态保真度 |⟨ψ|φ⟩|²，等 V 限制。

    Gram 矩阵 T[i,j]=_gauss_overlap(V, r_i^a, r_j^b)，⟨ψ|φ⟩=c_aᴴ T c_b。
    V 不同 → ValueError。通用双 V 留 B7。
    """
```

### 3.2 复用

- `_gauss_overlap`（gkp.py，等 V 纯高斯 kernel）——`pure_fidelity` 直接用
- `_check_mode`（observables.py，mode 校验）——purity 不需要 mode，跳过
- `Component`（state.py）：`.V` / `.rbar` / `.w`

### 3.3 公共面

- `cvsim/bosonic/__init__.py`：+`purity` +`pure_fidelity` 到 `__all__` + import
- `cvsim/bosonic/measure.py`：无需 re-export（analyse 量不经 measure）
- `pyproject.toml`：+`phaseB4` marker
- `tests/test_public_api.py`：BOSONIC_PUBLIC +`purity` +`pure_fidelity`

## 4. 坑

1. **purity 对角近似**：`Σ |w_k|² μ_k` ≠ 严格 `Tr(ρ²)`（非对角项 `Tr(ρ_i ρ_j)` 非零）。docstring 必须标注 teaching 限制 + 指向 `overlap` 升级路径。L1c 自洽测试用同公式对账（非 vs 外部解析），验证实现正确性而非物理严格性。
2. **pure_fidelity 复权重**：`c_i = √w_i` 复平方根保留相位；`c_aᴴ T c_b` 矩阵乘法 dtype complex。GKP/cat 实均值时退化实数，但代码必须走 complex 路径。
3. **等 V 检查**：`pure_fidelity` 必须先验 `V_a` 与 `V_b` 各分量 V 相同（`np.allclose(V_a_k, V_b_k)`），否则 ValueError。GKP 同 ε/grid_size 同 V；cat 同 α 同 V。跨态对账（gkp0 vs gkp1）V 相同（构造规则一致）。
4. **L2c 旧法对账**：`gkp_logical_overlap` 仅取对角峰（`_diag_peaks`），`pure_fidelity` 取全分量。等 V 同 grid 时两者应吻合（对角峰 = 全分量主项），atol 1e-7。若 GKP 含 cross 项（nn/full），旧法忽略 cross → 偏差，L2c 用 `cross="none"` 规避。
5. **L2d 反馈精度**：`homodyne_condition` 测 x 模后位移回最近格点，`pure_fidelity(post, gkp0)` 受 grid_size + homodyne 网格精度双重影响，atol 放宽 1e-6。
6. **filterwarnings**：`purity`/`pure_fidelity` 不发 warning（纯计算），无 `error:cvsim.*` 风险。

## 5. 测试设计

- 新文件 `tests/test_b4_bosonic_reconciliation.py`，全 `@pytest.mark.phaseB4`
- L1a-L1e：5 类，每类 1-2 测试
- L2a-L2e：5 类
- 共约 10-12 测试
- 复用 B3 的 `_fock_pdf` helper（L1e cat vs Fock）
