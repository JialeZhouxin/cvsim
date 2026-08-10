# Phase 5 C1 — F-BRIDGE 观测值桥

## Goal

顶层 `cvsim/bridge.py` 纯函数族（grill Q1/Q2 锁定：观测值桥，非态桥、非 DSL）。Phase 5 exit 2 主体。

## Requirements

- `cvsim/bridge.py`（顶层，ADR-0001 跨表示）5 个纯函数：
  - `coherent_element(n, alpha)` — ⟨n|α⟩ = e^{−|α|²/2} αⁿ/√n!
  - `squeezed_element(n, r, phi)` — 挤压态振幅（φ 约定与 FockState.squeezed 一致）
  - `thermal_diag(n, nbar)` — n̄ⁿ/(n̄+1)^{n+1}
  - `vacuum_probability(V, rbar, mode)` — 高斯态 0 光子概率解析闭式（threshold p_click 复用）
  - `fock_state_amplitude(n, state)` — 从 FockState 取振幅（对照辅助）
- `tests/test_bridge.py`：解析 vs Fock 数值对照（coherent/squeezed/thermal/vacuum）+ 已知解析值硬编码；atol=1e-10（截断内）
- 态桥（完整 ρ_fock）不做：ponytail 注释

## Acceptance Criteria

- [ ] AC1: coherent/squeezed 低截断矩阵元解析 vs Fock 数值一致（exit 2）
- [ ] AC2: vacuum_probability 与 Fock 截断 ⟨0|ρ|0⟩ 收敛一致（截断足够时）
- [ ] AC3: 全量 pytest 绿（700 基线 + 新增）；commit + OCR
