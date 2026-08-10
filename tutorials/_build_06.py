# -*- coding: utf-8 -*-
"""Build tutorial 06 (GKP feedforward error detection, Phase 5 C3).
Run from repo root:

    py -3 tutorials/_build_06.py

Generates tutorials/06_gkp_feedforward.ipynb (UTF-8, stdlib only).
All numeric claims below were calibrated on 2026-08-10 (see test_gkp_tutorial).
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
        r"""# 06 · GKP 逻辑比特与位移误差检测（测量反馈）

前一个教程用自动微分**设计**纠缠源；本教程回到**测量**主题，做一件量子
纠错味十足的事：

> 用 **CZ + Homodyne 测量 + 参数反馈（ParamRef）** 检测并修正一个
> 连续变量（CV）的**位移误差**。

这是 **GKP 量子纠错** 的最小教学切片：我们不做完整的 GKP 码字（那需要
无限挤压），而是在**强挤压 Gaussian 近似**下演示检测→反馈→修正的完整闭环。

依赖：`cvsim` 的 `GaussianCircuit` + 编译链路（`compile().run(values)`，
Phase 2 成果）。"""
    ),
    md(
        r"""## 1. GKP 的思想：用「梳子」编码比特

GKP（Gottesman–Kitaev–Preskill）码把量子比特编码进**单个谐振子**：

- 逻辑 $|0\rangle_{\rm GKP}$：在 $x = 2\sqrt{\pi}\,k$（$k\in\mathbb Z$）处有一串尖峰
- 逻辑 $|1\rangle_{\rm GKP}$：尖峰整体平移 $\sqrt{\pi}$（在奇位置）

尖峰越窄 → 对位移误差的容错越强。

**诚实标注**：理想 GKP 需要无限挤压（非物理）。本教程用**强挤压真空**
$S(r)|0\rangle$ 近似 —— 单个宽峰代替梳子。它能演示**位移检测与修正的
机制**，但不是完整 GKP 码字；$r$ 有限时峰有宽度，修正残差 $\sim e^{-r}$。"""
    ),
    md(
        r"""## 2. 电路设计：误差 → CZ → 读出 → 反馈

四步走：

1. **编码**：data 模强挤压（x 方向窄，承载逻辑 $|0\rangle$ 近似）；
   ancilla 模做 `F·S(r)·F` —— **p 方向**挤压（读出正交分量必须干净）
2. **误差注入**：data 模 x 方向位移 $\varepsilon$（模拟信道噪声）
3. **传播与读出**：`CZ(data, ancilla)` 把 $x_{\rm data}$ 的信息映射到
   $p_{\rm ancilla}$（$p_2 \to p_2 + x_1$，weight=1），再 Homodyne 测
   ancilla 的 p → 读出 $m_p \approx \varepsilon$
4. **反馈修正**：`ParamRef('m_p', gain)` 驱动 data 模位移，
   抵消误差 $\varepsilon$

物理关键：ancilla 的 p 方向挤压方差 $e^{-2r}/2$ 决定**读出精度**；
测量条件化 + 反馈后，修正残差 ≈ ancilla 读出噪声 $e^{-r}/\sqrt2$
—— 挤压越强，检测越准。"""
    ),
    code(
        r"""
import numpy as np
import cvsim
from cvsim.gaussian import GaussianCircuit, ParamRef

def gkp_detect_correct(eps, r, gain=-1.0/np.sqrt(2), seed=0):
    '''单次运行：注入 x 误差 eps，读出并反馈修正，返回 (m_p, x_after)。'''
    c = GaussianCircuit(2)
    c.squeeze(0, r=r)                              # data: x 挤压（GKP|0> 近似）
    c.fourier(1); c.squeeze(1, r=r); c.fourier(1)  # ancilla: p 挤压
    c.displace(0, alpha=eps/np.sqrt(2))            # 注入 x 误差 eps
    c.cz(0, 1, weight=1.0)                         # x1 -> p2 传播
    c.measure_homodyne(1, phi=np.pi/2, name='m_p') # 读出 p_ancilla
    c.displace(0, alpha=ParamRef('m_p', gain=gain)) # 反馈修正（x 方向）
    comp = c.compile()
    st, res = comp.run(rng=np.random.default_rng(seed))
    x_after = st.rbar[0] * np.sqrt(2)              # xxpp: rbar[0]=x/√2
    return res['m_p'], x_after
