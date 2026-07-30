# -*- coding: utf-8 -*-
"""Build beginner notebooks (stdlib only). Run from repo root."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent


def md(src: str) -> dict:
    text = src.strip("\n")
    lines = text.splitlines(keepends=True) or [text]
    return {"cell_type": "markdown", "metadata": {}, "source": lines}


def code(src: str) -> dict:
    text = src.strip("\n")
    lines = text.splitlines(keepends=True) or [text]
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": lines,
    }


def notebook(cells: list[dict]) -> dict:
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "cells": cells,
    }


def write(name: str, cells: list[dict]) -> None:
    path = OUT / name
    path.write_text(
        json.dumps(notebook(cells), ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print("wrote", path)


BOOT = r"""
# 从仓库根启动 Jupyter 最稳；若在 tutorials/ 里打开，这里兜底加路径
import sys
from pathlib import Path

ROOT = Path.cwd()
if not (ROOT / "cvsim").is_dir():
    ROOT = Path.cwd().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei']  # 中文支持
matplotlib.rcParams['axes.unicode_minus'] = False    # 负号显示
print("repo root:", ROOT)
print("numpy", np.__version__)
"""

# ---------------------------------------------------------------------------
# T1 Gaussian
# ---------------------------------------------------------------------------
write(
    "01_gaussian_beginner.ipynb",
    [
        md(
            r"""# 01 · Gaussian 表示新手教程

连续变量（CV / continuous variable）光量子里，**高斯态**用两样东西描述：

1. **均值向量** $\bar r$（displacement / 位移）
2. **协方差矩阵** $V$（covariance / 涨落与纠缠）

本教程只动 **`cvsim.gaussian`**：真空 → 挤压 → 位移 → 分束 → 损耗 → Homodyne。

配套笔记：`02-Gaussian表示原理.md`。"""
        ),
        md(
            r"""## 1. 这是啥 / 为啥用

- 激光近似真空 + 位移（相干态）是高斯的。
- 挤压光、分束器、多模线性光学：高斯门 **只改 $V,\bar r$**，不需要整本 Hilbert 空间。
- 成本：$O(m^2)$ 量级，模数 $m$ 可以比 Fock 大很多。

**一句话：** 你只关心「平均在哪 + 噪声椭圆长什么样」时，用 Gaussian。"""
        ),
        md(
            r"""## 2. 约定钉死（三表示共用）

| 项 | 值 |
|----|-----|
| $\hbar$ | **1** |
| 正交序 | **xxpp**：$(x_1\ldots x_m, p_1\ldots p_m)$ |
| 真空 | $V=I/2$，$\bar r=0$ |
| 纯单模高斯 | $\det V = 1/4$ |
| 单模挤压 | $\langle n\rangle = \sinh^2 r$ |
| 位移 | $d_x=\sqrt{2}\mathrm{Re}\alpha$，$d_p=\sqrt{2}\mathrm{Im}\alpha$ |"""
        ),
        code(BOOT),
        code(
            r"""
from cvsim.gaussian import (
    GaussianState,
    beamsplitter,
    det_cov,
    displace,
    homodyne_condition,
    homodyne_mean,
    homodyne_sample,
    homodyne_var,
    loss,
    mean_photon,
    squeeze,
    two_mode_squeeze,
)
from cvsim.wigner import wigner_grid
"""
        ),
        md(
            r"""## 3. 最小闭环：真空 → 挤压

真空 $V=I/2$。沿 $x$ 挤压（参数 $r$）后：

$$
V = \tfrac12\mathrm{diag}(e^{-2r}, e^{2r}),\quad
\det V = 1/4,\quad
\langle n\rangle = \sinh^2 r.
$$"""
        ),
        code(
            r"""
r = 0.8
vac = GaussianState.vacuum(1)
st = squeeze(vac, r=r, mode=0)

print("V =\n", st.V)
print("det V =", det_cov(st), "  expect 0.25")
print("<n>   =", mean_photon(st), "  expect", float(np.sinh(r) ** 2))
print("var x =", st.V[0, 0], "  expect", 0.5 * np.exp(-2 * r))
print("var p =", st.V[1, 1], "  expect", 0.5 * np.exp(+2 * r))
"""
        ),
        md(
            r"""### 看图：真空 vs 挤压真空的 Wigner 分布

真空是各向同性高斯圆斑；$x$ 方向挤压后变成椭圆——$x$ 方向压窄、$p$ 方向拉宽。"""
        ),
        code(
            r"""
lim = 4.0
X, P, W_vac = wigner_grid(GaussianState.vacuum(1), lim=lim)
_, _, W_sqz = wigner_grid(st, lim=lim)

fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(9, 4))
ax0.contourf(X, P, W_vac, levels=20, cmap="RdBu_r")
ax0.set_title("vacuum W(x,p)")
ax0.set_xlabel("x"); ax0.set_ylabel("p")
ax1.contourf(X, P, W_sqz, levels=20, cmap="RdBu_r")
ax1.set_title(f"squeezed r={r} W(x,p)")
ax1.set_xlabel("x"); ax1.set_ylabel("p")
fig.tight_layout()
plt.show()
"""
        ),
        md(
            r"""## 4. 数字检查：位移 + Homodyne

相干态 ≈ 真空位移。本约定 $\langle x\rangle = \sqrt{2}\mathrm{Re}\alpha$。

---

### Homodyne（零差检测）原理

**物理装置**

信号光 + 强本振光（LO, Local Oscillator）在 50:50 分束器合束，两输出端光电流相减，差值正比于信号在 LO 相位 $\phi$ 上的正交分量：

$$x_\phi = x\cos\phi + p\sin\phi$$

- $\phi=0$：测 $x$（位置/振幅正交）
- $\phi=\pi/2$：测 $p$（动量/相位正交）
- LO 远强于信号 → 差电流 ≈ 信号正交的经典放大版

**统计（边缘分布）**

对高斯态 $(V,\bar r)$，定义单位向量 $u$ 指向被测方向。

**单模**（xxpp 序 $(x,p)$，测模 0 的 $\phi$ 相位）：

$$u = \begin{bmatrix} \cos\phi \\ \sin\phi \end{bmatrix}$$

- $\phi=0$：$u=[1,0]^{\mathsf T}$，测 $x$
- $\phi=\pi/2$：$u=[0,1]^{\mathsf T}$，测 $p$

**多模**（xxpp 序 $(x_1\dots x_m,\, p_1\dots p_m)$，测模 $k$ 的相位 $\phi$）：

$$u = [\,0,\dots,\underbrace{\cos\phi}_{\text{位置 }x_k},\dots,0,\dots,\underbrace{\sin\phi}_{\text{位置 }p_{m+k}},\dots,0\,]^{\mathsf T}$$

$u$ 只有两个非零元：$x_k$ 位 $=\cos\phi$，$p_k$ 位 $=\sin\phi$，长度 $|u|=1$。

用 $u$ 算边缘统计：

$$\mu = u\cdot\bar r,\qquad \sigma^2 = u^{\mathsf T} V u$$

测量结果是一维高斯随机数：$\mathrm{outcome}\sim\mathcal N(\mu,\sigma^2)$。真空任意 $\phi$：$\mu=0,\,\sigma^2=1/2$。

**采样 vs 条件更新（可分离）**

| 操作 | 函数 | 干什么 |
|------|------|--------|
| 采样 | `homodyne_sample` | 从 $\mathcal N(\mu,\sigma^2)$ 抽一个结果 |
| 条件 | `homodyne_condition` | 拿到结果后，**更新态**到后验 |

