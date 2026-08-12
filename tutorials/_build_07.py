# -*- coding: utf-8 -*-
"""Build tutorial 07 (Fock differentiable designer, Phase F4). Run from repo root.

    py -3 tutorials/_build_07.py

Generates tutorials/07_fock_ad_designer.ipynb (UTF-8, stdlib only).
"""
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

CELLS = [
    md(
        r"""# 07 · Fock 可微设计器：梯度反推猫态生成电路

教程 05 用**梯度**反向设计了 Gaussian 纠缠源（`cvsim.ad`）。
本教程做同样的事，但站在 **Fock** 表示上（`cvsim.fock_ad`，Phase F4）：

- 电路：**挤压** S(r) → **Kerr** K(χ) → 光子损耗通道
- 目标：让输出态尽量接近**偶猫态** $|α\rangle + |-\alpha\rangle$
- 工具：`jax.grad` 穿过整条链（expm 门 + 密度矩阵 + 损耗超算符），
  梯度上升自动找 (r, χ)

依赖：`cvsim.fock_ad` + **JAX**（可选后端，未装时本教程不运行）。"""
    ),
    md(
        r"""## 1. 物理设定：Kerr-squeezed 态 ≈ 猫态

偶猫态 $|\psi_{\rm cat}\rangle \propto |α\rangle + |-\alpha\rangle$ 只含**偶数**光子数分量，
是量子纠错（GKP/猫码）的基本资源。怎么造？

**Kerr-squeezed 方案**：先把真空挤压成薛定谔猫的"苗"（偶光子数分量的交错相位），
再让 Kerr 非线性 $e^{iχ\hat n^2}$ 给第 $n$ 分量一个 $n^2$ 的相位。
$χ = π/4$ 时相位 $n^2π/4 \bmod 2π$ 恰好把分量重新对齐成猫态。

损耗（透射率 $η$）会破坏这个干涉图案 —— 保真度下降。
**反向设计问题**：给定 $η$，最优 (r, χ) 是多少？

本教程全用**公共 API**：`cvsim.fock_ad`（可微链）+ `cvsim.fock`（参考实现）。"""
    ),
    code(
        r"""
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
matplotlib.rcParams['font.sans-serif'] = ['SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False

from cvsim.fock_ad import cat_fidelity, bs_overlap, squeeze_u, bs_u, kerr_diag
import cvsim.fock as fock  # 公共参考实现（猫工厂 / 泄漏检查）

ALPHA = 1.2   # 猫振幅 |α|
ETA = 0.85    # 损耗透射率（默认）
CUT = 12      # 截断维数
"""
    ),
    md(
        r"""## 2. numpy 网格扫描：先看地形，找好初值

纯 numpy 路径（复用 `cvsim.fock.gates` 真源公式）把 (r, χ) 网格全算一遍，
得到保真度地形图 —— 既看全局最优在哪，也给梯度上升一个好起点。"""
    ),
    code(
        r"""
rs = np.linspace(0.05, 1.5, 30)
cs = np.linspace(0.0, 1.2, 30)
F = np.empty((len(rs), len(cs)))
for i, r in enumerate(rs):
    for j, c in enumerate(cs):
        F[i, j] = cat_fidelity("numpy", r, c, alpha=ALPHA, T=ETA, cutoff=CUT)

i0, j0 = np.unravel_index(np.argmax(F), F.shape)
r_init, c_init = rs[i0], cs[j0]
print(f"网格最优: F = {F[i0, j0]:.4f}  @ r = {r_init:.3f}, χ = {c_init:.3f}")

plt.figure(figsize=(6, 5))
plt.contourf(cs, rs, F, levels=24)
plt.colorbar(label="cat fidelity F")
plt.plot(c_init, r_init, "r*", ms=14, label="网格最优")
plt.xlabel("Kerr χ"); plt.ylabel("挤压 r")
plt.title(f"F(r, χ) 地形（α={ALPHA}, η={ETA}）")
plt.legend(); plt.show()
"""
    ),
    md(
        r"""## 3. jax.grad vs 有限差分：梯度自检

`cvsim.fock_ad` 的 jax 路径是 numpy 公式的 **jnp 镜像**（`jax.scipy.linalg.expm`
可微，损耗 Kraus 用 numpy 预构建常数张量 + einsum `'kam,mn,kbn->ab'`，
不在 jax 内重建）——所以 `jax.grad` 能穿过 expm 门、密度矩阵和损耗链。

Phase F4 exit 1 标准：梯度与中心有限差分一致（h=1e-6, atol=1e-6）。
三个参数各查一次：挤压 r、BS θ、Kerr χ。"""
    ),
    code(
        r"""
import jax
import jax.numpy as jnp

H = 1e-6

def fd(f, x):
    return (float(f(x + H)) - float(f(x - H))) / (2 * H)

# r: 穿过整条猫链
def fr(r):
    return cat_fidelity("jax", r, 0.2, alpha=ALPHA, T=ETA, cutoff=CUT)

# θ: BS 链（解析值 sin²θ → 2 sinθ cosθ）
def fth(th):
    return bs_overlap("jax", th, cutoff=8)

# χ: 穿过整条猫链
def fc(c):
    return cat_fidelity("jax", 0.3, c, alpha=ALPHA, T=ETA, cutoff=CUT)

for name, f, x0, analytic in [
    ("dF/dr", fr, 0.3, None),
    ("d|⟨0,1|BS|1,0⟩|²/dθ", fth, 0.4, 2 * np.sin(0.4) * np.cos(0.4)),
    ("dF/dχ", fc, 0.2, None),
]:
    g = float(jax.grad(f)(x0))
    fdv = fd(f, x0)
    ref = analytic if analytic is not None else fdv
    print(f"{name} @ x={x0}: jax.grad = {g:.6f}  解析/fd = {ref:.6f}  差 = {abs(g - ref):.2e}")
    assert abs(g - ref) < 1e-6
print("梯度 OK：与有限差分一致（exit 1 bar 1e-6）")
"""
    ),
    md(
        r"""## 4. 梯度上升：自动优化 (r, χ)

从网格初值出发，沿 $+\nabla F$ 走 150 步（r 和 χ 各用自己的学习率）。
参照物：第 2 节的暴力网格最优。收敛后 χ* 应该停在 **π/4** 附近
（Kerr 猫态的教科书值）——优化器自己"发现"了物理。"""
    ),
    code(
        r"""
def objective(r, c, eta=ETA):
    return cat_fidelity("jax", r, c, alpha=ALPHA, T=eta, cutoff=CUT)

grad = jax.grad(objective, argnums=(0, 1))

r, c = r_init, c_init
hist = []
for step in range(150):
    gr, gc = grad(r, c)
    r = float(np.clip(r + 0.05 * float(gr), 0.0, 3.0))
    c = float(np.clip(c + 0.02 * float(gc), 0.0, 3.0))
    hist.append(float(objective(r, c)))

print(f"梯度上升 150 步 → r* = {r:.4f}, χ* = {c:.4f}, F* = {hist[-1]:.4f}")
print(f"χ* vs π/4: {abs(c - np.pi / 4):.2e}   网格最优 F = {F[i0, j0]:.4f}")
assert abs(c - np.pi / 4) < 1e-3
assert hist[-1] >= F[i0, j0] - 0.01

# 截断诚实性：Kerr 是对角门，不改变截断外质量 → 用挤压态的解析 tail
leak = fock.truncation_leakage(fock.FockState.squeezed(CUT, r))
print(f"挤压态截断泄漏: {leak:.2e}" + ("（可忽略）" if leak < 1e-6 else "（边界效应，cutoff 需加大）"))

plt.figure(figsize=(10, 3.5))
plt.subplot(1, 2, 1)
plt.plot(hist)
plt.axhline(F[i0, j0], color="r", ls="--", label="网格最优")
plt.xlabel("步数"); plt.ylabel("F"); plt.title("保真度上升")
plt.legend()
plt.subplot(1, 2, 2)
plt.plot([objective(r, c) for r in np.linspace(0.3, 1.4, 40)], ".")
plt.xlabel("r"); plt.ylabel("F"); plt.title("收敛点附近地形")
plt.tight_layout(); plt.show()
"""
    ),
    md(
        r"""## 5. 生存曲线：最优设计随损耗 η 变化

把"反向设计"重复在多个 η 上：每个 η 都从网格初值重新跑一遍梯度上升，
记录最优 (r*, χ*)。得到**设计曲线**：

- **弱损耗区（η ≥ 0.7）**：损耗越强，最优挤压 r* 越小 ——
  挤压出的光子反正会丢，少挤压更划算（设计直觉成立）
- **强损耗区（η < 0.6）**：r* 反而回升 —— 强损耗把态拉向真空，
  需要更多初始挤压来补偿猫振幅；此区同时受截断（cutoff=12）边界影响，
  保真度是"截断内"的值

χ* 始终钉在 π/4 —— Kerr 相位是猫态的**普适**配方，与损耗无关。"""
    ),
    code(
        r"""
etas = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]
r_opts, c_opts, F_opts = [], [], []
for eta in etas:
    grad_e = jax.grad(lambda r, c, eta=eta: objective(r, c, eta), argnums=(0, 1))
    r, c = r_init, c_init
    for _ in range(150):
        gr, gc = grad_e(r, c)
        r = float(np.clip(r + 0.05 * float(gr), 0.0, 3.0))
        c = float(np.clip(c + 0.02 * float(gc), 0.0, 3.0))
    r_opts.append(r); c_opts.append(c); F_opts.append(float(objective(r, c, eta)))
    print(f"η={eta:.2f}: r* = {r:.3f}, χ* = {c:.3f}, F* = {F_opts[-1]:.4f}")

plt.figure(figsize=(10, 3.5))
plt.subplot(1, 2, 1)
plt.plot(etas, F_opts, "o-")
plt.xlabel("透射率 η"); plt.ylabel("最优保真度 F*")
plt.title("生存曲线：损耗越强，最优保真度越低")
plt.grid(alpha=0.3)
plt.subplot(1, 2, 2)
plt.plot(etas, r_opts, "o-")
plt.axvspan(0.6, 0.3, color="orange", alpha=0.15, label="强损耗补偿区")
plt.xlabel("透射率 η"); plt.ylabel("最优挤压 r*")
plt.title("设计曲线：弱损耗区 r* 随 η 下降")
plt.legend(); plt.grid(alpha=0.3)
plt.tight_layout(); plt.show()
"""
    ),
    md(
        r"""## 6. 小结

- **正向**（教程 02）：给定 (r, χ, η) 算态、算保真度
- **反向**（本教程）：`cvsim.fock_ad` 把整条链变成可微函数，
  梯度上升自动找 (r*, χ*) —— 与 Gaussian 05 对仗，Fock 侧"参数 → 梯度 → 优化"闭环打通
- 优化器"发现"了 χ* = π/4（Kerr 猫态配方）—— 没喂它任何解析公式
- **诚实性**：保真度是截断基内的值（cutoff=12），强损耗区的最优 r 回升
  部分来自截断边界效应（泄漏检查见上）；加大 cutoff 可验证收敛
- JAX 是可选后端：numpy 路径复用 `cvsim.fock.gates` 真源公式，
  双后端共享同一套测试（`tests/test_fock_ad_f4.py`）

下一步可玩：把损耗换成放大器/相位噪声，或优化 BS 角 + 挤压的多参数猫态制备。"""
    ),
]

if __name__ == "__main__":
    OUT.joinpath("07_fock_ad_designer.ipynb").write_text(
        json.dumps(notebook(CELLS), ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print("wrote tutorials/07_fock_ad_designer.ipynb")
