# 三表示光量子模拟器

## Goal

把 `cv-photonic-notes` 纯理论笔记落地为可运行的三个 CV 光量子模拟器：**Gaussian → Fock → Bosonic**（串行）。  
按笔记四问实现最小可验证闭环，并做跨表示对照。代码与理论笔记分离：笔记保持纯物理，实现可引用笔记公式。

## Background

- 仓库现状：理论 MD/HTML 齐全，**无模拟器源码**。
- 三表示同一物理，差结构与代价：

| 表示 | 对象 | 代价 | 笔记 |
|------|------|------|------|
| Gaussian | \(V,\bar r\) | \(O(m^2)\) | `02`, `04` 中篇 |
| Fock | 截断振幅 | \(N^m\) | `01`, `04` 上篇 |
| Bosonic | \(\{(V_k,\bar r_k,w_k)\}\) | \(O(K·m^2)\) | `03`, `04` 下篇 |

- 物理约定：\(\hbar=1\)，真空 \(V=I/2\)；正交序实现固定一套（推荐 **xxpp**，与笔记辛矩阵表一致）。
- 理论源：README 最小闭环；`04` 四问与公式。

## Decisions

| # | 决策 | 选择 |
|---|------|------|
| D1 | 交付策略 | 串行：Gaussian 最小闭环 → Fock 对照 → Bosonic cat |
| D2 | 语言/依赖 | Python + uv；**numpy + scipy**；禁止量子库依赖 |
| D3 | 测量范围 | 观测量优先（\(\det V\)、\(\langle n\rangle\)、权重；Wigner 可选）；无 Homodyne/PNRD/Threshold |
| D4 | 验收门槛 | **README 四步硬门槛**（见 Acceptance） |

## Requirements

- **R1 串行交付**  
  M1 Gaussian → M2 Fock → M3 Bosonic；前一里程碑验收通过再开下一里程碑。

- **R2 实现栈**  
  Python + uv 虚拟环境；依赖上限 numpy、scipy；不依赖 DeepQuantum 或其它量子计算库。

- **R3 物理约定**  
  \(\hbar=1\)；真空 \(V_{\mathrm{vac}}=I/2\)、\(\bar r=0\)；全库统一正交序（默认 xxpp）；文档写清序与 \(\Omega\)。

- **R4 Gaussian（M1）**  
  态：\((V,\bar r)\)；门：至少单模挤压 \(S(r)\)（仿射辛更新 \(V\mapsto SVS^T\)，\(\bar r\mapsto S\bar r+d\)）；观测量：\(\det V\)、平均光子 \(\langle n\rangle\)。

- **R5 Fock（M2）**  
  截断振幅态；至少实现与 M1 同电路的单模挤压；可扫 cutoff；\(\langle n\rangle\) 随 cutoff 逼近 Gaussian / 解析 \(\sinh^2 r\)。

- **R6 Bosonic（M3）**  
  高斯组件列表 \(\{(V_k,\bar r_k,w_k)\}\)；构造小振幅 even/odd cat（4 组件级）；可检权重/归一相关量；Wigner 可选。

- **R7 代码与笔记隔离**  
  模拟器代码放独立目录（如 `sim/` 或 `cvsim/`，design 定名）；**不**向笔记 MD 写库/API 绑定。

- **R8 可验证**  
  每个里程碑至少一条可自动跑的数值检查（assert / 小脚本），对应 Acceptance。

## Acceptance Criteria

### M1 · Gaussian

- [x] AC1.1 真空 → 单模挤压 \(S(r)\) 后可打印 \(V\)
- [x] AC1.2 纯态挤压：\(|\det V - 1/4|\) 在数值容差内
- [x] AC1.3 \(|\langle n\rangle - \sinh^2 r|\) 在数值容差内（解析对照）

### M2 · Fock

- [x] AC2.1 同参数单模挤压可算 \(\langle n\rangle\)
- [x] AC2.2 cutoff 扫描下 \(\langle n\rangle\) 逼近 \(\sinh^2 r\)
- [x] AC2.3 高 cutoff 投影到低 N 可见概率亏损

### M3 · Bosonic

- [x] AC3.1 小振幅 cat 四组件（对角 + 交叉）
- [x] AC3.2 权重 ∑w=1 可检
- [ ] AC3.3（可选加分）单模 Wigner 网格 — 未做

### 总验收

- [x] AC0 README 最小闭环 1–4 有 demo（4=权重；Wigner 可选）
- [x] AC0.1 理论笔记未绑库/API

## Out of Scope

- 笔记 MD 绑定 DeepQuantum / 其它库 API
- Homodyne / PNRD / Threshold 与生产级 Hafnian/Torontonian
- 完整多模门表、GBS 端到端、Kerr 生产用例
- GPU / 分布式 / UI；MVP 内 Numba/JAX/CuPy
- GKP 完整实现（可后续任务）

## Open Questions

无阻塞项。实现期细节（目录名、测试 runner、容差数值）由 `design.md` / `implement.md` 定，不改 PRD 决策。
