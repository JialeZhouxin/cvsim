# Phase 5 C4 — Bosonic consistency

## Goal

Bosonic 三表示一致性测试（grill Q5 锁定：合同固化 + 桥锚定）。

## Requirements

- `tests/test_bosonic_consistency.py`：
  - **合同固化**：vacuum 单分量、加权矩公式、loss w 不变、单分量 == Gaussian（spec quality-guidelines 已写，从文档变测试）
  - **桥锚定**：cat（偶/奇）与 GKP 多峰态的 ⟨x⟩、Var —— 三向对照：Bosonic 加权矩 vs bridge 解析 vs Fock 截断数值
- 纠缠量跨表示（log-neg 截断收敛）不做：ponytail 注释

## Acceptance Criteria

- [ ] AC1: 现有 Bosonic 合同全部测试化并通过
- [ ] AC2: cat/GKP ⟨x⟩/Var 三向一致（Bosonic == bridge 解析 == Fock 数值，容差明确）
- [ ] AC3: 全量 pytest 绿；commit + OCR
