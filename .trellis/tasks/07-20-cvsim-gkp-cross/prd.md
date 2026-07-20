# Bosonic GKP 交叉项（近邻 nn）

## Goal

`gkp0` 增加 **近邻 x 齿交叉**（`cross="nn"`），教学向更纯 `|0⟩_GKP`；Wigner 相对对角版有干涉差。默认 `cross="none"` **不破** U7。

## Background

- 对角 `gkp0` 已归档；Wigner 支持复中心
- cat：交叉中心 `((x_k+x_l)/2, i(x_k-x_l)/2)`；权重含 ov
- 用户选 **A = 近邻 cross**

## Decisions

| # | 选择 |
|---|------|
| D1 | **A：nn cross only** |
| D2 | API：`gkp0(epsilon, grid_size, *, cross="none"\|"nn")`；默认 none |
| D3 | 振幅 `a_k∝exp(−π ε k²/2)`；对角 `w∝a_k²`；nn 交叉含 ov 后 **全局 ∑w→1** |
| D4 | 无 `|1⟩`、无 2D p 齿 |

## Requirements

### R1 对角（`cross="none"`）
保持现契约：K=2N+1，间距 √(2π)，U7/旧测通过。

### R2 近邻（`cross="nn"`）
- 齿 k∈[−N,N]，x_k=k√(2π)，同 V=½diag(ε,1/ε)
- 对角：每 k 一组件，w 基 `a_k²`
- 每对 (k,k+1)：两向交叉
  - r̄₊ = ((x_k+x_{k+1})/2, +i(x_k−x_{k+1})/2)
  - r̄₋ = ((x_k+x_{k+1})/2, −i(x_k−x_{k+1})/2)
  - 基权 `a_k a_{k+1} · ov`（a 实 → 两向同实权，类 even）
- ov：同 V 纯高斯 `exp(−⅛ Δrᵀ V⁻¹ Δr)`（真空/相干对齐 cat `e^{-2α²}`）
- 最后 `w ← w/∑w`

### R3
`tests/test_bosonic_gkp_cross.py`；README/quality 一行；UAT 6/6 不破。

## Acceptance Criteria

- [x] **AC-X1** `cross="none"`：K=2N+1，旧 gkp 测绿
- [x] **AC-X2** `cross="nn", N=2`：K=**13**；`|∑w−1|<1e-12`
- [x] **AC-X3** 交叉中心：邻齿中点 + 虚 p
- [x] **AC-X4** Wigner nn vs none 可测差
- [x] **AC-X5** 门后 w 不变；pytest + UAT

## Out of Scope

- 全配对 cross；`|1⟩_GKP`；2D 格；纠错电路；Fock 对照

## Notes

- ε≪1 时 ov≈exp(−π/(2ε)) 极小 → 条纹弱；测选用中等 ε
- 诚实：nn 截断 ≠ 完整 Gram 纯态
