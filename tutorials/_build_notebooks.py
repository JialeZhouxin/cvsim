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

1. **均值向量** \(\bar r\)（displacement / 位移）
2. **协方差矩阵** \(V\)（covariance / 涨落与纠缠）

本教程只动 **`cvsim.gaussian`**：真空 → 挤压 → 位移 → 分束 → 损耗 → Homodyne。

配套笔记：`02-Gaussian表示原理.md`。"""
        ),
        md(
            r"""## 1. 这是啥 / 为啥用

- 激光近似真空 + 位移（相干态）是高斯的。
- 挤压光、分束器、多模线性光学：高斯门 **只改 \(V,\bar r\)**，不需要整本 Hilbert 空间。
- 成本：\(O(m^2)\) 量级，模数 \(m\) 可以比 Fock 大很多。

**一句话：** 你只关心「平均在哪 + 噪声椭圆长什么样」时，用 Gaussian。"""
        ),
        md(
            r"""## 2. 约定钉死（三表示共用）

| 项 | 值 |
|----|-----|
| \(\hbar\) | **1** |
| 正交序 | **xxpp**：\((x_1\ldots x_m, p_1\ldots p_m)\) |
| 真空 | \(V=I/2\)，\(\bar r=0\) |
| 纯单模高斯 | \(\det V = 1/4\) |
| 单模挤压 | \(\langle n\rangle = \sinh^2 r\) |
| 位移 | \(d_x=\sqrt{2}\mathrm{Re}\alpha\)，\(d_p=\sqrt{2}\mathrm{Im}\alpha\) |"""
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
)
"""
        ),
        md(
            r"""## 3. 最小闭环：真空 → 挤压

真空 \(V=I/2\)。沿 \(x\) 挤压（参数 \(r\)）后：

\[
V = \tfrac12\mathrm{diag}(e^{-2r}, e^{2r}),\quad
\det V = 1/4,\quad
\langle n\rangle = \sinh^2 r.
\]"""
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
            r"""## 4. 数字检查：位移 + Homodyne

相干态 ≈ 真空位移。本约定 \(\langle x\rangle = \sqrt{2}\mathrm{Re}\alpha\)。

Homodyne（零差测量）测 \(x_\varphi = x\cos\varphi + p\sin\varphi\)；高斯边缘方差 \(u^\top V u\)。

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
            r"""## 5a. 再进一步：两模挤压 + 分束

模 0 先挤，再与真空模 1 做 50/50 BS。总光子数守恒（理想无损）。"""
        ),
        code(
            r"""
r = 0.6
two = GaussianState.vacuum(2)
two = squeeze(two, r=r, mode=0)
two = beamsplitter(two, 0, 1, theta=np.pi / 4)
print("total <n> :", mean_photon(two), "expect", float(np.sinh(r) ** 2))
print("det V     :", det_cov(two), "expect (1/4)^2 =", 0.0625)
"""
        ),
        md(
            r"""## 5b. 损耗 loss 与条件 Homodyne

纯损耗：`loss(T)`，\(0\le T\le 1\)，环境真空。相干态 \(\langle n\rangle \to T|\alpha|^2\)。

`homodyne_condition(state, mode, phi, outcome)`：高斯 **Kalman 更新**——测完后测向方差 → 0，均值 → outcome。"""
        ),
        code(
            r"""
alpha, T = 1.5, 0.4
st = loss(displace(GaussianState.vacuum(1), alpha=alpha), T=T)
print("after loss <n>:", mean_photon(st), "expect", T * abs(alpha) ** 2)

# 条件测量：真空上「假装」测到 x=0.7
post = homodyne_condition(GaussianState.vacuum(1), mode=0, phi=0.0, outcome=0.7)
print("post mean x:", homodyne_mean(post, phi=0.0), "  var x:", homodyne_var(post, phi=0.0))

# 采样（随机抽一次结果；可设 seed）
rng = np.random.default_rng(0)
samples = [
    homodyne_sample(GaussianState.vacuum(1), phi=0.0, rng=rng) for _ in range(5)
]
print("5 vacuum samples:", samples)
"""
        ),
        md(
            r"""## 6. 诚实边界 + 何时换表示

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

**Fock 表示**把态写成光子数基底 \(\{|n\rangle\}\) 上的振幅（或密度矩阵 \(\rho\)）。

本教程只动 **`cvsim.fock`**：截断 → 门 → PNRD → loss→ρ → Wigner → Homodyne。

配套笔记：`01-Fock表示原理.md`、`04-…` 四问篇。"""
        ),
        md(
            r"""## 1. 这是啥 / 为啥用

- 你想问：「测到 0、1、2… 光子的概率是多少？」→ Fock 最直接。
- 非高斯门（Kerr）、截断下的精确幺正，也走 Fock。
- **代价：** 截断 \(N\)，\(m\) 模维度 \(\sim N^m\)。本包教学用 **1–2 模**。

**一句话：** 要光子数 / 非高斯，用 Fock；模一多就痛。"""
        ),
        md(
            r"""## 2. 约定

与 Gaussian 同一物理：\(\hbar=1\)，位移 \(\sqrt{2}\) 约定。

额外：

- `FockState`：纯态振幅；2 模时 `amps` 形状 \((N,N)\)
- `FockDensity`：混态 \(\rho\)（loss 之后）
- **截断不是物理墙**，是数值近似——\(N\) 太小会错"""
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

解析：\(\langle n\rangle = \sinh^2 r\)。Fock 里用截断幺正近似——**N 越大越准**。"""
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

\(|10\rangle\) 过 50/50 BS → 两端单光子概率各约 \(1/2\)。"""
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

纯态 \(|1\rangle\) 经透射率 \(T\) 的纯损耗：\(\rho_{00}\approx 1-T\)，\(\rho_{11}\approx T\)。

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

真空：\(W(0,0)=1/\pi\)。\(|1\rangle\) 中心可负（非经典）。

**诚实：** Fock 的 `homodyne_condition` 是 **截断空间里 \(x_\varphi\) 本征投影**，  
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

- \(m\ge 3\)、大 cutoff
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

\[
\{(V_k, \bar r_k, w_k)\}_{k=1}^K
\]

权重 \(w_k\) 可复；纯态归一要 **Gram**（组件不正交时 \(\sum w\) 有讲究）。

本教程：`even_cat`、`gkp0`/`gkp1`、门、loss、logical overlap。

配套笔记：`03-Bosonic表示原理.md`。"""
        ),
        md(
            r"""## 1. 这是啥 / 为啥用

- Cat：\(|\alpha\rangle \pm |-\alpha\rangle\) → 对角高斯 + **交叉项**（复均值组件）
- GKP：格子上许多窄峰 + 可选交叉 → 教学纠错码态
- **高斯门**：每个组件用同一 \(S,d\) 变；**权重 \(w\) 不变**
- 比 Fock 截断更适合「中等非高斯 + 仍近似高斯峰」

**一句话：** 非高斯，但还能拆成有限个高斯包时，用 Bosonic。"""
        ),
        md(
            r"""## 2. 约定

- 与 G 相同：\(\hbar=1\)，xxpp，真空 \(V=I/2\)
- \(\sum_k w_k = 1\)（可检）
- GKP：\(\Delta=\sqrt{2\pi}\)；`lattice=1d|2d`；`cross=none|nn|full`（2d 无 nn）
- 权重形式 \(Z=c^\dagger S c\)（Gram）——与 cat 同构思想"""
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

\(|\mathrm{cat}_+\rangle \propto |\alpha\rangle + |-\alpha\rangle\) → **4 组件**（2 对角 + 2 交叉）。"""
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

高斯门不改 \(w\)（仅改各组件的 \(V,\bar r\)）。"""
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
- `lattice="2d"`：\((x,p)\) 方格对角峰；`cross="full"` 可开但组件数 \(M^2\)

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

`loss(T=0)` 理想全丢 → 近似真空，\(\langle n\rangle\approx 0\)，∑w 仍 1。

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

print("done")
