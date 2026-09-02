# 二维 GKP 码(平方格子)——组成、数学、逻辑比特、制备

> 连续变量 qumode 里编码一个逻辑 qubit 的位移码(GKP 码)。
> 本文档聚焦**单模平方格子(rectangular/square lattice)** GKP:这是 x、p 两个正交量都出现周期性峰结构的标准形式,是项目默认 `lattice="1d"`(只有 x 梳)的完整版。
> 与 `cvsim/bosonic/gkp.py` 现状的对照见 §7。

---

## 0. 一句话

一个 GKP 逻辑态 = **谐振子态在相空间 (x, p) 上具有晶格周期结构**,位置峰梳子 + 动量峰梳子由同一个态决定;逻辑 0 与逻辑 1 的区别 = **把梳子整体平移半个格点(逻辑 X)**,以及**在动量基上带 ±1 交替相位(逻辑 Z)**。

- **为什么 "只有 X 没 P" 是不完整的**:`lattice="1d"` 只画了 x 方向梳。但一个周期为 Δ 的位置梳,其动量空间分布(傅里叶)自动也是周期为 Δ 的梳(Poisson 求和)。所以完整的 GKP 天然 x、p 都有峰,不是两个独立结构,而是同一种波函数的两个视图。

---

## 1. 组成(物理结构)

平方格子 GKP 由三层结构堆出:

1. **格子(晶格)**:相空间二维晶格,周期常数 Δ。稳定子 = 两个正交位移算符
   - 稳定子 X:`q̂ → q̂ + Δ`(位置方向平移 Δ)
   - 稳定子 P:`p̂ → p̂ + Δ`(动量方向平移 Δ)

2. **逻辑码空间**:由上面两个稳定子同时固定的态(＋1 本征)→ 张成一个 2 维子空间 = **1 个逻辑 qubit**。

3. **逻辑基态**:该 2 维空间的基就是 `|0⟩_L` / `|1⟩_L`。

4. **有限能量包络**:理想 GKP 是无限能量的 δ 梳(不可实现)。物理上给每根峰裹一个高斯包络(峰宽由 `epsilon` 控制,即代码里每峰真空挤压),得到"近似 GKP"。

> 关键:这是**一个 qumode** 里的一维位置波动函数,其周期结构在相空间画出来是"二维格子"。所谓"二维"指 **相空间 (x,p) 的二维晶格**,不是两个 qumode。项目 `lattice="2d"` 当前实现与此有偏差,见 §7。

---

## 2. 数学表示

约定:ℏ=1,正则算符 `q̂, p̂`,满足 `[q̂,p̂]=i`;`q̂=(a+a†)/√2`。位移算符 `D(α)=e^{αa†−α*a}`。真空协方差 `V=I/2`(与项目 CONTEXT 一致)。

### 2.1 格常数

$$\Delta = \sqrt{2\pi}$$

(项目 `gkp.py` 中 `delta = np.sqrt(2*np.pi)`,一致。)

位置的半周期位移、逻辑算符里自然出现:

$$\frac{\Delta}{2}=\sqrt{\frac{\pi}{2}}$$

### 2.2 稳定子群

平方格子位移子群(稳定子):

$$S=\{\,D(n_1\,\Delta,\;n_2\,\Delta):n_1,n_2\in\mathbb{Z}\,\}$$

其中记法 `D(Δx, Δp)` = 位置平移 Δx、动量平移 Δp 的位移算符。等价写成:

$$\hat S_X=e^{i\,\Delta\,\hat p} \quad(\text{位置平移 }\Delta),\qquad \hat S_Z=e^{-i\,\Delta\,\hat q} \quad(\text{动量平移 }\Delta)$$

### 2.3 逻辑算符(Pauli 对)

- **逻辑 X**:位置方向平移半个格点 `Δ/2` → `0↔1`,对应位移算符 `D(√π/2)`。
- **逻辑 Z**:动量方向平移 `Δ/2` → 给位置基乘交替相位 `(−1)^n`。
- 二者反对易:`X̄ Z̄ = −Z̄ X̄`。

$$\bar X=D\!\Big(\frac{\Delta}{2}\Big),\qquad \bar Z=D\!\Big(i\frac{\Delta}{2}\Big)$$

### 2.4 位置基波函数(理想,无包络)

|0⟩ 峰在整数格点,|1⟩ 峰错开半格:

$$\langle q|0\rangle_L \propto \sum_{n\in\mathbb{Z}}\delta\!\big(q-n\Delta\big)$$

