# 笔记对齐 · condition / sample / loss / Wigner

## Goal

理论笔记就地补齐与 U8 同一套物理的**纯公式 + 手算检查点**。人只读 MD 能推出关键数字为何对。**禁止**理论 MD 出现 `cvsim` / API / 源码路径。

## Background

- 代码：G/B condition·sample·loss；F 1 模 Kraus→ρ；Wigner G+B；UAT 7/7
- 笔记：有概念，缺可推演闭式
- 用户选 **A：就地补丁**；可搜专业资料

## Decisions

| # | 选择 |
|---|------|
| D0 | 纯理论；无包名/API/路径 |
| D1 | ħ=1，xxpp，`V_vac=I/2` |
| D2 | **A：就地补丁** 02 / 01 / 03 + 术语表 + 根 README |
| D3 | 04 只加交叉引用指针（不大扩） |
| D4 | 默认**只改 `.md`**；HTML 另说 |
| D5 | 每块：**闭式 + 1 手算检查点 + 诚实边界** |

## Literature anchors（正文可引用 arXiv/书，不绑软件）

| 主题 | 锚 |
|------|-----|
| 高斯测量/条件 | Weedbrook RMP 2012 / arXiv:1110.3234；Serafini *Quantum Continuous Variables* |
| 高斯通道 loss | 同 Weedbrook；`X=√T`, 真空噪声对齐 `V_vac=I/2` → `Y=(1-T)I/2` |
| 纯损耗 Kraus | BS 与 vac 环境 + 偏迹；数基 \(E_k\lvert n\rangle=\sqrt{C(n,k)}(\sqrt T)^{n-k}(\sqrt{1-T})^k\lvert n-k\rangle\) |
| Wigner 真空 | ħ=1：\(W(0,0)=1/\pi\)（勿与 ħ=2 文献的 \(2/\pi\) 混） |

## Requirements

### R1 · `02-Gaussian表示原理.md`

在 §4.1 附近扩：

1. **边缘** \(\mu=u\cdot\bar r\), \(\sigma^2=u^\top V u\), \(x_\phi=x\cos\phi+p\sin\phi\)
2. **理想条件**（不删模）：\(v=Vu\), \(\sigma=u^\top Vu\),  
   \(V'=V-vv^\top/\sigma\), \(\bar r'=\bar r+v(\mathrm{outcome}-\mu)/\sigma\)  
   检查点：真空 outcome \(o\) → \(\langle x\rangle\to o\)，测向 var→0
3. **采样**：outcome \(\sim\mathcal N(\mu,\sigma^2)\)；与条件分离（先抽再条件）
4. **§ 通道 loss**（可并 §3）：\(X=\sqrt T\), \(Y=(1-T)\frac12 I\) 作用在所选模；  
   检查点：相干 \(\langle n\rangle\to T\lvert\alpha\rvert^2\)

### R2 · `01-Fock表示原理.md`

1. **1 模纯损耗 Kraus** 公式 + \(\rho'=\sum_k E_k\rho E_k^\dagger\)
2. 检查点：\(\lvert1\rangle\) → \(\rho_{00}=1-T\), \(\rho_{11}=T\)
3. 诚实：截断；混合需密度矩阵；本笔记不展开 2 模 ρ

### R3 · `03-Bosonic表示原理.md` §5

1. **条件**：每组件同 G 仿射；\(\mu_k=u\cdot\bar r_k\) **可复**；  
   \(w_k\leftarrow w_k L(\mathrm{outcome};\mu_k,\sigma_k)\)，\(L\propto\sigma^{-1/2}\exp(-(o-\mu)^2/(2\sigma))\)，再 \(\sum w\to1\)
2. **采样（教学）**：仅**实中心**且权重正贡献的峰，按经典混合抽组件再高斯；**交叉不入池**
3. **Wigner**：单模网格；真空 \(1/\pi\)；复中心相位结构一句；odd cat \(W(0,0)<0\) 检查点
4. 诚实：复似然 = 教学闭式推广 ≠ 完整 Generaldyne 文献全式；采样 ≠ 精确干涉边缘

### R4 · `术语表.md`

测量/通道表加：条件 Homodyne、采样、纯损耗 \(T\)、Wigner 真空 \(1/\pi\)。

### R5 · 根 `README.md`

最小闭环加概念步（条件或损耗或 Wigner 负区），**仍不写 API**；工程验收链接可保留（已在工程段）。

### R6 · `04-...md`（轻）

相关节末 **一行指针**：「细节闭式见 01/02/03 补丁节」——不大段复制。

## Acceptance Criteria

- [x] **AC-N1** 02 条件/采样/loss + 检查点
- [x] **AC-N2** 01 Kraus + \|1⟩
- [x] **AC-N3** 03 条件/采样/Wigner
- [x] **AC-N4** 术语表 + 根 README
- [x] **AC-N5** 理论 MD 禁词仅根 README 工程段
- [x] **AC-N6** 未改代码

## Out of Scope

- 再生全部 HTML（除非用户另要求）
- 改代码；U9；跨表示 demo（策略 B）
- 完整 GKP Gram；Fock Wigner 全推

## Notes

- 公式与 Weedbrook/Serafini/标准 Kraus 对齐；笔记内部 ħ 自洽优先于抄 ħ=2 数
- 中文叙述 + 标准符号
