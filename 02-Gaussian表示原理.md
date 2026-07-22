# 02 · Gaussian 表示原理

> **精髓主线**（建议最先深读）  
> \(\hbar=1\) 正文；正交序见 [术语表](./术语表.md)

---

## §1 物理图像与定位

### 1.1 什么是 Gaussian 表示

若 Wigner 是**多维高斯**，态由两对象定死：

- 位移 \(\bar{\mathbf r}=\langle\mathbf r\rangle\)  
- 协方差 \(V_{ij}=\frac12\langle\{\Delta\mathbf r_i,\Delta\mathbf r_j\}\rangle\)

\(m\) 模：\(\bar r\) 长 \(2m\)，\(V\) 为 \(2m\times 2m\)。

**不存振幅** → 无 Fock cutoff → 大规模可行。  
代价：**只能描述高斯态**（初态高斯 + 高斯门/通道）。

### 1.2 三表示定位

```text
        相同物理：单模 squeezing
         │
  Fock          Gaussian        Bosonic
 cutoff=N      V, r̄            多组件
```

### 1.3 物理图像：相空间椭圆

```text
p ^
  |    ╱───╲     挤压：扁椭圆，面积 ∝ det V 守恒（纯态）
  |   │  ●  │    位移：中心平移
  |    ╲───╱     相移：椭圆旋转
  └──────────→ x
```

**辛：** \(S\Omega S^T=\Omega\) = 面积守恒 + 正则对易。  
一个方向压扁，另一方向必鼓起。

---

## §2 辛结构与高斯态