条件更新（Kalman）——给定结果 $o$：

$$V' = V - \frac{vv^{\mathsf T}}{\sigma},\qquad
\bar r' = \bar r + v\,\frac{o-\mu}{\sigma}$$

其中 $v = V u$。结果：
- **测向方差 $\to 0$**（$u^{\mathsf T}V'u=0$）
- **均值 $\to o$**（$u\cdot\bar r' = o$）
- 正交方向方差不变

> 这就是为什么条件后 $\det V'=0$（协方差奇异）——Wigner 退化，画不了。
> 海森堡：$\Delta x \to 0$ 则 $\Delta p \to \infty$（$V_{pp}$ 不变，本来也不是无穷，但这个"理想投影"是教学近似）。

API：`homodyne_mean(state, mode=0, phi=0.0)`。"""
        ),
        code(
            r"""
alpha = 1.2 + 0.0j
coh = displace(GaussianState.vacuum(1), alpha=alpha)
print("<n> ~ |alpha|^2 :", mean_photon(coh), "vs", abs(alpha) ** 2)
print("homodyne mean φ=0 :", homodyne_mean(coh, phi=0.0), "expect", np.sqrt(2) * alpha.real)
print("homodyne var  φ=0 :", homodyne_var(coh, phi=0.0), "expect ~0.5 (vacuum noise)")
"""
        ),
        md(
            r"""### 看图：真空 → 位移 → 相干态

位移把真空圆斑平移到 $(\sqrt{2}\mathrm{Re}\alpha,\sqrt{2}\mathrm{Im}\alpha)$，形状不变。"""
        ),
        code(
            r"""
lim = 4.0
X, P, W_vac = wigner_grid(GaussianState.vacuum(1), lim=lim)
_, _, W_coh = wigner_grid(coh, lim=lim)

fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(9, 4))
ax0.contourf(X, P, W_vac, levels=20, cmap="RdBu_r")
ax0.set_title("vacuum")
ax0.set_xlabel("x"); ax0.set_ylabel("p")
ax1.contourf(X, P, W_coh, levels=20, cmap="RdBu_r")
ax1.set_title(f"coherent α={alpha}")
ax1.set_xlabel("x"); ax1.set_ylabel("p")
fig.tight_layout()
plt.show()
"""
        ),
        md(
            r"""## 5a. 双模挤压真空（TMSV）与 EPR 纠缠

**双模挤压** $S_2(r)$ 是 CV 里最经典的纠缠源。

物理上对应**参量下转换**（parametric down-conversion）：一个泵浦光子劈成一对纠缠光子，分别进模 0 和模 1。

对两模真空作用 $S_2(r)$ 得 TMSV 态：

$$V_{\mathrm{TMSV}} = \frac12
\begin{bmatrix}
\cosh 2r & \sinh 2r & 0 & 0 \\
\sinh 2r & \cosh 2r & 0 & 0 \\
0 & 0 & \cosh 2r & -\sinh 2r \\
0 & 0 & -\sinh 2r & \cosh 2r
\end{bmatrix}$$

> 注意：xxpp 二模顺序是 $(x_0,x_1,p_0,p_1)$，不是逐个模的 $(x_0,p_0,x_1,p_1)$。$x$ 块在前、$p$ 块在后。

关键特征：

1. **单模看是热态** — 对角块 $\frac12\cosh 2r \cdot I_2$，$\langle n_i\rangle = \sinh^2 r$，但 $\det V_i > 1/4$（不纯）
2. **模间强关联** — 非对角块 $\pm\frac12\sinh 2r$ 非零
3. **EPR 相关** — 考察联合正交：
   $$\mathrm{Var}(x_0 - x_1) = e^{-2r},\qquad \mathrm{Var}(p_0 + p_1) = e^{-2r}$$
   挤压越强（$r$ 越大），这两个组合越确定 → **位置差分 + 动量和**同时精确 → EPR 佯谬的连续变量版本"""
        ),
        code(
            r"""
r = 0.6
# 从两模真空直接做双模挤压
tmsv = two_mode_squeeze(GaussianState.vacuum(2), r=r, mode1=0, mode2=1)
V = tmsv.V

print("V =", V, sep="\n")
print("det V =", det_cov(tmsv), "  expect (1/4)^2 = 0.0625 (整体纯态)")
print("<n_0> =", mean_photon(tmsv, mode=0), "  expect", float(np.sinh(r) ** 2))
print("<n_1> =", mean_photon(tmsv, mode=1), "  expect", float(np.sinh(r) ** 2))

# EPR 关联：x0 - x1 的方差 → 0（r 大时）
var_x0 = tmsv.V[0, 0]  # V_{x0,x0}
var_x1 = tmsv.V[1, 1]  # V_{x1,x1}
cov_x0x1 = tmsv.V[0, 1]  # V_{x0,x1}
var_diff = var_x0 + var_x1 - 2 * cov_x0x1
print("Var(x0 - x1) =", var_diff, "  expect", float(np.exp(-2 * r)))

var_p0 = tmsv.V[2, 2]  # V_{p0,p0}
var_p1 = tmsv.V[3, 3]  # V_{p1,p1}
cov_p0p1 = tmsv.V[2, 3]  # V_{p0,p1}
var_sum = var_p0 + var_p1 + 2 * cov_p0p1
print("Var(p0 + p1) =", var_sum, "  expect", float(np.exp(-2 * r)))

# 单模约化态是热态：det(单模 V_i) > 1/4（纠缠的必然结果）
# xxpp 二模: (x0,x1,p0,p1)，模0 = 索引[0,2]
idx0 = [0, 2]
V_mode0 = V[np.ix_(idx0, idx0)]
print("V_mode0 =", V_mode0, sep="\n")
print("det V_mode0 =", np.linalg.det(V_mode0), "  expect", 0.25 * np.cosh(2 * r) ** 2)
print("  (> 0.25 = 纠缠态的子模不纯 → 混合度判据)")
"""
        ),
        md(
            r"""### 结果解读：数字背后的物理

| 数字 | 物理含义 |
|------|--------|
| `det V = 0.0625` | 两模整体是**纯态**（$= (1/4)^2$）。与真空相同——双模挤压是幺正变换，不引入混合 |
| `Var(x0-x1) = 0.30` | 真空下 $\mathrm{Var}(x_0-x_1)=1.0$，TMSV 把位置差不确定性**压缩了 3.3 倍**。测 $x_0$ 就能精确推断 $x_1$ |
| `Var(p0+p1) = 0.30` | 动量和同样被压缩。位置差分 + 动量和**同时精确**——经典不可能同时做到（海森堡对单模限制 $\Delta x\Delta p\ge 1/2$，但 $x_0-x_1$ 与 $p_0+p_1$ **对易**，可同时确定） |
| `det V_mode0 = 0.82` | 单模约化态 $\det V = 0.82 > 0.25$ → 子模是**混合态**（热态），虽然你只看模 0 觉得它"有噪声"，但加上模 1 的信息后整体是纯的——这是量子纠缠区别于经典关联的核心特征 |
| V 非对角块 $\pm 0.75$ | 模间**量子关联**。关键不是"协方差非零"（经典也有），而是**噪声抵消机制**：单模看很噪（Var=0.91），但 $x_0-x_1$ 把噪声对消了（Var=0.30）。经典独立噪声做不到——只有纠缠态的关联才能让噪+噪=静 |

