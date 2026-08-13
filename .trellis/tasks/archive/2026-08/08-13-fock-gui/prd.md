# PRD — Fock Lab GUI（同壳双后端）

> 需求与验收标准。技术设计见 `design.md`，执行清单见 `implement.md`。
> 决策来源：2026-08-13 grilling 十问 + Q11 初始态分支，用户逐题拍板。

## 1. 背景

Fock 模拟器（F1–F6 完成）可模拟高斯模拟器做不了的光学操作（Kerr/CZ/CX/PNR/非高斯源），输出为所有可能光量子态的**精确概率分布**与**采样结果**。高斯 Lab GUI（L0–L5）已有成熟电路编辑器。本次把 Lab GUI 扩展为 **Gaussian/Fock 同壳双后端**，复用电路构造方法，为 Fock 后端换血结果面板。

解锁依据：`vision-fock-simulator.md` §10 Q9（评估门槛 F3+ 已满足）；`vision-gaussian-lab-ui.md` §2.2 砍项表原文「Fock/Bosonic UI」条款显式 amend。

## 2. 需求（R）

| ID | 需求 |
|----|------|
| **R1** | Lab GUI 顶栏加 **backend 切换**（Gaussian/Fock）；电路编辑器（staff 五线谱、拖拽、参数浮层、撤销、Save/Load）两后端共用，零复制 |
| **R2** | 托盘 **per-backend 分表**。Fock 托盘：门 `displace/phase/squeeze/kerr/beamsplitter/two_mode_squeeze/mach_zehnder/cz/cx`；通道 `loss/amplifier/phase_noise`；测量 `measure_pnr/measure_homodyne/measure_heterodyne`。**不放** `interferometer/apply_unitary`（矩阵编辑器 = 通用 IDE，反白名单教义，defer） |
| **R3** | Fock 结果面板 = **双卡并列**：单模 Wigner 热图（复用现有组件，`wigner_grid` 已支持 Fock）+ PNR 概率分布柱状图（`pnrd_probs`，共用 mode 选择器）。**加 joint 2 模分布 2D heatmap**（选 2 模时显示，≤30×30 格） |
| **R4** | **采样对照**：Measure once = 单次 PNR 结果向量 + seed 显示（复现键）；**Batch 采样固定 1000 shots** = 累积直方图双色叠画在理论分布柱/heatmap 上（采样频率 vs 精确概率收敛对照） |
| **R5** | **截断护栏**：全局 cutoff 滑块（1..30，默认 10）+ per-mode 高级覆盖；态摘要卡加**截断泄漏仪表**（`truncation_leakage`，leakage>1% 变黄）；cutoff>20 显示 Wigner 慢速提示 |
| **R6** | **测量语义对齐 FockCircuit**：测量节点按序执行 condition 链（坍缩+移除模）；结果卡显示 outcomes 向量 + seed；剩余模自动切条件态视图，诚实显示（singular 不造假数据） |
| **R7** | **初始态**（Q11 b）：`FockCircuit` 支持 per-mode Fock 数态初始态（`initial=[n0,n1,...]`，真空缺省 = 旧文件零破坏）；**cat 不加源**——教学剧本用 displace+Kerr(π/2) 协议构建（对齐高斯「纠缠由门构建」教义）；coherent/squeezed 照旧门可达，不设源节点 |
| **R8** | **兼容**：`"backend"` 字段缺省 `gaussian`——所有旧 `circuit_v1.json` 原样可跑；Save/Load 持久化 backend/initial/cutoffs |
| **R9** | **v0 无扫描面板**（scan 进 P1，第一候选 = cutoff 收敛曲线，组件复用 `/scan` 面板） |

## 3. 验收标准（A）

### A1 主剧本 — HOM 聚束（无手写 Python，≤5 分钟）

1. 冷启动 → 切 backend=Fock → 加 2 模 → 设初始态 `[1,1]`
2. 拖 `beamsplitter(θ=π/4)` → joint 2D heatmap 显示 **P(1,1)≈0**（双光子聚束）
3. 点 Batch 1000 → 直方图叠画，采样频率与理论分布一致（统计 tol）
4. 拧 cutoff → 泄漏仪表变化；泄漏 >1% 变黄；cutoff>20 出慢速提示
5. Save → 刷新 → Load → 拓扑/backend/initial/读数一致

### A2 次剧本 — Kerr 猫态

displace(α≈√2) + kerr(χ=π/2) → Wigner 卡可见双峰猫态（截断收敛叙事）

### A3 测量剧本

PNR 测量节点 → outcomes 向量 + seed；同 seed 复现一致；被测模移除后剩余模条件态诚实显示

### A4 兼容回归

- 旧高斯 JSON（无 `backend` 字段）→ 原样运行，行为不变
- 后端无 `cvsim.*._*` private import；无新依赖；无 console.log/debugger 残留
- `pytest tests` 全套绿 + `node --test` 全套绿
- Golden fixture：Fock JSON → run 结果与等价脚本 `FockCircuit` 一致（atol 约定）

## 4. 非目标（v0 明确不做）

- Bosonic 后端；scan 面板；batch shots 可调（固定 1000）；矩阵编辑器；多用户/云端；`FockCircuit` 之外的第二套执行路径（lab 不得手写物理）