> Weedbrook RMP 2012 [1110.3234](https://arxiv.org/abs/1110.3234)

### 2.1 正交序与 \(\Omega\)

**xxpp：** \(\mathbf r=(x_1,\ldots,x_m,p_1,\ldots,p_m)^{\mathsf T}\)

**xpxp：** \((x_1,p_1,\ldots)\) — 许多教科书。

\[
\Omega=\begin{pmatrix}0&I_m\\-I_m&0\end{pmatrix}\quad(\mathrm{xxpp}).
\]

序不同 → \(S\) 不同。写错序 = 分束器/挤压全错。

### 2.2 不确定关系

\[
V+\frac{i}{2}\Omega\ge 0\quad(\hbar=1).
\]

单模纯态：\(\det V=1/4\)。

### 2.3 真空标定

```text
本笔记 / Weedbrook / Ferraro 常见:  V_vac = I/2   (ħ=1)
其它软件可能 ħ=2 或带 κ：先对真空再对门
```

**黄金法则：** 读任一文献，先验证真空 \(V\) 是否 \(I/2\)。

### 2.4 Williamson 分解

\[
V=S\,\mathrm{diag}(\nu_1,\ldots,\nu_m)\,S^{\mathsf T},\quad\nu_k\ge 1/2.
\]

\(\nu_k\) = 有效热占位；\(\nu=1/2\) 纯。

### 2.5 Takagi

\(A=U\Sigma U^{\mathsf T}\)，GBS 对角化干涉仪结构常用。

### 2.6 纯度

\[
\mu=\frac{1}{\sqrt{\det(4\kappa^2 V/\hbar)}}.
\]

纯高斯 \(\Rightarrow\mu=1\)。

### 2.7 门更新（闭式）

\[
V\mapsto S V S^{\mathsf T},\qquad \bar r\mapsto S\bar r+\mathbf d.
\]

| 门 | \(S\) 要点 |
|----|-----------|
| \(D(\alpha)\) | \(S=I\)，只动 \(\bar r\) |
| \(R(\theta)\) | 平面旋转 |
| \(S(r)\) | \(\mathrm{diag}(e^{-r},e^{r})\)（单模适当轴） |
| \(BS\) | 两模块混合 \(x\) 与 \(p\) |
| \(S_2(r)\) | 纠缠源 |

---

## §3 高斯通道

### 3.1 一般形式

\[
V\mapsto XVX^{\mathsf T}+Y,\qquad\bar r\mapsto X\bar r.
\]

### 3.2 光子损失（纯损耗）

物理：系统模与真空环境模做 BS（透过率 \(T\in[0,1]\)），再偏迹环境。

本笔记 \(\hbar=1\)、\(V_{\mathrm{vac}}=I/2\) 下，作用在所选模的正交上：

\[
X=\sqrt{T}\,I_{\mathrm{act}},\qquad
Y=(1-T)\,\frac12 I_{\mathrm{act}}.
\]

\[
V\mapsto XVX^{\mathsf T}+Y,\qquad
\bar r\mapsto X\bar r.
\]

（一般文献常写 \(Y=(1-T)(\hbar/4\kappa^2)I\)；与本约定真空对齐时即上式。）

**检查点：** 相干态 \(\langle n\rangle=|\alpha|^2\) 经损耗后 \(\langle n\rangle\to T|\alpha|^2\)。  
**边界：** \(T=1\) 恒等；\(T=0\) 作用模回到真空涨落。

[quant-ph/0503237 Eq.(4.19–4.20)](https://arxiv.org/pdf/quant-ph/0503237)；Weedbrook [1110.3234](https://arxiv.org/abs/1110.3234)

### 3.3 热环境损耗

若环境是平均光子 \(\bar n\ge 0\) 的热态（而非真空），同一 \(X\) 下噪声加性变为

\[
Y=(1-T)\Bigl(\bar n+\tfrac12\Bigr)I_{\mathrm{act}}.
\]

- \(\bar n=0\) 还原 §3.2 纯损耗。  
- 检查点：真空初态、\(T=0\) 时作用模 \(\langle n\rangle=\bar n\)，\(V=(\bar n+1/2)I\)。  
- 加权高斯峰表示对每个组件用同一 \((X,Y)\)，权重不变。

### 3.4 放大等其它通道

相位不敏感放大等见 Weedbrook §5。

---

## §4 测量理论

### 4.1 Homodyne

测正交

\[
x_\phi = x\cos\phi + p\sin\phi.
\]

xxpp 下取实方向向量 \(u\)（模 \(i\) 上 \(u_{x_i}=\cos\phi\)，\(u_{p_i}=\sin\phi\)，其余 0）。

#### 边缘（统计）

\[
\mu = u\cdot\bar r,\qquad
\sigma^2 = u^{\mathsf T} V u.
\]

输出是一维高斯随机数；真空任意 \(\phi\)：\(\mu=0\)，\(\sigma^2=1/2\)。

#### 采样

\[
\mathrm{outcome}\sim\mathcal N(\mu,\sigma^2).
\]

采样与条件更新**可分离**：先抽结果，再（可选）用该结果做条件。

#### 理想条件更新（不删模）

令 \(v=Vu\)，\(\sigma=u^{\mathsf T}Vu\)（要求 \(\sigma>0\)），\(\mu=u\cdot\bar r\)，结果 \(o\in\mathbb R\)：

\[
V' = V - \frac{vv^{\mathsf T}}{\sigma},\qquad
\bar r' = \bar r + v\,\frac{o-\mu}{\sigma}.
\]

测向方差 \(\to 0\)（理想极限下 \(V'\) 在 \(u\) 方向奇异，仍可作教学更新）。  
极限观点：极窄 Generaldyne \(\varepsilon\to0\)。见 Weedbrook / Serafini。

**检查点（真空，\(\phi=0\)，结果 \(o\)）：** \(\langle x\rangle\to o\)，\(V_{xx}\to 0\)。  
**检查点（挤态）：** 真空 \(\to S(r)\) 后，\(\mathrm{Var}(x)=\tfrac12 e^{-2r}\)，\(\mathrm{Var}(p)=\tfrac12 e^{2r}\)。

### 4.2 Generaldyne

Serafini Eq.5.143–5.144：

\[
V'=V-V_{\mathrm{cross}}(V+V_m)^{-1}V_{\mathrm{cross}}^{\mathsf T}.
\]

### 4.3 PNRD — Hafnian

\[
p(\mathbf n)\propto\frac{|\operatorname{haf}(A_{\mathbf n})|^2}{n_1!\cdots n_m!}.
\]

Hafnian = 完美匹配边权积和。有位移时用 **loop hafnian**。

### 4.4 Threshold — Torontonian

只答 click / no-click（[1807.01639](https://arxiv.org/abs/1807.01639)）。  
大规模 GBS 主路径。

### 4.5 纠缠度量

PPT：部分转置后最小辛特征值 \(<1/2\)。  
对数负性 \(\mathcal E_N=\max\{0,-\log_2\tilde\nu\}\)。

---

## §5 误差与约定

### 5.1 误差源

| 类型 | 表现 |
|------|------|
| 辛结构漂移 | 多次更新后 \(V+i\Omega/2\not\ge0\) |
| 采样 | Hafnian / Torontonian 组合爆炸 |
| 约定 | \(\hbar\) / 序 / 定义混用 |

无 Fock cutoff ≠ 无误差。

### 5.2 约定对齐

1. 真空 \(V_{00}=1/2\)？  
2. 正交序一致？  
3. 位移含 \(\sqrt{\hbar}\) 否？

### 5.3 数据流（概念）

```text
初态 (V, r̄)
  → 每门：V ← S V Sᵀ,  r̄ ← S r̄ + d
  → 通道：V ← X V Xᵀ + Y
  → 测量：边缘 / 条件 / Hafnian / Torontonian
```

### 5.4 选型

```text
用 Gaussian:
├─ m 大（10–100+）
├─ GBS
├─ 仅高斯门
└─ 只需低阶矩

改 Bosonic: Cat/GKP
改 Fock:    m≤6 或需精确光子数 / Kerr
```

---

## 练习

1. 手写 50:50 分束器在 xpxp 与 xxpp 下的 \(S\)，验证 \(S\Omega S^{\mathsf T}=\Omega\)。  
2. 真空 → \(S(r)\) → BS，numpy 算 \(V\)，对 \(\det V\) 与 \(\langle n\rangle\)。  
3. 为何 threshold GBS 用 Torontonian 不是 Hafnian？  
4. Williamson 输出 \(\nu_k\) 的物理意义？  
5. \(K\) 次门后如何检查 \(V\) 是否仍物理？

---

## 阅读顺序

[00-CV核心原理](./00-CV核心原理.md) → **本篇** → [01-Fock](./01-Fock表示原理.md) → [03-Bosonic](./03-Bosonic表示原理.md)

```text
Gaussian (m²) → Bosonic (K·m²) → Fock (N^m)
```

---

## 文献

- Weedbrook et al. [1110.3234](https://arxiv.org/abs/1110.3234)  
- Braunstein & van Loock [quant-ph/0410100](https://arxiv.org/abs/quant-ph/0410100)  
- Ferraro et al. [quant-ph/0503237](https://arxiv.org/abs/quant-ph/0503237)  
- Hafnian：[1805.12498](https://arxiv.org/abs/1805.12498)  
- Torontonian：[1807.01639](https://arxiv.org/abs/1807.01639)  
- Loop Hafnian：[2108.01622](https://arxiv.org/abs/2108.01622)  
- GBS 经典模拟：[1908.08068](https://arxiv.org/abs/1908.08068)  
- Serafini, *Quantum Continuous Variables*
