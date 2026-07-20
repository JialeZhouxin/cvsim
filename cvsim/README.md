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

## 能力矩阵（当前）

| 表示 | 初态 | 门 | 通道 | 测量 / 矩 |
|------|------|----|------|-----------|
| **Gaussian** | 真空 | D/R/S/BS/**S₂** | **`loss(T)`** | det / ⟨n⟩ / Homodyne 边缘 / **条件 Homodyne** |
| **Fock** | 真空 / `fock` / `fock2` | D/R/S/**Kerr** / **BS(2 模)** | — | norm / ⟨n⟩ / **`pnrd_probs`** |
| **Bosonic** | 真空 / **cat** / **`gkp0`** | D/R/S/BS/S₂（逐组件，**w 不变**） | **`loss(T)`** | ∑w / 加权 ⟨n⟩ / 加权 Homodyne / **`homodyne_condition`**（实峰+丢交叉） |

辛矩阵只在 `cvsim/gaussian/symplectic.py`。无 Circuit DSL。

### 概念闭环

```text
G: 真空 → 门(+S₂) → [loss] → condition Homodyne → 矩
F: 1–2 模 → D/R/S/Kerr/BS → PNRD
B: cat|gkp0 → 门 → [loss] → 加权矩
```

### Wigner（教学单模）

```python
from cvsim.wigner import wigner_grid, wigner_gaussian, wigner_bosonic
X, P, W = wigner_grid(GaussianState.vacuum(1), lim=4, n=81)  # W(0,0)≈1/π
# even/odd cat：odd 中心 W<0（干涉）
```

### 诚实边界

- `gkp0`：x 齿梳；默认 `cross="none"` 对角混合；`cross="nn"` 近邻交叉（教学干涉，非完整 Gram）  
- Fock：仅 **1–2 模**；无 Fock loss / Fock Wigner  
- 无 Hafnian / 生产 GBS

## 最终用户验收

目标、U1–U5 + **U7**、未做列表见 **[USER_ACCEPTANCE.md](./USER_ACCEPTANCE.md)**。

```bash
python -m cvsim.demos.user_acceptance   # U1–U5 + U7；汇总后 exit
```

## 里程碑自检（MVP 最小闭环）

```bash
python -m cvsim.demos.m1_gaussian_squeeze   # 真空→挤压→V, det V, ⟨n⟩=sinh²r
python -m cvsim.demos.m2_fock_cutoff_scan   # 同电路扫 cutoff 逼近解析
python -m cvsim.demos.m3_cat_weights        # 小 cat 四组件 + ∑w=1
```

## 测试

```bash
uv pip install pytest
python -m pytest tests -q   # 当前锚点：56
```

## 包结构

```text
cvsim/
  conventions.py   # ħ, xxpp, Ω, vacuum
  gaussian/        # state, symplectic, gates, channels.loss, observables(+condition)
  fock/            # 1–2 模 state, D/R/S/Kerr/BS, norm/⟨n⟩/pnrd
  bosonic/         # Component, cat, gkp0, gates, channels.loss, weighted moments
  demos/           # m1–m3 + user_acceptance
```

理论笔记（根目录 `*.md`）保持纯物理，不绑本包 API。
