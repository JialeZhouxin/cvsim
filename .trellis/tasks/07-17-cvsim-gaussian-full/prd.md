# Gaussian 全流程闭环

## Goal

只补 **Gaussian** 成可独立闭环：

```text
初态 → 高斯门(含 S₂) → [可选损失] → 条件 Homodyne → 观测量
```

Fock / Bosonic **本任务不交付**（后续独立）。无 PNRD / Hafnian / Circuit DSL。

## Background

- 已有：D/R/S/BS/S₂、det/⟨n⟩、Homodyne **边缘** mean/var
- 缺：条件态、光子损失
- 用户：先高斯全流程；两模块独立

## Decisions

| # | 决策 | 选择 |
|---|------|------|
| D1 | 范围 | 条件 Homodyne + 光子损失；无 PNRD |
| D2 | 切片序 | **G1 条件 Homodyne → G2 损失** |
| D3 | API / 验收 | **最瘦 A**（见 Requirements） |

## Requirements

### G1 · 条件 Homodyne

- **R1** `homodyne_condition(state, mode, phi, outcome) -> GaussianState`
  - ħ=1、xxpp；`x_φ = x cosφ + p sinφ`
  - 理想 Homodyne 条件更新（全空间 rank-1，**不删模**）：
    - `u` 使 `x_φ = u·r`，`σ = uᵀVu`，`μ = u·r̄`
    - `V' = V − (Vu)(Vu)ᵀ/σ`
    - `r̄' = r̄ + (Vu)(outcome−μ)/σ`
  - 与既有 `homodyne_mean` / `homodyne_var` 一致（同一 `u`）
- **R2** 导出；`tests/test_g1_homodyne_condition.py`

### G2 · 光子损失

- **R3** `loss(state, T, mode=None) -> GaussianState`
  - `0 ≤ T ≤ 1`；`mode is None` → 全模同一 `T`，否则单模
  - `V ↦ X V Xᵀ + Y`，`r̄ ↦ X r̄`
  - 本约定 ħ=1、`V_vac=I/2`：作用子空间 `X=√T I`，`Y=(1-T)·(I/2)`
- **R4** 导出；`tests/test_g2_loss.py`

### 共同

- **R5** 仅 `cvsim/gaussian/`（+ tests / README / quality）；不改 F/B 行为承诺
- **R6** 全量 pytest 绿；可选 README「高斯闭环」短节

## Acceptance Criteria

### G1

- [x] **AC-C1** 真空 + 任意 outcome：测方向 var→0；未测正交仍 ~½
- [x] **AC-C2** 位移态：条件后 `⟨x_φ⟩` 钉在 `outcome`
- [x] **AC-C3** TMS：测模 0 后模 1 var 收缩
- [x] **AC-C4** 与 `homodyne_var` 同 `u`

### G2

- [x] **AC-L1** `T=1` 恒等
- [x] **AC-L2** `T=0` → 真空
- [x] **AC-L3** `⟨n⟩ ≈ T|α|²`
- [x] **AC-L4** 单模 loss 不碰另一模位移

### 总

- [x] **AC-0** pytest 37 绿；UAT 5/5 PASS

## Out of Scope

- Fock / Bosonic 条件测与损失
- PNRD / Hafnian / Torontonian / 采样
- 热态、Williamson、删模版 condition、S₂ 相位
- 理论笔记 API 绑定

## Open Questions

无阻塞项。G1 可先合并实现再 G2；同一任务一次或两次 commit 均可。

## Notes

- 笔记 02：`Y=(1-T)(ħ/4κ²)I` → 本栈 κ 对齐 `V_vac=I/2` 得 `Y=(1-T)I/2`。
- 条件更新奇异 `V`：接受；调用方可只读未测方向矩。
