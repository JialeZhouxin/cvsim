# 01 · Fock 表示原理

> 截断 Fock 空间 · 算符矩阵 · 精确测量  
> \(\hbar=1\) 正文；符号见 [术语表](./术语表.md)

---

## §1 Fock 表示的物理图像

### 1.1 什么是 Fock 表示

Fock 表示 = 在光子数基上把无穷维 Hilbert 空间**砍成有限维向量**：

\[
\lvert\psi\rangle=\sum_{n_1=0}^{N-1}\cdots\sum_{n_m=0}^{N-1}
c_{n_1\ldots n_m}\lvert n_1\ldots n_m\rangle.
\]

- **是 CV**：物理仍是玻色模  
- **离散的是基标签 \(n\)**，相空间仍连续  
- **cutoff \(N\)**：砍掉高阶激发

### 1.2 物理图像：量子谐振子阶梯

```text
能量      波函数形状
n=3 ───  三阶厄米，三个节点
n=2 ───  二阶，两个节点
n=1 ───  一阶，一个节点（奇）
n=0 ───  基态，高斯波包（偶）
```

- \(\lvert 0\rangle\) = 真空涨落高斯波包  
- \(n\) = 谐振子第 \(n\) 激发级  
- 强位移 / 强挤压把概率推到外围 → 需更高 cutoff

### 1.3 三表示定位

```text
        相同物理：单模 squeezing
         │
  Fock          Gaussian        Bosonic
 cutoff=N      V, r̄            多组件
 精确但贵      高斯族内精确      Cat/GKP 友好
```

Fock 独占：**精确光子数概率**、**任意门（Kerr）**、**部分模测量直接塌缩**。

---

## §2 态与存储

### 2.1 两种模式

| 模式 | 稀疏占有数 | 完整振幅张量 |
|------|-----------|--------------|
| 存储 | 各模光子数向量 | \(N^m\) 张量 |
| 用途 | 初态构造 | 演化 |
| 例 | \([1,0,1]\) | 张量积振幅 |

### 2.2 密度矩阵

纯态 → 形状 \((\mathrm{batch},[N]\times m)\)。  
密度矩阵 → 额外共轭维：\(|\psi\rangle\langle\psi|\) 重塑为 \(2m\) 阶截断张量。

损失信道常在密度矩阵上走 Kraus。

### 2.3 MPS

弱纠缠多模可用矩阵积态：存储从 \(N^m\) 降到 \(O(m\cdot N\cdot\chi^2)\)。  
纠缠越强，bond dimension \(\chi\) 越大。

### 2.4 维数爆炸

\[
\text{存储量}=N^m
\]

| \(m\backslash N\) | 5 | 10 | 20 |
|-------------------|----|-----|-----|
| 4 | 625 | \(10^4\) | \(1.6\times10^5\) |
| 8 | \(3.9\times10^5\) | \(10^8\) | \(2.5\times10^{10}\) |
| 12 | \(2.4\times10^8\) | \(10^{12}\) | \(4\times10^{15}\) |

8 模、\(N>12\) 时常爆显存。

---

## §3 门操作

### 3.1 通用框架

\[
|\psi'\rangle=U_{\mathrm{gate}}|\psi\rangle,\qquad
\rho'=U\rho U^\dagger.
\]

截断空间中的幺正（或等距）矩阵。

### 3.2 阶梯算符

cutoff \(=4\)：

\[
a=\begin{pmatrix}
0&1&0&0\\
0&0&\sqrt2&0\\
0&0&0&\sqrt3\\
0&0&0&0
\end{pmatrix}.
\]

**截断伪影根因：** \(a^\dagger\lvert N-1\rangle=\sqrt N\lvert N\rangle\) 被丢，\([a,a^\dagger]\) 末对角不是 1。

### 3.3 PhaseShift

\[
PS(\theta)\lvert n\rangle=e^{in\theta}\lvert n\rangle
\]

Fock 基对角；相空间绕原点转，高 \(n\) 转得更快。

### 3.4 BeamSplitter

BS 在 Fock 基不对角，矩阵元由辐射跃迁强度**递推**填充，复杂度 \(O(N^4)\)（两模四指标）。

物理：从 \(|m,n\rangle\) 打散到各种光子数分配。

### 3.5 位移

