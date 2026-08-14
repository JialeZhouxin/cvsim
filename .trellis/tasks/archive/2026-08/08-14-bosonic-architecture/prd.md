# Bosonic 生产级模拟器架构设计

## Goal

grill A1–A12 锁定 Bosonic 模拟器**架构层**设计（战略层已锁于 vision-bosonic-simulator.md + ADR-0005），落盘为可执行的设计文档，并同步 vision 模块树 / ADR / 术语表。

## Requirements

- 架构设计覆盖：数据结构（A1, A3）、门执行（A2）、测量数学与采样（A4, A5）、组件工程 API（A6）、analyse 边界（A7）、电路/IR（A8, A9, A10）、工程纪律（A11）、GKP 角色（A12）
- 每个决策记录：决策 + 理由 + 权衡 + 对 B 阶段切片的影响
- 不改战略层：B0–B7 路线、C1–C4 支柱、A1 锚、R1 对账、P1/M1/G1 均不重开
- 落盘同步物：vision §3 模块树 amend（A4）、ADR-0006（A5+A8，硬反转决策）、CONTEXT.md 术语（weight_sum 语义、CDF 反演）

## Acceptance Criteria

- [ ] `design.md` 含 A1–A12 全部决策总表 + 模块架构 + 每决策理由/权衡/B 映射
- [ ] vision-bosonic-simulator.md §3 模块树反映 A4（measure.py 合并）且 §11 文档控制有记录
- [ ] ADR-0006 存在（A5 CDF 网格反演 + A8 initial 工厂规格，含否决项与权衡）
- [ ] CONTEXT.md 增补：weight_sum 归一化语义、is_hermitian 共轭对闭合、CDF 网格反演采样
- [ ] 用户复核 design.md 无异议（review gate）
- [ ] 12 个决策全部可追溯到本任务设计文档（无悬空问题）

## Notes

- grill 过程：A1–A12 逐题一问一答，用户每题采纳推荐答案（2026-08-14）
- 战略层 = vision-bosonic-simulator.md（Q1–Q13 锁）；本任务只锁架构层
