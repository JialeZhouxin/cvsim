# 03 · Bosonic 表示原理

> 高斯叠加 · Cat / GKP · 三表示之一  
> \(\hbar=1\) 正文；符号见 [术语表](./术语表.md)

---

## §1 物理图像与定位

### 1.1 什么是 Bosonic 表示

许多非高斯态 Wigner 非单峰，但可写成**高斯态加权叠加**：

\[
\rho=\sum_k w_k\,\rho_G(V_k,\bar r_k).
\]

纯态层：多个高斯波包相干叠加（\(w_k\) 可复）。

- **Cat：** 两（多）峰 + 相位  
- **GKP：** 格子上许多窄峰  
- **损失后的非高斯：** 峰变胖、权重变

用高斯积木搭非高斯：

- 效率 \(\sim O(K\cdot m^2)\)  
- 表达能力：只要峰结构能描述 Wigner

### 1.2 三表示定位

```text
Gaussian (m²) → Bosonic (K·m²) → Fock (N^m)
  高斯基           高斯叠加           任意
```

---

## §2 数据结构与线性代数

### 2.1 三元组

每个组件：

```text
V_k     : 2m × 2m 协方差
r̄_k    : 2m 位移（可为复，虚部编码相干）
w_k     : 复权重
```

\(K\) 个组件：总存储 \(\sim K\cdot m^2\)。

归一化：概念上 \(\sum_k w_k\) 与迹相关。

### 2.2 复权重的物理来源

\[
\rho=|c_1|^2|G_1\rangle\langle G_1|+|c_2|^2|G_2\rangle\langle G_2|
+c_1c_2^*|G_1\rangle\langle G_2|+c_2c_1^*|G_2\rangle\langle G_1|.
\]

- 前两项：正权重，经典混合  
- 后两项：**复权重**，量子相干 / 干涉

交叉项的「中心」可在复位移上——故 \(\bar r\) 允许虚部。

### 2.3 高斯门 / 通道

每组件独立：

\[
V_k\mapsto S V_k S^{\mathsf T},\qquad
\bar r_k\mapsto S\bar r_k+\mathbf d.
\]

通道：每组件 \(X,Y\) 仿射；权重规则依赖表示（Kraus vs 耗散）。

---

## §3 Cat 态

### 3.1 为何常是 4 组件

直觉 \(\lvert\alpha\rangle+e^{i\phi}\lvert-\alpha\rangle\) 像 2 峰，但交叉项 \(\lvert\alpha\rangle\langle-\alpha\rvert\) 的 Wigner 是**复中心高斯**，不能与对角项共享同一实位移 → **4 组件**：

```text
组件 0:  |α⟩⟨α|     实权重，中心 +r
组件 1:  |-α⟩⟨-α|   实权重，中心 -r
组件 2,3: 交叉项     复权重，中心含虚部
```