"""
        ),
        code(
            r"""# 对比实验：TMSV vs 两个独立单模挤压态
# 两者 Var(x0-x1) 相同，但物理来源完全不同！

r = 0.6

# --- TMSV (纠缠) ---
tmsv = two_mode_squeeze(GaussianState.vacuum(2), r=r, mode1=0, mode2=1)
V_ent = tmsv.V

# --- 两个独立单模挤压 (无纠缠) ---
indep = GaussianState.vacuum(2)
indep = squeeze(indep, r=r, mode=0)
indep = squeeze(indep, r=r, mode=1)
V_ind = indep.V

print("=== 单模 x 方差：谁更'安静'？ ===")
print("真空基准：Var(x) = 0.5")
print("TMSV  Var(x0) =", round(V_ent[0,0], 4), "  ← 比真空大！模0单独看像热态")
print("独立  Var(x0) =", round(V_ind[0,0], 4), "  ← 比真空小，模0自己也挤过")

print("\n=== Var(x0-x1)：两者相等 ===")
var_ent = V_ent[0,0] + V_ent[1,1] - 2*V_ent[0,1]
var_ind = V_ind[0,0] + V_ind[1,1] - 2*V_ind[0,1]
print("TMSV  =", round(var_ent,4), "   = 单个噪 + 单个噪 - 2×强关联")
print("独立  =", round(var_ind,4), "   = 单个静 + 单个静 - 2×0")

print("\n=== 模间协方差 Cov(x0,x1) ===")
print("TMSV :", round(V_ent[0,1], 4), "  ← 强正关联（纠缠的 signature）")
print("独立 :", round(V_ind[0,1], 4), "   ← 零（真·独立）")

print("\n=== 关键直觉 ===")
print("TMSV：每个模单独看很噪，但噪声互相关联→相减后抵消")
print("  这叫'隐藏的秩序'——量子纠缠的本质")
print("独立挤压：每个模本来就安静，无需互相'照应'")
print("  这是经典可分的——不是纠缠")
"""
        ),
        md(
            r"""**一句话总结**

> 高斯纠缠 = 整体是纯态 + 每个子模是混合态 + 联合正交（$x_0-x_1$、$p_0+p_1$）的方差被压缩到经典极限以下。

TMSV 就是 CV 版的 Bell 态：你没法只看模 0 就知道一切，必须两个模一起看才"干净"。

---

"""
        ),
        md(
            r"""## 5b. 损耗 loss 与条件 Homodyne

---

### 损耗（纯损耗 / pure loss）

**物理模型**：系统模与真空环境模在一个**假想的 BS** 上耦合（透过率 $T\in[0,1]$），然后把环境偏迹（partial trace）扔掉。

$$\text{系统} \xrightarrow{\text{BS}(\theta=\arccos\sqrt{T})} \text{系统} \otimes \text{环境} \xrightarrow{\mathrm{Tr}_{\text{env}}} \text{约化系统}$$

- $T=1$：完全透明 → 恒等变换
- $T=0$：完全丢光 → 作用模回到真空涨落

**对 $(V,\bar r)$ 的更新**（只改作用模的正交，xxpp + $\hbar=1$ 下）：

$$V \mapsto X V X^{\mathsf T} + Y,\qquad \bar r \mapsto X\bar r$$

$$X = \sqrt{T}\,I_{\mathrm{act}},\qquad Y = (1-T)\,\frac12\,I_{\mathrm{act}}$$

- $X$：信号衰减（$\sqrt{T} < 1$）
- $Y$：真空噪声注入（$V_{\mathrm{vac}}=I/2$，比例 $1-T$）

**检查点**：相干态 $|\alpha|^2$ 经损耗后 $\langle n\rangle \to T|\alpha|^2$。

> `loss(state, T, nbar=0.0)`：`nbar` 默认 0 = 真空环境；设 `nbar>0` 则 $Y=(1-T)(\bar n+1/2)I$（热环境损耗）。

---

### Homodyne 条件（condition）

与采样 `homodyne_sample` 不同，条件是**拿到测量结果后更新态**：

$$V' = V - \frac{vv^{\mathsf T}}{\sigma},\qquad
\bar r' = \bar r + v\,\frac{o-\mu}{\sigma}$$

其中 $v = Vu$，$\sigma = u^{\mathsf T}Vu$，$\mu = u\cdot\bar r$，$o$ 是测量结果。

- **测向方差 $\to 0$**（$u^{\mathsf T}V'u=0$）
- **均值 $\to o$**（$u\cdot\bar r' = o$）
- 正交方向方差不变

> 因此条件后 $\det V'=0$（奇异）——Wigner 退化，画不了图。这是理想投影的必然结果。

**条件 vs 采样**：采样只管抽随机数；条件才改变态。两者可独立使用：先 `sample` 得结果，再用该结果调 `condition`，或直接 `sample_and_condition` 一步到位。"""
        ),
        code(
            r"""
alpha, T = 1.5, 0.4
st = loss(displace(GaussianState.vacuum(1), alpha=alpha), T=T)
print("after loss <n>:", mean_photon(st), "expect", T * abs(alpha) ** 2)

# 条件测量：真空上「假装」测到 x=0.7
post = homodyne_condition(GaussianState.vacuum(1), mode=0, phi=0.0, outcome=0.7)
print("post mean x:", homodyne_mean(post, phi=0.0), "  var x:", homodyne_var(post, phi=0.0))
"""
        ),
        md(
            r"""### 看图：损耗如何缩小 Wigner 峰

**丢失的是什么？** 光子从系统模泄漏到真空环境，一去不回（偏迹）。

**Wigner 峰为什么向原点收缩？** 两个效应叠加：

1. **位移衰减** — $\bar r \to \sqrt{T}\,\bar r$。相干态的"中心"从 $(\sqrt{2}\mathrm{Re}\alpha, \sqrt{2}\mathrm{Im}\alpha)$ 挪到 $\sqrt{T}$ 倍 → 靠近原点
2. **真空噪声混入** — $V \to T\,V + (1-T)\,I/2$。环境真空涨落"稀释"了原来的信号

$$\langle n\rangle \to T|\alpha|^2,\qquad \det V \to T\det V + \cdots$$

- $T=1$：无损耗，峰不动
- $T=0$：全部丢光，峰回到原点 + 真空涨落 → 变回真空
- $0<T<1$：峰在两者之间，高斯仍保持（纯损耗不改高斯性）

图上红色实线 → 蓝色虚线的变化就是这两个效应：中心向原点缩 + 等高线圈微微变宽（噪声混入）。

> **注意** Homodyne 条件后 $x$ 方差→0，协方差奇异，Wigner 函数退化（画不了）。条件后的行为看数字就好。"""
        ),
        code(
            r"""
alpha, T = 1.5, 0.4
st_before = displace(GaussianState.vacuum(1), alpha=alpha)
st_loss = loss(st_before, T=T)

lim = 4.0
X, P, W0 = wigner_grid(st_before, lim=lim)
_, _, W1 = wigner_grid(st_loss, lim=lim)

fig, ax = plt.subplots(1, 1, figsize=(5, 5))
# 相干态：红色实线
c0 = ax.contour(X, P, W0, levels=8, colors='red', linewidths=1.5)
# 损耗后：蓝色虚线
c1 = ax.contour(X, P, W1, levels=8, colors='blue', linestyles='dashed', linewidths=1.5)
# 图例
from matplotlib.lines import Line2D
legend_elements = [
    Line2D([0], [0], color='red', lw=1.5, label=f'coherent α={alpha}'),
    Line2D([0], [0], color='blue', lw=1.5, linestyle='dashed', label=f'after loss T={T}'),
]
ax.legend(handles=legend_elements, loc='upper right')
ax.set_xlabel("x"); ax.set_ylabel("p")
ax.set_title("loss 效果：Wigner 峰向原点收缩")
ax.set_aspect('equal')
fig.tight_layout()
plt.show()

