# 高斯模拟器相关文献资料

> 检索日期：2026-08-03 · 主题：Gaussian 态/GBS 的经典模拟、仿真软件、理论基础
> 用途：cvsim 库（Gaussian 表示 + 辛矩阵层）理论对照与算法参考

## 一、奠基性综述（理论地基）

| # | 文献 | 内容要点 |
|---|------|----------|
| 1 | **Weedbrook et al., "Gaussian quantum information", Rev. Mod. Phys. 84, 621 (2012)**<br>arXiv:1110.3234 · DOI: 10.1103/RevModPhys.84.621 | CV 量子信息权威综述。相空间表示、高斯态（真空/热态/压缩态）、高斯酉、协方差矩阵演化、高斯测量、纠缠判定（PPT 判据）等全部基础，cvsim 的 Gaussian 表示层公式基本都出自这里。**首选对照文献。** |
| 2 | **A. Serafini, "Quantum Continuous Variables: A Primer of Theoretical Methods", CRC Press (2017)** | 教科书，体系化讲解高斯态与 CV 量子信息，比综述更系统，适合逐章对照。cvsim 的辛矩阵层（xxpp 约定、辛性保持）与其符号约定基本一致。 |
| 3 | **G. S. Agarwal (Carnaval) 等高斯统计综述（见各论文引用链）** | 相空间方法与高斯态统计的开山脉络，间接引用。 |

## 二、GBS 与采样问题（Hafnian 复杂度核心）

| # | 文献 | 内容要点 |
|---|------|----------|
| 4 | **C. S. Hamilton et al., "Gaussian boson sampling", PRL 119, 170501 (2017)**<br>arXiv:1612.01199 | GBS 协议原始论文：用压缩真空态替代单光子源，概率由散射矩阵的 **Hafnian** 给出（对应 BS 的 Permanent），确立 #P 复杂度论证。GBS 一切讨论的起点。 |
| 5 | **N. Quesada & J. M. Arrazola, "Classical simulation of Gaussian boson sampling", arXiv:2001.11984** | GBS 经典模拟的关键文献：用协方差矩阵 + 相空间方法做经典模拟的算法框架，讨论噪声（光子损失）如何让 GBS 变得经典可模拟。cvsim 若加采样功能，此为其算法蓝图。 |
| 6 | **A. S. Dellios, M. D. Reid, P. D. Drummond, "Simulating Gaussian Boson Sampling Quantum Computers", AAPPS Bulletin 33, 11 (2023)**<br>arXiv:2303.04675 | 2023 年综述：用正 P 表示（positive-P）等相空间方法模拟实验 GBS 网络，含噪声/热化压缩态情形，用于验证量子优越性声明。与 cvsim 的相空间视角最贴近。 |
| 7 | **J. Vinther, M. J. Kastoryano, "Variational tensor network simulation of Gaussian boson sampling and beyond", PRA 112, 022605 (2025)**<br>arXiv:2410.18740 | 变分张量网络模拟 GBS（含非高斯采样），把采样问题化为少数体哈密顿量基态问题。非高斯扩展方向的参考。 |
| 8 | **L. Bianchi et al., "Unified boson sampling", arXiv:2509.02058 (2025)** | 统一 scattershot BS 与 GBS 的方案，生成函数形式主义，混合 DV/CV 平台的采样协议。2025 新动向。 |

## 三、实验实现与优越性验证

| # | 文献 | 内容要点 |
|---|------|----------|
| 9 | **Zhong et al., "Quantum computational advantage using photons", Science 370, 1460 (2020)** | 九章（Jiuzhang）光量子计算原型，76 光子 GBS，首个光子平台量子优越性声明。 |
| 10 | **Zhong et al., "Phase-programmable Gaussian boson sampling using stimulated squeezed light", PRL 127, 180502 (2021)** | 九章 2.0：可编程相位、144 模、量子优越性升级版实验。 |
| 11 | **L. S. Madsen et al., "Quantum computational advantage with a programmable photonic processor", Nature 606, 75 (2022)** | Xanadu Borealis：216 压缩态模、可编程干涉仪，GBS 优越性的代表性实验。 |

## 四、仿真软件与库（cvsim 对标对象）

