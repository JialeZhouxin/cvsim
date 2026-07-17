# 最终用户验收剧本（Markdown + 一键 demo）

## Goal

钉死项目目标与**当前已交付**能力，交付可更新用户验收文档 + 一键 demo，使人按教程顺序复现物理结果并做门禁。

## Background

- 理论：`README.md` 最小闭环四步；笔记禁 API
- `cvsim`：MVP + B1 门 + B2 Homodyne；pytest 25；demos m1/m2/m3
- 缺口：无统一 U1–U6 用户验收叙事

## Decisions

| # | 决策 | 选择 |
|---|------|------|
| D1 | 形态 | **B**：Markdown + 一键 demo |
| D2 | 场景 | 已交付 U1–U6；未做单列，不假装绿 |
| D3 | 文档路径 | **`cvsim/USER_ACCEPTANCE.md`** |
| D4 | demo 失败策略 | **跑完汇总**；任一 FAIL → 最终 `exit 1` |

## Requirements

- **R1 目标段**（文档内固定，少改）  
  - 两层：笔记自学 / `cvsim` 最小三表示模拟  
  - 成功：ħ=1、xxpp、`V=I/2`；G 挤+BS+Homodyne；Fock cutoff；Bosonic cat  
  - 不是：生产 GBS、Circuit DSL、量子库替代品

- **R2 场景 U1–U6**（给定/操作/期望/容差/笔记索引）  
  - U1 真空与约定  
  - U2 挤 + det + ⟨n⟩ + Homodyne var  
  - U3 D + S→BS + phase  
  - U4 Fock cutoff（+ 可选范数亏损）  
  - U5 cat `∑w` + phase  
  - U6 机器门禁：`pytest` + m1/m2/m3（文档命令；可不强制 demo 内调 pytest）

- **R3 一键 demo**  
  - `python -m cvsim.demos.user_acceptance`  
  - 跑 U1–U5 检查；每场景 PASS/FAIL；**全部跑完**再汇总；有 FAIL → `sys.exit(1)`  
  - 容差与既有 AC 对齐（如 1e-10 / 1e-3 按量）

- **R4 链接**  
  - `cvsim/README.md` + 根 `README.md` 链到验收文与一键命令

- **R5** 不实现新物理；理论 MD 不绑 API

## Acceptance Criteria

- [x] `cvsim/USER_ACCEPTANCE.md` 含目标 + U1–U6 + 未做 + 更新约定
- [x] `python -m cvsim.demos.user_acceptance` 全 PASS、exit 0
- [x] 失败策略：run-all + try/except 保汇总（代码内；文档 D4）
- [x] `pytest tests -q` 25 绿
- [x] 两处 README 有链

## Out of Scope

- S₂ / 条件 Homodyne / 损失 / Fock BS / Wigner 必选
- 重写理论笔记；Circuit DSL

## Open Questions

无阻塞项。
