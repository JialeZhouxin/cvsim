# B4 — Bosonic 调和对账分层套件 PRD

## Goal

B4 = **analyse 闭式补全**（`purity` + `pure_fidelity`）+ **R1 分层对账套件**（layer 1 退化 atol + layer 2 GKP 内部恒等式）。验证 Bosonic 模拟器的内部自洽与跨包退化对账。

## Background

- B0-B3 done（vision v0.4.0）。BOSONIC_PUBLIC 39 名，analyse 量仅 `mean_photon`，缺 `purity`/`pure_fidelity`。
- `gkp_logical_overlap`（gkp.py）已 deprecated，docstring 指向 B2/B4 `pure_fidelity`——B4 落地此替代。
- B3 已落 cat vs Fock cross-check 骨架（cutoff=30, atol=1e-7，L1e 复用）。
- Fock 侧无 `gkp0` 工厂——GKP 跨包交叉核对延后 B7。

## Requirements

### R1 — analyse 闭式（公共面 +2 名）

- **R1.1 `purity(state, *, validate=False) -> float`**：`μ = Σ_k |w_k|² / (2^m · √det V_k)`，teaching 对角近似（非严格 Tr(ρ²)）。docstring 标限制 + 指向 `overlap`（未实现）升级路径。`validate=True` 走 `is_hermitian`；`det V_k ≤ 0` 抛 ValueError。
- **R1.2 `pure_fidelity(state_a, state_b) -> float`**：`|⟨ψ|φ⟩|²`，等 V 限制。Gram `T[i,j] = _gauss_overlap(V, r_i^a, r_j^b)`，`⟨ψ|φ⟩ = c_aᴴ T c_b`（c=√w，complex）。V 不同 → ValueError。docstring 标等 V 限制 + B7 通用双 V 升级路径。
- **R1.3 公共面**：`__init__.py` `__all__` +`purity` +`pure_fidelity`；`pyproject.toml` +`phaseB4` marker；`test_public_api.py` BOSONIC_PUBLIC 39→41。

### R2 — layer 1 退化对账套件（L1a-L1e）

| # | Bosonic 侧 | 基线 | atol |
|---|-----------|------|------|
| L1a | K=1 squeezed r=0.6 | `purity` vs `gaussian.purity`；`homodyne_var` vs gaussian | 1e-12 |
| L1b | K=1 coherent 0.7+0.3j | `mean_photon` vs \|α\|² | 1e-12 |
| L1c | K=2 thermal-like（两 coherent w=0.5/0.5） | `purity` vs `Σ\|w\|²·μ_k` 自洽 | 1e-7 |
| L1d | cat even α=2.0（4 分量） | `mean_photon` vs Gaussian `from_gaussian` 对账 | 1e-7 |
| L1e | cat even α=2.0 vs `FockState.cat(cutoff=30)` | `homodyne_pdf` 网格点 | 1e-7 |

### R3 — layer 2 GKP 内部恒等式（L2a-L2e）

| # | 恒等式 | atol |
|---|--------|------|
| L2a | `pure_fidelity(gkp0, gkp0) ≈ 1` | 1e-10 |
| L2b | `pure_fidelity(gkp1, gkp1) ≈ 1` | 1e-10 |
| L2c | `pure_fidelity(gkp0, gkp1)` vs `\|gkp_logical_overlap\|²`，`cross="none"` | 1e-7 |
| L2d | gkp0 测 x + 位移回格点 → `pure_fidelity(post, gkp0) ≈ 1` | 1e-6 |
| L2e | gkp0 → loss γ=0.1 → `pure_fidelity(lossed, gkp0) < 1` | 定性 |

## Acceptance criteria

1. **AC1（R1）**：`purity` + `pure_fidelity` 落地 `cvsim/bosonic/analyse.py`，公共面 +2 名，phaseB4 marker 注册，`test_public_api.py` 绿。
2. **AC2（R2）**：L1a-L1e 五项 atol 全绿。
3. **AC3（R3）**：L2a-L2e 五项全绿，GKP 无解析基准 caveat 写入 spec。
4. **AC4**：全套回归绿（1094 + B4 新增 ~10-12 passed），`error:cvsim.*`  filterwarnings 不破。

## Out of scope

- `overlap`（混合态 Uhlmann 无闭式，跳过）
- Fock `gkp0` 工厂 + GKP 跨包交叉核对（延后 B7）
- `pure_fidelity` 通用双 V 公式（等 V 限制，双 V 留 B7）

## Technical notes

- `_gauss_overlap`（gkp.py, 等 V 纯高斯 kernel）复用于 `pure_fidelity`，同包内跨子模块 import（不违反 ADR-0001）
- purity teaching 对角近似：`Σ|w|²·μ_k` 忽略非对角项 `Tr(ρ_i ρ_j)`，GKP/cat 分量空间分离时误差极小
- L1c 自洽测试（同公式对账）验证实现正确性，非物理严格性
- L2c `cross="none"` 规避旧法对角峰近似与新法全 Gram 的 cross 项偏差
- L2d 反馈精度受 grid_size + homodyne 网格双重影响，atol 放宽 1e-6
