# G6 · Fock Homodyne（P1-B）

## Goal

1 模 Fock / `FockDensity`：**Homodyne 边缘 mean/var**；**采样**（教学）。  
与 G 在真空/相干上对齐。**无新量子库。**

## Background

- P1 包 A（G7+G8）已归档；pytest **96**；UAT **8/8**
- 未做表仍写：Fock Homodyne sample
- 用户：续开 **P1-B（+G6）**

## Decisions

| # | 选择 |
|---|------|
| D0 | 仅 **1 模**；2 模 raise |
| D1 | ħ=1：`x_φ=x cosφ+p sinφ`；`x=(a+a†)/√2`，`p=(a-a†)/(i√2)` |
| D2 | **mean/var 必做**；**sample 必做**（纯态优先；ρ 走 PDF 对角化或拒采） |
| D3 | API 名对齐：`homodyne_mean` / `homodyne_var` / `homodyne_sample` 在 `fock/observables.py` |
| D4 | **不做** condition on Fock（P1 本切片外；贵且非本包 A/B 原表） |
| D5 | 理论 MD 默认不动；改 `USER_ACCEPTANCE`/README 未做 + 能力矩阵 |

## Requirements

### R1 mean/var

- pure + density
- 真空：`mean=0`，`var(x)=var(p)=1/2`
- 相干 `D(α)`：mean 跟 G（√2 约定）；var≈1/2（高 cutoff）
- 挤态：var(x)≈½e^{-2r}，var(p)≈½e^{2r}（松容差）

### R2 sample

- `homodyne_sample(state, mode=0, phi=0, *, rng)` → float  
- 真空：多样本 mean≈0，var≈0.5（统计容差）  
- 实现建议：在 `x_φ` 轴上建截断波函数/边缘 PDF，再 `rng.choice` 离散轴（教学够用）

### R3 docs

- README Fock 行加 Homodyne  
- USER_ACCEPTANCE 未做去掉 Fock Homodyne sample  
- 可选：不强制 U10（tests 够）

## Acceptance Criteria

- [x] **AC1** vac mean/var 钉死 0 / ½  
- [x] **AC2** 相干 mean ≡ G  
- [x] **AC3** sample 统计合理  
- [x] **AC4** pytest **101**；UAT 8/8  
- [x] **AC5** 文档未做表更新  

## Out of Scope

- Fock Homodyne **condition**  
- 2 模 / m≥3  
- G5 2 模 loss、G9、G10  
- P2  

## Open（开工前可默认）

| 项 | 默认 |
|----|------|
| sample 网格 | `lim=8`，`n=512` 可内置常量 |
| ρ sample | 用 ρ 的位置表示对角（非负边缘）；不保证 Wigner 负区 PDF |

## Notes

- 矩：用 `a` 矩阵算 ⟨a⟩, ⟨a†a⟩, ⟨a²⟩ 等闭式，比数值积分稳  
- sample：PDF 路线；诚实注释「离散网格近似」
