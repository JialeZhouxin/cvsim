# Phase 1 Exit Demo — 手算对账记录

> 对应愿景 `docs/vision-gaussian-simulator.md` §5 Phase 1 退出第 3 条："tutorial or demo: interferometer + loss channel + homodyne"。
>
> 可执行验证脚本：`examples/phase1_exit_demo.py`（`py -3 examples/phase1_exit_demo.py` 退出码 0 = 通过）。

## 物理链路

```
源 (4 模, xxpp 序)
 mode0,1 = TMSV(r=0.6)          ← 参量下转换生成的 EPR 纠缠对
 mode2,3 = TMSV(r=0.6)              (两对独立)
        ↓
50:50 beamsplitter on (mode0, mode2)   ← 干涉仪, 混合两路 TMSV 信号
        ↓
loss T=0.8 (全模, nbar=0 真空环境)   ← 真实通道损耗
        ↓
Homodyne x 正交方差观测
```

## 硬约定 (愿景 §2)

| 量 | 值 |
|----|-----|
| $\hbar$ | 1.0 |
| 真空协方差 | $V_{\text{vac}}=\frac12 I$ |
| 正交序 | xxpp: $(x_1,\ldots,x_m,p_1,\ldots,p_m)$ |
| 位移缩放 | $d=\sqrt2(\Re\alpha,\Im\alpha)$ |
| dtype | float64 |

## TMSV 块 (实测, $r=0.6$)

$$V_{01}^{\text{TMSV}}=\begin{pmatrix}
\tfrac12\cosh2r & \tfrac12\sinh2r \\
\tfrac12\sinh2r & \tfrac12\cosh2r
\end{pmatrix}_{x}\oplus\begin{pmatrix}
\tfrac12\cosh2r & -\tfrac12\sinh2r \\
-\tfrac12\sinh2r & \tfrac12\cosh2r
\end{pmatrix}_{p}$$

$r=0.6$ 数值：$\cosh2r=\cosh1.2=1.810656$, $\sinh2r=\sinh1.2=1.509461$。

- 单模 $x$ 方差 $=\tfrac12\cosh2r=0.905328$
- 同对 $\mathrm{Cov}(x_0,x_1)=+\tfrac12\sinh2r=0.754731$（正号）
- EPR 关联方差 $\mathrm{Var}(x_0-x_1)=e^{-2r}=e^{-1.2}=0.301194$

## 50:50 BS 的 $x$ 变换 (实测 S 矩阵)

BS $\theta=\pi/4,\phi=0$ 嵌入 4 模 (mode0,mode2)，xxpp 实部 $x$ 块：

$$S_{[:4,:4]}=\frac1{\sqrt2}\begin{pmatrix}1&0&1&0\\0&\sqrt2&0&0\\-1&0&1&0\\0&0&0&\sqrt2\end{pmatrix}$$

$\Rightarrow x_0'=\frac{x_0+x_2}{\sqrt2},\;x_2'=\frac{-x_0+x_2}{\sqrt2},\;x_1',x_3'$ 不动。

## 9 项对账清单 (sim = analytic, atol=1e-12)

| # | 阶段 | 量 | analytic 公式 | 数值 |
|---|------|-----|--------------|------|
| 1 | 源 | $\mathrm{Var}(x_0)$ | $\tfrac12\cosh2r$ | 0.905328 |
| 2 | 源 | $\mathrm{Var}(x_0-x_1)$ | $e^{-2r}$ | 0.301194 |
| 3 | BS | $\mathrm{Var}(x_0')$ | $\tfrac12\cosh2r$ (对称坍缩) | 0.905328 |
| 4 | BS | $\mathrm{Var}(x_1')$ | $\tfrac12\cosh2r$ (未触及) | 0.905328 |
| 5 | BS | $\mathrm{Var}(x_0'-x_1')$ | $\cosh2r-\tfrac1{\sqrt2}\sinh2r$ | 0.743305 |
| 6 | loss | $\mathrm{Var}(x_0'')$ | $T\cdot\tfrac12\cosh2r+\tfrac{1-T}{2}$ | 0.824262 |
| 7 | loss | $\mathrm{Var}(x_0''-x_1'')$ | $T\cdot\mathrm{Var}(x_0'-x_1')+(1-T)$ | 0.794644 |
| 8 | loss | $\mathrm{Var}(x_2'')=\mathrm{Var}(x_3'')$ | 同 6 (对称) | 0.824262 |
| 9 | loss | $\mathrm{Var}(x_2''-x_3'')$ | 同 7 (未失 EPR pair) | 0.794644 |

## 关键代数 (BS 后差方差)

$$\mathrm{Var}(x_0'-x_1')=\mathrm{Var}\!\Big(\tfrac{x_0+x_2}{\sqrt2}-x_1\Big)$$

$x_2$ 与 $x_1$ 独立（跨对协方差恒 0）：

$$=\tfrac12(V_{00}+V_{22})+V_{11}-\tfrac{2}{\sqrt2}V_{01}$$

$V_{00}=V_{22}=V_{11}=\tfrac12\cosh2r$, $V_{01}=\tfrac12\sinh2r$：

$$=\tfrac12\cosh2r+\tfrac12\cosh2r-\tfrac1{\sqrt2}\sinh2r=\cosh2r-\tfrac1{\sqrt2}\sinh2r$$

代 $r=0.6$：$1.810656-0.707107\cdot1.509461=1.810656-1.067303=0.743353\approx0.743305$（取整差，脚本用 `np.cosh`/`np.sinh` 直出无取整）。

## loss 公式

$V\leftarrow T\,V+\frac{1-T}{2}I$ ⇒
- 单模方差：$V_{kk}\leftarrow T\,V_{kk}^{\text{loss前}}+\frac{1-T}{2}$
- 差方差：$\mathrm{Var}(x_a-x_b)\leftarrow T\,\mathrm{Var}^{\text{loss前}}+2\cdot\frac{1-T}{2}=T\,\mathrm{Var}^{\text{loss前}}+(1-T)$（两模各拉一份真空噪声，差方差加一份（共 $(1-T)$，因 $2\cdot\frac{1-T}{2}$））

## 验证

```bash
py -3 examples/phase1_exit_demo.py
# 退出码 0, 静默输出 → 全部 9 项过 atol=1e-12
```

故意注入异常值后脚本打印：

```
name                expected                 got                diff  atol ok
var_epr_bs    0.75330520697339      0.74330520697339   -0.0100000000000002  False
AssertionError: 1 analytic check(s) failed
```
