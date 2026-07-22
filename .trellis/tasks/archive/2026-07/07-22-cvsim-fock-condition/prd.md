# Fock Homodyne condition（1 模）

## Goal

Fock **1 模** ideal Homodyne **条件化**：给定 outcome，返回后态。  
与 G/B 的 mean→outcome、测向 var→0 **教学对齐**。无新量子库。

## Background

- 现 Fock：`homodyne_mean|var|sample`；**无** condition  
- G/B：`homodyne_condition` + `sample_and_condition`  
- 未做表：Fock Homodyne **condition**

## Physics（诚实）

单模 **投影** Homodyne：测得 \(x_φ=m\) 后，系统坍缩为正交本征态 \(|m\rangle_φ\)（与先验 pure 态形状无关；先验只进 \(p(m)=|\psi(m)|^2\)）。

教学实现（截断 Fock）：

```text
c_n ∝ ψ_n(m; φ)     # 与 sample 同套 HO 波函数 + 相位旋转
|ψ'⟩ = normalize(c)  # FockState
ρ' = |ψ'⟩⟨ψ'|        # 若输入 dens，仍投影到 |m⟩⟨m|
```

与 **Gaussian Kalman**（\(V'=V-vv^T/σ\)）**不同公式**：

| | G condition | F condition（本切片） |
|--|-------------|----------------------|
| 先验进后态 | 是（高斯闭合） | 否（投影本征态） |
| 测向 | var→0，mean→m | mean≈m，var 小（截断/网格极限） |
| 共轭正交 | 高斯奇异/发散 | Fock 截断下有限 |

对照检查：真空/相干 **mean≈outcome**；不要求 F 后态 ≡ G 后态的全体矩。

## Decisions

| # | 选择 |
|---|------|
| D0 | API：`fock.homodyne_condition(state, mode=0, phi=0.0, outcome=...)` |
| D1 | **仅 1 模** pure 或 dens；2 模 raise |
| D2 | 后态：**pure `FockState`**（dens 输入也压成 pure \|m⟩ 再可选 dens——默认 **返回 FockState**，简单） |
| D3 | 薄封装 `homodyne_sample_and_condition` 同 G/B |
| D4 | HO 基复用 sample 路径（`eval_hermite`） |
| D5 | 无弱测/效率 η；无多模 partial trace condition |
| D6 | 理论 MD 可选轻补；工程 docs 必改 |

## Requirements

### R1

```python
homodyne_condition(state, mode=0, phi=0.0, outcome: float) -> FockState
homodyne_sample_and_condition(...) -> tuple[float, FockState]
```

### R2 检查点

- 任意先验 → condition(m) → `homodyne_mean≈m`（同 φ，N≥16）  
- `homodyne_var` 小于先验真空 var（教学：塌缩尖）  
- sample_and_condition：outcome 与 condition 一致  
- 2 模 / mode≠0 raise  
- G 测仍绿  

### R3 docs

- USER_ACCEPTANCE 未做去掉 F condition；锚点 +N  
- README 一行；诚实：投影 ≠ G Kalman  

## Acceptance Criteria

- [x] **AC1** condition 后 mean≈outcome（近邻截断本征值）  
- [x] **AC2** sample_and_condition 可跑  
- [x] **AC3** pytest **122**；UAT 8/8  
- [x] **AC4** 文档 + 诚实边界（投影 ≠ G Kalman）  

## Out of Scope

- 2 模 / 测一模条件另一模  
- 有限效率 Homodyne  
- 与 G condition 全矩数值等同  
- P2  

## Open 默认

| 项 | 默认 |
|----|------|
| dens 输入返回 | `FockState`（pure \|m⟩） |
| 数值稳定 | \|ψ_n\| 全 0 → raise |
