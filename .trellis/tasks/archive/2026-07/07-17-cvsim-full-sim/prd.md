# CV 模拟器全功能扩展（B 轨 · B1 门集）

## Goal

在 MVP 三表示骨架上，交付 **B1 门集**：能搭「有意义高斯电路」（位移 / 相移 / 挤压 / 分束器），Gaussian 多模为主，Fock 单模跟齐，Bosonic 逐组件复用辛更新。不引入 Circuit DSL。

## Background

- MVP 已归档：`archive/2026-07/07-17-three-cv-simulators`
- 现有 API：Gaussian `squeeze`；Fock `squeeze`；Bosonic cat，无门
- 已有 `apply_symplectic(state, S, d)` 可作为 Gaussian 门公共核
- 约定：`ħ=1`，xxpp，`V=I/2`；numpy+scipy；笔记禁 API

## Decisions

| # | 决策 | 选择 |
|---|------|------|
| D1 | B1 切片 | 门集优先（测量/通道后置） |
| D2 | 三表示对齐 | **Gaussian 先厚**；Fock 单模 D/R/S；Bosonic 逐组件辛更新 |
| D3 | Circuit | **不要**；函数式 per-backend |
| D4 | 门表与验收 | **核心四门**，不含 S₂；硬验收三场景（下） |

## Requirements

- **R1 Gaussian 多模门**  
  - `displace(state, alpha, mode)`：`α` 复；`x`/`p` 位移按 `ħ=1`：`d_x=√2 Re α`，`d_p=√2 Im α`  
  - `phase(state, theta, mode)`：xxpp 平面旋转  
  - `squeeze`（已有，保持）  
  - `beamsplitter(state, mode1, mode2, theta, phi=0)`：两模混合；`phi` 支持（默认 0）  
  - 门经 `apply_symplectic`；返回新 state

- **R2 Fock 单模门**  
  - `displace`、`phase`、`squeeze`（已有）  
  - `D,R,S` 用 ladder + `expm` 或对角相位  
  - **不做** 多模 BS / Kerr（B1 外）

- **R3 Bosonic 高斯门**  
  - 对每个组件 `(V,r̄)` 套同一 `S,d`；`w` 不变（酉高斯）  
  - 至少暴露：`displace` / `phase` / `squeeze` / `beamsplitter`（多模组件时 BS 有意义；单模 cat 至少 phase/squeeze/displace）

- **R4 观测量**  
  - 沿用 `det_cov`、`mean_photon`（Gaussian 多模 per-mode 已有）  
  - 不新增 Homodyne

- **R5 验证**  
  - pytest + 可选 demo；数值 AC 如下

- **R6 约束**  
  - 无量子库；不改理论笔记绑 API；不引入 Circuit 类

## Acceptance Criteria

- [x] **AC-G1** 真空 → `D(α)`：Gaussian `|⟨n⟩ − |α|²|` 在容差内
- [x] **AC-G2** 真空 → `S(r)` → `BS(π/4)` 两模：总 `⟨n⟩` 守恒；`det V ≈ (1/4)²`
- [x] **AC-G3** `phase(θ)` 后 `V` 旋转符合 `R V Rᵀ`
- [x] **AC-F1** Fock 真空 → `D(α)`：`⟨n⟩` 逼近 `|α|²`
- [x] **AC-F2** Fock–Gaussian `⟨n⟩` 差随 cutoff 减小
- [x] **AC-B1** cat → `phase`：`∑w=1`；峰旋转
- [x] **AC-B2** 单组件 `displace` 后权重仍归一
- [x] **AC-0** 全量 pytest 21 绿（含 MVP）

## Out of Scope（B1）

- S₂ 双模挤压；Circuit DSL
- Homodyne / PNRD / Hafnian；光子损失通道
- Fock 多模 BS / Kerr；GKP；Wigner 必选
- GPU / 分布式；笔记 API 绑定

## Open Questions

无阻塞项。实现容差与 `phi` 符号约定写在 `design.md`。
