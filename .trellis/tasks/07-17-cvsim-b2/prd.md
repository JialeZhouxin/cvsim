# CV 模拟器 B 轨 · B2 切片（Homodyne）

## Goal

在 B1 门集之上交付 **B2 Homodyne**：Gaussian 正交边缘均值/方差，使电路「能读结果」。不引入 Circuit DSL。

## Background

- MVP + B1 已归档；`det_cov` / `mean_photon` 有；无 Homodyne
- 约定：ħ=1，xxpp；numpy+scipy；笔记禁 API
- 物理：`x_φ = x cos φ + p sin φ`（单模）

## Confirmed facts

- 用户：D1 Homodyne；D2 边缘矩 · G only；D3 API 双函数 A
- 复杂：prd/design/implement → 审 → start

## Decisions

| # | 决策 | 选择 |
|---|------|------|
| D1 | B2 切片 | Homodyne |
| D2 | 深度/后端 | 边缘矩 only · 仅 Gaussian；无条件更新；无 Bosonic/Fock Homodyne |
| D3 | API / 验收 | `homodyne_mean` / `homodyne_var`；硬验收四条见 AC |

## Requirements

- **R1** `homodyne_mean(state, mode, phi) -> float`  
  - `x_φ = x cos φ + p sin φ`  
  - `⟨x_φ⟩ = cosφ · r̄_x + sinφ · r̄_p`（该 mode 槽位）

- **R2** `homodyne_var(state, mode, phi) -> float`  
  - 边缘方差 = 二次型 `uᵀ V u`，`u` 在 (x_i,p_i) 上为 `(cosφ, sinφ)`  
  - 与位移无关（中心矩）

- **R3** 放在 `cvsim/gaussian/observables.py`；导出 `__init__`

- **R4** pytest 覆盖 AC；既有 tests 不破

- **R5** 无采样 RNG；无条件态；不改理论笔记 API 绑定

## Acceptance Criteria

- [x] **AC-H1** 真空任意 `φ`：`var = 1/2`；`mean = 0`
- [x] **AC-H2** 真空 → `S(r)`：`var(φ=0)=½ e^{-2r}`，`var(φ=π/2)=½ e^{2r}`
- [x] **AC-H3** 真空 → `D(α)`：`mean(φ)` 匹配 `√2 (Reα cosφ + Imα sinφ)`
- [x] **AC-H4** 挤后 `phase(θ)`：与 `uᵀ V u` 一致且相对纯挤变化
- [x] **AC-0** 全量 pytest 绿

## Out of Scope（B2）

- 条件态 / Generaldyne；采样 `sample_homodyne`
- Bosonic/Fock Homodyne
- PNRD/Hafnian；S₂；损失；Fock BS；GKP；Wigner
- Circuit DSL；GPU；笔记 API

## Open Questions

无阻塞项。
