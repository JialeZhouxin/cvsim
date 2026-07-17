# Design · 三表示光量子模拟器

## 1. Scope & boundaries

| 在界内 | 在界外 |
|--------|--------|
| 三表示最小态 + 挤压闭环 + 观测量 | 光子采样测量、Hafnian |
| 笔记公式 → 独立 Python 包 | 改笔记绑 API |
| numpy/scipy | 量子库、GPU |

**代码边界：** 新建包目录（建议 `cvsim/`），与根目录理论 MD 平级。笔记只被**人类/注释引用**，不 import 笔记。

## 2. Architecture

```text
cvsim/
  __init__.py
  conventions.py      # ħ=1, xxpp, Ω, vacuum helpers
  gaussian/
    state.py          # GaussianState(V, rbar)
    gates.py          # squeeze, (later: phase, displace, BS)
    observables.py    # det_V, mean_photon
  fock/
    state.py          # amplitudes + cutoff
    gates.py          # squeeze via expm ladder
    observables.py    # mean_photon, norm
  bosonic/
    state.py          # list of (V, rbar, w)
    cat.py            # even/odd cat 4-component ctor
    observables.py    # weight checks; optional wigner
  demos/ or tests/
    m1_gaussian_squeeze.py
    m2_fock_cutoff_scan.py
    m3_cat_weights.py
```

串行：只先写 `conventions` + `gaussian` + M1 检查；Fock/Bosonic 目录可空到对应里程碑。

## 3. Physical contracts

### 3.1 Conventions（全库）

- \(\hbar = 1\)
- 正交序：**xxpp**  
  \(\mathbf r=(x_1,\ldots,x_m,p_1,\ldots,p_m)\)  
  \(\Omega=\begin{pmatrix}0&I\\-I&0\end{pmatrix}\)
- 真空：\(\bar r=0\), \(V=\frac12 I_{2m}\)
- 单模纯态：\(\det V = 1/4\)

### 3.2 Gaussian

- 存储：`V: (2m,2m) float`, `rbar: (2m,) float`
- 门：\(V \leftarrow S V S^T\), \(\bar r \leftarrow S\bar r + d\)
- 单模挤压（笔记）：  
  \(S=\mathrm{diag}(e^{-r}, e^{r})\)（单模 xxpp 块）  
  \(V'=\frac12\mathrm{diag}(e^{-2r}, e^{2r})\)（真空进）
- \(\langle n\rangle\)：单模从 \(V,\bar r\) 用标准公式  
  \(\langle n\rangle=\frac12(\langle x^2\rangle+\langle p^2\rangle-1)+\ldots\)（位移项）；纯真空挤压 → \(\sinh^2 r\)

### 3.3 Fock

- 存储：复数振幅向量/张量，cutoff \(N\)，单模 MVP 用长度 \(N\) 向量
- ladder：截断 \(a,a^\dagger\)；\(S(r)=\exp(\frac12(r^* a^2 - r a^{\dagger2}))\) 用 `scipy.linalg.expm`
- \(\langle n\rangle = \sum_n n|c_n|^2\)；`norm = sum |c|^2` 暴露截断亏损

### 3.4 Bosonic

- 组件：`(V_k, rbar_k, w_k)`；`rbar` 允许复（交叉项）
- 小 cat：4 组件（对角 2 + 交叉 2），参数 \(|\alpha|\) 小（0.5–1.0）
- 公式锚：笔记 `03` §3 + arXiv:2103.05530 §IV B（实现注释引用，不绑库）

## 4. Data flow（M1 闭环）

```text
vacuum(m=1) → apply S(r) → (V, rbar)
                  ├→ det(V)  ?? 1/4
                  └→ mean_n  ?? sinh²(r)
```

M2：同 \(r\)，扫 \(N\)，`mean_n(N)` → `sinh²(r)`。  
M3：`cat(α)` → 组件权重结构检查。

## 5. Trade-offs

| 选择 | 原因 | 代价 |
|------|------|------|
| xxpp 固定 | 对齐笔记辛表 | 与部分教科书 xpxp 对照需置换 |
| 单模优先 | 最快验收 | 多模 BS 后置 |
| scipy.expm | Fock 门稳 | 多依赖一个包（已 D2 允许） |
| 无统一 Circuit DSL | YAGNI | 三表示 API 略不齐；里程碑后再抽象 |

## 6. Compatibility / rollout

- 无旧代码迁移。
- 回滚：删 `cvsim/` + venv 即可；笔记不动。
- 环境：`uv venv` + `uv pip install numpy scipy`（+ pytest 可选；MVP 可用 `python -m` 自检脚本）。

## 7. Test strategy

- 每里程碑一个 **可执行自检**（assert），不强制 pytest 框架。
- 容差：`atol≈1e-10`（Gaussian 解析）；Fock 相对误差随 cutoff 表驱动（如 \(r=0.5\), \(N\ge8\) 相对误差 \(<10^{-3}\) 量级，implement 写死具体阈值）。
