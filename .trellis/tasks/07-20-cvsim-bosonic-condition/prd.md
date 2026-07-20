# Bosonic 条件 Homodyne（教学瘦 A）

## Goal

`BosonicState` **理想条件 Homodyne**：

```text
homodyne_condition(state, mode, phi, outcome) → BosonicState
```

逐组件复用 G 更新；**实 r̄** 组件按高斯边缘似然乘权；**复 r̄ 交叉** 本切片丢弃（w→0 后归一）。不删模。

## Background

- G：`V'=V−vvᵀ/σ`，`r̄'=r̄+v(o−μ)/σ`
- 笔记 04：逐组件条件 + p_k 乘权 + 重归一
- 用户选 **A：教学瘦**

## Decisions

| # | 选择 |
|---|------|
| D1 | **A：实 r̄ 似然 + 丢弃复 r̄ 交叉** |
| D2 | API 名同 G：`bosonic.homodyne_condition`（导出） |
| D3 | 不删模；σ≤ε → ValueError（同 G） |
| D4 | 单组件 B ≡ G 数值对齐 |

## Requirements

### R1 组件分类
- **实中心**：`‖Im r̄‖_∞ ≤ tol` → 条件更新 + 似然乘权  
- **复中心**：丢弃（不进入输出列表）

### R2 实组件更新（与 G 同）
```text
u = (cosφ e_x + sinφ e_p) on mode
v = V u,  σ = uᵀ V u,  μ = u·Re(r̄)   # r̄ 实 → μ 实
V' = V − vvᵀ/σ
r̄' = r̄ + v (outcome−μ)/σ            # 保持 float→complex 存储
```

### R3 似然（未归一）
```text
L_k = (2π σ_k)^{-1/2} exp( −(outcome−μ_k)² / (2 σ_k) )
w_k⁰ = w_k · L_k
```
最后 `w ← w⁰ / Σ w⁰`（仅存活组件）。若无存活 / Σ=0 → ValueError。

### R4
- 文件：`cvsim/bosonic/observables.py`（或 `measurements.py` 若过长则仍 observables）
- tests：`tests/test_bosonic_condition.py`
- README + quality 一行；UAT 不破（可选不加 Ux）

## Acceptance Criteria

- [x] **AC-C1** 单组件 ≡ G
- [x] **AC-C2** even cat：仅对角；+峰权 > −峰权
- [x] **AC-C3** `∑w≈1`；无复中心
- [x] **AC-C4** 真空 outcome=0.3：B≡G
- [x] **AC-C5** pytest 69；UAT 6/6

## Out of Scope

- 交叉项完整条件似然；采样；删模；Fock；Generaldyne

## Notes

- 诚实：丢交叉 = 条件后态 **混合峰选择近似**，非完整 cat 干涉条件态
- tol 建议 `1e-12` 量级