$$\langle q|1\rangle_L \propto \sum_{n\in\mathbb{Z}}\delta\!\big(q-(n+\tfrac12)\Delta\big)$$

等价算子形式(位置周期梳 = 平移不变线性组合):

$$|0\rangle_L \propto \sum_{n\in\mathbb{Z}}\;D\!\big(n\Delta\big)\,|q{=}0\rangle$$

### 2.5 动量基波函数(傅里叶,自动成梳)

因为 `Δ·(2π/Δ)=2π`,位置梳的傅里叶仍是周期 Δ 的梳。这是"x 和 p 都有峰"的来源:

$$\langle p|0\rangle_L \propto \sum_{n\in\mathbb{Z}}\delta\!\big(p-n\Delta\big)$$

$$\langle p|1\rangle_L \propto \sum_{n\in\mathbb{Z}}e^{-i\,(n\Delta)\tfrac{\Delta}{2}}\,\delta\!\big(p-n\Delta\big)=\sum_{n\in\mathbb{Z}}(-1)^{n}\,\delta\!\big(p-n\Delta\big)$$

**重点**:|0⟩ 和 |1⟩ 的动量峰**位置相同**(都在 `p=nΔ`),区别只在**交替符号数列 `(−1)^n`**。这就是动量方向的相位编码——单靠位置峰无法区分,必须看到 p 方向的这种相位结构,才叫"完整二维 GKP"。

### 2.6 有限能量(近似 GKP)

给理想梳乘高斯包络(峰序号 n 上包络,或相空间高斯调制):

$$|0\rangle_L^{\text{finite}} \;\propto\; e^{-\Delta^2 \hat n}\,|0\rangle_L^{\text{ideal}}$$

在 `gkp.py` 里体现为:峰权重 `c_k ∝ exp(−½πεk²)`,峰局域结构 `V=½diag(ε,1/ε)`(1d)。`ε→0` 极限即理想 GKP。

---

## 3. 如何表示逻辑比特

| 逻辑量 | 操作 | 作用 |
|---|---|---|
| 逻辑 0 | `|0⟩_L` | 位置峰在 `nΔ` |
| 逻辑 1 | `|1⟩_L` | 位置峰在 `(n+½)Δ`(整体平移 `Δ/2`) |
| **X̄** | 位移 `D(Δ/2)` | `|0⟩↔|1⟩` |
| **Z̄** | 动量位移 `D(iΔ/2)` | `|0⟩` 加 `(−1)^n` 交替相位 |
| **Ȳ** | `iX̄Z̄` | 组合 |
| 稳定子测量 | 位移 `Δ` | 提取 syndrome,纠位移噪声 |

**纠错直觉**:叠加到态上的任意位移噪声,只要小于 `Δ/2`,波峰就塌到"最近格点",把错误抹掉;稳定子(位移 Δ)正好量出"偏离量",据此回推校正。连续变量噪声被晶格"离散化"到最近格点 → 纠错。

---

## 4. Wigner 函数视角

GKP 的 Wigner 函数在相空间是**二维晶格化的峰阵列 + 峰间负值(干涉结构)**。负值是关键:高斯态 Wigner 恒非负,GKP 有负值 ⇒ **非高斯**,这直接决定了从真空制备必须走非高斯路线(§5)。

---

## 5. 从真空态制备 GKP 的方法

### 5.0 根本约束

**仅靠高斯操作(位移、压缩、分束、线性光学)从真空制备不了 GKP**。高斯操作把高斯态映射到高斯态(Wigner 恒正),而 GKP 非高斯。所以任何制备路线必须包含至少一个**非高斯步骤**:非高斯测量(光子数分辨探测、条件 homodyne)、光子非线性、或受控耗散。

### 5.1 测量制备(measurement-based, Flühmann–Home 线)

用 ancilla qumode + 纠缠移位门(CNOT/SUM 型)+ 半空间 homodyne 测量 + 条件位移反馈。

1. 把压缩真空/单模高斯态送进纠缠门,与 ancilla 纠缠;
2. homodyne 测 ancilla 一个正交量 → 投影出目标模的近似 GKP 网格态;
3. 根据测量结果做条件位移,把格子对正到逻辑格点。

优点:确定性概率叠加;缺点:需要高精度纠缠门与实时反馈。这是囚禁离子声子、超导微波腔平台的经典实现路线。

### 5.2 自举/迭代(pipelined improvement)

