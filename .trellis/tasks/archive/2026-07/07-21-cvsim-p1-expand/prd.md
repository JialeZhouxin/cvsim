# 三表示 P1 扩展战役（父）· 包 A

## Goal

**仅 G7 + G8**：Fock S₂ + 高斯热噪声通道。  
G5/G6/G9/G10 本战役 **Won't**。P2 硬外。

## Background

- 基线：pytest **90**；UAT **8/8**
- 用户锁 **包 A**

## Decisions

| # | 选择 |
|---|------|
| D0 | 父规划 + 两子任务独立验收 |
| D1 | **包 A = G7 + G8 only** |
| D2 | G5/G6/G9/G10 Won't this campaign |
| D3 | 串行：G8（易）→ G7，或并行；本会话可 G8 先 |
| D4 | 理论 MD 默认不动；工程 docs 在收口子任务或各自改 |
| D5 | ħ=1 xxpp；无新量子库 |

## Scope

### In

| ID | 子任务 slug（拟） | 交付 | 验收要点 |
|----|-------------------|------|----------|
| **G8** | `cvsim-thermal-channel` | G/B `thermal_loss` 或 `loss(..., nbar=)`：Y 可调 | 真空→热：⟨n⟩=n̄；T=1 恒等；B≡G 单组件 |
| **G7** | `cvsim-fock-s2` | Fock 2 模 `two_mode_squeeze` | 真空 S₂：⟨n_i⟩≈sinh²r（cutoff 够）；与 G 低阶矩对齐 |

### Won't

- G5 2 模 F loss · G6 F Homodyne · G9 GKP\|1⟩ · G10 HTML  
- P2 全项

## Campaign acceptance

- [x] G7、G8 子任务 archived
- [x] pytest **96**；UAT 8/8
- [x] USER_ACCEPTANCE 未做表更新

## Formula cards

### G8 · 热损耗（ħ=1）

纯损耗 = 环境真空。热环境平均光子 n̄≥0：

\[
X=\sqrt{T}\,I_{\mathrm{act}},\qquad
Y=(1-T)\Bigl(\bar n+\tfrac12\Bigr)I_{\mathrm{act}}.
\]

- n̄=0 → 现有 pure loss  
- T=1 → 恒等  
- 真空 T=0：V=(n̄+1/2)I 作用模；⟨n⟩=n̄

API 形态（子任务锁一）：

```text
# 推荐：扩展 loss 可选参数
loss(state, T, mode=None, nbar=0.0)
# 或新名 thermal_loss(state, T, nbar, mode=None)
```

### G7 · Fock S₂

与 symplectic 同生成元：  
\(S_2(r)=\exp[r(a_0^\dagger a_1^\dagger - a_0 a_1)]\)（实 r 教学形式；与 G 的 ch/sh xxpp 一致）。

实现：2 模截断矩阵指数，同 BS 套路 `kron` + `expm`。

检查点：

- r 小、cutoff≥20：`mean_photon(mode i) ≈ sinh²r`  
- 与 G `two_mode_squeeze` 总 ⟨n⟩ 差 < 截断容差

## Out of Scope

见 Won't + P2。

## Open（子任务内）

- G8：扩展 `loss` 的 `nbar` vs 新函数名  
- G7：仅 pure `FockState` 2 模，不做 2 模 ρ S₂

## Notes

- 子任务依赖：互相独立  
- 战役收口可轻：tests + README 矩阵 + 未做列表；**可不**强开 U10（可选）