even / odd 由相对相位与权重公式决定（[2103.05530](https://arxiv.org/abs/2103.05530) §IV B）。

### 3.2 参数扫描

| \(|\alpha|\) | 峰分离 | 备注 |
|-------------|--------|------|
| 0.5–1.0 | 小–中 | 4 组件足够 |
| 2.0+ | 大 | 交叉项 \(\sim e^{-2|\alpha|^2}\) 指数小，可近似 2 组件混合 |

### 3.3 Cat breeding（概念）

两小 cat 在 BS 上干涉 → 测一臂 → 条件得大 cat。  
Bosonic：每步只更新少量组件的 \((V,\bar r,w)\)。

---

## §4 GKP 态

### 4.1 相空间格子

```text
p ^
  | ╋ ╋ ╋ ╋   理想：Dirac 梳
  | ╋ ● ╋ ╋   物理：窄高斯齿 × 宽包络
  └────────→ x
```

- 理想 \(\lvert0\rangle_{\mathrm{GKP}}\)：\(x\) 向间隔 \(\sqrt{2\pi}\) 的峰梳  
- 物理：每齿方差 \(\varepsilon\)，包络方差 \(\sim1/\varepsilon\)

### 4.2 组件截断

格点 \((k,l)\) 上放组件；丢掉 \(|w|\) 过小的远齿（`amp_cutoff` 类旋钮）。  
越接近理想 GKP → 组件越多 → 越贵。

### 4.3 相对 Fock 的优势

Fock 需极大 cutoff 才像 Dirac 峰；  
Bosonic 几十–几百窄高斯即可。

---

## §5 测量与 Wigner

### 5.1 Wigner（单模，\(\hbar=1\)）

对每组件算高斯 Wigner，再按 \(w_k\) 加权求和：

\[
W(x,p)=\sum_k w_k\,W_G^{(k)}(x,p).
\]

实中心高斯组件（教学主公式）：

\[
W_G\propto
\frac{1}{\pi\sqrt{\det(2V)}}
\exp\!\Bigl(-\tfrac12\,\delta^{\mathsf T}V^{-1}\delta\Bigr),
\quad
\delta=(x,p)^{\mathsf T}-\mathrm{Re}\,\bar r.
\]

**真空检查点：** \(V=I/2\) \(\Rightarrow\) \(W(0,0)=1/\pi\)。  
（勿与部分 \(\hbar=2\) 文献的 \(2/\pi\) 混用。）

复中心：\(\mathrm{Im}\,\bar r\) 与 \(\arg w\) 给出干涉相位；odd cat 在原点可出现 **\(W(0,0)<0\)**。

**检查点：** even/odd cat 的中心干涉符号相反（even 增强、odd 相消）。

### 5.2 Homodyne 条件（教学闭式）

每组件用与 Gaussian **同一仿射**（不删模）：

\[
v_k=V_k u,\quad
\sigma_k=u^{\mathsf T}V_k u,\quad
\mu_k=u\cdot\bar r_k\ \text{（可复）},
\]

\[
V_k'=V_k-\frac{v_kv_k^{\mathsf T}}{\sigma_k},\qquad
\bar r_k'=\bar r_k+v_k\frac{o-\mu_k}{\sigma_k}.
\]

似然乘权（\(o\) 实，\(\mu\) 可复 \(\Rightarrow L\) 可复）：

\[
L_k\propto\sigma_k^{-1/2}
\exp\!\Bigl(-\frac{(o-\mu_k)^2}{2\sigma_k}\Bigr),
\qquad
w_k\leftarrow w_k L_k,
\quad
\sum_k w_k\to 1.
\]

**检查点：** 单组件、实 \(\bar r\) 时，与 Gaussian 条件更新一致。  
**检查点：** even cat、\(o\approx +\sqrt2\,\alpha\)（\(\phi=0\)）时，靠近 \(+\alpha\) 的对角峰 \(|w|\) 应大于靠近 \(-\alpha\) 的峰；交叉组件可保留（复中心）。

**诚实：** 此为教学用复仿射似然，**不是**完整 Generaldyne 文献 POVM 全式。

### 5.3 Homodyne 采样（教学混合）

1. 仅把 **实中心**、权重实部为正的对角峰放进抽样池；  
2. 按 \(\mathrm{Re}(w)\) 归一抽组件；  
3. 再从该组件边缘 \(\mathcal N(\mu_k,\sigma_k^2)\) 抽 \(o\)。

**交叉项（复中心）不进池。**  
**诚实：** 得到的是对角峰的**经典混合边缘**，不是含完整干涉核的精确边缘分布。  
采样**不**自动做条件；条件需另用 §5.2。

### 5.4 测量能力总表

| 测量 | Bosonic | 备注 |
|------|---------|------|
| Homodyne 条件 | ✅ 教学闭式 | 逐组件仿射 + 似然乘权 |
| Homodyne 采样 | ✅ 教学混合 | 实峰池；交叉出池 |
| Generaldyne 全式 | 概念上 ✅ | 见 Serafini；本笔记不展开 |
| PNR（组件式） | 有理论路径 | 比 Gaussian 更绕 |
| 大规模 Fock 采样 | 通常转 Fock | 表示不擅长 |

### 5.5 测量后态

按结果更新组件列表 \((V_k,\bar r_k,w_k)\)。  
Fock 是切下标；Bosonic 是改三元组。

---

## §6 数值考量

| 问题 | 处理 |
|------|------|
| 组件数爆炸 | 门后合并近邻峰；截断小权重 |
| 权重下溢 | 大 \(|\alpha|\) 交叉项 → 0 |
| 复位移数值 | 与实部分开跟踪 |
| 归一化漂移 | 定期按迹重整 |

### 选型

```text
用 Bosonic:
├─ Cat / GKP
├─ 峰结构清晰、K 可控

改 Fock:
├─ Kerr 连续扭曲
├─ 精确光子数分布

改 Gaussian:
├─ 纯高斯
└─ 峰很远、交叉可忽略
```

---

## 练习

1. 写出 even cat 的 4 组件 \((V,\bar r,w)\) 概念表。  
2. 哪些 weight 实、哪些复？为什么？  
3. 大 \(|\alpha|\) 时为何可近似 2 组件混合？  
4. 同 cat：Fock 高 cutoff 振幅 vs Bosonic 组件，比低阶矩或 Wigner 切片。  
5. GKP 中 amp 截断如何权衡精度与 \(K\)？

---

## 阅读顺序

[00-CV核心原理](./00-CV核心原理.md) → [02-Gaussian](./02-Gaussian表示原理.md) → **本篇** → [01-Fock](./01-Fock表示原理.md)

---

## 文献

- 高斯叠加 / GBS 经典模拟：Quesada & Arrazola [1908.08068](https://arxiv.org/abs/1908.08068)  
- GKP 构造：[2103.05530](https://arxiv.org/abs/2103.05530) §IV B  
- Piquasso：[2403.04006](https://arxiv.org/abs/2403.04006)  
- Cat 制备动机：[2206.08828](https://arxiv.org/abs/2206.08828)