从"较差的近似 GKP"(例如大包络窄)出发,用"编码→纠错测量→条件位移"循环**逐轮收紧包络**,逼近理想 GKP。本质是 GKP 作为纠错码的"提高阶次"。

### 5.3 非高斯光学资源法(光子数分辨检测, PNR)

Eaton–Nehra–Pfister (arXiv:1903.01925):**不需要挤压资源**,只用 PNR 检测。

- **光子催化 / Fock 态滤波(FSF)**:相干态与单光子态经分束器干涉,PNR 探测,条件性地"过滤掉"特定 Fock 分量 → 生成大位移单光子态、大振幅猫态 `|cat±⟩∝|β⟩±|−β⟩`。
- **猫态干涉成 GKP**:两个猫态在平衡分束器干涉 + 同相 homodyne 测量 → 近似 GKP(文中给出 hex 版,平方格子同理)。
- 关键方程(FSF 滤波条件):对相干态做 `n` 光子过滤,系数含 `[n t²−r²(m−n+1)]`,在 `n=m(r²+1)` 时为零 → "梳状滤波"。

### 5.4 光子减法/光子增喵法

从压缩真空经**光子减法**(分束器 + PNR 检测)产生猫态,再干涉成形 → 近似 GKP。这是早于 PNR 过滤、已实验实现的路线(Ourjoumtsev 等的光猫态)。

### 5.5 耗散 / 测量无关制备(measurement-free, arXiv:1912.12645)

用受控耗散动力学(非高斯耗散 Lindblad)把一个普通态"冷却"到网格态;无需投影测量,可能是容错片上制备的候选。

### 5.6 平台化概述(哪类平台怎么做)

- **光学/自由空间**:5.3/5.4(猫态+干涉+PNR)。
- **囚禁离子声子、超导微波腔**:5.1/5.2(纠缠门+测量+反馈)。
- **片上/集成**:5.5(耗散)。

---

## 6. 参考来源

- D. Gottesman, A. Kitaev, J. Preskill, *Encoding a qubit in an oscillator*, Phys. Rev. A 64, 012310 (2001).
- K. Noh, V. V. Albert, L. Jiang, *Improved quantum capacity bounds... with GKP codes*, arXiv:1801.07271 (hex GKP 定义来源之一)。
- V. V. Albert et al., *Symmetries and conserved quantities in lattice-based CV QEC*, Phys. Rev. A 97, 032346 (2018).
- M. Eaton, R. Nehra, O. Pfister, *Experimental preparation of GKP states by photon-number-resolving detection*, arXiv:1903.01925 (PNR/FSF/猫态干涉制备)。
- *Measurement-free preparation of grid states*, arXiv:1912.12645 (耗散制备)。
- 稳定子定义权威速查:errorcorrectionzoo.org/c/gkp (single-mode GKP qudit-into-oscillator; stabilizer generators = oscillator displacement operators)。
- 多模格点解码背景:Lin, Chamberland, Noh, *Closest lattice point decoding for multimode GKP codes*, PRX Quantum 4, 040334 (2023)。

---

## 7. 与 `cvsim/bosonic/gkp.py` 现状对照

| 维度 | 标准单模平方 GKP | 项目现状 `gkp.py` |
|---|---|---|
| 峰结构 | 位置梳 + **动量梳(自动,带 `(−1)^n` 相位)** | `lattice="1d"` 只建 x 梳(默认);p 方向结构未展示 |
| 波函数 | 单模 1D 波动函数,相空间呈二维晶格 | `lattice="2d"` 把峰直接摆到 (x,p) 网格 `(kΔ,ℓΔ)` |
| 每峰局域 | 挤压真空 `V=½diag(ε,1/ε)`(纯态) | 1d 正确;2d 用 `V=½εI` **各向同性**(混合,非纯态,注释已标) |
| 逻辑 Z 相位 | 动量基交替 `(−1)^n` | 未实现(记忆里留了 `e^{iπkℓ}` 待办) |

**核心偏差(要接轨应修)**:标准单模平方 GKP 是**一个 qumode 的位置梳**,动量峰是傅里叶自动出现的,不需要把峰"平铺"到 (x,p) 二维网格上再乘各向同性包络。项目 `lattice="2d"` 把 `(x,p)` 当作两个独立峰坐标,更像**两个 qumode 的乘积态**,而非单模平方 GKP 的相空间晶格视图。若要正确实现单模二维 GKP,波函数应是位置基下的一维梳,且逻辑 Z 相位 `(−1)^n` 必须在动量基/复权重分量里编码。