# 采样（随机抽一次结果；可设 seed）
rng = np.random.default_rng(0)
samples = [
    homodyne_sample(GaussianState.vacuum(1), phi=0.0, rng=rng) for _ in range(5)
]
print("5 vacuum samples:", samples)
"""
        ),
        md(
            r"""---

## 5c. 参数化电路：定义一次，多次运行

之前我们手动写 `for` 循环、每次重新构建门序列。`GaussianCircuit`
提供一种更干净的方式：**分离"电路结构"和"参数值"**。

核心规则：
- 门参数是**数字** → 固定值
- 门参数是**字符串**（如 `'g'`） → 参数占位，`run()` 时传入

"""
        ),
        code(
            r"""from cvsim.gaussian import GaussianCircuit

# 定义电路：structure = once
c = GaussianCircuit(2)
c.squeeze(0, r=0.5)          # 固定 r=0.5
c.phase(0, theta='theta')     # 参数占位
c.cz(0, 1, weight='g')        # 参数占位
c.beamsplitter(0, 1, theta=np.pi/4)

print(repr(c))  # 看门序列：${} 标记参数占位

# 扫描参数：run = many
import numpy as np
import matplotlib.pyplot as plt

g_vals = np.linspace(0, 1.5, 30)
n_vals = []
for g in g_vals:
    st = c.run(theta=0.3, g=g)
    n_vals.append(mean_photon(st))

fig, ax = plt.subplots()
ax.plot(g_vals, n_vals, 'o-', markersize=4)
ax.set_xlabel("CZ weight g")
ax.set_ylabel(r"$\langle n\rangle$")
ax.set_title("扫 CZ 权重 → 总光子数变化")
fig.tight_layout()
plt.show()
"""
        ),
        md(
            r"""对比旧方式（手动重复代码）：

```python
# 旧：结构混在循环里，改了易出错
for g in g_vals:
    st = GaussianState.vacuum(2)
    st = squeeze(st, r=0.5, mode=0)
    st = phase(st, theta=0.3, mode=0)
    st = cz(st, weight=g, mode1=0, mode2=1)
    st = beamsplitter(st, 0, 1, theta=np.pi/4)
```

新方式：**"这个电路长什么样"** 和 **"参数取什么值"** 完全解耦。
对教学非常友好——一眼看出电路拓扑。

### 电路组合：`+`

把两个电路拼起来，复用子电路。

"""
        ),
        code(
            r"""# 子电路 A：制备挤压
c1 = GaussianCircuit(2)
c1.squeeze(0, r=0.5)

# 子电路 B：纠缠 + 操作
c2 = GaussianCircuit(2)
c2.cz(0, 1, weight=0.4)
c2.beamsplitter(0, 1, theta=np.pi/4)

# 组合：A + B = 完整电路
c_full = c1 + c2
print(f"A has {len(c1)} ops, B has {len(c2)} ops, full has {len(c_full)} ops")

# c1 不变（+ 返回新电路）
print(f"c1 unchanged: {len(c1)} ops")

# += 就地修改
c1 += c2
print(f"c1 after +=: {len(c1)} ops")
"""
        ),
        md(
            r"""小总结：`GaussianCircuit` 的关键价值

| 概念 | 旧方式 | 新方式 |
|------|--------|--------|
| 电路定义 | 手动写代码行 | `c.squeeze(0, r=...)` 语义化 |
| 参数 | 写死在代码里 | 字符串占位 → `run()` 传值 |
| 复用 | 复制粘贴 | `c1 + c2` |
| 可视 | 无 | `repr(c)` 打印门序列 |

## 5d. 测量与前馈（通向 GKP 纠错）

**核心想法**：电路不仅是"一堆门加上去"，还包括**中间测量**——
测得的结果可以**前馈**(feedforward)到后续门的参数。

这是做 GKP 纠错的基石：
1. 纠缠数据模和 ancilla
2. 测量 ancilla 的某个正交分量
3. 根据测量结果，位移数据模来抵消噪声

---

"""
        ),
        md(
            r"""### 单步测量：模式消除

`measure_homodyne(mode, phi, name)` 做三件事：
1. 从当前态**采样**一个 Homodyne 结果
2. 将态**投影**（条件化）到对应本征态
3. 将测量模**消除**（`nmode` 减 1）

返回的 `results` 字典记录每次测量值。

"""
        ),
        code(
            r"""from cvsim.gaussian import GaussianCircuit, ParamRef

# 简单例子：2模真空 → 挤压 → 测模1
c = GaussianCircuit(2)
c.squeeze(1, r=0.5)                       # ancilla 制备
c.measure_homodyne(1, phi=0, name='m_x')  # 测 x 分量

rng = np.random.default_rng(42)
state, results = c.run(rng=rng)

print(f"测量前 nmode=2 → 测量后 nmode={state.nmode}")
print(f"测量结果: m_x = {results['m_x']:.4f}")
print(f"剩余态的模式是原来的 mode 0（数据模）")
"""
        ),
        md(
            r"""### 前馈位移：`ParamRef`

`ParamRef(source, gain)` 告诉电路："等 `source` 测完，用 `结果 × gain` 作为本门的参数"。

下面演示一个迷你 GKP 式纠错序列：

"""
        ),
        code(
            r"""# 迷你 GKP 式纠错：squeeze → CZ → measure p → feedback
c = GaussianCircuit(2)
c.squeeze(0, r=0.3)                        # 数据模（模拟有噪声）
c.squeeze(1, r=0.5)                        # ancilla 制备
c.cz(0, 1, weight=1.0)                     # 纠缠
c.measure_homodyne(1, phi=np.pi/2, name='m_p')  # 测 ancilla 的 p
c.displace(0, alpha=ParamRef('m_p', gain=0.5))  # feedback

rng = np.random.default_rng(42)
st_fb, res = c.run(rng=rng)

# 对比：同样电路，但 feedback gain=0（不做反馈）
c_no_fb = GaussianCircuit(2)
c_no_fb.squeeze(0, r=0.3)
c_no_fb.squeeze(1, r=0.5)
c_no_fb.cz(0, 1, weight=1.0)
c_no_fb.measure_homodyne(1, phi=np.pi/2, name='m_p')
c_no_fb.displace(0, alpha=ParamRef('m_p', gain=0.0))  # gain=0 = no feedback

rng2 = np.random.default_rng(42)
st_no, _ = c_no_fb.run(rng=rng2)

print(f"测量结果 m_p = {res['m_p']:.4f}")
print(f"有反馈: r̄₀ = {st_fb.rbar[0]:.4f} (x 分量)")
print(f"无反馈: r̄₀ = {st_no.rbar[0]:.4f} (x 分量)")
print(f"反馈贡献的位移量 ≈ {abs(st_fb.rbar[0] - st_no.rbar[0]):.4f}")
print(f"  = |m_p| × gain × √2 = {abs(res['m_p']) * 0.5 * np.sqrt(2):.4f}  ← 吻合")
"""
        ),
        md(
            r"""### 这是什么意思？

GKP 纠错的核心思想：

