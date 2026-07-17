# CV 模拟器 B 轨 · B3 双模挤压 S₂

## Goal

交付 **S₂(r)**（实 r）：Gaussian 多模 + Bosonic 逐组件，共享 `symplectic.py`。补纠缠高斯源。无 Circuit；无 Fock S₂；无 φ。

## Background

- 已有：单模 S、BS、Homodyne 边缘；UAT U1–U6
- 笔记 04：`S₂` 块形式 `[[ch I, sh Z],[sh Z, ch I]]`，`Z=diag(1,-1)`（两模子空间）
- 真空 TMS：总 `⟨n⟩ = 2 sinh² r`

## Decisions

| # | 决策 | 选择 |
|---|------|------|
| D1 | 切片 | S₂ |
| D2 | 后端 | Gaussian + Bosonic；**无 Fock** |
| D3 | API / 验收 | **实 r only**；硬验收见 AC（不强制本切片改 UAT） |

## Requirements

- **R1** `S_two_mode_squeeze(nmode, r, mode1, mode2) -> S` 于 `symplectic.py`（xxpp）
- **R2** Gaussian：`two_mode_squeeze(state, r, mode1, mode2)` → `apply_symplectic`
- **R3** Bosonic：同名包装，逐组件同一 S；`w` 不变
- **R4** 导出 `__init__`；pytest AC；既有 tests 不破
- **R5** 无 φ、无 Fock、不改理论笔记 API

## Acceptance Criteria

- [x] **AC-S1** `S Ω Sᵀ ≈ Ω`（两模 + 嵌入多模）
- [x] **AC-S2** 真空 2 模 → S₂(r)：总 `⟨n⟩ = 2 sinh² r`；`⟨n₀⟩≈⟨n₁⟩`
- [x] **AC-S3** 模间相关：`V_x0x1`、`V_p0p1` 非零且异号
- [x] **AC-S4** `det V ≈ (1/4)²`
- [x] **AC-S5** Bosonic 单组件 S₂：`∑w` 不变；V 与 Gaussian 一致
- [x] **AC-0** 全量 pytest 绿

## Out of Scope

- S₂ 相位 φ；Fock TMS；条件 Homodyne；损失；UAT U7 必做（可选后续）
- Circuit；PNRD；笔记 API

## Open Questions

无阻塞项。嵌入 xxpp 的精确下标约定写 `design.md`，并用 Ω 单测锁死。