| # | 文献/软件 | 内容要点 |
|---|----------|----------|
| 12 | **N. Killoran et al., "Strawberry Fields: A Software Platform for Photonic Quantum Computing", Quantum 3, 129 (2019)**<br>arXiv:1804.03159 | Xanadu 开源的 CV 光量子全栈库（Python + Blackbird 语言），三后端（Fock/Gaussian/可微分）。GBS 采样、变分 CV 电路等范式算法样例齐全。**cvsim 的 Gaussian 表示与采样功能对标主参照。** |
| 13 | **The Walrus 库**（https://github.com/XanaduAI/thewalrus） | Strawberry Fields 的底层数值库：Hafnian/Permanent 高效计算、GBS 采样优化算法。cvsim 未来若做 GBS 采样/Hafnian，直接参考其算法（纯 C++/numba 加速，Python 接口）。 |
| 14 | **B. Bourdoncle et al. / Piquasso**（arXiv:2210.08730 附近） | 匈牙利 Wigner 中心的光量子模拟平台，GPU 加速（cuQuantum 后端），CV+部分非高斯。硬件加速方向参考。 |
| 15 | **QuTiP, Perceval, QuantumOptics.jl 等**（见下方综述 #16） | 通用量子模拟生态，Perceval 主打离散变量光子线路，非 CV 主线，仅作生态对照。 |

## 五、2025 年新综述（软件生态全景）

| # | 文献 | 内容要点 |
|---|------|----------|
| 16 | **D. D. K. Wayo et al., "Gaussian Models to Non-Gaussian Realms of Quantum Photonic Simulators", arXiv:2502.05245 (2025)** | 最新光量子模拟器综述：Gaussian→非 Gaussian 过渡、协方差矩阵与相空间表示、张量网络 + GPU 加速、噪声建模（光子损失/暗计数）、对比 Strawberry Fields / Piquasso / QuTiP / Perceval / QuantumOptics.jl。**读这一篇即可快速建立全景。** |

## 六、GBS 应用方向（图论/化学）

| # | 文献 | 内容要点 |
|---|------|----------|
| 17 | **J. M. Arrazola et al., "Quantum approximate optimization with Gaussian boson sampling", PRA 98, 032312 (2018)**<br>arXiv:1712.05748 | GBS 最大团问题启发式算法，图论编码方式（邻接矩阵 → 压缩参数）。 |
| 18 | **T. R. Bromley et al., "Applications of near-term photonic quantum computers: software and algorithms", Quantum 4, 311 (2020)**<br>arXiv:1912.07634 | Strawberry Fields apps 层的 GBS 应用综述：图同构、点云配准、分子振动谱、最大团等，附代码示例（sample/postselect 模块）。 |
| 19 | **S. Bagheri Novir, "Applications of Gaussian Boson Sampling to Solve Some Chemistry Problems", Quantum Rep. 7, 56 (2025)** | 2025 年最新 GBS 化学应用综述：分子对接（docking）、分子振动，图→GBS 编码，NISQ 适配讨论。 |

## 阅读顺序建议

1. **先读 #1（Weedbrook 2012）** 对应部分（第 II 章：相空间/高斯态/高斯酉）——cvsim 公式的理论来源
2. **再读 #16（Wayo 2025 综述）** ——软件生态全景 + 模拟方法分类
3. **GBS 专项：#4（Hamilton 2017）→ #5（Quesada 2020 经典模拟）→ #12/#13（软件与数值库）**
4. **实验对照：#9–#11**（九章 1.0/2.0、Borealis）

## 与 cvsim 现状的差距对照

| cvsim 能力 | 对应文献 | 待补 |
|------------|----------|------|
| Gaussian 表示（协方差矩阵演化、辛性保持） | #1, #2 | 已覆盖 |
| 真空回归验证、解析对照 | #1 | 已覆盖 |
| Fock 1-2 模表示 | #12（SF 的 Fock 后端） | 可扩展多模 |
| GBS 采样 | #4, #5, #13 | **未实现**（Hafnian 是核心缺口） |
| 噪声模型（损耗/热化） | #5, #6 | 未实现 |
| 非高斯（张量网络/变分） | #7, #16 | 未实现（远期） |

---

*注：条目 #9–#11 实验论文、#4 等为常识性确认；检索到的 arXiv 链接与年份以搜索结果为准确认。详细摘要可在 arXiv / DOI 处获取原文。*