1. **纠缠**数据模和 ancilla（CZ 门）
2. 噪声在**两个模上都有印记**（纠缠的数学性质）
3. **测量 ancilla** 提取噪声信息，同时**投影数据模**（量子 "纠错" 不是"消除"噪声，而是"平移"它）
4. **根据测量结果平移数据模**，抵消噪声

上面 `gain=0.5` 是故意选的子最优值——真正 GKP 的增益需要精确匹配压缩参数。
教学目的：让你**看到反馈位移量的合理性**（不是魔法数）。

### 多步测量

三模起步，逐步测量 → 最终只剩一个模。

"""
        ),
        code(
            r"""# 三步测量：展示测量消模 + mode 索引偏移
c = GaussianCircuit(3)
c.squeeze(0, r=0.3)
c.squeeze(1, r=0.5)
c.squeeze(2, r=0.2)
c.cz(0, 1, weight=0.5)         # 纠缠 (0,1)
c.cz(1, 2, weight=0.3)         # 纠缠 (1,2)
c.measure_homodyne(1, phi=0, name='mx1')   # 测中间模
c.measure_homodyne(0, phi=np.pi/2, name='mp0')  # 测数据模 0
# 剩余的是原来的 mode 2（现物理 index 0）

rng = np.random.default_rng(7)
st, res = c.run(rng=rng)

print(f"起始 nmode=3 → 2步测量后 nmode={st.nmode}")
print(f"测量值: { {k: round(v, 4) for k, v in res.items()} }")
print(f"剩余态光子数: <n> = {mean_photon(st):.4f}")
"""
        ),
        md(
            r"""> **诚实标注**：`measure_homodyne` 后模式**消除**（A1 方案），
> 但 `run()` 内部维护 `original→physical` 映射表，后续门**自动使用原 mode 编号**
> ——你不需要手动调整索引。电路建造时始终用初始 mode 编号即可。

---

## 6. API 速查

### 态（State）

| API | 作用 |
|-----|------|
| `GaussianState(V, rbar)` | 高斯态，nmode 模。`V` 协方差矩阵 $(2m\times 2m)$，`rbar` 均值向量 $(2m,)$ |
| `GaussianState.vacuum(nmode)` | 工厂方法：nmode 真空 $V=I/2$，$\bar r=0$ |
| `state.remove_mode(k)` | 返回移除物理模 k 后的新态（nmode-1）|

### 门（Gates）— 幺正、保纯

| API | 签名 | 作用 |
|-----|------|------|
| `squeeze` | `(state, r, mode=0)` | 单模挤压 $S(r)$：$x\to e^{-r}x$，$p\to e^{r}p$ |
| `displace` | `(state, alpha, mode=0)` | 单模位移 $D(\alpha)$：$\bar r$ 加 $\sqrt{2}(\mathrm{Re}\alpha,\mathrm{Im}\alpha)$ |
| `phase` | `(state, theta, mode=0)` | 单模相位旋转 $R(\theta)$：$x,p$ 平面上转 $\theta$ |
| `beamsplitter` | `(state, m1, m2, theta, phi=0)` | 双模分束器 BS$(\theta,\phi)$；$\theta=\pi/4$ = 50:50 |
| `two_mode_squeeze` | `(state, r, m1, m2)` | 双模挤压 $S_2(r)$ — **产生 EPR 纠缠** |
| `cz` | `(state, weight, m1, m2)` | CZ $=\exp(i\cdot g\cdot\hat x_1\hat x_2)$：$p_1\leftarrow p_1+g x_2$ |
| `cx` | `(state, weight, m1, m2)` | CX $=\exp(-i\cdot g\cdot\hat x_1\hat p_2)$：$x_2\leftarrow x_2+g x_1$，$p_1\leftarrow p_1-g p_2$ |

> 所有门返回**新 `GaussianState`**，不修改原态（函数式风格）。

### 电路（Circuit）— 参数化 + 测量 + 前馈

| API | 签名 | 作用 |
|-----|------|------|
| `GaussianCircuit(nmode)` | 构造空电路 | 定义门序列，支持参数占位 + 测量 |
| `c.squeeze(mode, r)` | `r` 可为数（固定）或字符串（占位）| 添加挤压门 |
| `c.measure_homodyne(mode, phi, name)` | `name` 为结果键名 | 采样+投影+消除 mode |
| `c.displace(mode, alpha=ParamRef(...))` | `ParamRef('name', gain)` | 前馈：alpha = 测量值 × gain |
| `c.run(rng=None, **params)` | 返回 `state` 或 `(state, results)` | 执行电路，有测量则返回测量字典 |
| `c1 + c2` / `c1 += c2` | nmode 必须相同 | 电路拼接 |

> 门函数 `squeeze(state, ...)` 和电路方法 `c.squeeze(...)` 并存——前者是函数式 API，后者是电路建造器。

### 通道（Channels）— 非幺正、可能增混

| API | 签名 | 作用 |
|-----|------|------|
| `loss` | `(state, T, nbar=0.0)` | 纯损耗 $0\le T\le 1$；`nbar>0` = 热环境 |

### 可观测量（Observables）— 不改态

| API | 签名 | 返回 |
|-----|------|------|
| `det_cov` | `(state)` | $\det V$；纯态 $=(1/4)^m$ |
| `mean_photon` | `(state, mode=None)` | $\langle n\rangle$；`mode=None`=总光子数，`mode=int`=单模 |
| `homodyne_mean` | `(state, mode, phi)` | 边缘均值 $\mu = u\cdot\bar r$ |
| `homodyne_var` | `(state, mode, phi)` | 边缘方差 $\sigma^2 = u^{\mathsf T}Vu$ |
| `homodyne_sample` | `(state, mode, phi, rng=None)` | 从 $\mathcal N(\mu,\sigma^2)$ 抽一个结果 |
| `homodyne_condition` | `(state, mode, phi, outcome)` | 条件更新，返回**新态**（测向后方差→0） |
| `homodyne_sample_and_condition` | `(state, mode, phi, rng=None)` | 采样 + 条件一步到位，返回 `(新态, 结果)` |

### 可视化（`cvsim.wigner`）

| API | 签名 | 返回 |
|-----|------|------|
| `wigner_grid` | `(state, lim=5.0, n=81)` | `(X, P, W)` 网格，W 形状 `(n,n)`，用于 `contourf` |

---

"""
        ),
        md(
            r"""## 7. 诚实边界 + 何时换表示

**Gaussian 适合**

- 线性光学 + 高斯通道（loss / 热 n̄）
- 大规模 GBS 的「态演化」侧（本包 **不做** Hafnian 采样）

**Gaussian 不适合 / 本包不做**

- 光子数分辨（PNRD）精确分布 → 用 **Fock**
- Cat / GKP 这种非高斯叠加 → 用 **Bosonic**
- Kerr 等非高斯门 → **Fock**（截断）

下一本：`02_fock_beginner.ipynb`。"""
        ),
        md("## 自检（全绿才算过）"),
        code(
            r"""
r = 0.8
st = squeeze(GaussianState.vacuum(1), r=r)
assert abs(det_cov(st) - 0.25) < 1e-10
assert abs(mean_photon(st) - np.sinh(r) ** 2) < 1e-10
assert abs(homodyne_mean(displace(GaussianState.vacuum(1), 1.0), phi=0.0) - np.sqrt(2.0)) < 1e-10
post = homodyne_condition(GaussianState.vacuum(1), mode=0, phi=0.0, outcome=0.3)
assert abs(homodyne_mean(post, phi=0.0) - 0.3) < 1e-8
assert abs(homodyne_var(post, phi=0.0)) < 1e-8
print("T1 self-check OK")
"""
        ),
    ],
)

# ---------------------------------------------------------------------------
# T2 Fock
# ---------------------------------------------------------------------------
write(
    "02_fock_beginner.ipynb",
    [
        md(
            r"""# 02 · Fock 表示新手教程

