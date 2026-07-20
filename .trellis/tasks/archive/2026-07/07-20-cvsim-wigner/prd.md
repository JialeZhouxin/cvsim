# Wigner 网格教学切片

## Goal

单模教学 **Wigner 网格**（G 闭式 + B 加权；含 cat 复中心相位）：

```text
wigner_grid(state, lim=5, n=81) → (X, P, W)
```

可 `imshow`；无 GUI；无 Fock；无多模。

## Background

- ① 文档已归档；用户选 **A = G+B**
- 笔记 03/04：`W=∑ w_k W_G`；虚位移 → 条纹相位
- 约定 ħ=1、xxpp、`V_vac=I/2` → 真空 `W(0,0)=1/π`（非 ħ=2 文献的 2/π）

## Decisions

| # | 选择 |
|---|------|
| D1 | **A：Gaussian + Bosonic**；无 Fock |
| D2 | 仅 **单模**；网格 `meshgrid` |
| D3 | 返回实部 `W.real` 作主输出；物理 Im 应≈0 |

## Requirements

### API

- **R1** `wigner_gaussian_point(V, rbar, x, p) -> complex`  
  ħ=1 单模高斯 Wigner（允许 `rbar` 复）：
  - `d = Re(r̄)`，`s = Im(r̄)`
  - `δ = (x,p) − d`
  - 高斯包络 `G = 1/(π √(det(2V))?` — **design 锁最终归一**使真空 `W(0)=1/π`
  - 相位：`exp(i · 2 δᵀ Ω? / note φ)` 对齐笔记 04：  
    `φ = δᵀ V^{-1} s`（或 2 倍；**以 vacuum+相干+cat 负区测通为准**）
- **R2** `wigner_gaussian(state: GaussianState, x, p)` — 单点
- **R3** `wigner_bosonic(state: BosonicState, x, p) = ∑ w_k W_G(V_k,r̄_k)`
- **R4** `wigner_grid(state, lim=5.0, n=81) -> tuple[X,P,W]`  
  `state` 为 G 或 B；`X,P` shape `(n,n)`；`W` float 实部
- **R5** 模块 `cvsim/wigner.py` 或 `gaussian/wigner.py` + bosonic 薄封装；优先 **共享 `cvsim/wigner.py`**
- **R6** tests + README 一行 + quality；UAT 不强制新 Ux（可选 U8 后开）
- **R7** 全量 pytest 绿；UAT 6/6 不破

## Acceptance Criteria

- [x] **AC-W1** 真空：`W(0,0) ≈ 1/π`；径向衰减
- [x] **AC-W2** 挤态 x 更尖
- [x] **AC-W3** **odd** cat：`W(0,0)<0`（even 中心增强）
- [x] **AC-W4** 单组件 B = G
- [x] **AC-W5** pytest + UAT

## Out of Scope

- Fock Wigner；多模；matplotlib 必选依赖（demo 可试 import）
- GKP 图美化；完整纯态 GKP cross 升级
- GUI

## Open Questions

无阻塞。归一与相位系数在 design/实现用 vacuum+cat 校准。

## Notes

- 笔记 04 条纹：`φ_k = ((x,p)−Re r̄)ᵀ V^{-1} Im r̄`
- gkp0 无 cross → Wigner 无干涉条纹（预期，非 bug）
