# 三表示缺口补齐战役（父任务）· 包 A

## Goal

**仅 P0**：关教学真缺口 G1–G4。  
不做 P1/P2。子任务独立可验收；父任务只规划 + 跟踪。

## Background

- pytest **80**；UAT **7/7**；笔记 A + m4 已归档
- 用户锁 **包 A**

## Decisions

| # | 选择 |
|---|------|
| D0 | 父任务规划 + 拆子任务；**不**在父任务里堆全部实现 |
| D1 | **包 A = P0 only**（G1–G4） |
| D2 | P1 显式 **Won't this campaign**；P2 产品外 |
| D3 | 子任务串行优先：G1 → G2 → G3 → G4（G1/G2 可并行） |
| D4 | 理论 MD 本战役默认**不**扩（除非公式缺检查点）；工程文档可更 |
| D5 | 无新量子库；ħ=1 xxpp `V=I/2` |

## Scope map

### In（P0）

| ID | 子任务 slug（拟） | 交付 | 独立验收 |
|----|-------------------|------|----------|
| **G1** | `cvsim-fock-wigner` | 单模 Fock/ρ → W(x,p) + grid 挂接 | vac `1/π`；\|1⟩ 原点负；纯态挤逼近 G |
| **G2** | `cvsim-fock-density-gates` | `FockDensity` 上 D/R/S（UρU†） | loss 后再 D；⟨n⟩ 合理；纯态 ρ 与 pure 门一致 |
| **G3** | `cvsim-sample-and-condition` | 薄封装 **或** demo（二选一，子任务锁） | G 真空 sample→condition 测向 var→0 |
| **G4** | `cvsim-uat-p0-close` | UAT 场景 + README/未做表 + pytest 锚点 | run-all 全绿；未做列表更新 |

### Won't（本战役）

- **P1** G5–G10（2 模 loss、F Homodyne、F S₂、热噪声、GKP\|1⟩、HTML）
- **P2** X1–X6（DSL、Hafnian、m≥3、full GKP Gram、GUI、替 SF）

## Campaign acceptance

- [x] 四个子任务均 **archived**（G1–G4）
- [x] 战役末：pytest **90**；UAT **8/8**；未做表更新
- [x] 无 P2 代码

## Out of Scope

见 Won't。

## Open Questions（子任务内再锁）

- G3：API 封装 vs 仅 demo？
- G1：纯态 only 还是 `FockDensity` 也支持？（推荐 **两者**，ρ 通用）

## Notes

- 子任务依赖写在**子** prd，不靠目录暗示
- 父任务 `start` 仅当：用户批准本规划 **且** 开始建/跑第一个子任务
