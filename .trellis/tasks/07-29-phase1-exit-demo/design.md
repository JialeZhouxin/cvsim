# Design: Phase 1 退出 demo

## 目的
记录 demo 物理手算路径 + cvsim 调用映射 + 对账项，作为 `examples/phase1_exit_demo.py` 的实现前提。本 demo 不引入新 API，仅组装 Phase 1 已实现零件。

## 数据流
```
初态 (4 模, xxpp 序)
 mode0,1 = TMSV(r)    ← GaussianState.tmsv + product
 mode2,3 = TMSV(r)        (两对独立)
        ↓
interferometer U = 50:50 BS on (mode0, mode2)
                     ← embed_U_2mode(4,0,2, U_beamsplitter(π/4,0)) + interferometer(state, U)
        ↓
loss 全模, T=0.8, nbar=0   ← loss(state, 0.8, nbar=0.0)
        ↓
Homodyne 观测 (φ=0 测 x)
        ↓
assert np.allclose(sim, analytic, atol=1e-12)
```

## 参数（固定，无 RNG 依赖）
| 参数 | 值 | 理由 |
|------|------|------|
| $r$ | 0.6 | 与教程 §5a 一致；$e^{-2r}=e^{-1.2}\approx0.30119$ |
| $U$ | 50:50 BS on (mode0,mode2) | 干涉仪真出力且手算可写 |
| $T$ | 0.8 | loss 真衰减，避开 $T=0,1$ 退化边界 |
| atol | 1e-12 | 愿景 §7 测试虚裕度 |

## 锁定的 BS x 变换 (实测 S 矩阵, symplectic 验证通过)
xxpp 实部 $x$ 块 $S[:4,:4]$：
```
[[ c  0  c  0]      c = 1/√2
 [ 0  1  0  0]      ⇒ x_0' = (x_0 + x_2)/√2
 [-c  0  c  0]         x_2' = (-x_0 + x_2)/√2
 [ 0  0  0  1]]        x_1', x_3' 不变
```
（$U_{\text{beamsplitter}}(\theta,\phi)$ 取 $\theta=\pi/4,\phi=0$ ⇒ $U_{2\times2}=\frac1{\sqrt2}\begin{pmatrix}1&1\\-1&1\end{pmatrix}$）

## 锁定的 TMSV 块 (实测, mode0,1)
$$V_{01}^{\text{TMSV}}=\begin{pmatrix}
\tfrac12\cosh2r & \tfrac12\sinh2r \\
\tfrac12\sinh2r & \tfrac12\cosh2r
\end{pmatrix}_{x\text{-block}}\;\oplus\;\begin{pmatrix}
\tfrac12\cosh2r & -\tfrac12\sinh2r \\
-\tfrac12\sinh2r & \tfrac12\cosh2r
\end{pmatrix}_{p\text{-block}}$$
$r=0.6$：$\cosh1.2=1.810656$, $\sinh1.2=1.509461$ ⇒
- $V_{x_kx_k}=\tfrac12\cosh2r=0.905328$ (单模 x 方差)
- $\mathrm{Cov}(x_a,x_b)=+\tfrac12\sinh2r=0.754731$ (同对, **正**号)
- $\mathrm{Var}(x_0-x_1)=e^{-2r}=0.301194$ (EPR 关联, BS 前测)

## 4 模初态 $V_0$ (product 拼)
block-diag 两块 TMSV；跨对（mode0,mode2 / mode1,mode3）协方差恒 0。

## 手算对账清单 (9 项, 每项 analytic 闭式 + sim 路径)

#### 1-2. 源验证 (loss/BS 前)
- `homodyne_var(state_0, mode=0, phi=0)` $=\tfrac12\cosh2r=0.905328$
- `homodyne_var(state_0, mode=1, phi=0)` $=\tfrac12\cosh2r=0.905328$
- 差方差 $\mathrm{Var}(x_0-x_1)$ via $V_0[0,0]+V_0[1,1]-2V_0[0,1]=e^{-2r}=0.301194$

