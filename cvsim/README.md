# cvsim · 三表示最小模拟器

从 `cv-photonic-notes` 理论笔记落地的 **Gaussian / Fock / Bosonic**。  
依赖：`numpy` + `scipy`。约定：`ħ=1`，正交序 **xxpp**，真空 `V=I/2`。

## 环境

```bash
uv venv
# Windows
.venv\Scripts\activate
uv pip install numpy scipy
```

**新手教程（Jupyter）**：[`../tutorials/README.md`](../tutorials/README.md) — Gaussian / Fock / Bosonic 各一本。

## 能力矩阵（当前）

| 表示 | 初态 | 门 | 通道 | 测量 / 分析 |
|------|------|----|------|-------------|
| **Gaussian** | vacuum / coherent / thermal / squeezed / displaced_squeezed / tmsv / product | D/R/S/BS/**S₂**/Fourier/MZ/CZ/CX/interferometer | **loss** / amplifier / phase_noise / general `(X,Y)` | Homodyne + **Heterodyne**；F-ANALYSE（purity / ν / entropy_vn / ptrace / log_neg / fidelity）；**`GaussianCircuit`** |
| **Fock** | `fock`/`fock2`/`FockDensity`/**`FockSparse`（m≤10，COO）** | D/R/S/**Kerr**/BS/S₂/CZ/CX/MZ/interferometer + **`FockCircuit`（任意 m，per-mode cutoff，Kronecker 逐 op）** | **`loss(T, mode=)`** / amplifier / phase_noise / **apply_kraus**（1–2 模 Kraus→ρ） | norm / ⟨n⟩ / **`pnrd_probs`** / **PNR·Homodyne·Heterodyne（sample/condition + `pnr_sample_batch` 10³）** / Wigner / **IR roundtrip** |
| **Bosonic** | 真空 / **cat** / **`gkp0`/`gkp1`** | D/R/S/BS/S₂（逐组件，**w 不变**） | **`loss(T, nbar=0)`** | ∑w / 加权 ⟨n⟩ / Homodyne / **sample** / **condition** / **sample_and_condition** |

辛矩阵只在 **`cvsim/symplectic.py`**（G/B 共享地基）。Gaussian 有 **`GaussianCircuit`**（含 Homodyne/Heterodyne + feedforward）。B **不** import G 包。

**API 稳定性政策**（公开面 / semver / 硬约定）：[`docs/api-stability.md`](../docs/api-stability.md)。公开导出以 `cvsim.gaussian.__all__` 为准，由 `tests/test_public_api.py` 冻结。

### 概念闭环

```text
G: factories → 门/干涉仪 → channel → Homodyne|Heterodyne → analyse (purity/log_neg/…)
F: FockState/FockSparse → FockCircuit（门/通道/测量）→ PNR/Homodyne/Heterodyne → analyse（熵/log_neg/…）
B: cat|gkp0 → 门 → [loss] → 加权矩
```

### Wigner（教学单模）

```python
from cvsim.wigner import wigner_grid, wigner_gaussian, wigner_bosonic, wigner_fock

X, P, W = wigner_grid(GaussianState.vacuum(1), lim=4, n=81)  # W(0,0)≈1/π
# Fock: wigner_fock(FockState.fock(1, N), 0, 0) < 0
# even/odd cat：odd 中心 W<0（干涉）
```

### 诚实边界

- `gkp0`/`gkp1`：`lattice=1d|2d`；`cross=none|nn|full`（2d 无 nn）；**Gram** `Z=c†Sc`；`gkp_logical_overlap`；非 Clifford  
- Fock：**`FockState`/`FockDensity` m=1–4 稠密**（`FockCircuit` 任意 m，per-mode cutoffs，双模门需等 cutoff）；**`FockSparse` m≤10**（光子数稀疏态，如 cat/GKP）；sample=网格 PDF；**condition=截断 x_φ 本征态（≠G Kalman）**；截断预算纪律见 `docs/vision-fock-simulator.md` §F3  
- `sample_and_condition` = sample + condition 薄组合，无新物理  
- 无 Hafnian / 生产 GBS

## 最终用户验收

目标、U1–U5 + **U7** + **U8**、未做列表见 **[USER_ACCEPTANCE.md](./USER_ACCEPTANCE.md)**。

```bash
python -m cvsim.demos.user_acceptance   # U1–U5 + U7–U9；汇总后 exit
```

## 里程碑自检（MVP 最小闭环）

```bash
python -m cvsim.demos.m1_gaussian_squeeze   # 真空→挤压→V, det V, ⟨n⟩=sinh²r
python -m cvsim.demos.m2_fock_cutoff_scan   # 同电路扫 cutoff 逼近解析
python -m cvsim.demos.m3_cat_weights        # 小 cat 四组件 + ∑w=1
python -m cvsim.demos.m4_cross_rep          # 跨表示：T4挤 / T1 loss / T5 S₂ / T6 nbar / T7 Homodyne mean
```

## 测试

```bash
uv pip install pytest
python -m pytest tests -q   # Phase 2 锚点：≈368+（以 CI/本地全绿为准）
```

Phase 1 退出 demo：`examples/phase1_exit_demo.py`（4-mode TMSV → BS → loss → homodyne var）。

## 包结构

```text
cvsim/
  conventions.py   # ħ, xxpp, Ω, vacuum
  symplectic.py    # shared S/d (G+B gates only)
  gaussian/        # state, gates, channels, observables, analyse, circuit
  fock/            # F1–F3 完成：state/density/sparse/circuit/ir；独立，不依赖 G/B
  bosonic/         # Component, cat, gkp0, gates→symplectic, loss, moments
  wigner.py        # 跨表示门面（故意）
  demos/           # m1–m4 + user_acceptance
```

理论笔记（根目录 `*.md`）保持纯物理，不绑本包 API。
