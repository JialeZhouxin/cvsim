# -*- coding: utf-8 -*-
"""Build tutorial 05 (differentiable designer, Phase 4 F-AD). Run from repo root.

    py -3 tutorials/_build_05.py

Generates tutorials/05_ad_designer.ipynb (UTF-8, stdlib only).
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
        r"""# 05 · 可微设计器：用梯度反向设计纠缠源

前四个教程都是**正向**问题：给定电路参数，算结果。

本教程反过来 —— **反向设计**：给定一个目标（最大纠缠、有限光子预算），
让优化器自己找电路参数。

工具：**自动微分（AD）**。电路参数 `r, θ` 是变量，
目标函数对它们可求梯度，梯度上升自动爬向最优。

依赖：`cvsim.ad`（Phase 4 F-AD）+ **JAX**（可选后端）。
JAX 未装时本教程不运行（见最下方安装说明）。"""
    ),
    md(
        r"""## 1. 正向回顾：TMSV → 损耗 → 纠缠

两模压缩态（TMSV）是最经典的纠缠源：

- 挤压参数 $r$ 越大 → 纠缠越大，$E_N = 2r/\ln 2$（无损时）
- 但光子数 $\langle n\rangle = 2\sinh^2 r$ 也指数增长 —— 纠缠不免费
- 经过损耗通道 $\eta$ 后 $E_N$ 会**饱和**（继续增加 $r$ 收益递减）

