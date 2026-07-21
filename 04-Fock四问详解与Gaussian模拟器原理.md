# 04 · Fock / Gaussian / Bosonic 模拟器原理

> 上篇：Fock 表示四问逐条展开 + GHZ 完整示例
> 中篇：Gaussian 表示模拟器原理
> 下篇：Bosonic 表示模拟器原理
> \(\hbar=1\) 正文；正交约定见文内说明

---

# 第一部分：Fock 模拟器四问详解

---

## 一、态怎么存？

### 数学模型

Fock 表示把无限维 Hilbert 空间**砍成有限维向量**：

\[
\lvert\psi\rangle = \sum_{n_1=0}^{N-1} \cdots \sum_{n_m=0}^{N-1} c_{n_1\ldots n_m} \lvert n_1\ldots n_m\rangle
\]

存储结构是一个 **\(m\) 阶张量**，形状为：

[cutoff] × [cutoff] × ... × [cutoff]   ← m 个维度
**存储量 = \(N^m\)**。

密度矩阵模式下张量形状翻倍：`[cutoff]×[cutoff]×...`（共 \(2m\) 维），编码 \(\rho = \lvert\psi\rangle\langle\psi\rvert\) 或混合态。

| \(m\) \ \(N\) | 5 | 10 | 20 |
|---|---|---|---|
| 1 | 5 | 10 | 20 |
| 4 | 625 | 1×10⁴ | 1.6×10⁵ |
| 8 | 3.9×10⁵ | 1×10⁸ | 2.5×10¹⁰ |
| 12 | 4×10³ | 1×10¹² | 4×10¹⁵ |

### 物理意义

- \(\lvert n\rangle\) = 谐振子第 \(n\) 激发级（**不是**"n 个光子在飞"）
- 基态 \(\lvert 0\rangle\) = 相空间中心的高斯波包（真空涨落）
- cutoff \(N\) = 在能量上切一刀——丢弃高阶激发
- 态仍然是**连续变量**的（相空间 \((x,p)\) 连续），离散的只是基标签

### 两种存储模式

实践中一般有两种管理振幅的方式：

| 模式 | 存储形式 | 形状 | 用途 |
|------|---------|------|------|
| 稀疏模式 | 只存非零振幅对应的占有数向量 | `(nmode,)` 索引 | 初态构造（\(|0\rangle,|1\rangle,|n\rangle\) 等） |
| 密集模式 | 完整振幅张量 | `[cutoff]×...×[cutoff]` | 演化与测量 |

对于高模数弱纠缠态，还可引入**矩阵积态（MPS）压缩**：存储量从 \(N^m\) 降到 \(O(m\cdot N\cdot\chi^2)\)（\(\chi\) 为 bond dimension），可推到 30-100 模。

---

## 二、门怎么更新？

### 通用框架

每门 = 截断空间中的幺正矩阵 \(U_{\text{gate}}\)：

\[
\lvert\psi'\rangle = U_{\text{gate}} \lvert\psi\rangle
\quad\Longleftrightarrow\quad
c'_{n'_1\ldots} = \sum_{n_1\ldots} \langle n'_1\ldots \lvert U_{\text{gate}} \rvert n_1\ldots\rangle \; c_{n_1\ldots}
\]