\[
D(\alpha)=e^{\alpha a^\dagger-\alpha^* a}.
\]

截断下用**矩阵指数**。Provazník 2022 [2202.07332](https://arxiv.org/abs/2202.07332)：直接截幂级数易伪影。

### 3.6 挤压

\[
S(r)=\exp\!\left[\tfrac12(r^*a^2-r a^{\dagger2})\right],\qquad
\langle n\rangle=\sinh^2 r.
\]

| \(r\) | \(\langle n\rangle\) | 推荐最小 cutoff |
|------|----------------------|-----------------|
| 0.5 | 0.27 | 8 |
| 1.0 | 1.38 | 15 |
| 1.5 | 4.53 | 25+ |

### 3.7 Kerr（非高斯）

\[
K(\chi)=e^{i\chi(a^\dagger a)^2}
\]

Fock 基对角，Gaussian / Bosonic 不自然。

---

## §4 测量

- **PNRD：** \(|c_{n_1\ldots n_m}|^2\) 直接读  
- **部分模测量：** 切对应下标，其余模条件更新  
- **Homodyne：** 构造投影到无限挤压真空（比高斯表示贵）

---

## §4.1 纯损耗（1 模 · Kraus）

物理同高斯：透过率 \(T\) 的 BS 耦合真空环境，再偏迹环境。  
Fock 侧：纯态经损耗一般变**混合**，需密度矩阵 \(\rho\)。

数基 Kraus 算符（\(k=0,1,\ldots\)；截断下 \(n,n-k<N\)）：

\[
E_k\lvert n\rangle
=
\sqrt{\binom{n}{k}}
(\sqrt{T})^{n-k}
(\sqrt{1-T})^{k}
\lvert n-k\rangle.
\]

\[
\rho' = \sum_k E_k\,\rho\,E_k^\dagger.
\]

**检查点：** 初态 \(\lvert 1\rangle\)（\(\rho=\lvert1\rangle\langle1\rvert\)）

\[
\rho'_{00}=1-T,\qquad
\rho'_{11}=T,\qquad
\text{非对角}\approx 0.
\]

**检查点：** 相干态（高 cutoff）\(\langle n\rangle\to T\lvert\alpha\rvert^2\)，与高斯通道同趋势。

**诚实边界：** 截断砍掉 \(n\ge N\) 的泄漏；本笔记不展开多模 \(\rho\) 的完整张量更新。

---

## §5 数值与选型

### 5.1 Cutoff 经验

```text
位移 |α|:  N > |α|² + 5√|α|²
挤压 r:    N > 3·sinh²(r) + 10
```

更稳：扫 \(N=10,15,20,25\)，观测量平台化。

### 5.2 跨表示验证

同参挤压：Fock 平均光子 vs 理论 \(\sinh^2 r\)。  
小挤压低阶矩应逼近 Gaussian；范数 \(<1\) 说明漏到 cutoff 外。

### 5.3 选型

```text
用 Fock 当:
├─ m ≤ 6
├─ 精确光子数分布
├─ Kerr / 任意非高斯门
└─ 部分模直接测量

改 Gaussian: 纯高斯 + 大 m
改 Bosonic:  Cat/GKP 峰结构清晰
```

---

## 练习

1. 单模 cutoff=5，\(D(2)\) 后 \(\sum_{n<5}|c_n|^2\) 是多少？漏到哪？  
2. 同 \(S(r=0.8)\)，cutoff 6 vs 20，比范数。  
3. 为何 BS 的 Fock 矩阵是 \(O(N^4)\) 不是 \(O(N^2)\)？  
4. 解释 \([a,a^\dagger]\) 在截断末对角为何偏离 1。

---

## 阅读顺序

[00-CV核心原理](./00-CV核心原理.md) → 本篇 → [02-Gaussian](./02-Gaussian表示原理.md) → [03-Bosonic](./03-Bosonic表示原理.md)

```text
Fock 精密 (N^m) → Gaussian 高效 (m²) → Bosonic 折中 (K·m²)
```

---

## 文献

- **截断误差**：Provazník et al. [2202.07332](https://arxiv.org/abs/2202.07332)  
- **Fock 与 Wigner**：Cahill & Glauber, Phys. Rev. 177, 1857 (1969)
