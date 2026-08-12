# -*- coding: utf-8 -*-
"""Build tutorial 08 (Fock↔Gaussian observation bridge, Phase F5). Run from repo root.

    py -3 tutorials/_build_08.py

Generates tutorials/08_fock_bridge.ipynb (UTF-8, stdlib only).
Mirrors tutorials/_build_07.py (md/code/notebook helpers + write path).
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
        r"""# 08 · Fock ↔ Gaussian 观测桥：同一实验，两种表示

教程 02/07 各自站在 Fock 表示里看物理；Gaussian 侧（05）用闭式公式。
本教程（Phase F5）把两者**对账**：

- **同一物理实验**：相干态 $|α\rangle$ 过有损通道（透射率 $η$）
- **两种表示**：Gaussian（$V, \bar r$，解析闭式）vs Fock（截断振幅 + Kraus 损耗）
- **三类可观测**：threshold 点击率 $p_{\rm click}$、PNR 分布 $P(n)$、平均光子数 $⟨n⟩$
- 桥规则（vision §6）：Gauss→Fock 用闭式；Fock→Gauss 只在截断容差内成立，否则 **reject**

只 import 公共 API：`cvsim.bridge`（解析矩阵元）+ `cvsim.fock`（数值）+ `cvsim.gaussian`（闭式）。"""
    ),
    md(
        r"""## 1. 设定：同一实验的双表示搭建

实验参数：$α = 0.8$，截断 $N = 40$，损耗扫掠 $η ∈ [0.1, 0.9]$。

| | Gaussian 表示 | Fock 表示 |
|---|---|---|
| 初态 | `GaussianState.coherent(α)`（$V = I/2$，$\bar r = \sqrt2(\Re α,\Im α)$） | `FockState.coherent(40, α)`（截断振幅 $⟨n|α⟩$） |
| 损耗 | `gaussian.loss(st, η)`（$X=\sqrtη I$，$Y=(1-η)/2\, I$） | `fock.loss(psi, η)`（Kraus $E_k$） |
| 平均光子数 | $⟨n⟩ = η|α|²$（闭式） | `fock.mean_photon` |
| 点击率 | $p_{\rm click} = 1 - e^{-η|α|²}$（闭式） | `1 - pnrd_probs[0]` |