先看曲线形状。"""
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

from cvsim.ad import apply_gaussian, log_neg_loss
from cvsim.symplectic import S_two_mode_squeeze

def tmsv_after_loss(r, eta):
    '''TMSV(r) 的协方差 → 模0过损耗 η → 返回 V。'''
    S = np.asarray(S_two_mode_squeeze(2, r, 0, 1))
    V = S @ (np.eye(4) * 0.5) @ S.T
    X = np.eye(4); Y = np.zeros((4, 4))
    sT = np.sqrt(eta); y = (1 - eta) * 0.5
    X[0, 0] = sT; X[2, 2] = sT; Y[0, 0] = y; Y[2, 2] = y
    return X @ V @ X.T + Y

rs = np.linspace(0, 3, 200)
for eta, lab in [(1.0, "无损 η=1"), (0.7, "η=0.7"), (0.3, "η=0.3")]:
    es = [log_neg_loss("numpy", tmsv_after_loss(r, eta), 0) for r in rs]
    plt.plot(rs, es, label=lab)
plt.xlabel("挤压参数 r"); plt.ylabel("log-negativity $E_N$（bits）")
plt.title("损耗下 $E_N(r)$ 饱和 —— 没有有限最优")
plt.legend(); plt.grid(alpha=0.3); plt.show()
"""
    ),
    md(
        r"""## 2. 目标函数：纠缠不免费

上图显示 $E_N(r)$ 在损耗下**饱和** —— 单纯最大化 $E_N$ 会一路推到 $r\to\infty$。

给目标加上**能量惩罚**就有内点最优了：

$$\text{obj}(r) = E_N(r;\eta) - \lambda \cdot \langle n \rangle, \qquad
\langle n \rangle = 2\sinh^2 r$$

- $\lambda$：每个光子的"价格"（成本系数）
- 大 $r$：纠缠收益饱和，但光子成本指数涨 → 惩罚主导 → 最优在中间

物理故事：**给定光子预算，最优挤压是多少？** 这就是反向设计。"""
    ),
    code(
        r"""
LAM = 0.5   # 光子价格
ETA = 0.7   # 损耗透射率

def objective_np(r):
    '''numpy 版目标（用于画图/扫描对照）。'''
    return float(log_neg_loss("numpy", tmsv_after_loss(r, ETA), 0)) - LAM * 2 * np.sinh(r) ** 2

rs = np.linspace(0, 3, 200)
objs = [objective_np(r) for r in rs]
plt.plot(rs, objs)
plt.axvline(rs[int(np.argmax(objs))], color="r", ls="--", label="扫描最优")
plt.xlabel("r"); plt.ylabel("obj = $E_N - \\lambda\\langle n\\rangle$")
plt.title(f"目标函数（η={ETA}, λ={LAM}）：有内点最优")
plt.legend(); plt.grid(alpha=0.3); plt.show()
"""
    ),
    md(
        r"""## 3. 可微路径：jax.grad

现在把同一目标用 **JAX** 重写 —— 全链路 jnp：

`r → S₂(r) → V = S V₀ Sᵀ → 损耗 → PT → 原始辛谱 → E_N`

`log_neg_loss(backend="jax")` 是 numpy 版 `analyse.log_negativity` 的
jnp 镜像（公式同一处，见 `cvsim/ad.py` 注释），
所以 `jax.grad` 能穿过整条链求 $d\,\text{obj}/dr$。

**梯度自检**：与有限差分对照（Phase 4 exit 1 标准）。"""
    ),
    code(
        r"""
import jax
import jax.numpy as jnp

def objective(r):
    S = S_two_mode_squeeze(2, r, 0, 1, backend="jax")
    V = apply_gaussian("jax", S, jnp.eye(4) * 0.5)
    X = jnp.eye(4); Y = jnp.zeros((4, 4))
    sT = jnp.sqrt(ETA); y = (1 - ETA) * 0.5
    X = X.at[0, 0].set(sT); X = X.at[2, 2].set(sT)
    Y = Y.at[0, 0].set(y); Y = Y.at[2, 2].set(y)
    V_l = X @ V @ X.T + Y
    return log_neg_loss("jax", V_l, 0) - LAM * 2.0 * jnp.sinh(r) ** 2

r0 = 0.6
g = float(jax.grad(objective)(r0))
h = 1e-6
fd = (float(objective(r0 + h)) - float(objective(r0 - h))) / (2 * h)
print(f"r={r0}:  jax.grad = {g:.6f}  有限差分 = {fd:.6f}  差 = {abs(g-fd):.2e}")
assert abs(g - fd) < 1e-5
print("梯度 OK：与有限差分一致")
"""
    ),
    md(
        r"""## 4. 梯度上升：自动找最优 r

从 $r=0.1$ 出发，沿着 $+\nabla\,\text{obj}$ 走 60 步，收敛到最优。
红虚线是暴力扫描的参照 —— 优化器自己爬到了那里。"""
    ),
    code(
        r"""
r = 0.1
lr = 0.03
history = []
for step in range(60):
    g = float(jax.grad(objective)(r))
    r += lr * g
    history.append((r, float(objective(r))))

r_opt = r
print(f"梯度上升 60 步 → r* = {r_opt:.4f}")

# 与扫描最优对照
rs = np.linspace(0.01, 4.0, 400)
objs = [objective_np(x) for x in rs]
r_scan = rs[int(np.argmax(objs))]
print(f"暴力扫描最优    → r* = {r_scan:.4f}")
assert abs(r_opt - r_scan) < 0.05

plt.figure(figsize=(10, 3.5))
plt.subplot(1, 2, 1)
plt.plot([h[0] for h in history])
plt.xlabel("步数"); plt.ylabel("r"); plt.title("r 的轨迹")
plt.subplot(1, 2, 2)
plt.plot([h[1] for h in history])
plt.xlabel("步数"); plt.ylabel("obj"); plt.title("目标上升")
plt.tight_layout(); plt.show()
"""
    ),
    md(
        r"""## 5. 设计曲线：最优 r 随光子价格 λ 变化

把"反向设计"重复在多个 λ 上，得到**设计曲线**：
光子越贵 → 最优挤压越小（少买纠缠）；光子越便宜 → 挤压越大。

这就是可微设计器：每个点都是优化器算出来的，不是手推公式。"""
    ),
    code(
        r"""
lams = [0.1, 0.2, 0.5, 1.0, 2.0]
r_opts = []
for lam in lams:
    def obj(r):
        S = S_two_mode_squeeze(2, r, 0, 1, backend="jax")
        V = apply_gaussian("jax", S, jnp.eye(4) * 0.5)
        X = jnp.eye(4); Y = jnp.zeros((4, 4))
        sT = jnp.sqrt(ETA); y = (1 - ETA) * 0.5
        X = X.at[0, 0].set(sT); X = X.at[2, 2].set(sT)
        Y = Y.at[0, 0].set(y); Y = Y.at[2, 2].set(y)
        V_l = X @ V @ X.T + Y
        return log_neg_loss("jax", V_l, 0) - lam * 2.0 * jnp.sinh(r) ** 2
    r = 0.3
    for _ in range(80):
        r += 0.03 * float(jax.grad(obj)(r))
    r_opts.append(r)
    print(f"λ={lam:>4}:  r* = {r:.3f}")

plt.plot(lams, r_opts, "o-")
plt.xlabel("光子价格 λ"); plt.ylabel("最优挤压 r*")
plt.title("设计曲线：光子越贵，纠缠买得越少（η=0.7）")
plt.grid(alpha=0.3); plt.show()
"""
    ),
    md(
        r"""## 6. 系统化做法：`cvsim.optim`

第 4 节的循环手写公式，教学上看得见每一步；但它有三个隐患：

1. **学习率是魔数**：`0.03` 是试出来的，换个目标（比如第 5 节的每个 λ）就未必合适；
2. **步数写死**：跑满 60 步到底"到了"还是"没到"，代码不说；`history` 得自己攒；
3. **没有停止判据**：发散时只能眼睁睁看着 `nan` 一路传下去。

`cvsim.optim.minimize` 把这些收进一个带测试的入口。约定：**`minimize` 是下降**，
要最大化就取负（和 `scipy.optimize.minimize` 一样）。

返回的 `Result` 里，`converged` 只在**真判据**满足时为 `True`（这里是梯度范数
降到 `grad_tol` 以下）；跑满步数只报 `reason="max_steps"`，绝不冒充收敛。"""
    ),
    code(
        r"""
from cvsim.optim import minimize

# 目标取负 → 最小化 -obj 就是最大化 obj
res = minimize(lambda r: -objective(r), jnp.asarray(0.1),
               optimiser="adam", lr=0.05, max_steps=500)

print(f"cvsim.optim  → r* = {float(res.x):.4f}")
print(f"  收敛吗 = {res.converged}   原因 = {res.reason}   走了 {res.n_steps} 步")
print(f"  最终梯度范数 = {res.grad_norm_history[-1]:.2e}")

assert res.converged and res.reason == "grad_norm"
assert abs(float(res.x) - r_scan) < 0.05        # 与第 4 节的扫描参照一致

# 轨迹直接返回，不用自己攒：history 是 (x, f) 列表，起于初始点
plt.figure(figsize=(10, 3.5))
plt.subplot(1, 2, 1)
plt.plot([h[1] for h in res.history]); plt.xlabel("步数")
plt.ylabel("obj"); plt.title("目标上升（自动停机）")
plt.subplot(1, 2, 2)
plt.semilogy(res.grad_norm_history); plt.xlabel("步数")
plt.ylabel(r"$\|\nabla\|_\infty$"); plt.title("梯度范数 → 判据")
plt.tight_layout(); plt.show()
"""
    ),
    md(
        r"""对比第 4 节手写循环：`r*` 相同（都在 0.918），但这里多知道两件事
——**是收敛还是跑满**，以及**梯度真的降下去了吗**。"""
    ),
    md(
        r"""## 7. 小结

- **正向**：给定 $r$ 算 $E_N$（教程 01–04 的路线）
- **反向**：给定目标与成本，优化器用梯度找 $r$ —— 自动微分让电路参数可训练
- `cvsim.ad` 提供可微的 `apply_gaussian` + `log_neg_loss`，
  numpy / JAX 双后端共享同一套数学与测试
- JAX 是可选的：`pip install -e ".[jax]"`（或 `uv pip install "jax[cpu]"`）
- **系统化**：`cvsim.optim.minimize` 把「学习率 + 步数 + 停止判据」收进一个带测试的入口；
  `converged` 只在真判据满足时为 `True`，跑满步数绝不冒充收敛

下一步可玩：把损耗换成放大器/相位噪声通道，或优化多参数（r 和 BS 角度一起）。"""
    ),
]


if __name__ == "__main__":
    OUT.joinpath("05_ad_designer.ipynb").write_text(
        json.dumps(notebook(CELLS), ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print("wrote tutorials/05_ad_designer.ipynb")
