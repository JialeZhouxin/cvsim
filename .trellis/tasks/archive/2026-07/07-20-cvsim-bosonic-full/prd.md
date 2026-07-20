# Bosonic 模拟器独立全流程

## Goal

Bosonic **矩闭环**：

```text
真空/cat → 高斯门(D/R/S/BS/S₂) → weight_sum / ⟨n⟩ / Homodyne 边缘
```

G/F 本任务不动。无 loss / GKP / Wigner / 条件测。

## Background

- 已有：4 组件 cat、逐组件门（`w` 不变）、`weight_sum`
- 缺：真空工厂、加权 ⟨n⟩、加权 Homodyne 边缘

## Decisions

| # | 决策 | 选择 |
|---|------|------|
| D1 | 轨道 | 独立 Bosonic |
| D2 | 范围 | **A 矩闭环** |
| D3 | API / 矩 | **B 加权完整**（∑w 含二阶中心修正；w 可复） |

## Requirements

### 态

- **R1** `BosonicState.vacuum(nmode=1)`：单组件 `V=I/2`，`r̄=0`，`w=1`
- **R2** 可选薄封装 `from_gaussian(GaussianState)`（1 组件 w=1）— 有则测，无则跳过

### 观测量

- **R3** `mean_photon(state, mode=None)`  
  ħ=1：对每组件 `⟨n⟩_k` 用高斯公式（`r̄` 可复：`r²` 按复数乘）；  
  `⟨n⟩ = ∑_k w_k ⟨n⟩_k`（物理态 Im≈0 → 返回 `float` 取实部）
- **R4** `homodyne_mean(state, mode=0, phi=0)`  
  `μ = ∑_k w_k (u·r̄_k)` → 实部
- **R5** `homodyne_var(state, mode=0, phi=0)`  
  `⟨x_φ²⟩ = ∑_k w_k (uᵀV_k u + (u·r̄_k)²)`，`Var = ⟨x_φ²⟩ − μ²` → 实部  
  （**非** `∑ w·var_k` 忽略位移项）
- **R6** `weight_sum` 保持

### 工程

- **R7** 既有门/cat 回归不破
- **R8** `tests/test_bosonic_full.py`（或等价）
- **R9** README + quality；全量 pytest + UAT

## Acceptance Criteria

- [x] **AC-B1** 真空：`∑w=1`，⟨n⟩=0，Homodyne mean=0、var=½
- [x] **AC-B2** 单组件 = Gaussian 对照
- [x] **AC-B3** even cat：`∑w=1`，⟨n⟩ 随 α 增
- [x] **AC-B4** phase 后 ∑w 不变
- [x] **AC-B5** 门不改 `w`
- [x] **AC-B6** pytest 47 绿；UAT 5/5

## Out of Scope

- loss、条件 Homodyne、GKP、Wigner 采样
- Fock；Circuit；Hafnian

## Open Questions

无阻塞。

## Notes

- cat cross：`r̄` 复 → 二阶矩公式必须保留 `(u·r̄)²` 复数路径再取实部。
