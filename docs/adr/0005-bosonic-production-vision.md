# ADR-0005: Bosonic 生产级模拟器愿景

- 日期: 2026-08-13
- 状态: 已接受（grill Q1–Q13 锁定）
- 前置: ADR-0001（模块边界）、ADR-0003（circuit_v1 IR）、ADR-0004（circuit_common 共享框架）

## 背景

Gaussian 生产级已完成（Phase 0–5），Fock 生产级已完成（F1–F7）。Bosonic 仍是
教学 MVP（`cvsim/bosonic`：state/cat/gkp/gates/channels/observables，单模
homodyne 教学切）。Gaussian 愿景 §1.2 原话："Full product includes Fock,
Bosonic (cat/GKP), and bridges" —— 第三个生产级 peer 是既定方向，本次 grill
锁定其愿景（`docs/vision-bosonic-simulator.md`）。

主舞台（用户拍板）：**GKP 量子纠错教学**。前端复用 Gaussian/Fock 同壳 GUI
做教学展示；后端是生产级模拟器。教学产出三件套：保真度 sweep 曲线 + Wigner
演化视图 + 协议因果链（分步执行）。

## 决策

1. **支柱（全要）**：C1 能力完备（门/通道/测量/DSL 对齐 Gaussian）、C2 组件
   工程（合并/截断/下溢/归一化 + 组件截断泄漏度量）、C3 测量精确化（homodyne
   教学混合 → 精确边缘分布 + 精确条件化）、C4 对账信任（分层对账）。
2. **规模锚 A1**：单模生产级（K ≤ 几百，ε ≥ 0.05，B2 校准）；架构按任意 m 写；
   双模（K² 组件爆炸）进 open questions，无场景驱动不做。
3. **对账 R1（分层）**：层 1 = 退化情形对解析/Fock 闭式（K=1 即 Gaussian、
   小 cat 4 组件、coherent/thermal 单组件）atol 1e-7 硬约束；层 2 = GKP
   内禀恒等式 + Fock 高 cutoff 数值互证。**诚实标注：GKP 无解析基准，层 2
   是互证不是解析对账**。否决：只对退化情形（R2，生产级名不副实）、等外部
   golden（R3，SF 无成熟 Bosonic GKP 表示，等不到）。
4. **协议 P1：积木进库，协议进教程**。GKP 纠错循环（测量→反馈→恢复）写教程/
   GUI 剧本，不做库 API。对齐 Fock 立场"algorithms are users' business"。
5. **测量面 M1**：homodyne（精确化）+ heterodyne + threshold；threshold 复用
   Gaussian 已锁定语义（outcome-only，无态更新）。B9 Phase 1 解锁单模边际
   `pnr_probs` 与有限 cutoff 内的 `pnr_sample`；PNR 条件化、联合多模 PNR 仍延期。
6. **电路 B1：BosonicCircuit = circuit_common 第三消费者**。任意 m、组件式
   执行（每 op 逐组件仿射 + 权重规则）、to_ir/from_ir 对齐 Fock F3。
   ADR-0004 的泛化承诺兑现（Fock 是第二消费者）。AD（可微）进 open questions。
7. **GUI G1（三件套）**：同壳第三后端（`backend="bosonic"`）+ 结果面板 =
   Wigner 演化视图 + 保真度 sweep 曲线 + **分步执行**（纠错链每步条件化后
   中间态可查 —— 纯新增 UI 能力，Fock F7 没有，治"流程黑盒"痛）。
8. **路线 B0–B7**：B0 约定冻结 → B1 能力完备 → B2 组件工程 → B3 测量精确化 →
   B4 对账套件 → B5 BosonicCircuit → B6 GUI → B7 桥+教程。顺序认（B5 插
   B4 后，对账要有电路才完整）。
9. **非目标**：Kerr/任意非高斯门的组件式表示（选型表：转 Fock）；协议库；
   多模生产级；PNR 条件化/联合多模 PNR；AD；tensor networks；云服务。

## 权衡

- 曾考虑只精确化 homodyne、heterodyne/threshold defer（M2）：被否。C1
  "对齐 Gaussian 全集"缺两块，生产级不完整。
- 曾考虑不造 DSL、GUI 用脚本直调积木（B2）：被否。前端复用壳要求电路编辑器
  接 circuit_v1，不造 DSL 壳就断了。
- 曾考虑把全部 PNR 能力一次性做完（M3）：被否。B9 先交付可验证的单模边际
  概率/采样；条件化和联合多模路径仍需独立表示与规模设计。

## 后果

- 正面：三表示生产级齐平，Gaussian 愿景 §1.2 承诺兑现；GKP 纠错教学有
  fast+accurate 后端 + 现成 GUI 壳。
- 负面：B2 组件工程（合并/截断泄漏度量）是全新暗活，无先例可抄；B3 homodyne
  精确采样含复权重干涉核，是 Bosonic 独有难点（教学切 → 生产切）；B6 分步执行
  是纯新增 UI 工作量。
- 契约：修改物理语义必须先改 `docs/vision-bosonic-simulator.md`；K=1 退化
  到 Gaussian 是硬不变量（atol 1e-7）；组件泄漏纪律镜像 Fock 截断纪律
  （warn >1e-6，fail >1e-3）。
- 开放：双模生产级、PNR 条件化/联合多模路径、AD、tensor networks（vision §10）。
