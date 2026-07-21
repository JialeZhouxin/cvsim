# CV 光量子模拟 · 自学笔记

> 定位：个人理论主线笔记（非工程手册）  
> 约定：正文公式默认 **论文常见 \(\hbar=1\)**；正交序见 [术语表](./术语表.md)

---

## 阅读顺序

| 顺序 | 文件 | 作用 |
|------|------|------|
| 0 | [术语表.md](./术语表.md) | 符号、\(\hbar\)、正交序、换算 |
| 1 | [00-CV核心原理.md](./00-CV核心原理.md) | 物理图像、三表示总览、选型、统一约定 |
| 2 | [02-Gaussian表示原理.md](./02-Gaussian表示原理.md) | **优先**。辛几何 = 精髓主线 |
| 3 | [01-Fock表示原理.md](./01-Fock表示原理.md) | 截断、通用但贵 |
| 4 | [04-Fock四问详解与Gaussian模拟器原理.md](./04-Fock四问详解与Gaussian模拟器原理.md) | **三表示模拟器对照**（纯原理） |
| 5 | [03-Bosonic表示原理.md](./03-Bosonic表示原理.md) | （原文，建议与 04 的 Bosonic 节对照） |

建议：核心 → 术语表扫一遍 → **Gaussian 专篇吃透** → Fock → Bosonic。  
不要先从 Fock 矩阵堆砌开始。

---

## 三表示一句话

| 表示 | 存什么 | 何时用 |
|------|--------|--------|
| Fock | 截断光子数振幅 | 小系统、非高斯门、精确 Fock 概率 |
| Gaussian | 协方差 \(V\) + 位移 \(\bar r\) | 大规模高斯演化、GBS |
| Bosonic | \(\{(V_k,\bar r_k,w_k)\}\) | Cat/GKP、高斯叠加非高斯态 |

三者都是 **CV（连续变量 / 玻色模）**；差别是表示，不是物理种类。

---

## 核心文献入口

| 主题 | 文献 |
|------|------|
| CV 总览 | Braunstein & van Loock, [quant-ph/0410100](https://arxiv.org/abs/quant-ph/0410100) |
| 高斯量子信息 | Weedbrook et al., RMP 2012, [arXiv:1110.3234](https://arxiv.org/abs/1110.3234) |
| Fock 截断数值 | Provazník et al., [2202.07332](https://arxiv.org/abs/2202.07332) |
| Torontonian / threshold GBS | Quesada et al., [1807.01639](https://arxiv.org/abs/1807.01639) |
| Hafnian 算法 | Björklund et al., [1805.12498](https://arxiv.org/abs/1805.12498) |
| GBS 经典模拟 | Quesada & Arrazola, [1908.08068](https://arxiv.org/abs/1908.08068) |
| Photonic 软件栈 | Piquasso, [2403.04006](https://arxiv.org/abs/2403.04006) |
| Cat 的高斯分解 | [2103.05530](https://arxiv.org/abs/2103.05530) §IV B |

---

## 最小闭环实验（全笔记共用）

1. 手写 / numpy：真空 → 单模挤压 → 打印 \(V\)  
2. 同一参数下核对 \(\det V\)、平均光子 \(\sinh^2 r\)  
3. 同一电路用 Fock 扫 cutoff，看何时逼近高斯结果  
4. 建一个小振幅 cat（高斯叠加），画 Wigner 或看组件权重  
5. **通道与测量检查点**（公式见 01/02/03）：  
   - 真空 Homodyne 条件：结果 \(o\) 后 \(\langle x\rangle\to o\)、测向 var\(\to0\)  
   - 相干/单光子损耗：\(\langle n\rangle\to T|\alpha|^2\) 或 \(\lvert1\rangle\to\rho_{00}=1-T,\rho_{11}=T\)  
   - 真空 Wigner：\(W(0,0)=1/\pi\)；odd cat 可有 \(W(0,0)<0\)

工程落地与**最终用户验收**（目标 / U1–U5+U7+U8 / 能力矩阵）见：
[`cvsim/README.md`](./cvsim/README.md) · [`cvsim/USER_ACCEPTANCE.md`](./cvsim/USER_ACCEPTANCE.md) · `python -m cvsim.demos.user_acceptance`

---

## 目录结构

cv-photonic-notes/
├── README.md
├── 术语表.md
├── 00-CV核心原理.md
├── 01-Fock表示原理.md
├── 02-Gaussian表示原理.md
├── 03-Bosonic表示原理.md
└── 04-Fock四问详解与Gaussian模拟器原理.md

*公式主约定 \(\hbar=1\)。*