**Fock 表示**把态写成光子数基底 $\{|n\rangle\}$ 上的振幅（或密度矩阵 $\rho$）。

本教程只动 **`cvsim.fock`**：截断 → 门 → PNRD → loss→ρ → Wigner → Homodyne。

配套笔记：`01-Fock表示原理.md`、`04-…` 四问篇。"""
        ),
        md(
            r"""## 1. 这是啥 / 为啥用

- 你想问：「测到 0、1、2… 光子的概率是多少？」→ Fock 最直接。
- 非高斯门（Kerr）、截断下的精确幺正，也走 Fock。
- **代价：** 截断 $N$，$m$ 模维度 $\sim N^m$。本包教学用 **1–2 模**。

**一句话：** 要光子数 / 非高斯，用 Fock；模一多就痛。"""
        ),
        md(
            r"""## 2. 约定

与 Gaussian 同一物理：$\hbar=1$，位移 $\sqrt{2}$ 约定。

额外：

- `FockState`：纯态振幅；2 模时 `amps` 形状 $(N,N)$
- `FockDensity`：混态 $\rho$（loss 之后）
- **截断不是物理墙**，是数值近似——$N$ 太小会错"""
        ),
        code(BOOT),
        code(
            r"""
from cvsim.fock import (
    FockState,
    beamsplitter,
    displace,
    homodyne_condition,
    homodyne_mean,
    loss,
    mean_photon,
    norm,
    pnrd_probs,
    squeeze,
    trace,
)
from cvsim.wigner import wigner_fock
"""
        ),
        md(
            r"""## 3. 最小闭环：截断挤压

解析：$\langle n\rangle = \sinh^2 r$。Fock 里用截断幺正近似——**N 越大越准**。"""
        ),
        code(
            r"""
r = 0.5
n_exact = float(np.sinh(r) ** 2)
print(f"target <n> = sinh^2({r}) = {n_exact:.6f}")
for N in [4, 6, 8, 12, 20]:
    st = squeeze(FockState.vacuum(N), r=r)
    err = abs(mean_photon(st) - n_exact)
    print(f"  N={N:3d}  <n>={mean_photon(st):.6f}  |err|={err:.3e}  ||ψ||={norm(st):.6f}")
"""
        ),
        md(
            r"""## 4. 数字检查：PNRD 与双模 BS

$|10\rangle$ 过 50/50 BS → 两端单光子概率各约 $1/2$。"""
        ),
        code(
            r"""
# 单模：|1> 的光子数分布
st1 = FockState.fock(1, cutoff=8)
print("|1> pnrd:", pnrd_probs(st1))

# 双模 |10> → BS（amps 形状 (N,N)）
psi = FockState.fock2(1, 0, cutoff=6)
psi = beamsplitter(psi, theta=np.pi / 4)
p10 = abs(psi.amps[1, 0]) ** 2
p01 = abs(psi.amps[0, 1]) ** 2
print("|c10|^2, |c01|^2 ≈", float(p10), float(p01), "  (expect ~0.5 each)")
"""
        ),
        md(
            r"""## 5a. 损耗 → 密度矩阵

纯态 $|1\rangle$ 经透射率 $T$ 的纯损耗：$\rho_{00}\approx 1-T$，$\rho_{11}\approx T$。

**混态**用 `FockDensity`；`trace(ρ)≈1`。"""
        ),
        code(
            r"""
T = 0.3
rho = loss(FockState.fock(1, cutoff=10), T=T)
print("type:", type(rho).__name__)
print("Tr ρ =", trace(rho))
print("ρ[0,0], ρ[1,1] ≈", float(rho.rho[0, 0].real), float(rho.rho[1, 1].real))
print("expect ~", 1 - T, T)
"""
        ),
        md(
            r"""## 5b. Wigner 与 Homodyne

真空：$W(0,0)=1/\pi$。$|1\rangle$ 中心可负（非经典）。

**诚实：** Fock 的 `homodyne_condition` 是 **截断空间里 $x_\varphi$ 本征投影**，  
**不是** Gaussian 那套 Kalman 后验。先验振幅几乎被扔掉，后验 ≈ 最近本征矢。"""
        ),
        code(
            r"""
N = 20
vac = FockState.vacuum(N)
one = FockState.fock(1, N)
w0 = wigner_fock(vac, 0.0, 0.0)
w1 = wigner_fock(one, 0.0, 0.0)
print("W_vac(0,0) =", w0, "  expect", 1 / np.pi)
print("W_|1|(0,0) =", w1, "  (should be negative)")

print("homodyne mean |1> φ=0:", homodyne_mean(one, phi=0.0))  # ~0 by parity
# 条件：投到最近 x 本征态（教学）
post = homodyne_condition(one, mode=0, phi=0.0, outcome=0.0)
print("after condition: type", type(post).__name__, "norm", norm(post))
"""
        ),
        md(
            r"""## 6. 诚实边界 + 何时换表示

**Fock 适合**

- PNRD、小 cutoff 精确门、loss→ρ、单模 Wigner

**Fock 不适合 / 本包限制**

- $m\ge 3$、大 cutoff
- 2 模 ρ 上门 / Wigner / Homodyne（多数未做）
- 大规模高斯电路 → **Gaussian**
- 大振幅 cat/GKP 全貌 → **Bosonic** 高斯叠加更省

下一本：`03_bosonic_beginner.ipynb`。"""
        ),
        md("## 自检"),
        code(
            r"""
r = 0.5
st = squeeze(FockState.vacuum(20), r=r)
assert abs(mean_photon(st) - np.sinh(r) ** 2) < 1e-3
rho = loss(FockState.fock(1, 12), T=0.4)
assert abs(trace(rho) - 1.0) < 1e-10
assert abs(rho.rho[0, 0].real - 0.6) < 1e-8
assert abs(rho.rho[1, 1].real - 0.4) < 1e-8
assert abs(wigner_fock(FockState.vacuum(30), 0.0, 0.0) - 1 / np.pi) < 1e-6
assert wigner_fock(FockState.fock(1, 30), 0.0, 0.0) < 0
print("T2 self-check OK")
"""
        ),
    ],
)

# ---------------------------------------------------------------------------
# T3 Bosonic
# ---------------------------------------------------------------------------
write(
    "03_bosonic_beginner.ipynb",
    [
        md(
            r"""# 03 · Bosonic 表示新手教程

**Bosonic（高斯叠加）表示**把态写成若干高斯组件：

$$
\{(V_k, \bar r_k, w_k)\}_{k=1}^K
$$

权重 $w_k$ 可复；纯态归一要 **Gram**（组件不正交时 $\sum w$ 有讲究）。

本教程：`even_cat`、`gkp0`/`gkp1`、门、loss、logical overlap。

配套笔记：`03-Bosonic表示原理.md`。"""
        ),
        md(
            r"""## 1. 这是啥 / 为啥用

- Cat：$|\alpha\rangle \pm |-\alpha\rangle$ → 对角高斯 + **交叉项**（复均值组件）
- GKP：格子上许多窄峰 + 可选交叉 → 教学纠错码态
- **高斯门**：每个组件用同一 $S,d$ 变；**权重 $w$ 不变**
- 比 Fock 截断更适合「中等非高斯 + 仍近似高斯峰」

