# cvsim · 三表示最小模拟器

从 `cv-photonic-notes` 理论笔记落地的 **Gaussian / Fock / Bosonic** MVP。  
依赖：`numpy` + `scipy`。约定：`ħ=1`，正交序 **xxpp**，真空 `V=I/2`。

## 环境

```bash
uv venv
# Windows
.venv\Scripts\activate
uv pip install numpy scipy
```

## 验收自检（README 最小闭环）

```bash
python -m cvsim.demos.m1_gaussian_squeeze   # 真空→挤压→V, det V, ⟨n⟩=sinh²r
python -m cvsim.demos.m2_fock_cutoff_scan   # 同电路扫 cutoff 逼近解析
python -m cvsim.demos.m3_cat_weights        # 小 cat 四组件 + ∑w=1
```

## 测试

```bash
uv pip install pytest
python -m pytest tests -q
```

## 门集（B1）

| 后端 | 门 |
|------|----|
| Gaussian 多模 | `displace` / `phase` / `squeeze` / `beamsplitter` |
| Fock 单模 | `displace` / `phase` / `squeeze` |
| Bosonic | 同上（逐组件辛更新，权重不变） |

辛矩阵生成在 `cvsim/gaussian/symplectic.py`（共享）。无 Circuit DSL。

## 观测量

| 后端 | 量 |
|------|----|
| Gaussian | `det_cov` / `mean_photon` / **`homodyne_mean` · `homodyne_var`**（B2 边缘矩） |
| Fock | `norm` / `mean_photon` |
| Bosonic | `weight_sum` |

```bash
python -m pytest tests -q   # MVP + B1 + B2
```

## 包结构

```text
cvsim/
  conventions.py   # ħ, xxpp, Ω, vacuum
  gaussian/        # (V, r̄) + D/R/S/BS + det/⟨n⟩
  fock/            # 截断振幅 + D/R/S + ⟨n⟩/norm
  bosonic/         # 组件 + cat + 高斯门
  demos/           # 里程碑自检
```

理论笔记（根目录 `*.md`）保持纯物理，不绑本包 API。