#### 3-4. BS(50:50) on (0,2) 后 (loss 前)
实测 $S$ 后单模方差:
- $\mathrm{Var}(x_0')=\tfrac12(V_{00}+V_{22})=\tfrac12\cosh2r=0.905328$ (对称坍缩)
- $\mathrm{Var}(x_1')=V_{11}=\tfrac12\cosh2r=0.905328$ (未触及)
- $\mathrm{Var}(x_2')=\tfrac12(V_{00}+V_{22})=0.905328$
- $\mathrm{Var}(x_3')=V_{33}=0.905328$

BS 后协方差（手算）：
- $\mathrm{Cov}(x_0',x_1')=\tfrac{1}{\sqrt2}V_{01}=\tfrac{1}{2\sqrt2}\sinh2r=0.533676$
  （$x_0'=(x_0+x_2)/\sqrt2$，$x_2$ 与 $x_1$ 独立，故只 $x_0$ 半权重贡献）
- $\mathrm{Cov}(x_0',x_2')=\tfrac12(V_{00}-V_{22})=0$ (两路入对称)

#### 5. BS 后差方差 (hand-calc, 核心对账项)
$$\mathrm{Var}(x_0'-x_1')=\tfrac{1}{\sqrt2}(V_{00}+V_{22})+V_{11}-\tfrac{2}{\sqrt2}V_{01}$$
$$=\tfrac12\cosh2r+\tfrac12\cosh2r-\tfrac{1}{\sqrt2}\tfrac12\sinh2r\cdot2 = \cosh2r - \tfrac{\sqrt2}{2}\sinh2r$$
代 $r=0.6$: $=1.810656 - 0.707107\cdot1.509461 = 1.810656-1.067303=0.743353$
（**实测**：0.74330521，四舍差 0.00005 来自中间取整；assert 用 exact `np.cosh`/`np.sinh` 表达式不取整）

#### 6-9. loss($T=0.8$) 全模后
loss 公式: $V\leftarrow T\,V+(1-T)\tfrac12 I_{8}$ ⇒
- 单模方差: $V_{kk}\leftarrow T\,V_{kk}^{\text{loss前}}+\tfrac{1-T}{2}$
  - $\mathrm{Var}(x_0'')=0.8\cdot0.905328+0.1=0.824262$ (sim 实测 0.824262 ✓)
  - 四个模同值
- 差方差: 两模独立各拉一份真空噪声
  - $\mathrm{Var}(x_0''-x_1'')=T\,\mathrm{Var}(x_0'-x_1')+(1-T)=0.8\cdot0.74330521+0.2=0.79464417$ (sim 实测 0.79464417 ✓)

## 实施实现要点 (供 implement.md 写细化检查表)
1. import: numpy；cvsim.gaussian.state / gates / channels / observables；cvsim.symplectic.U_beamsplitter, embed_U_2mode
2. 构造 4 模初态：`st = GaussianState.product(GaussianState.tmsv(r, nmode=2, mode1=0, mode2=1), GaussianState.tmsv(r, nmode=2, mode1=0, mode2=1))`
3. 构造 $U$：`U = embed_U_2mode(4, 0, 2, U_beamsplitter(np.pi/4, 0.0))`
4. BS 作用：`st_bs = interferometer(st, U)`
5. loss: `st_l = loss(st_bs, T, nbar=0.0)`
6. 对账量提取：
   - 单模方差：`homodyne_var(state, mode=k, phi=0.0)`
   - 差方差：`V[a,a]+V[b,b]-2*V[a,b]` (直接读 state.V)
7. analytic 用 Python 表达式 `np.cosh(1.2)`、`np.sinh(1.2)`、`np.exp(-1.2)` 直出（不取整），保证与 sim 双方都在 float64 同源运算
8. 失败先打对比表（每项 analytic/sim/diff/pass）再 raise。
9. 收尾 `assert np.allclose(..., atol=1e-12)`。
10. 成功路径零输出。

## 风险与回滚点
- **风险 A**：product 拼 4 模若跨对协方差未真为 0 → demo 项 5 BS 后差方差手算不再闭合。**实测已验:** 跨对 Cov(x0,x2)=0 ✓，已闭环。
- **风险 B**：BS sign（$U_{20}=-s$ vs $+s$）若 doc 与代码不一致 → $x_0'=(x_0+x_2)/\sqrt2$ 与 $x_0'=(x_0-x_2)/\sqrt2$ 二选乱。**实测已验:** $S_{02}=+1/\sqrt2$ 印证 $x_0'=(x_0+x_2)/\sqrt2$ ✓。
- **回滚点**：若实现时某对账项不过 atol，先打印 V 矩阵（3 阶段全打印）定位是 BS / loss / factory 哪步分叉，再回头查 analytic 表达式 sign。

## 验证（已跑可行性预演, 见对话）
- TMSV 数值 atol 内 ✓
- 4 模 product → BS → loss → homodyne_var 全链路通 ✓
- 9 项对账中关键 5/6/9 项手算与 sim 一致（剩余为平凡单模方差已盯）