密度矩阵下：\(\rho' = U_{\text{gate}} \rho U_{\text{gate}}^\dagger\)。

### 积木：产生湮灭算符（ladder operators）

\[
a \lvert n\rangle = \sqrt{n}\,\lvert n-1\rangle,\qquad
a^\dagger \lvert n\rangle = \sqrt{n+1}\,\lvert n+1\rangle
\]

在截断空间中的矩阵表示（cutoff=4 例）：

\[
a = \begin{pmatrix}
0 & 1 & 0 & 0 \\
0 & 0 & \sqrt2 & 0 \\
0 & 0 & 0 & \sqrt3 \\
0 & 0 & 0 & 0
\end{pmatrix}
\]

`python
# 伪代码
sqrt = [√1, √2, ..., √(N-1)]
a    = diag(sqrt, offset=1)    # 湮灭
a_dag = a.T.conj()             # 产生
**截断伪影的根因**：\(a^\dagger\lvert N-1\rangle = \sqrt{N}\lvert N\rangle\) 被丢弃，所以 \([a,a^\dagger]\) 在最后一个对角元是 \(1-N\) 而非 1。这是所有截断误差的源头。

### 常用门的 Fock 矩阵

| 门 | 数学形式 | 矩阵构造 | 复杂度 |
|---|---|---|---|
| **PhaseShift** \(PS(\theta)\) | \(e^{i n\theta}\lvert n\rangle\) | \(\operatorname{diag}([e^{i n\theta}])\) | \(O(N)\) |
| **Kerr** \(K(\chi)\) | \(e^{i\chi n^2}\lvert n\rangle\) | \(\operatorname{diag}([e^{i\chi n^2}])\) | \(O(N)\) |
| **Displacement** \(D(\alpha)\) | \(e^{\alpha a^\dagger - \alpha^* a}\) | 矩阵指数 \(\exp(\alpha a^\dagger - \alpha^* a)\) | \(O(N^3)\) |
| **Squeezing** \(S(r)\) | \(e^{\frac12(r^* a^2 - r a^{\dagger2})}\) | 矩阵指数 | \(O(N^3)\) |
| **BeamSplitter** \(BS(\theta,\phi)\) | 递推填充 4 阶张量 | 辐射跃迁强度递推 | \(O(N^4)\) |

**Kerr 是 Fock 的独占优势**：Kerr 产生不可压缩的 Wigner 扭曲，Gaussian 无能为力，Bosonic 组件数爆炸，Fock 天然对角。

### 物理图像速览

- **PhaseShift**：相空间绕原点旋转，高光子数转更快
- **Displacement**：平移相空间，从 \(|0\rangle\) 产生相干态（泊松光子数分布）
- **Squeezing**：压缩一个正交方向，平均光子 \(\langle n\rangle = \sinh^2 r\)
- **BS**：打散两个模的光子数
- **Kerr**：真空 → 挤压 → 椭圆 → Kerr → S 形 Wigner 扭曲

### 强挤压推荐 cutoff

| \(r\) | \(\langle n\rangle\) | 推荐最小 cutoff |
|---|---|---|
| 0.5 | 0.27 | 8 |
| 1.0 | 1.38 | 15 |
| 1.5 | 3.63 | 25 |
| 2.0 | 7.38 | 40+ |
| 2.5 | 32.0 | 80+ |

---

## 三、测量怎么算？

### Fock 概率（最直接）

测量模 \(k\) 得到 \(n\) 个光子：

\[
p_k(n) = \text{Tr}_k\bigl(\lvert n\rangle\langle n\rvert_k \;\rho\bigr)
\]

纯态下直接读振幅模平方：\(p_k(n) = |c_n|^2\)。

### 测量类型

| 测量 | 输出 | Fock 实现 |
|---|---|---|
| **PNRD**（光子数分辨探测） | 各 \(n\) 的概率 | 直接读 \(|c_n|^2\) |
| **Threshold**（有/无光子探测） | click / no-click | \(\sum_{n\ge 1} p_n\) |
| **Homodyne**（正交测量） | 连续值 \(x_\phi\) | 投影到无限挤压真空（数学上较贵） |
| **Heterodyne** | 复振幅 \(\alpha\) | 投影到相干态 |

### 部分模测量——Fock 的独特优势

测量一个模后，剩余模的**条件振幅直接从张量切片**得到，无需 Hafnian 或高斯条件：

输入: |ψ⟩ = Σ_{n0,n1,...} c_{n0,n1,...} |n0⟩|n1⟩...
测量模 0 得 n0=5 → 剩余态:
       |ψ'⟩ ∝ Σ_{n1,...} c_{5,n1,...} |n1⟩...  (未归一)
代价：未测模的振幅仍是完整张量（维数爆炸）。

---

## 四、误差从哪来？

### 三大来源

1. **态的尾巴**（截断误差）
   - 强位移/挤压在 \(n\ge N\) 有非零幅值，被直接砍掉
   - 概率亏损：\(\sum_{n=0}^{N-1} |c_n|^2 < 1\)

2. **算符伪影**
   - 截断下的 ladder 算符不满足精确对易关系，级联放大
   - \(a^\dagger\lvert N-1\rangle\) 本该到 \(\lvert N\rangle\)，被丢弃

3. **测量精度下降**
   - 概率不归一化 → 采样偏差
   - 高阶矩误差最大

### Cutoff 经验法则

位移 |α|:  N > |α|² + 5√|α|²
挤压 r:   N > 3·sinh²(r) + 10
稳妥做法：**cutoff 扫描**（\(N=10,15,20,25\)），观察观测量趋于平台。

### 跨后端交叉验证

实践中常用两种方法交叉验证 Fock 的精度：

- **与解析公式对比**：单模挤压态的平均光子数 \(\langle n\rangle = \sinh^2 r\) 有解析值，Fock 计算结果应随 cutoff 增大趋近它
- **与 Gaussian 后端对比**：纯高斯电路下，Gaussian 后端给出精确结果（协方差无截断），Fock 的低阶矩应随 cutoff 增大趋近 Gaussian 值；若 cutoff 不足，Fock 的态范数会小于 1

---

## 五、完整示例：三比特 GHZ 态模拟

### 5.1 编码方式：单轨编码（Single-Rail Encoding）

把 qubit 映射到 Fock 态的最简方案：

| 逻辑 qubit | Fock 态 |
|---|---|
| \(\lvert 0\rangle_L\) | \(\lvert 0\rangle\)（真空，0 光子） |
| \(\lvert 1\rangle_L\) | \(\lvert 1\rangle\)（单光子） |

3 个逻辑 qubit = 3 个 qumode，cutoff \(N=2\)（只需 \(|0\rangle,|1\rangle\)）。

### 5.2 GHZ 态与制备电路

目标态：

\[
\lvert \text{GHZ}\rangle = \frac{1}{\sqrt{2}}\bigl(\lvert 000\rangle_L + \lvert 111\rangle_L\bigr)
= \frac{1}{\sqrt{2}}\bigl(\lvert 0,0,0\rangle + \lvert 1,1,1\rangle\bigr)
\]

在单轨编码中，标准 qubit 电路：

q0: ── H ──●──────────
            │
q1: ───────┼──●───────
            │  │
q2: ───────┼──┼──●────
            │  │  │
          CNOT  CNOT
转化为 Fock 空间的门矩阵（在 \(\{|0\rangle,|1\rangle\}\) 子空间）：

| 门 | 矩阵（Fock 基） |
|---|---|
| **Hadamard** | \(H = \frac{1}{\sqrt{2}}\begin{pmatrix}1 & 1 \\ 1 & -1\end{pmatrix}\) |
| **CNOT**（模 0 控制模 1） | \(\begin{pmatrix}1 & 0 & 0 & 0 \\ 0 & 1 & 0 & 0 \\ 0 & 0 & 0 & 1 \\ 0 & 0 & 1 & 0\end{pmatrix}\) 在 \(\{|00\rangle,|01\rangle,|10\rangle,|11\rangle\}\) |

### 5.3 模拟器中发生了什么

#### Step 1：初态

\[
\lvert\psi_0\rangle = \lvert 0,0,0\rangle
\]

振幅张量（形状 `[2,2,2]`）：

c[0,0,0] = 1.0
其余全 0
#### Step 2：Hadamard 在模 0

只作用在第一个维度上，矩阵乘法：

\[
H \otimes I \otimes I : c_{n_0 n_1 n_2}
\]

张量更新后：

c[0,0,0] = 1/√2 ≈ 0.707
c[1,0,0] = 1/√2 ≈ 0.707
其余全 0
#### Step 3：CNOT(0→1)

作用在模 0 和模 1 上。逻辑：若模 0 = \(|1\rangle\)，则翻转模 1（\(|0\rangle\leftrightarrow|1\rangle\)）。

张量更新：

c[0,0,0] = 1/√2  ← 不变（控制=0）
c[1,1,0] = 1/√2  ← 从 c[1,0,0] 来（控制=1 → 目标翻转）
c[1,0,0] = 0
#### Step 4：CNOT(0→2)

作用在模 0 和模 2 上。若模 0 = \(|1\rangle\)，翻转模 2：

c[0,0,0] = 1/√2  ← 不变
c[1,1,1] = 1/√2  ← 从 c[1,1,0] 来
c[1,1,0] = 0
#### 终态张量

c[0,0,0] = 0.707
c[1,1,1] = 0.707
其余全 0
**这就是 GHZ 态**：\(\frac{1}{\sqrt{2}}(\lvert 000\rangle + \lvert 111\rangle)\)。

### 5.4 结果解读

#### 振幅解读

c[0,0,0] = 0.707 → 态 |0,0,0⟩ 的幅值
c[1,1,1] = 0.707 → 态 |1,1,1⟩ 的幅值
两个分量等幅叠加，**无其他分量** → 完美三体纠缠。

#### 测量结果

| 测量模式 0 | 概率 | 剩余条件态 |
|---|---|---|
| 得 \(n_0=0\) | 50% | \(\lvert 00\rangle\) |
| 得 \(n_0=1\) | 50% | \(\lvert 11\rangle\) |

关键：测量一个模后，剩余两模**完全关联**（要么都是 0，要么都是 1）——这就是纠缠。

#### 误差检查——概率归一性

\[
\sum_{n_0,n_1,n_2} |c_{n_0 n_1 n_2}|^2 = |c_{000}|^2 + |c_{111}|^2 = 0.5 + 0.5 = 1.0
\]

完美归一化 → 无截断误差（cutoff=2 已覆盖全部有意义态）。

**如果 cutoff=1**：只能存 \(|0\rangle\)，无法表示 \(|1\rangle\)，GHZ 完全无法制备。

#### 扩展到更大 cutoff

如果电路加入**光子损失通道**或 **Kerr 门**，态会泄漏到 \(n\ge 2\) 的高阶 Fock 空间。这时 cutoff 不足会导致：
- 漏掉幅值 → 概率不守恒
- 纠缠结构失真
- 高阶校正丢失

**这就是截断误差的活例子**。

---

## 六、Fock 四问总结

| 问题 | 回答 |
|---|---|
| **态怎么存？** | \(m\) 阶振幅张量，形状 \([N]^m\)，存储量 \(N^m\) |
| **门怎么更新？** | \(U_{\text{gate}}\) 矩阵乘法；对角门 \(O(N)\)，BS \(O(N^4)\)，指数门 \(O(N^3)\) |
| **测量怎么算？** | PNRD 直接读 \(|c_n|^2\)；部分模测量直接切片 |
| **误差从哪来？** | 截断砍掉高阶幅值 + ladder 算符不满足精确对易 + 概率亏损 |

> 1 模纯损耗 Kraus 与 \(\lvert1\rangle\) 对角检查点：见 [01 · §4.1](./01-Fock表示原理.md)。

---

# 第二部分：Gaussian 模拟器原理

---

## §1 物理图像与定位

### 1.1 什么是 Gaussian 表示

若 Wigner 函数是**多维高斯**，态被两个经典对象定死：

- **位移** \(\bar{\mathbf r} = \langle\mathbf r\rangle\) — 相空间中心
- **协方差** \(V_{ij} = \frac12\langle\{\Delta\mathbf r_i,\Delta\mathbf r_j\}\rangle\) — 形状与大小

\(m\) 模：\(\bar r\) 长 \(2m\)，\(V\) 为 \(2m\times 2m\) 对称矩阵。

**不存振幅 → 无 Fock cutoff → 大规模可行。**
代价：**只能描述高斯态**（初态高斯 + 高斯门/高斯通道）。

### 1.2 与 Fock / Bosonic 的定位

        相同物理：单模 squeezing
         │
  Fock          Gaussian        Bosonic
 cutoff=20     V, r̄(无截断)     4 组件
 精确度≈1      精确(高斯族内)    精确(Cat类)
 ▲代价 N^m     O(m²)           O(K·m²)
Gaussian 的独占优势：
- **唯一的无截断后端**——协方差是精确的
- **唯一能上 100+ 模的**——辛矩阵更新 O(m²)
- **唯一能直接算 Hafnian/Torontonian**——匹配图计数

### 1.3 相空间椭圆

单模高斯态在相空间 = **椭圆**（Wigner 等高线）：

p ^
  |    椭圆 => V 决定长短轴
  |   ⟋    椭圆面积 = 不确定度积
  |  ⟋ \   ⟳ 旋转角 = 相位
  | ⟋   ↘
  |⟋      ● ← 中心 r̄
  └────────────→ x
| 态 | 椭圆 | 原因 |
|----|------|------|
| 真空 | 圆，半径 √(½) | 对称涨落 |
| 相干态 | 圆，中心偏 | 平移不变形状 |
| 挤压态 | 扁椭圆 | 一方向压缩 |
| 热态 | 大圆，半径 > √(½) | 热噪声 |
| 双模挤压 | 两模椭圆耦合 | 纠缠关联 |

**为什么叫"辛"？** 线性光学门保持椭圆面积不变——\(S\Omega S^{\mathsf T}=\Omega\) 等价于面积守恒 + 正则对易。挤压可以压扁一个方向，但另一方向必然鼓起——不确定关系是一只"压不下去的弹簧"。

---

## §2 Gaussian 模拟器四问

### 2.1 态怎么存？

**数学模型**：

\[
\text{高斯态} \longleftrightarrow (\bar{\mathbf r}, V)
\]

- \(\bar{\mathbf r} \in \mathbb{R}^{2m}\)：位移向量
- \(V \in \mathbb{R}^{2m\times 2m}\)：对称协方差矩阵，满足量子条件 \(V + \frac{i}{2}\Omega \ge 0\)

真空（\(\hbar=1\) 常见约定）：\(\bar{\mathbf r}=0,\; V = \frac12 I\)。

**存储量**：\(O(m^2)\)。

与 Fock 对比：

| 模数 \(m\) | Fock cutoff=10 | Gaussian |
|---|---|---|
| 1 | 10 个振幅 | 3 个数（\(V\) 有 3 个独立元 + \(\bar r\) 有 2 个） |
| 8 | 1×10⁸ | 136 个数 |
| 100 | 不可行 | ~20k 个数 |

#### 正交序与辛形式 \(\Omega\)

正交序定义了 \(\mathbf r\) 的排列方式，直接影响辛矩阵的形式。常见两种：

**xxpp 序**：

\[
\mathbf r = (x_1, x_2, \ldots, x_m,\; p_1, p_2, \ldots, p_m)^{\mathsf T},
\qquad
\Omega = \begin{pmatrix} 0 & I_m \\ -I_m & 0 \end{pmatrix}.
\]

**xpxp 序**：

\[
\mathbf r = (x_1, p_1, x_2, p_2, \ldots)^{\mathsf T}.
\]

序不同 → 辛矩阵形式不同。实现时须统一约定，不可混用。

#### 物理意义

- \(V\) 编码了态在相空间的形状和纯度
- 椭圆面积 = 不确定度积
- 辛特征值 \(\nu_k \ge 1/2\) 度量每个模的"有效热占位数"
- 纯高斯单模条件：\(\det V = 1/4\)

---

### 2.2 门怎么更新？

#### 通用框架：仿射辛变换

所有高斯门都是**仿射辛变换**：

\[
\mathbf r \mapsto S\mathbf r + \mathbf d,\quad
V \mapsto S V S^{\mathsf T},\quad
\bar r \mapsto S\bar r + \mathbf d,
\]

其中 \(S\Omega S^{\mathsf T} = \Omega\)（辛群条件）。

**根本不涉及矩阵指数**——只要做矩阵乘法。这是 Gaussian 后端的核心效率来源。

#### 常用高斯门的辛矩阵

| 门 | 相空间作用 | 辛矩阵（xxpp 序单模块） | 复杂度 |
|---|---|---|---|
| 位移 \(D(\alpha)\) | 平移 | \(I\) | \(O(1)\) |
| 相移 \(R(\theta)\) | 平面旋转 | \(\begin{pmatrix}\cos\theta&-\sin\theta\\\sin\theta&\cos\theta\end{pmatrix}\) | \(O(m)\) |
| 挤压 \(S(r)\) | 某方向压缩 | \(\begin{pmatrix}e^{-r}&0\\0&e^{r}\end{pmatrix}\) | \(O(m)\) |
| 分束器 \(BS(\theta,\varphi)\) | 两模混合 | \(\begin{pmatrix}\operatorname{Re}U&-\operatorname{Im}U\\\operatorname{Im}U&\operatorname{Re}U\end{pmatrix}\) | \(O(m^2)\) |
| 双模挤压 \(S_2(r)\) | 纠缠产生 | \(\begin{pmatrix}\cosh r\,I & \sinh r\,Z \\ \sinh r\,Z & \cosh r\,I\end{pmatrix}\), \(Z=\operatorname{diag}(1,-1)\) | \(O(m^2)\) |

**例：单模挤压 \(\hbar=1\)**：

\[
V_{\text{vac}}=\frac12 I,\quad
S=\begin{pmatrix}e^{-r}&0\\0&e^{r}\end{pmatrix},\quad
V' = S V S^{\mathsf T} = \frac12\begin{pmatrix}e^{-2r}&0\\0&e^{2r}\end{pmatrix}.
\]

\[\det V' = 1/4 \quad\text{(仍是纯高斯)}.\]

#### 物理图像

高斯门 = 相空间椭圆的线性变形

位移   → 平移椭圆中心（不改变形状）
相移   → 旋转椭圆
挤压   → 压扁一个方向，拉长另一方向
分束器 → 两个椭圆混合（纠缠）
双模挤压 → 产生两模间关联（EPR 型纠缠）
#### 高斯通道

比一般 CPTP 映射便宜得多——闭式仿射更新：

\[
V \mapsto X V X^{\mathsf T} + Y,\qquad \bar r \mapsto X\bar r.
\]

\(X,Y\) 由通道物理决定，满足完全正定性条件。

**光子损失**示例：
- 物理：透过率 \(T\) 的分束器耦合真空，然后偏迹掉 ancilla
- 数学：\(X = \sqrt{T}\,I,\quad Y = (1-T)\,\frac{\hbar}{4\kappa^2}I\)

---

### 2.3 测量怎么算？

这是 Gaussian 后端最"不平凡"的部分——协方差本身不说光子数，投影到 Fock 基需要图论计数。

#### Homodyne（正交测量）

**物理图像**：把相空间投影到角度 \(\phi\) 方向。

p ^
  |   ● ← 高斯态
  |  /|
  | / | ← 沿 φ 的边缘分布（一维高斯）
  |/  |
  └───┴──────→ x
**数学**：在方向 \(\phi\) 上测 \(x_\phi = x\cos\phi + p\sin\phi\)，输出是**一个高斯随机数**，均值和方差由 \(V,\bar r\) 的边缘分布给出。条件态按经典高斯条件更新（因为高斯态的 Wigner 条件分布仍是高斯）。

Homodyne 的极限实现方式：用"无限挤压真空"作为投影算符，挤压比 → ∞ 时退化为正交投影。

#### Generaldyne（一般高斯 POVM）

任意高斯测量的统一框架：

- 给定测量 POVM 的协方差 \(V_m\) 和投影方向
- 条件态更新公式：\(V' = V - V_{\text{cross}}(V+V_m)^{-1}V_{\text{cross}}^{\mathsf T}\)

这个公式将 Homodyne、Heterodyne 等统一为同一个数学操作。

#### 光子数测量 (PNRD)——Hafnian

**物理图像**：高斯态没有确定光子数——协方差 \(V\) 对应无限维 Wigner 函数，它叠加了无穷多 Fock 振幅。要算看到 \(n\) 个光子的概率，必须做**偶匹配图计数**。

**数学根源**：输出 Fock 态 \(|n_1\ldots n_m\rangle\) 的概率正比于

\[
p(\mathbf n) \propto \frac{|\operatorname{haf}(A_{\mathbf n})|^2}{n_1!\cdots n_m!}
\]

**Hafnian 直观**：在 \(N\) 个顶点完全图上，所有**完美匹配**的边权积之和。

完全图 4 个顶点:
  ●──●
  |\╱|
  |/ \|
  ●──●

完美匹配举例: (1-2, 3-4), (1-3, 2-4), (1-4, 2-3)
Hafnian = 三个匹配的边权积之和
计算代价 \(O(n^3 2^{n/2})\)，总光子数 > 20 时指数爆炸。

**Loop Hafnian**：含位移（一阶矩 ≠ 0）时的推广。

#### Threshold 探测——Torontonian

比 PNRD 简单：只答"有无光子"。

\[
p(\text{click}) = 1 - \frac{\operatorname{Tor}(O)}{\sqrt{\det(\Sigma)}}.
\]

Torontonian = Hafnian 的 threshold 版本——对**所有子集**而非完美匹配求和。

#### 测量关系总图

`text
测量类型           数学对象
────────────────────────────────
Homodyne          高斯条件式
Generaldyne       高斯 POVM 条件更新
PNRD              Hafnian / Loop Hafnian
Threshold         Torontonian

Hafnian:       偶阶完全子集匹配 → PNRD 概率
Torontonian:   所有子集上求和  → threshold 概率
Loop Hafnian:  + displacement  → PNRD 有位移
#### GBS（Gaussian Boson Sampling）

`text
每个模: 挤压真空 → 线性干涉仪 U → threshold 探测
输出概率 = Torontonian。经典模拟边界问题（近似采样难度）是光量子计算的核心理论问题之一。

GBS 的物理直觉：挤压真空经过干涉仪后，两模之间的光子数关联编码了图的边权——threshold 探测器 "click = 存在光子" 回答图顶点是否活跃。

---

### 2.4 误差从哪来？

| 类型 | 说明 |
|------|------|
| **表示误差** | 态根本非高斯 → 不可用（硬限制） |
| **数值误差** | \(V\) 迭代失去半正定性/辛结构（需投影修复） |
| **采样概率** | Hafnian/Torontonian 本身组合爆炸（总光子数 > 20 时） |
| **约定误差** | \(\hbar\)/正交序/真空定义混用——最隐蔽也最常见 |

**无 Fock cutoff ≠ 无误差。**

#### 辛结构漂移

多次门更新后，浮点误差的累积可能导致 \(V\) 不再满足量子条件 \(V + i\Omega/2 \ge 0\)。具体表现为：
- 对称性破损
- 辛特征值出现虚部或小于 1/2
- 后续计算产生无物理意义的概率

实践中需要**定期验证辛结构**并做投影修复。

#### 约定对齐

不同文献和实现对 \(\hbar\) 的约定不同：

- 本笔记正文：\(\hbar = 1\)，真空 \(V = I/2\)
- 一些教科书：\(\hbar = 2\) 或 \(\hbar = 1\) 但 \(x,p\) 系数不同
- 不同正交序（xxpp vs xpxp）导致相同门的辛矩阵不同

**黄金法则**：拿到任一实现，第一步先标定其真空 \(V\)——对上这个，才能继续推导。

---

## §3 辛特征值与 Williamson 分解

任意物理协方差 \(V\) 可通过某个辛变换变为对角形式：

\[
V = S \begin{pmatrix}\nu_1 & & \\ & \ddots & \\ & & \nu_m\end{pmatrix} S^{\mathsf T},\qquad \nu_k \ge \frac12.
\]

\(\nu_k\) 叫**辛特征值**（symplectic eigenvalues）：

- \(\nu_k = 1/2\) → 纯模
- \(\nu_k > 1/2\) → 混态（热噪声污染）

**物理解释**：\(V\) 描述的是一个处于温度中的谐振子系综——\(\nu_k\) 越大，该模受热噪声污染越重。Williamson 分解是将协方差矩阵"对角化"的标准数学工具。

---

## §4 Gaussian 四问总结

| 问题 | 回答 |
|---|---|
| **态怎么存？** | 协方差 \(V\) + 位移 \(\bar r\)，\(O(m^2)\) 存储 |
| **门怎么更新？** | 仿射辛变换 \(V\mapsto SVS^{\mathsf T},\; \bar r\mapsto S\bar r+\mathbf d\)，仅矩阵乘法 |
| **测量怎么算？** | Homodyne = 高斯条件；PNRD = Hafnian；Threshold = Torontonian |
| **误差从哪来？** | 非高斯态不可用 + \(V\) 辛结构漂移 + Hafnian 组合爆炸 + 约定混用 |

> 边缘 / 理想条件闭式 / 采样分离 / 纯损耗 \(X,Y\)：见 [02 · §3.2、§4.1](./02-Gaussian表示原理.md)。

---

## 练习

### Fock 篇

1. 单模 cutoff=5，位移 \(D(2)\) 后范数 \(\sum_{n<5}|c_n|^2\) 是多少？丢掉的概率去了哪？
2. 同一挤压 \(r=0.8\)，cutoff=6 vs 20，观察范数差异。
3. 为何 BS 的 Fock 矩阵复杂度是 \(O(N^4)\) 而非 \(O(N^2)\)？

### Gaussian 篇

4. 手写 50:50 分束器在 `xpxp` 与 `xxpp` 下的 \(S\)，验证 \(S\Omega S^{\mathsf T}=\Omega\)。
5. 真空 → 单模挤压 \(r\) → 分束器，用 numpy 手动算 \(V\)，与任意软件实现的结果对齐到 1e-5。
6. 多次随机高斯门后，检查 \(V\) 是否仍满足量子条件。

### 跨表示

7. 同一纯高斯电路分别用 Fock（扫 cutoff）和 Gaussian 跑，比较平均光子数，观察 Fock 何时收敛到 Gaussian 结果。
8. 若 Fock 的态范数 < 0.99，说明什么？测量概率还能信吗？

---

## 文献

| 主题 | 文献 |
|------|------|
| Fock 截断误差 | Provazník et al. [2202.07332](https://arxiv.org/abs/2202.07332) |
| 高斯量子信息综述 | Weedbrook et al. RMP 2012 [1110.3234](https://arxiv.org/abs/1110.3234) |
| CV 量子计算总览 | Braunstein & van Loock [quant-ph/0410100](https://arxiv.org/abs/quant-ph/0410100) |
| 高斯态讲义 | Ferraro/Olivares/Paris [quant-ph/0503237](https://arxiv.org/abs/quant-ph/0503237) |
| Hafnian 算法 | Björklund et al. [1805.12498](https://arxiv.org/abs/1805.12498) |
| Torontonian | Quesada et al. [1807.01639](https://arxiv.org/abs/1807.01639) |
| Loop Hafnian | [2108.01622](https://arxiv.org/abs/2108.01622) |
| GBS 经典模拟边界 | [1908.08068](https://arxiv.org/abs/1908.08068) |
| Serafini 教材 | *Quantum Continuous Variables* (CRC Press, 2017) |

---

# 第三部分：Bosonic 模拟器原理

---

## §1 物理图像与定位

### 1.1 什么是 Bosonic 表示

许多重要非高斯态的 Wigner 不是单峰高斯，但可写成**高斯态的加权叠加**：

\[
\rho = \sum_{k=1}^{K} w_k \;\rho_G(V_k, \bar r_k)
\]

或纯态层面：多个高斯波包的相干叠加（权重可为复数）。

- **Cat 态**：两（或多）个相干峰 + 相位
- **GKP 态**：格子上许多窄高斯峰
- **含损失淬炼的非高斯**：峰变胖、权重衰减

这是**用高斯积木搭非高斯**的模拟路线——组件数 \(K\) 可控时，同时得到：
- 高斯后端的效率（\(O(K\cdot m^2)\) 对纯高斯 \(O(m^2)\)）
- 非高斯的表达能力（只要叠加的峰能描述 Wigner）

### 1.2 三后端定位

        相同物理：单模 squeezing
         │
  Fock          Gaussian        Bosonic
 cutoff=20     V, r̄(无截断)     4 组件
 精确度≈1      精确(高斯族内)    精确(Cat类)
 ▲代价 N^m     O(m²)           O(K·m²)
Bosonic 的独占优势：
- **唯一能算 Cat/GKP 精确 Wigner**（多峰干涉）
- **唯一能高效处理含损失的非高斯演化**（每组件是高斯通道闭式更新）
- **唯一能在精度-代价上滑动**——少组件 ≈ 快但不精确，多组件 ≈ 慢但准

### 1.3 物理图像：从"一个椭圆"到"多个椭圆"

Fock (任意):  Wigner 可以是任意扭曲形状
              ─── 无结构假设，最通用

Gaussian:     Wigner 是单峰高斯（唯一椭圆）
              ● 代价最低

Bosonic:      Wigner = 多个高斯峰的加权叠加
              ● + ● + ● → ⋈ (干涉条纹)
              椭圆偏移 + 相位干涉 → 非高斯
**核心直觉**：两个高斯波包相干叠加 → Wigner 出现干涉条纹（负值区域）→ 非高斯。

### 1.4 Cat 干涉条纹

p ^
  |   ●  ← |α⟩ 高斯峰
  |   |\
  |   | \  ← 干涉条纹（Wigner 负值）
  |   |  \
  |   |   ● ← |-α⟩ 高斯峰
  └───┴──────────→ x

even cat:  中心条纹为正（增强）
odd cat:   中心条纹为负（相消）
关键物理：
- 每个峰是相干态——高斯、圆形
- **叠加不是**简单把两个高斯 Wigner 加起来——Wigner 的线性组合产生余弦调制
- 干涉条纹频率由 \(|\bar r_1 - \bar r_2|\) 决定：峰越远条纹越密
- 条纹 = 非高斯性的量子指纹

---

## §2 Bosonic 模拟器四问

### 2.1 态怎么存？

#### 数学模型：三元组

Bosonic 态的存储结构是 **\(K\) 个高斯组件的集合**，每个组件是一个三元组：

\[
\{\;(V_k,\; \bar r_k,\; w_k)\; \mid k = 1,\ldots, K\;\}
\]

- \(V_k \in \mathbb{R}^{2m \times 2m}\)：第 \(k\) 个高斯组件的协方差矩阵
- \(\bar r_k \in \mathbb{C}^{2m}\)：位移向量（**复数**，虚部编码相干信息）
- \(w_k \in \mathbb{C}\)：权重（**复数**，相位编码量子干涉）

**存储量**：\(O(K \cdot m^2)\)。

| 模数 \(m\) | Fock cutoff=10 | Gaussian | Bosonic \(K=10\) |
|---|---|---|---|
| 1 | 10 | 3 个数 | ~30 个数 |
| 8 | 1×10⁸ | 136 个数 | ~1360 个数 |
| 100 | 不可行 | ~20k 个数 | ~200k 个数 |

#### 复权重的物理来源

纯态叠加 \(\lvert\psi\rangle = c_1\lvert G_1\rangle + c_2\lvert G_2\rangle\)：

\[
\rho = |c_1|^2\;|G_1\rangle\langle G_1| + |c_2|^2\;|G_2\rangle\langle G_2|
      + c_1c_2^*\;|G_1\rangle\langle G_2| + c_2c_1^*\;|G_2\rangle\langle G_1|
\]

- 前两项：正权重（\(|c|^2\)），经典混合部分
- 后两项：**复权重**，编码量子相干性（交叉干涉）

如果所有 \(w_k\) 为正实数且 \(\bar r_k\) 实 → 纯经典混合，无量子干涉。
如果权重或位移出现复数 → 有 Wigner 负值区 → 非高斯性。

#### 物理意义

Bosonic 态 = 一堆相空间椭圆，每个带权
            椭圆偏移 + 复权重相位 = 干涉
              ↓
           非高斯 Wigner
---

### 2.2 门怎么更新？

#### 高斯门：逐组件辛变换

每个高斯组件独立更新，规则与 Gaussian 后端**完全相同**：

\[
V_k \mapsto S V_k S^{\mathsf T},\qquad
\bar r_k \mapsto S\bar r_k + \mathbf d,\qquad
w_k \mapsto w_k.
\]

实现方式 = 在 Gaussian 后端外包一层 batch 维（对 \(K\) 个组件做同样操作）。

**酉高斯门不改变权重**——纯态叠加的系数在幺正变换下不变。

#### 高斯通道

每个组件按高斯通道公式更新 \(V_k, \bar r_k\)：

\[
V_k \mapsto X V_k X^{\mathsf T} + Y,\qquad
\bar r_k \mapsto X \bar r_k.
\]

**权重更新**规则依赖通道类型：
- **无损失耗散**（如纯相移）：权重不变
- **有损失耦合**（如光子损失）：权重可能重新归一化或按概率衰减

这是"含损失非高斯态演化"的高效路径——Fock 需增大 cutoff 来捕捉泄漏到高阶的幅值，Bosonic 只需保留下每个组件的权重变化。

#### Kerr 门：组件数爆炸的临界点

Kerr 在 Fock 基下对角（代价 \(O(N)\)），但在 Bosonic 下**每个高斯组件做 Kerr 后不再是高斯**，必须用更多组件近似：

Kerr 操作
   │
   ▼
┌─────────────────────────┐
│ Fock:    O(N) 对角      │ ← 便宜
│ Bosonic: K 不断增长     │ ← 昂贵
│                           │
│ Kerr 扭曲越强 → K 越大    │
└─────────────────────────┘
这是 Bosonic 的**适用边界**：当非高斯态可被少量高斯峰描述时高效；当态是连续扭曲（如 Kerr 演化中途）时组件数爆炸。

---

### 2.3 测量怎么算？

#### Bosonic Wigner 函数

Bosonic 的核心能力之一：直接计算 Wigner 准概率分布，展示多峰干涉。

对空间点 \((x,p)\)，Wigner 值是所有组件的加权和：

\[
W(x,p) = \sum_{k=1}^{K} w_k \cdot \mathcal{N}\bigl((x,p) \mid \operatorname{Re}(\bar r_k),\, V_k^{(x,p)}\bigr) \cdot e^{i\phi_k(x,p)}
\]

其中：
- \(\mathcal{N}\)：高斯分布值（由 \(V_k\) 在 \((x,p)\) 子块决定）
- \(e^{i\phi_k}\)：相位因子，来自 \(\bar r_k\) 的虚部（编码相干）
- \(w_k\) 的复数相位：贡献干涉条纹

**干涉条纹来源**：

\[
\phi_k(x,p) = ( (x,p) - \operatorname{Re}(\bar r_k) )^{\mathsf T} \, V_k^{-1} \, \operatorname{Im}(\bar r_k)
\]

虚位移 \(\operatorname{Im}(\bar r_k)\) ≠ 0 → 产生余弦/正弦调制 → 干涉条纹。

#### Homodyne / Generaldyne

通过**逐组件高斯条件**实现：

1. 对每个组件 \((V_k, \bar r_k, w_k)\) 做高斯测量条件更新
2. 更新权重：基于测量算符在每组件上的投影概率加权
3. 重新归一化

**数学**：测量算符的投影值 \(p_k(\text{outcome})\) 作为权重乘子

#### 光子数测量

Bosonic 的光子数概率需要**额外复杂计算**：

\[
p(n) = \sum_{k,l} w_k w_l^* \cdot \langle n | G_k \rangle \langle G_l | n \rangle
\]

其中 \(\langle n | G_k \rangle\) 是高斯态在 Fock 基下的振幅（涉及 Hafnian 或 Hermite 多项式）。这比 Fock 的直接读 \(|c_n|^2\) 和 Gaussian 的 Hafnian 都更复杂。

#### 测量限制

| 测量类型 | Bosonic 支持 | 备注 |
|---------|-------------|------|
| Homodyne | ✅ | 逐组件高斯条件 |
| Generaldyne | ✅ | 通用高斯 POVM |
| Wigner 函数直接计算 | ✅ 核心优势 | 多峰干涉直观可见 |
| PNRD（光子数分辨） | ⚠ 支持但复杂 | 需额外交叉项求和 |
| 电路级 Fock 采样 | ❌ 不支持 | 需转 Fock 后端 |

---

### 2.4 误差从哪来？

| 类型 | 说明 |
|------|------|
| **组件截断误差** | 截掉小权重组件 → 丢失 Wigner 精细结构 |
| **组件数爆炸** | 某些演化（Kerr）导致 K 指数增长 → 失去效率优势 |
| **权重相位漂移** | 浮点误差累积 → 干涉条纹畸变 |
| **组件坍缩** | 两组件 mean 几乎相同 → 冗余可合并 |
| **负权重/非物理** | 数值误差导致权重违反物理条件 |
| **大 \(|\alpha|\) 下溢出** | 交叉项 \(e^{-2|\alpha|^2}\) 浮点下溢 → 可近似舍弃 |

#### 组件数爆炸的根源

Bosonic **不是万能非高斯压缩**：

`text
Bosonic 擅长:   含高斯峰的干涉态 (Cat, GKP)
Bosonic 不擅长:  连续扭曲的 Wigner (Kerr 演化到一半)
                 多模 Cat 组件指数增长（每模 ×2）

Fock 擅长:      任意非高斯，但受限于 cutoff N^m
#### 精度-代价旋钮

Bosonic 有三个可调的精度-代价旋钮：

1. **组件数 \(K\)**：多组件 = 高精度 = 高代价
2. **最小权重阈值**：丢弃 \(|w_k| < \epsilon\) 的组件（幅度截断）
3. **组件合并**：当两组件 \((V_k,\bar r_k)\) 足够接近时合并为一个

---

## §3 具体态示例

### 3.1 Cat 态

#### 数学形式

\[
\lvert\text{cat}\rangle \propto \lvert\alpha\rangle + e^{i\phi}\lvert-\alpha\rangle
\]

直觉是 2 个组件，但交叉项需要额外 2 个：

| 组件 | 物理意义 | 位移 \(\bar r\) | 权重 \(w\) |
|------|---------|----------------|------------|
| 1 | \(\lvert\alpha\rangle\langle\alpha\rvert\) | \(+\alpha\) | 正实数 |
| 2 | \(\lvert-\alpha\rangle\langle-\alpha\rvert\) | \(-\alpha\) | 正实数 |
| 3 | \(\lvert\alpha\rangle\langle-\alpha\rvert\) | 复平面 | 复数 |
| 4 | \(\lvert-\alpha\rangle\langle\alpha\rvert\) | 反复平面 | 复数（共轭） |

**为什么 4 组件？** 因为 \(\lvert\alpha\rangle\langle-\alpha\rvert\) 的 Wigner 是高斯但中心在**复平面**——mean 有虚部，不能与 \(|\alpha\rangle\langle\alpha|\) 共享同一个实位移。

#### 参数与精度

| \(|\alpha|\) | 峰分离 | 组件数需求 | 注意事项 |
|-------------|--------|-----------|---------|
| 0.5 | 小 | 4 足够 | |
| 1.0 | 中 | 4 足够 | |
| 2.0 | 大 | 4 足够 | 交叉项权指数级缩小 |
| 3.0+ | 很大 | 可近似 2 组件 | 交叉项 \(e^{-2|\alpha|^2} \to 0\) 可忽略 |

**大 \(|\alpha|\) 工程近似**：交叉项消失 → Cat 退化为 2 组件的经典混合态（无干涉条纹）。

### 3.2 GKP 态

#### 物理图像：相空间格子

p ^
  | ╋ ╋ ╋ ╋ ╋  理想 GKP: Dirac 梳
  | ╋ ● ╋ ╋      ● = 一个高斯峰
  | ╋ ╋ ╋ ╋  物理 GKP: 窄高斯 × 宽包络高斯
  | ╋ ╋ ╋ ╋
  └──────────→ x
- **理想 GKP 码字** \(\lvert 0\rangle_{\text{GKP}}\)：\(x\) 方向间隔 \(\sqrt{2\pi}\) 的 Dirac 峰梳
- **物理 GKP**：每个齿换窄高斯（方差 \(\epsilon\)），外包更宽的包络高斯（方差 \(1/\epsilon\)）

#### Bosonic 参数化

GKP 在 Bosonic 下的关键参数：

| 参数 | 含义 | 对模拟的影响 |
|------|------|------------|
| 齿展宽 \(\epsilon\) | 每个高斯峰的宽度 | \(\epsilon \to 0\) → 峰更窄 → 更接近理想 → 更贵 |
| 包络展宽 \(1/\epsilon\) | 整体分布的宽度 | 决定截断远齿的阈值 |
| 齿数 | 保留的峰数量 | ≈ 包络半宽 / 齿展宽 |
| \(amp\_cutoff\) | 权重截断阈值 | 降精度换效率的旋钮 |

**物理 GKP 越接近理想 → 组件数越多 → 越贵**。

#### Fock vs Bosonic 模拟 GKP

Fock 模拟 GKP:   需要极大 cutoff（Dirac 峰用高阶 Fock 基组合）
                 代价 N^m 爆炸

Bosonic 模拟 GKP: 只需几十到几百组件
                 每个组件是知道闭式的窄高斯
                 代价 K·m² 可控
---

## §4 完整示例：Cat 态的 Wigner 干涉条纹

### 4.1 编码

Even Cat 态：

\[
\lvert\text{cat}_+\rangle \propto \lvert\alpha\rangle + \lvert-\alpha\rangle,\quad \alpha > 0
\]

在 Bosonic 中参数化：

\[
\begin{aligned}
\text{组件 1:}\quad & V_1 = \frac12 I,\; \bar r_1 = (\sqrt{2}\alpha, 0),\; w_1 = \frac{1}{2(1+e^{-2\alpha^2})} \\
\text{组件 2:}\quad & V_2 = \frac12 I,\; \bar r_2 = (-\sqrt{2}\alpha, 0),\; w_2 = w_1 \\
\text{组件 3:}\quad & V_3 = \frac12 I,\; \bar r_3 = (0, i\sqrt{2}\alpha),\; w_3 = w_1 e^{-2\alpha^2} \\
\text{组件 4:}\quad & V_4 = \frac12 I,\; \bar r_4 = (0, -i\sqrt{2}\alpha),\; w_4 = w_3^*
\end{aligned}
\]

### 4.2 Wigner 计算过程

对相空间点 \((x,p)\)：

\[
W(x,p) = \sum_{k=1}^{4} w_k \cdot \frac{1}{\pi} \exp\!\bigl( -|x - \operatorname{Re}(\bar r_{k,x})|^2 - |p - \operatorname{Re}(\bar r_{k,p})|^2 \bigr) \cdot e^{i\phi_k(x,p)}
\]

其中 \(\phi_k\) 来自 \(\operatorname{Im}(\bar r_k)\)。

### 4.3 结果解读

取 \(\alpha=1.5\)，四个组件叠加后的 Wigner 等高线：

p ^
  |   ●     ↑ |α|=1.5
  |  / \      两个相干峰在 x 轴对称分布
  | /   \     中心竖线 = 干涉条纹
  |/     \
  └───────●──→ x

even cat:   中心 Wigner 为正（增强条纹）
odd cat:    中心 Wigner 为负（相消条纹）
关键观察：
- 组件 1 和 2 贡献两个圆峰（经典混合部分）
- 组件 3 和 4 贡献中心条纹（量子干涉部分）
- 当 \(\alpha\) 增大 → 组件 3,4 的权重指数衰减 → 条纹消失 → 退化为经典混合

### 4.4 误差检查

**概率归一性**：

\[
\int W(x,p)\, dx\, dp = \sum_k w_k = 1
\]

**如果组件截断过多**（丢弃了权重小的交叉项）→ 失去干涉条纹 → Cat 被错误模拟为经典混合。

**如果 \(\alpha\) 很大时保留 4 组件** → 组件 3,4 的权重因 \(e^{-2\alpha^2}\) 浮点下溢 → 等价于 2 组件的经典混合 → 是否可接受取决于精度需求。

---

## §5 Bosonic 四问总结

| 问题 | 回答 |
|---|---|
| **态怎么存？** | 三元组 \(\{(V_k, \bar r_k, w_k)\}\)，\(K\) 组件，存储量 \(O(K\cdot m^2)\) |
| **门怎么更新？** | 高斯门：逐组件辛变换（与 Gaussian 相同）；通道：\(V,\bar r\) 仿射更新 + 权重重归一 |
| **测量怎么算？** | Wigner 直算（所有组件加权求和）；Homodyne：逐组件高斯条件 |
| **误差从哪来？** | 组件截断 + 组件数爆炸（Kerr 等）+ 权重相位漂移 + 浮点下溢 |

> 复仿射条件、实峰混合采样诚实边界、真空 \(W(0,0)=1/\pi\)：见 [03 · §5](./03-Bosonic表示原理.md)。

### 三后端选型对照

`text
态是单峰高斯?                    → Gaussian (O(m²))
态是 Cat / GKP / 含损失非高斯?   → Bosonic (O(K·m²))
态是 Kerr 扭曲 / 需要精确光子数?  → Fock (O(N^m))

Bosonic 不擅长:
├─ Kerr 连续扭曲的 Wigner
├─ 多模 Cat（每模×2，指数增长）
└─ 需要电路级 Fock 采样
---

---

# 第四部分：原理深入——七项缺失专题

---

## 专题一：为什么 Gaussian = 经典可模拟（CV Gottesman-Knill）

> **一句话**：如果你的电路只用高斯门 + 高斯初态 + 高斯测量，经典计算机可以高效模拟它。量子优势必须来自非高斯操作。

### 1.1 一个让人困惑的问题

初学 CV 时很容易问："Gaussian 后端跑一百个模这么快，还无截断误差——这为什么叫『量子』模拟？不是经典模拟吗？"

答案是：**纯高斯电路本质上就是经典模拟**，只不过是用矩阵乘法模拟了量子谐振子的演化。

### 1.2 类比 DV：Clifford 门 + 稳定子理论

在离散变量（qubit）量子计算中有一个经典的分界线：

Clifford 门 (H, S, CNOT) + Pauli 测量
    ─── 经典可高效模拟（Gottesman-Knill 定理）

Clifford + 任意 T 门
    ─── 通用量子计算（需要量子计算机）
**Clifford 门虽然也是量子门，但它们作用在稳定子态上时，态的结构可以用经典线性代数跟踪，不需要维护 \(2^n\) 维状态向量。**

### 1.3 CV 中同样的故事

CV 里有完全平行的分界线：

高斯门 (位移、相移、挤压、分束器、双模挤压) + 高斯初态 + Homodyne 测量
    ─── 经典可高效模拟（CV Gottesman-Knill）

高斯门 + 至少一个非高斯门（Kerr、光子加减）
    ─── 通用 CV 量子计算
**为什么高斯门可以经典模拟？** 因为高斯态完全被协方差 \(V\) 和位移 \(\bar r\) 确定（\(2m + m(2m+1)\) 个实数）。不需要指数级信息。高斯门的更新就是矩阵乘法——它一直待在"低维经典轨道"里。

非高斯门把态推出这个轨道。Wigner 不再是高斯，需要指数级信息（Fock 振幅 \(N^m\)）才能精确描述。

### 1.4 直觉类比

经典力学                   高斯量子力学
质点: (x, p)              高斯态: (V, r̄)
线性变换: x' = Ax + b      高斯门: V → SVSᵀ
需要 O(1) 个数             需要 O(m²) 个数

非高斯量子力学
态: 振幅张量 c_{n1...nm}
需要 O(N^m) 个数
就像一个质点的位置和动量（2 个数）被线性变换（矩阵乘法）更新——你永远不会想到要用指数级来跟踪它。高斯态在相空间中的演化本质上就是这种"经典"层面的运动，只不过它遵守的是量子力学规则（不确定关系）。

### 1.5 这对模拟器架构意味着什么

纯高斯的电路 ──→ 用 Gaussian 后端（经典可模拟，高效）
                  │
                  └── "模拟"的只是量子谐振子的经典可跟踪部分

含非高斯的电路 ──→ 必须用 Fock 或 Bosonic
                  │
                  ├── Fock: 存储全部振幅（昂贵但通用）
                  └── Bosonic: 用高斯组件拼出非高斯（折中）
**这就是三后端的逻辑起点**：不是工程上的巧合，而是物理原理决定的——高斯部分需要一种表示，非高斯部分需要另一种。

### 1.6 为什么说"量子优势必须来自非高斯"

假设有一个算法只用了高斯门。因为经典计算机可以用 \(O(m^3)\) 时间模拟它，所以不存在量子优势。想打败经典计算机，必须引入非高斯门——这就是为什么：

- GBS（Gaussian Boson Sampling）的困难来自**threshold 探测**（它把高斯态投影到非高斯 Fock 基）
- Bosonic 编码（Cat、GKP）靠的是**相干叠加**（非高斯性）
- 模拟器架构的根源问题是：**非高斯性是计算优势的来源，也是模拟困难的原因**

> **核心教训**：如果你用一个模拟器跑电路，发现跑得飞快（Gaussian 后端），那它很可能在"经典可模拟"的区域内。真正的量子模拟——需要真正的量子计算机——门槛很高。

---

## 专题二：相空间表示的层级——特征函数与 Wigner

> **一句话**：Wigner 函数不是最基本的。它的父亲是特征函数（characteristic function），它的兄弟姐妹是 P-函数和 Q-函数。理解这层关系，才能理解为什么有些态容易模拟、有些不能。

### 2.1 特征函数：最根本的态表示

回忆概率论中，一个随机变量的特征函数 = \(\mathbb{E}[e^{itX}]\)——包含了所有矩的信息。

CV 量子态的特征函数：

\[
\chi(\xi) = \operatorname{Tr}\bigl(\rho \, D(\xi)\bigr)
\]

其中 \(D(\xi) = \exp(\xi a^\dagger - \xi^* a)\) 是位移算符，\(\xi \in \mathbb{C}\)（或等价地 \(\xi \in \mathbb{R}^{2m}\)）。

**物理意义**：\(\chi(\xi)\) 回答"把态位移 \(\xi\) 后与原态的重叠有多大"——它编码了态的相干结构。

### 2.2 三种相空间表示来自同一个母亲

        特征函数 χ(ξ)
        /      |      \
  对称序   正规序   反正规序
   Wigner    P-函数    Q-函数
三种函数 = 特征函数乘上不同权重后做傅里叶变换：

\[
\begin{aligned}
W(\alpha) &= \frac{1}{\pi^2} \int e^{\alpha\xi^* - \alpha^*\xi} \; \chi(\xi) \; d^2\xi \\
P(\alpha) &= \frac{1}{\pi^2} \int e^{\alpha\xi^* - \alpha^*\xi} \; \chi(\xi) \; e^{|\xi|^2/2} \; d^2\xi \\
Q(\alpha) &= \frac{1}{\pi^2} \int e^{\alpha\xi^* - \alpha^*\xi} \; \chi(\xi) \; e^{-|\xi|^2/2} \; d^2\xi
\end{aligned}
\]

差别只在于指数上那个 \(\pm|\xi|^2/2\)——对应算符排序方式（对称序 / 正规序 / 反正规序）。

### 2.3 为什么 P-函数=经典性

**P-函数**（Glauber-Sudarshan P-表示）：

\[
\rho = \int P(\alpha) \; \lvert\alpha\rangle\langle\alpha\rvert \; d^2\alpha
\]

把态写成相干态的古典混合。**如果 \(P(\alpha) \ge 0\)**，这个态完全等同于一个经典概率分布——没有任何量子性。

可悲的事实：绝大多数非经典态（压缩态、Cat 态）的 P-函数高度奇异（δ 函数导数），没有良好定义的函数。

### 2.4 三者的性质对比

函数      平滑性    非负性意义          经典判断
──────────────────────────────────────────────────
P-function 最奇异   ≥ 0 ⇒ 完全经典      标准
Q-function 最光滑   ≥ 0 总是成立         过于乐观
Wigner     中等     ≥ 0 ⇒ 仍可经典计算?  中间标准
**Q-函数总是非负的**——它太光滑了，把非经典性都平滑掉了。所以 Q-函数非负不能作为"经典性"的证据。

**Wigner 函数的负值**是量子性的充分条件，但不是必要条件（有些非经典态 Wigner 为正）。

### 2.5 对模拟器的深刻影响

**Gaussian 态的特征**在所有三种表示中都是高斯：

\[
\chi(\xi) = \exp\!\bigl(-\frac12 \xi^\dagger V \xi + i \xi^\dagger \Omega \bar r\bigr)
\]

- P-函数是高斯且正定 → 高斯态在"经典"意义上永远是经典的
- 这就是高斯态可以经典模拟的数学根源
- 非高斯态的特征函数不是高斯 → 至少在某些表示中出现负值或奇异

**为什么 Hafnian 出现？**

\[
p(\mathbf n) \propto \frac{|\operatorname{haf}(A_{\mathbf n})|^2}{n_1!\cdots n_m!}
\]

Hafnian 的直接推导来自：把 Fock 投影算符写成位移算符的傅里叶变换，然后代入高斯特征函数。计算 Fock 概率 = 对高斯特征函数乘上某个多项式再积分——这个积分恰好等于 Hafnian。

**数学链条**：

`text
高斯态 → 特征函数是指数二次型
   ↓ 乘以 Fock 投影多项式
   ↓ 积分 → Hafnian
   ↓
光子数概率
### 2.6 初学者应该记住的

1. **特征函数是王**：其他一切都是它的衍生
2. **P-函数正 = 完全经典**：但绝大多数量子态没有良定义的 P-函数
3. **Wigner 负 = 非经典**：这是实践中用得最多的判据
4. **Hafnian 的根源在特征函数**：不是凭空冒出来的公式

---

## 专题三：通用门集合——Lloyd-Braunstein 定理

> **一句话**：CV 量子计算中，不是所有门都能通用。你需要哪些门才能做到"任意精度逼近任意酉变换"？

### 3.1 先理解问题

在离散变量中，说"一个门集合是通用的"意味着：你只需要 {H, S, CNOT, T} 就能以任意精度逼近任何 qubit 电路。

在 CV 中同样的事：一个集合 \(\{G_1, G_2, \ldots, G_k\}\) 如果满足"用这些门的组合可以任意精度逼近任意 CV 酉变换"，就叫通用。

### 3.2 Lloyd-Braunstein（1999）的回答

Lloyd 和 Braunstein 证明了一个干净的结果：

> **CV 通用门集合** = \(\{\) 位移 \(D(\alpha)\), 挤压 \(S(r)\), 分束器 \(BS(\theta,\phi)\), **Kerr** \(K(\chi)\) \(\}\)

**Kerr 是关键**：去掉它，剩下的门只能产生高斯酉变换——经典可模拟。加上它，就能逼近任意操作。

### 3.3 为什么恰恰是这四个门？

一个等价的说法：通用 CV 电路需要生成**多项式哈密顿量**。

任何酉变换 \(U = e^{-iHt}\) 的哈密顿量 \(H\) 是产生湮灭算符的多项式。

多项式次数    能生成什么门        通用性
──────────────────────────────────────────────
1 次         位移               不能混合不同模
2 次         高斯门 (挤压、BS)   只能产生高斯酉
3 次 (Kerr)  Kerr 相互作用      通用
≥4 次        Kerr 的重复应用    通用（不是必须）
- **1 次项** \(a, a^\dagger\)：位移
- **2 次项** \(a^2, a^{\dagger2}, a^\dagger a\)：挤压、相移
- **2 次交叉项** \(a_i^\dagger a_j, a_i a_j, a_i^\dagger a_j^\dagger\)：分束器、双模挤压
- **3 次项** \(a^{\dagger2} a, a^\dagger a^2\)：等价于 Kerr

- **4 次项** \((a^\dagger a)^2\)：**Kerr 门** \(K(\chi) = e^{i\chi (a^\dagger a)^2}\)

关键洞察：**一旦有了 Kerr（4 次），可以合成任意高次项**。Kerr ≈ CV 世界的 T 门。

### 3.4 想象一下物理图像

高斯门世界:     椭圆 → 旋转 → 平移 → 混合 → 仍是椭圆
                   形状不变，只是位置和朝向变了

加上 Kerr 后:   椭圆 → Kerr → S 形扭曲（非高斯）
                   形状不再被保持，产生扭曲
                   更多的 Kerr → 更复杂的扭曲
                   最终可以产生任意 Wigner
这是**结构的质变**：高斯门是线性的（在相空间层面），Kerr 是**非线性的**。线性变换的反复应用只会产生更多的线性变换；非线性才是通向通用的桥梁。

### 3.5 对模拟器的直接冲击

门        Fock      Gaussian    Bosonic
─────────────────────────────────────────
高斯门     O(N³)     O(m²)       O(K·m²)
Kerr      O(N)      不可用       组件数爆炸 ← 因为 Kerr 不是高斯
**Kerr 是三后端的试金石**：
- Fock 处理 Kerr 最轻松（对角矩阵）
- Gaussian 根本不能用（Kerr 输出非高斯）
- Bosonic 理论上可以但组件数爆炸（Kerr 不是有限个高斯峰的叠加）

这**不是**工程优化能解决的问题——它是数学结构决定的：

Kerr 的哈密顿量 H ∝ (a†a)²
    Fock 基: |n⟩ 是 H 的本征态 → 对角
    相空间: Kerr 产生多项式扭曲 → 需要很多高斯峰
### 3.6 对初学者最重要的认识

**不要认为所有量子门都是等价的**。在 CV 世界里，门的"阶数"（哈密顿量的多项式次数）决定了它的力量和模拟代价。

> **口诀**：2 次以下温顺可控，3 次以上才是猛兽。模拟器的设计，本质上是在选择"你要驯服多少头猛兽"。

---

## 专题四：非高斯性的度量——怎么才算"非高斯"

> **一句话**：不是所有的非高斯态都一样"难模拟"。度量非高斯性，就是度量量子优势的潜力。

### 4.1 Wigner 负值（Negativity）

最直觉的度量：看 Wigner 函数有多少负值。

\[
\mathcal{N}(\rho) = \int |W(x,p)|\,dx\,dp - 1
\]

- **纯高斯态**：Wigner ≥ 0，所以 \(\mathcal{N} = 0\)
- **Cat 态**：干涉条纹有负值，\(\mathcal{N} > 0\)
- **Fock 态 \(|1\rangle\)**：中心有深负值，\(\mathcal{N}\) 较大

**物理意义**：Wigner 负值意味着态不能写成相干态的凸组合（概率混合）。它是"量子性"的直接证据。

**模拟意义**：Gaussian 后端要求 Wigner ≥ 0（单峰）。一旦 Wigner 有负值，必须用 Fock 或 Bosonic。

### 4.2 Stellar Rank——最能解释 Bosonic 的限制

这是一个较新的概念（Chabaud et al., 2020），但对模拟器的选型至关重要。

核心思想：任何单模纯态可以用一个复函数 \(F(z)\)（stellar function）来描述，这个函数的零点数决定了"最少需要多少个高斯峰来近似这个态"。

Stellar rank = stellar function 零点数

rank 0:   高斯态 ──→ Gaussian 后端（1 个椭圆）
rank 1:   Cat 态 ──→ Bosonic 几到几十个组件
rank 2:   两光子加减 ──→ Bosonic 更多组件
rank ∞:   Kerr 演化中途 ──→ Bosonic 失效 → Fock
**多模推广**：多模 Stellar rank 可能随模数指数增长。这就是为什么多模 Cat 会让 Bosonic 爆炸——不是因为工程问题，而是数学结构决定的。

### 4.3 最近高斯态距离

另一个视角：给定任意态 \(\rho\)，找离它最近的高斯态 \(\rho_G\)：

\[
\delta(\rho) = \min_{\rho_G \text{高斯}} \|\rho - \rho_G\|
\]

- 高斯态：\(\delta = 0\)
- 弱挤压 Cat：\(\delta\) 很小（近似高斯）
- 强 Kerr：\(\delta\) 很大

**模拟意义**：如果 \(\delta\) 很小，用 Gaussian 后端做近似可能就够了，不需要用昂贵的 Fock。

### 4.4 三个度量的关系

                    最近高斯距离大
                    ↑
Stellar rank 高 ──→ Wigner 负值大
                    ↑
                    难模拟（需 Fock）
它们不严格等价但高度相关。Stellar rank 对 Bosonic 最直接——它告诉你组件数的理论下界。

### 4.5 直觉类比

Wigner 负值     → "照片上的黑斑" —— 一眼看到量子性
Stellar rank    → "最小需要几块积木" —— 搭建态的复杂度
最近高斯距离    → "离安全区多远" —— 高斯近似失效程度
想象你在拼乐高：
- Wigner 负值 = 这模型有多少悬空部件
- Stellar rank = 最小需要多少种特殊积木
- 最近高斯距离 = 离标准方块的差距

这三种度量从不同角度帮你判断：**该用哪个后端**。

### 4.6 对初学者的建议

**不要被"非高斯"这三个字误导**。并不是用了 Fock 就是"真量子"，用 Gaussian 就是"经典"。

> **正确姿势是**：Stellar rank 低的态（Cat、GKP）用 Bosonic；Stellar rank 高的态（Kerr 扭曲）用 Fock；高斯态用 Gaussian。选后端就是选"假设你的态有多少结构"。

---

## 专题五：辛几何的深层结构——为什么量子力学用辛矩阵

> **一句话**：高斯门的辛结构不是人工选择，而是从 \([x,p]=i\) 必然推导出来的。辛矩阵是量子对易关系在线性变换下的化身。

### 5.1 辛群 \(Sp(2m,\mathbb{R})\) 的生成元

所有保持 \(\Omega\) 的 \(2m\times 2m\) 实矩阵构成辛群：

\[
S\Omega S^{\mathsf T} = \Omega
\]

辛群和所有高斯门之间有一一对应：

辛群生成元（二次型哈密顿量）    对应量子门
────────────────────────────────────────
x²/2                         挤压 (S)
p²/2                        反向挤压 (S⁻¹)
(xp + px)/4                  相移 (R)
x_i x_j                     分束器 (BS)
x_i p_j + p_i x_j           双模挤压 (S₂)
**关键**：这些哈密顿量都是**二次型**——这正是高斯门不需要矩阵指数的原因。二次型哈密顿量的时间演化是线性的（在相空间层面）。

### 5.2 Metaplectic 表示——从经典到量子的桥梁

有一个深刻的问题：**辛变换是经典相空间的变换，怎么变成量子态上的酉变换？**

答案：Metaplectic 表示。

经典辛变换 S ∈ Sp(2m,ℝ)
        ↓ Metaplectic 提升
量子酉算符 U_S（Hilbert 空间上）
        ↓
在相空间层面：U_S^† r U_S = S·r
**物理意义**：每一个经典线性光学网络（由分束器、相移器组成），都对应一个唯一（up to sign）的量子酉变换。这个对应关系是自动的——不需要额外推导。

**为什么这对模拟器重要？**
- 因为辛变换在经典层面完全确定了高斯门的量子效果
- 不需要去构造巨大的 Fock 矩阵——直接用辛矩阵更新 \(V\) 就够了
- 这就是 Gaussian 后端高效的**数学根源**

### 5.3 Lagrangian 子空间——GKP 编码的几何

Lagrangian 子空间 \(L\) 是相空间的一个子空间，满足两个条件：
1. 对任意 \(u,v \in L\)：\(\Omega(u,v) = 0\)（Lagrangian = "在 \(\Omega\) 下自正交"）
2. 维数极值：\(\dim L = m\)（最大自正交子空间）

例子（xxpp 序下）:
L_x = { (x₁,...,x_m, 0,...,0) } → x 轴张成的子空间
L_p = { (0,...,0, p₁,...,p_m) } → p 轴张成的子空间
L_x 和 L_p 都是 Lagrangian
**GKP 编码的几何**：GKP 码字对应于相空间中格点上的高斯峰。这个格子必须是 **Lagrangian 子格**——否则无法同时满足对易关系。

`text
GKP 码字 |0⟩_GKP:    x = √(2π)·k 上的 Dirac 峰
                    这个格 L = √(2π)·ℤ^m 是 Lagrangian

GKP 码字 |1⟩_GKP:    偏移 √π 后的格
                    L + √π = 另一组 Lagrangian 子格
**这就是为什么 GKP 的格子必须是正方形的变形**——不是编码设计者自由选择，而是辛几何的强制约束。

### 5.4 对模拟器架构的影响

概念层次             模拟器实现
─────────────────────────────────
辛群 Sp(2m,ℝ)       Gaussian 后端的门矩阵
Metaplectic 表示    保证辛变换 → 酉变换的一致性
Lagrangian 子空间    GKP 的组件定位规则
Williamson 分解      协方差对角化（检纯度、噪声）
Takagi 分解          GBS 干涉仪对角化
### 5.5 初学者应该记住的

1. **高斯门 不是 近似——它们是精确经典结构在量子世界的体现**
2. **辛矩阵乘法的效率来自二次型哈密顿量的线性性**——不是巧合
3. **GKP 格子不是任意选的——必须遵守 Lagrangian 条件**
4. **Williamson 分解≈协方差矩阵的"PCA"，但用的是辛变换而非正交变换**

---

## 专题六：CV 编码原理——从真空到纠错码

> **一句话**：将量子信息编码进连续变量系统的不同方式，决定了抗噪能力和计算能力。

### 6.1 先想一个问题

你有一个无穷维的 Hilbert 空间（一个玻色模），你想在里面存一个 qubit 的信息。怎么存？

有无数种方式把 2 维子空间嵌入无穷维空间。不同的嵌入方式 = 不同的编码——它们对噪声的响应完全不同。

### 6.2 单轨编码（Single-Rail）

|0⟩_L = |0⟩（真空，0 光子）
|1⟩_L = |1⟩（单光子）
**优点**：最简单的编码，1 模 = 1 qubit。
**致命伤**：光子损失 → \(|1\rangle\) 变成 \(|0\rangle\) → 信息丢失。一个光子损失 = 一个纠错无法恢复的错误。

**物理图像**：

单轨编码 = 用一个盒子里的光子数编码
           光子跑了 → 信息跑了
### 6.3 双轨编码（Dual-Rail）

|0⟩_L = |1,0⟩（第 0 模有光子，第 1 模没有）
|1⟩_L = |0,1⟩（第 1 模有光子，第 0 模没有）
**优点**：单光子损失 → \(|1,0\rangle\) 变成 \(|0,0\rangle\) → 探测器能发现（两个模都没有光子），可纠错。
**代价**：2 模 = 1 qubit，翻倍。

**物理图像**：

双轨编码 = 用光子"在哪条路"编码
           光子丢了一个 → "两条路都没了"——你可以知道丢了
### 6.4 Cat 编码

|0⟩_L ∝ |α⟩ + |−α⟩ （even cat）
|1⟩_L ∝ |α⟩ − |−α⟩ （odd cat）
**用相干态的同位相编码信息**。

**优点**：抗偏位错误——如果位移算符 \(D(\beta)\) 作用到 Cat 上，态变成 \(|α+β⟩ ± |−α+β⟩\)，仍在 Cat 码空间附近。可以通过"纠正小的偏位"来恢复。

**物理图像**：

Cat 编码 = 用钟摆两个相反方向的摆锤编码
           轻微的推搡不会改变"是正摆还是反摆"的信息
### 6.5 GKP 编码

|0⟩_GKP = Σ_k |x = k√(2π)⟩     （相空间 x 方向上的周期峰）
|1⟩_GKP = Σ_k |x = k√(2π) + √π⟩（偏移半个周期）
**用相空间格子编码信息**。

**优点**：能纠正连续的位移错误——小位移只是把格点稍微偏移，用"把它拉回最近的格点"就能恢复。这是**真正的 CV 量子纠错码**。

**物理图像**：

GKP 编码 = 用国际象棋棋盘的黑白格编码
           轻微的偏移 → 你知道它本来该在哪个格
           大幅偏移 → 无法分辨 → 错误
### 6.6 编码选型与模拟器选型的交叉关系

| 编码 | 天然后端 | 原因 |
|------|---------|------|
| 单轨 | Fock（cutoff=2） | 只需 \(|0\rangle,|1\rangle\) |
| 双轨 | Fock（cutoff=2） | 两模，每模只需 0/1 光子 |
| Cat | Bosonic | 天然是 2 或 4 个高斯组件 |
| GKP | Bosonic | 天然是格点上的高斯峰 |
| 复杂纠缠 | Fock 或 MPS | 无结构假设 |

### 6.7 核心教训

**没有最好的编码，只有最合适的编码**：

单轨:  最简单            → 但对损失最脆弱
双轨:  能检测损失          → 编码效率低 (2:1)
Cat:   抗偏位错误         → 损失下退相干快
GKP:   CV 标准纠错码     → 需要大量组件模拟
选编码 = 选你预期的噪声模式 + 可用的操作集合。
选模拟器后端 = 选编码天然适合的表示。

---

## 专题七：三后端的哲学——结构假设与代价

> **一句话**：每种模拟器后端都是对"态的结构做什么假设"的声明。假设越强 = 越高效 = 适用范围越窄。假设越弱 = 越通用 = 代价越昂贵。

### 7.1 统一框架

结构假设强度:
弱 ←──────────────────────────────→ 强

Fock                    Bosonic              Gaussian
无结构假设               Wigner 是 K 个高斯峰   Wigner 是单峰高斯
仅 cutoff 截断
                        ↓                    ↓
代价 N^m                O(K·m²)              O(m²)
通用任意态              Cat/GKP 高效          仅高斯态
**这不是一个技术选择——这是一个物理假设**。

### 7.2 概率论类比

想象你要描述一个一维概率分布：

方法            假设              代价              适用范围
───────────────────────────────────────────────────────────
直方图（Fock）  无假设             指数级 bins        任何分布
高斯混合（Bosonic N 个峰）         有限高斯           峰状分布
单高斯（Gaussian）                 2 个参数（μ,σ）   真正的高斯
text
单高斯: μ=0, σ=1  → 2 个数字 → 但只能描述高斯
高斯混合: {(μ_k,σ_k,w_k)} → 3K 个数字 → 能描述多峰
直方图: [p₁,...,p_{N_bin}] → N_bin 个数字 → 任意分布
**CV 三后端就是概率论中这三种方法在量子世界的翻版。**

### 7.3 结构假设的代价：容忍的误差类型

后端      含什么误差         不含什么误差
─────────────────────────────────────────
Gaussian  数值精度、约定对齐  → 无表示误差（在高斯族内精确）
Bosonic   组件截断、相位漂移  → 组件数充足时 Wigner 精确
Fock      截断误差           → cutoff 内所有振幅精确

选择后端 = 选择你愿意接受哪种误差
          = 选择你的态在哪种结构假设下"近似准确"
### 7.4 动态选择：精度-代价滑轨

理想情况下，模拟器应允许用户在**同一物理问题**上沿着精度-代价滑轨滑动：

Gaussian ──→ Bosonic ──→ Fock
O(m²)        O(K·m²)      O(N^m)
低精度        中等精度      高精度
在实践中，切换后端不是自动的——因为一旦选择了表示，门和测量的实现方式完全不同。但**概念上**，你可以把三者看作同一个物理的不同层次近似：

物理: 单模挤压 r=0.5

Gaussian: 精确（在高斯族内）               → V = ½ diag(e⁻¹, e¹)
Bosonic:  1 个组件（=Gaussian）          → {(V, 0, 1)}
Fock:     cutoff → ∞ 趋近高斯结果        → 振幅逼近

物理: Cat |α=1⟩

Gaussian: 不可用                        → 强迫用会给出无意义的正 Wigner
Bosonic:  4 组件精确                     → {4 个(V_k, r̄_k, w_k)}
Fock:     cutoff 足够时精确              → 许多非零振幅
### 7.5 什么时候该换后端——决策树

态是高斯?
├─ 是 → 你用 Gaussian（不需要别的东西）
└─ 否 → 态能用有限个高斯峰近似?
        ├─ 是 → 你用 Bosonic
        └─ 否 → 你用 Fock（或 MPS Fock）
这个决策树**不是经验法则，而是数学定理的直接后果**：
- 高斯态 = Wigner 是高斯 → Gaussian 表示完全充分
- 低 Stellar rank ≠ Gaussian → Bosonic 表示高效
- 高 Stellar rank → Fock（或 MPS）是唯一选择

### 7.6 哲学总结

> **模拟器的本质，不是黑盒计算工具，而是你对物理系统所做的结构假设的具象化。**

你相信态是高斯     ──→ 你用 Gaussian 后端
你相信态是几个高斯峰 ──→ 你用 Bosonic 后端
你相信态毫无结构   ──→ 你用 Fock 后端

你的速度 = 你的信念的回报
你的精度 = 你的信念的正确程度
### 7.7 最后再回顾整个系列

| 后端 | 一句话本质 | 像什么 |
|------|-----------|--------|
| Fock | "砍到有限维，算全部振幅" | 穷举法：把所有可能都列出来 |
| Gaussian | "只存均值和协方差" | 近似法：假设态是漂亮的椭球 |
| Bosonic | "用一堆椭球拼出复杂形状" | 拼图法：用基本形状搭出复杂图案 |

**三后端的完整图景**：

`text
物理世界（连续变量玻色模）
      │
      ├── 你的态有多"非高斯"？
      │
      ├─ 单峰高斯 ──────→ Gaussian ──→ 高效但受限
      ├─ 多峰可数 ──────→ Bosonic  ──→ 折中
      └─ 任意扭曲 ──────→ Fock     ──→ 通用但昂贵

      选后端 = 在效率和通用性之间做交易
      没有免费的午餐（No free lunch theorem of CV simulation）
---

## 全文档文献汇总

| 主题 | 文献 |
|------|------|
| Fock 截断误差 | Provazník et al. [2202.07332](https://arxiv.org/abs/2202.07332) |
| 高斯量子信息综述 | Weedbrook et al. RMP 2012 [1110.3234](https://arxiv.org/abs/1110.3234) |
| CV 量子计算总览 | Braunstein & van Loock [quant-ph/0410100](https://arxiv.org/abs/quant-ph/0410100) |
| 高斯态讲义 | Ferraro/Olivares/Paris [quant-ph/0503237](https://arxiv.org/abs/quant-ph/0503237) |
| Lloyd-Braunstein 通用门 | Lloyd & Braunstein [quant-ph/9810082](https://arxiv.org/abs/quant-ph/9810082) |
| CV Gottesman-Knill | Bartlett et al. [quant-ph/0109047](https://arxiv.org/abs/quant-ph/0109047) |
| Stellar rank | Chabaud et al. [2005.11848](https://arxiv.org/abs/2005.11848) |
| GKP 纠错码 | Gottesman, Kitaev, Preskill [quant-ph/0008040](https://arxiv.org/abs/quant-ph/0008040) |
| Cat 码综述 | Mirrahimi et al. [1304.2800](https://arxiv.org/abs/1304.2800) |
| Hafnian 算法 | Björklund et al. [1805.12498](https://arxiv.org/abs/1805.12498) |
| Torontonian | Quesada et al. [1807.01639](https://arxiv.org/abs/1807.01639) |
| Loop Hafnian | [2108.01622](https://arxiv.org/abs/2108.01622) |
| GBS 经典模拟边界 | [1908.08068](https://arxiv.org/abs/1908.08068) |
| Serafini 教材 | *Quantum Continuous Variables* (CRC Press, 2017)

1. 写出 even cat 的 4 组件概念表，解释为什么前两个权重是实、后两个是复。
2. 比较同一 Cat：Fock 高 cutoff 的振幅 vs Bosonic 4 组件的 Wigner 切片，观察它们在干涉条纹上的对应关系。
3. 若 GKP 的齿展宽 \(\epsilon\) 减半，组件数大约翻几倍？
4. 解释为何光子损失在 Bosonic 下比 Fock 高效？
5. 什么时候 Bosonic 组件数会爆炸？这时候该换什么后端？

### 跨表示

6. 同一非高斯态（如 Cat \(\alpha=1\)）：Fock、Gaussian（会报错或给假结果）、Bosonic 各输出什么？
7. 用 Bosonic 的精度-代价旋钮（组件数 / 最小权重 / 合并阈值）调一次 Cat 的 Wigner 精度，观察组件数 vs 误差的关系。