**一句话：** 非高斯，但还能拆成有限个高斯包时，用 Bosonic。"""
        ),
        md(
            r"""## 2. 约定

- 与 G 相同：$\hbar=1$，xxpp，真空 $V=I/2$
- $\sum_k w_k = 1$（可检）
- GKP：$\Delta=\sqrt{2\pi}$；`lattice=1d|2d`；`cross=none|nn|full`（2d 无 nn）
- 权重形式 $Z=c^\dagger S c$（Gram）——与 cat 同构思想"""
        ),
        code(BOOT),
        code(
            r"""
from cvsim.bosonic import (
    even_cat,
    gkp0,
    gkp1,
    gkp_logical_overlap,
    homodyne_condition,
    loss,
    mean_photon,
    phase,
    squeeze,
    weight_sum,
)
"""
        ),
        md(
            r"""## 3. 最小闭环：even cat

$|\mathrm{cat}_+\rangle \propto |\alpha\rangle + |-\alpha\rangle$ → **4 组件**（2 对角 + 2 交叉）。"""
        ),
        code(
            r"""
alpha = 0.8
cat = even_cat(alpha)
print("K =", cat.n_components)
print("sum w =", weight_sum(cat))
for i, c in enumerate(cat.components):
    print(f"  [{i}] w={c.w.real:+.5f}{c.w.imag:+.5f}j  rbar={c.rbar}")
"""
        ),
        md(
            r"""## 4. 数字检查：门保持权重；phase 转峰

高斯门不改 $w$（仅改各组件的 $V,\bar r$）。"""
        ),
        code(
            r"""
cat = even_cat(0.8)
w0 = [c.w for c in cat.components]
cat2 = squeeze(phase(cat, 0.3), 0.1)
w1 = [c.w for c in cat2.components]
print("weights unchanged?", all(abs(a - b) < 1e-14 for a, b in zip(w0, w1)))
print("sum w after gates:", weight_sum(cat2))
"""
        ),
        md(
            r"""## 5a. GKP 教学态

- `cross="none"`：只有对角峰（混态齿梳感）
- `cross="full"`：全齿对交叉（1d 更「纯态感」）
- `lattice="2d"`：$(x,p)$ 方格对角峰；`cross="full"` 可开但组件数 $M^2$

`gkp_logical_overlap`：用对角峰近似逻辑重叠；self ≈ 1，0 vs 1 应较小。"""
        ),
        code(
            r"""
eps, N = 0.12, 2
z0_none = gkp0(eps, grid_size=N, cross="none")
z0_full = gkp0(eps, grid_size=N, cross="full")
z1_full = gkp1(eps, grid_size=N, cross="full")
print("K none/full:", z0_none.n_components, z0_full.n_components)
print("sum w full:", weight_sum(z0_full))
print("<0|0> ~", gkp_logical_overlap(z0_full, z0_full))
print("<0|1> ~", gkp_logical_overlap(z0_full, z1_full), "  (|ov| should be smaller)")

z2 = gkp0(0.15, grid_size=1, lattice="2d", cross="none")
print("2d diag K:", z2.n_components, "expect 9")
"""
        ),
        md(
            r"""## 5b. loss 与 condition 一瞥

`loss(T=0)` 理想全丢 → 近似真空，$\langle n\rangle\approx 0$，∑w 仍 1。

`homodyne_condition(state, mode, phi, outcome)` 在 B 上走 **复仿射 + 似然**（比 G 更一般）。"""
        ),
        code(
            r"""
cat = even_cat(0.8)
print("<n> cat:", mean_photon(cat))
print("<n> after T=0 loss:", mean_photon(loss(cat, T=0.0)))
post = homodyne_condition(cat, mode=0, phi=0.0, outcome=0.0)
print("K after condition:", post.n_components, "sum w:", weight_sum(post))
"""
        ),
        md(
            r"""## 6. 诚实边界 + 何时换表示

**Bosonic 适合**

- Cat / 截断 GKP / 有限高斯叠加
- 与 G 共用辛门，但可保留交叉干涉

**诚实：本包 GKP 不是完整纠错栈**

- 无逻辑 Clifford 完备、无 dual 基展开、无 stabilizer 解码
- 2d `cross=nn` 未做；大 N 组件爆炸

**选型速查**

| 问题 | 优先 |
|------|------|
| 大规模线性光学、矩、loss | Gaussian |
| 光子数、Kerr、小系统 Wigner | Fock |
| Cat/GKP、有限非高斯叠加 | Bosonic |

跨表示同一数字：命令行 `python -m cvsim.demos.m4_cross_rep`。"""
        ),
        md("## 自检"),
        code(
            r"""
cat = even_cat(0.8)
assert cat.n_components == 4
assert abs(weight_sum(cat) - 1.0) < 1e-12
z0 = gkp0(0.15, 2, cross="full")
assert z0.n_components == 25
assert abs(weight_sum(z0) - 1.0) < 1e-12
assert abs(gkp_logical_overlap(z0, z0) - 1.0) < 1e-8
z1 = gkp1(0.15, 2, cross="full")
assert abs(gkp_logical_overlap(z0, z1)) < 0.5
assert abs(mean_photon(loss(cat, 0.0))) < 1e-10
print("T3 self-check OK")
"""
        ),
    ],
)

# ---------------------------------------------------------------------------
# T4 TMSV + F-ANALYSE (Phase 2 teach)
# ---------------------------------------------------------------------------
write(
    "04_tmsv_analyse.ipynb",
    [
        md(
            r"""# 04 · TMSV 与高斯分析量

Phase 2 教学本：用 **双模挤压真空（TMSV）** 串起

`purity` · `symplectic_eigenvalues` · `entropy_vn` · `partial_trace` · `log_negativity` · `heterodyne`

配套：`docs/vision-gaussian-simulator.md` §4.2 F-ANALYSE；`docs/api-stability.md`。
先完成本目录 `01_gaussian_beginner.ipynb` 再来。"""
        ),
        md(
            r"""## 1. 这是啥 / 为啥用

- TMSV 是连续变量里最标准的 **双模纠缠源**（EPR 光）。
- 整体是 **纯高斯态**；任一单模约化是 **热态** $\bar n=\sinh^2 r$。
- 分析量有闭式，最适合核对模拟器：

| 量 | TMSV 期望 |
|----|-----------|
| 整体 purity | $1$ |
| 整体 $S_{\mathrm{vN}}$ | $0$（nats） |
| 约化热态 purity | $1/(2\bar n+1)$ |
| 对数负性 $\mathcal E_N$ | $-\log_2(e^{-2r})=2r/\ln 2$（bits） |
| Heterodyne 导引 | 测 A 得 $\beta$ → B 为 $\lvert\tanh r\,\beta^*\rangle$ |"""
        ),
        md(
            r"""## 2. 约定（与全库一致）

| 项 | 值 |
|----|-----|
| $\hbar$ | 1 |
| 正交序 | **xxpp** |
| 真空 | $V=I/2$ |
| `entropy_vn` | **nats**（$\ln$） |
| `log_negativity` | **bits**（$\log_2$） |
| Heterodyne $\beta$ | $(x+ip)/\sqrt{2}$ |"""
        ),
        code(BOOT),
        code(
            r"""
