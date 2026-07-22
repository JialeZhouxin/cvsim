# 跨表示对照加深 · 包 α

## Goal

**同一套数**更可演示：扩 m4 + 笔记轻补。  
**无新物理 API**；pytest/UAT 不破。

## Background

- 用户锁深化包 **α**
- m4 现有：T4 单模挤 ⟨n⟩ G/F；T1 相干+loss G/F/B
- P1 已有未进 m4：F S₂、loss nbar、F Homodyne mean

## Decisions

| # | 选择 |
|---|------|
| D0 | **仅 demo + 笔记 + 文档**；不扩核心库 API |
| D1 | m4 增 **3** 场景（见下） |
| D2 | 理论 MD **轻补**（禁 API 名）：02 热环境 n̄；01 Homodyne 边缘矩一句 |
| D3 | **不**强制 UAT U10（m4 自 assert 够） |
| D4 | 可选 `tests/test_m4_cross_rep.py` 包一层 m4（推荐，防 demo 漂） |

## Scope

### In — m4 新场景

| ID | 物理 | 对照 | 检查点 |
|----|------|------|--------|
| **T5** | S₂(r) 真空 | G vs F | ⟨n₀⟩≈⟨n₁⟩≈sinh²r；\|G−F\| 松 |
| **T6** | 真空 `loss(T=0, nbar)` | G vs B | ⟨n⟩=n̄；G≡B |
| **T7** | 相干 Homodyne mean | G vs F | 各 φ：\|μ_G−μ_F\| 小 |

### In — 笔记（纯理论）

- `02`：loss 段补热环境 \(Y=(1-T)(\bar n+1/2)I\)；\(\bar n=0\) 还原纯损耗  
- `01`：Homodyne 一句：ħ=1 边缘矩可由 ⟨a⟩,⟨a²⟩,⟨n⟩ 得（不写函数名）  
- 术语表一行：热损耗 / 环境平均光子  
- 根 README 闭环可选一句「m4 对照」

### Won't

- 新 gate/channel/measure API  
- F condition · G5 2 模 loss · GKP\|1⟩  
- UAT 强制加 U10  
- P2  

## Acceptance Criteria

- [x] m4 打印并通过 T4+T1+T5+T6+T7  
- [x] `python -m cvsim.demos.m4_cross_rep` OK  
- [x] test_m4 绿；pytest **105**；UAT 8/8  
- [x] 理论 MD 无 API 名  
- [x] README 指 m4 扩场景  

## Out of Scope

见 Won't。

## Notes

- 参数建议：r_S2=0.3, N=24；nbar=0.5；α=0.55+0.2j, φ∈{0,π/4,π/2}