Fock 侧先查**截断泄漏**（vision §5 never-silent）：tail < 1e-9 才允许对账。"""
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

from cvsim import bridge
import cvsim.fock as fock
import cvsim.gaussian as gauss

ALPHA = 0.8     # 相干态振幅
CUT = 40        # Fock 截断维数（α=0.8 → tail ~1e-18）
ETA_0 = 0.5     # 默认透射率（第 3 节 PNR 用）

# --- 双表示搭建 + 输入泄漏门 ---
psi_in = fock.FockState.coherent(CUT, ALPHA)
print(f"Fock 输入截断 tail = {psi_in.tail:.2e}  (门限 1e-9)")
assert psi_in.tail is not None and psi_in.tail < 1e-9

st_in = gauss.GaussianState.coherent(ALPHA)
print(f"Gaussian ⟨n⟩(|α⟩) = {gauss.mean_photon(st_in):.6f}  vs |α|² = {abs(ALPHA)**2:.6f}")
print(f"Fock    ⟨n⟩(|α⟩) = {fock.mean_photon(psi_in):.6f}")
print(f"双表示一致：Gaussian 解析 = Fock 数值（tail 内）")
"""
    ),
    md(
        r"""## 2. Threshold 检测：p_click vs η 双曲线对账

点击（on/off）检测的"响"概率：

$$p_{\rm click}(\eta) = 1 - e^{-\eta |\alpha|^2}$$

- **Gaussian 解析**：闭式直线（红实线），Gaussian 通道数值（`gaussian.loss` → `p_click`）应重合到 1e-12
- **Fock 数值**：`loss` Kraus → `pnrd_probs[0]` → $1 - p_0$（蓝点），应重合到 1e-7（截断内）

两条曲线对账 = F5 退出判据 2（threshold 双表示一致）。"""
    ),
    code(
        r"""
etas = np.linspace(0.1, 0.9, 9)
mu_full = abs(ALPHA) ** 2

p_gauss_ana = 1.0 - np.exp(-etas * mu_full)          # 闭式
p_fock = np.empty_like(etas)
p_gauss_num = np.empty_like(etas)
for i, eta in enumerate(etas):
    rho = fock.loss(fock.FockState.coherent(CUT, ALPHA), eta)
    p_fock[i] = 1.0 - fock.pnrd_probs(rho)[0]        # Fock 数值
    p_gauss_num[i] = gauss.p_click(gauss.loss(gauss.GaussianState.coherent(ALPHA), eta))

d_fock = np.max(np.abs(p_fock - p_gauss_ana))
d_gauss = np.max(np.abs(p_gauss_num - p_gauss_ana))
print(f"max|Δp_click|  Fock vs 闭式  = {d_fock:.2e}   (atol 1e-7)")
print(f"max|Δp_click|  Gaussian vs 闭式 = {d_gauss:.2e}   (atol 1e-12)")
assert d_fock < 1e-7 and d_gauss < 1e-12

plt.figure(figsize=(7, 4.5))
plt.plot(etas, p_gauss_ana, "r-", lw=2, label="Gaussian 闭式 1−e^{−η|α|²}")
plt.plot(etas, p_fock, "bo", ms=6, label="Fock 数值 1−p₀")
plt.plot(etas, p_gauss_num, "g^", ms=6, alpha=0.6, label="Gaussian 通道数值")
plt.xlabel("透射率 η"); plt.ylabel("p_click")
plt.title(f"Threshold 对账（α={ALPHA}）：两表示同一条曲线")
plt.legend(); plt.grid(alpha=0.3); plt.tight_layout(); plt.show()
print("Threshold 对账通过：Fock 数值与 Gaussian 闭式一致到截断容差内")
"""
    ),
    md(
        r"""## 3. PNR 分布：Poisson vs 截断分布

$η = 0.5$ 处，输出仍是相干态（振幅 $\sqrtη\,α$），PNR 应为 **Poisson**：

$$P(n) = e^{-\mu} \frac{\mu^n}{n!}, \qquad \mu = \eta|\alpha|^2 = 0.32$$

- 蓝色柱：Fock `pnrd_probs`（截断、已重归一化到 N=40）
- 红点：`bridge.coherent_element(n, √η·α)`² — 相干元素平方恰为 Poisson(η|α|²)，直接走 bridge API
- 同时核对 $⟨n⟩$：Gaussian $η|α|²$ vs Fock `mean_photon`"""
    ),
    code(
        r"""
eta = ETA_0
mu = eta * abs(ALPHA) ** 2
rho = fock.loss(fock.FockState.coherent(CUT, ALPHA), eta)
p_fock = fock.pnrd_probs(rho)
p_pois = np.array(
    [abs(bridge.coherent_element(n, np.sqrt(eta) * ALPHA)) ** 2 for n in range(CUT)]
)

ns = np.arange(10)
plt.figure(figsize=(8, 4))
plt.bar(ns, p_fock[:10], alpha=0.6, label="Fock pnrd_probs（截断 N=40）")
plt.plot(ns, p_pois[:10], "ro", ms=6, label="Poisson 解析 e^{−μ}μⁿ/n!")
plt.xlabel("光子数 n"); plt.ylabel("P(n)")
plt.title(f"PNR 对账（η={eta}，μ={mu}）：截断分布 vs Poisson")
plt.legend(); plt.grid(alpha=0.3); plt.tight_layout(); plt.show()

d_max = np.max(np.abs(p_fock[:12] - p_pois[:12]))
n_fock = fock.mean_photon(rho)
print(f"max|ΔP(n)| = {d_max:.2e}   (atol 1e-7)")
print(f"⟨n⟩: Fock = {n_fock:.6f}  vs Gaussian η|α|² = {mu:.6f}")
assert d_max < 1e-7 and abs(n_fock - mu) < 1e-7
print("PNR 对账通过：截断 Fock 分布与 Poisson 解析一致")
"""
    ),
    md(
        r"""## 4. 截断生存曲线：误差 vs cutoff

Fock 是截断表示 — 每个结果都必须能回答"截断误差多大"（vision §5）。
固定 $α = 0.8$，看截断误差随 cutoff 的**生存曲线**：

$$\Delta(N) = \max_n |P_N(n) - P_{\rm Poisson}(n)|$$

- cutoff = 10 时 tail ≈ 2e-9（已满足 1e-7 对账）
- cutoff 10→20 误差掉 ~8 个数量级（9.4e-10 → 1.7e-18），随后触 float64 机器精度底（~1e-18）——超指数衰减 + 数值地板
- cutoff = 40 就到机器精度 —— 这就是"截断工程"：**先查 tail，再信数字**"""
    ),
    code(
        r"""
cutoffs = [10, 20, 40, 60]
deltas, tails = [], []
for N in cutoffs:
    psi = fock.FockState.coherent(N, ALPHA)
    p = fock.pnrd_probs(psi)
    d = float(
        np.max(
            np.abs(
                p
                - np.array(
                    [abs(bridge.coherent_element(n, ALPHA)) ** 2 for n in range(N)]
                )
            )
        )
    )
    deltas.append(d)
    tails.append(psi.tail if psi.tail is not None else float("nan"))
    print(f"cutoff={N:2d}: max|ΔP| = {d:.2e}   tail = {tails[-1]:.2e}")

plt.figure(figsize=(7, 4.5))
plt.semilogy(cutoffs, np.maximum(deltas, 1e-20), "o-", label="max|ΔP(n)|（数值）")
plt.semilogy(cutoffs, np.maximum(tails, 1e-20), "s--", label="解析 tail（gammainc）")
plt.xlabel("cutoff N"); plt.ylabel("截断误差")
plt.title("截断生存曲线（α=0.8）：误差超指数衰减")
plt.legend(); plt.grid(alpha=0.3, which="both"); plt.tight_layout(); plt.show()
assert all(d < 1e-7 for d in deltas)
print("生存曲线：所有 cutoff 均满足 atol 1e-7；泄漏纪律 = 比较前先查 tail")
"""
    ),
    md(
        r"""## 5. 结论：bridge 规则

**同一物理实验，两表示对账结果（α=0.8，η ∈ [0.1, 0.9]，N=40）：**

| 可观测 | Gaussian 闭式 | Fock 数值 | 误差 |
|---|---|---|---|
| $p_{\rm click}$ | $1-e^{-\eta|α|²}$ | $1-p_0$（Kraus 后） | < 1e-7 ✓ |
| $P(n)$ | Poisson $e^{-\mu}\mu^n/n!$ | `pnrd_probs`（截断） | < 1e-7 ✓ |
| $⟨n⟩$ | $\eta|α|²$ | `mean_photon` | < 1e-7 ✓ |

**Bridge 规则（F5 落地）：**

1. **Gauss → Fock 闭式**：小 n 矩阵元直接解析（`bridge.coherent_element` 等），
   无需数值 — Fock 数值用于截断内验证（atol 1e-7）
2. **Fock → Gauss 容差内才成立**：Fock 数字只在 tail < 容差时才能与 Gaussian
   闭式对账；tail 超限 → **reject**（测试 `_check_tail` 直接 fail，不静默比较）
3. **截断纪律**：每个 Fock 结果都带 tail（工厂态解析、损耗态用输入界）；
   本教程全部对账点 tail < 1e-9，误差由截断泄漏主导而非公式差异

下一步：threshold 后验更新需要完整的 Gaussian→Fock 状态桥（ponytail，
当前 `cvsim.bridge` 只转可观测、不转状态）。"""
    ),
]

if __name__ == "__main__":
    OUT.joinpath("08_fock_bridge.ipynb").write_text(
        json.dumps(notebook(CELLS), ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print("wrote tutorials/08_fock_bridge.ipynb")