from cvsim.gaussian import (
    GaussianState,
    entropy_vn,
    heterodyne_condition,
    log_negativity,
    loss,
    mean_photon,
    partial_trace,
    purity,
    symplectic_eigenvalues,
)
"""
        ),
        md(
            r"""## 3. 建造 TMSV 并确认「整体纯」

工厂：`GaussianState.tmsv(r, nmode=2)`。

纯高斯 ⟺ 全部辛本征值 $\nu_j=1/2$ ⟺ $\mu=1$ ⟺ $S=0$。"""
        ),
        code(
            r"""
r = 0.6
st = GaussianState.tmsv(r, nmode=2, mode1=0, mode2=1)
print("nmode", st.nmode)
print("ν =", symplectic_eigenvalues(st))
print("purity", purity(st))
print("S_vn (nats)", entropy_vn(st))
print("<n> total", mean_photon(st), "  2 sinh^2 r =", 2 * np.sinh(r) ** 2)
"""
        ),
        md(
            r"""## 4. 偏迹 → 单模热态

`partial_trace(state, keep)`：**无测量**地丢掉子系统（≠ Homodyne/Heterodyne conditioning）。

TMSV 对一模偏迹：

$$
\bar n = \sinh^2 r,\quad
\mu = \frac{1}{2\bar n+1},\quad
S = (\bar n+1)\ln(\bar n+1) - \bar n\ln\bar n
$$
（$\bar n=0$ 时 $S=0$）"""
        ),
        code(
            r"""
red = partial_trace(st, keep=[0])
nbar = float(np.sinh(r) ** 2)
print("reduced nmode", red.nmode)
print("ν_red", symplectic_eigenvalues(red), "  expect", [nbar + 0.5])
print("purity", purity(red), "  expect", 1.0 / (2 * nbar + 1))
S = entropy_vn(red)
S_closed = (nbar + 1) * np.log(nbar + 1) - nbar * np.log(nbar)
print("S_vn", S, "  closed", S_closed)
# 纠缠熵：纯二分下 S(A)=S(B)
assert abs(entropy_vn(partial_trace(st, [1])) - S) < 1e-12
print("S(A)=S(B) OK")
"""
        ),
        md(
            r"""## 5. 对数负性（bits）

对子系统 A 做 partial transpose（翻 $p_A$），再对 PT 协方差取 **raw** 辛谱（允许 $\tilde\nu<1/2$）：

$$
\mathcal E_N = \sum_j \max\{0, -\log_2(2\tilde\nu_j)\}
$$

TMSV 闭式（vision freeze）：

$$
\mathcal E_N = -\log_2(e^{-2r}) = \frac{2r}{\ln 2}
$$

可分态（如热态直积）→ $\mathcal E_N=0$。"""
        ),
        code(
            r"""
EN = log_negativity(st, modes_A=0)
EN_closed = -np.log2(np.exp(-2 * r))
print("E_N", EN, "  closed", EN_closed)
print("symmetric A|B", log_negativity(st, [1]))

prod = GaussianState.product(
    GaussianState.thermal(0.5, nmode=1),
    GaussianState.thermal(1.0, nmode=1),
)
print("separable E_N", log_negativity(prod, 0), "  (expect 0)")
"""
        ),
        md(
            r"""### 小图：E_N 随 r 增长"""
        ),
        code(
            r"""
rs = np.linspace(0.0, 1.2, 25)
EN_num = [log_negativity(GaussianState.tmsv(ri, nmode=2), 0) for ri in rs]
EN_th = -np.log2(np.exp(-2 * rs))

fig, ax = plt.subplots(figsize=(5, 3.2))
ax.plot(rs, EN_th, "k-", lw=2, label=r"$-\log_2(e^{-2r})$")
ax.plot(rs, EN_num, "o", ms=4, alpha=0.8, label="cvsim")
ax.set_xlabel(r"squeeze $r$")
ax.set_ylabel(r"$\mathcal{E}_N$ (bits)")
ax.legend()
ax.set_title("TMSV log-negativity")
fig.tight_layout()
plt.show()
"""
        ),
        md(
            r"""## 6. Heterodyne 导引

对 A 做 Heterodyne（POVM $\lvert\beta\rangle\langle\beta\rvert/\pi$）并 **删掉 A** 后，B 被导引到纯相干态：

$$
\lvert\psi_B\rangle = \lvert \tanh(r)\,\beta^*\rangle
$$

（标准 TMSV 的 $p$ 反关联 → 复数共轭。）"""
        ),
        code(
            r"""
beta = 0.4 + 0.2j
red_h = heterodyne_condition(st, mode=0, outcome=beta)
print("nmode after hetero", red_h.nmode)
print("purity", purity(red_h), "  (expect 1)")
beta_B = complex((red_h.rbar[0] + 1j * red_h.rbar[1]) / np.sqrt(2.0))
expect = np.tanh(r) * np.conjugate(beta)
print("beta_B", beta_B, "  expect", expect)
"""
        ),
        md(
            r"""## 7. 损耗会吃掉纠缠

对 TMSV 两模同时加 `loss(T)` 后，$\mathcal E_N$ 下降（无简单万能闭式；这里只看单调性）。"""
        ),
        code(
            r"""
Ts = [1.0, 0.8, 0.5, 0.2, 0.05]
print(f"{'T':>6}  {'E_N':>10}")
for T in Ts:
    noisy = loss(st, T)  # all modes
    print(f"{T:6.2f}  {log_negativity(noisy, 0):10.6f}")
"""
        ),
        md(
            r"""## 8. 诚实边界

- `entropy_vn` 是 **nats**；若要 bits，自己 `/ np.log(2)`。
- `log_negativity` 的 PT 谱 **不能**走带 vacuum-clip 的 `symplectic_eigenvalues`（内部用 raw 谱）。
- `partial_trace` ≠ 测量后的 `remove_mode`（无 outcome conditioning）。
- 公开 API 列表见 `cvsim.gaussian.__all__` / `docs/api-stability.md`。

**下一步**

- Phase 1 电路 demo：`examples/phase1_exit_demo.py`
- Phase 3 方向：compile 合并辛矩阵、批量采样、Walrus 适配"""
        ),
        md("## 自检（Run-All 应全绿）"),
        code(
            r"""
r = 0.6
st = GaussianState.tmsv(r, nmode=2)
assert abs(purity(st) - 1.0) < 1e-10
assert abs(entropy_vn(st)) < 1e-10
nu = symplectic_eigenvalues(st)
assert nu.shape == (2,) and np.allclose(nu, 0.5, atol=1e-10)

nbar = float(np.sinh(r) ** 2)
red = partial_trace(st, [0])
assert abs(purity(red) - 1.0 / (2 * nbar + 1)) < 1e-10
S_closed = (nbar + 1) * np.log(nbar + 1) - nbar * np.log(nbar)
assert abs(entropy_vn(red) - S_closed) < 1e-10

EN = log_negativity(st, 0)
assert abs(EN - (-np.log2(np.exp(-2 * r)))) < 1e-10
assert abs(log_negativity(st, 1) - EN) < 1e-12

beta = 0.4 + 0.2j
red_h = heterodyne_condition(st, 0, beta)
assert abs(purity(red_h) - 1.0) < 1e-10
beta_B = (red_h.rbar[0] + 1j * red_h.rbar[1]) / np.sqrt(2.0)
assert abs(beta_B - np.tanh(r) * np.conjugate(beta)) < 1e-10

assert log_negativity(loss(st, 0.5), 0) < EN
print("T4 TMSV analyse self-check OK")
"""
        ),
    ],
)

print("done")