""",
    ),
    md(
        r"""## 3. 标定读出：单次 vs 多次平均

先验证「读出 ≈ 误差」：固定误差，跑多个随机种子看读出的分布。

**预期**：读出均值 $\approx \varepsilon$（偏差 $\lesssim 0.05$）。
单次读出的噪声来自**两个独立来源**——data 自身挤压噪声 + ancilla
挤压噪声，各 $\sigma=e^{-r}/\sqrt2$，叠加后读出 std $\approx e^{-r}$
（修正后残差才是 $e^{-r}/\sqrt2$，见 §4/§5）。"""
    ),
    code(
        r"""
eps = 0.2
r = 2.0
readouts = [gkp_detect_correct(eps, r, gain=0.0, seed=s)[0] for s in range(200)]
print(f"读出均值 = {np.mean(readouts):+.4f}  (误差注入 eps = {eps})")
print(f"读出标准差 = {np.std(readouts):.4f}  (理论 e^-r = {np.exp(-r):.4f})")
assert abs(np.mean(readouts) - eps) < 0.05, "读出均值应≈注入误差"
""",
    ),
    md(
        r"""## 4. 闭环：修正后残差大幅下降

同一随机种子，对比**无修正**（gain=0）与**有修正**（gain=−1/√2）：

- 无修正：data 的 x 误差 $\varepsilon$ 留在那儿（残差 ≈ 0.2–0.5，
  含 data 自身挤压噪声）
- 有修正：残差只剩读出噪声级（≈ 0.01–0.1）"""
    ),
    code(
        r"""
for seed in [0, 1, 2, 3]:
    m_nc, x_nc = gkp_detect_correct(0.2, r, gain=0.0, seed=seed)
    m_c,  x_c  = gkp_detect_correct(0.2, r, gain=-1.0/np.sqrt(2), seed=seed)
    print(f"seed={seed}: 无修正 x={x_nc:+.4f} → 有修正 x={x_c:+.4f}")
    assert abs(x_c) < abs(x_nc), "修正后残差应更小"
""",
    ),
    md(
        r"""## 5. 挤压越强，检测越准

修正残差 ≈ ancilla 读出噪声 $e^{-r}/\sqrt2$：扫描挤压强度，残差标准差应
**指数下降**。"""
    ),
    code(
        r"""
for r in [1.0, 1.5, 2.0, 2.5]:
    xs = [gkp_detect_correct(0.2, r, seed=s)[1] for s in range(200)]
    print(f"r={r}: 修正残差 std = {np.std(xs):.4f}  (理论 e^-r/√2 = {np.exp(-r)/np.sqrt(2):.4f})")
    assert np.std(xs) < np.exp(-r) / np.sqrt(2) * 1.5, "残差应在理论量级附近"
""",
    ),
    md(
        r"""## 6. 小结与局限

**闭环成立**：CZ 把位移误差映射到 ancilla → Homodyne 读出 →
`ParamRef` 反馈修正。残差 $\sim e^{-r}/\sqrt2$ 随挤压指数下降。

**局限（诚实标注）**：

1. **不是完整 GKP 码字** —— 单宽峰近似，无多峰结构，无逻辑编码增益
2. **修正本身也是位移** —— 把读出噪声又注入回去；真实 GKP 用
   "逻辑层"修正（只动码字空间内的自由度）
3. **outcome-only 的 threshold 测量**（Phase 5 C2 成果）可做类似的
   光子数检测，但本教程的 Homodyne 是**连续**读出 —— 反馈增益可直接缩放
4. 真实纠错还需要**稳定化**（多轮测量），本教程只演示单轮

**延伸**：把 `r → ∞` 即理想 GKP；把 ancilla 换成 threshold 探测器 +
Gaussian→Fock 桥（Phase 5 C1）可做光子数级检测。"""
    ),
]

NB = notebook(CELLS)
OUT.joinpath("06_gkp_feedforward.ipynb").write_text(
    json.dumps(NB, ensure_ascii=False, indent=1), encoding="utf-8"
)
print(f"wrote {OUT / '06_gkp_feedforward.ipynb'} ({len(CELLS)} cells)")
