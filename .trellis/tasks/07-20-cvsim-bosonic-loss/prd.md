# Bosonic 光子损失通道

## Goal

Bosonic 补 **`loss(T)`**：逐组件 `V←XVXᵀ+Y`，`r̄←Xr̄`，**`w` 不变**。与 Gaussian `channels.loss` 同 X,Y 约定。

## Background

- Gaussian 已有 loss；Bosonic 有矩闭环无通道
- 用户选：补 Bosonic loss

## Decisions

| # | 决策 | 选择 |
|---|------|------|
| D1 | 公式 | 同 G：`X=√T`，`Y=(1-T)I/2` 作用模；`0≤T≤1` |
| D2 | API | `loss(state, T, mode=None)`；`mode=None` 全模 |
| D3 | 权重 | **w 不变**（高斯信道线性作用每组件） |

## Requirements

- **R1** `cvsim/bosonic/channels.py`（或 `gates` 旁薄模块）实现 `loss`
- **R2** 导出；`tests/test_bosonic_loss.py`
- **R3** 单组件 = `from_gaussian` + G `loss` 对照
- **R4** cat：`T=1` 恒等；`T=0` 回真空矩（⟨n⟩→0，var→½）；∑w 不变
- **R5** 全量 pytest + UAT 不破

## Acceptance Criteria

- [x] **AC-L1** `T=1`：V,r̄,w 不变
- [x] **AC-L2** 单组件相干 + loss：⟨n⟩≈T|α|² 对齐 Gaussian
- [x] **AC-L3** even cat + `T=0`：⟨n⟩≈0，Homodyne var≈½，∑w=1
- [x] **AC-L4** loss 后 `w` 列表与前相同
- [x] **AC-L5** pytest 51 绿；UAT 5/5

## Out of Scope

- 条件 Homodyne、GKP、Wigner
- 改 Gaussian / Fock
- 热浴放大

## Open Questions

无。实现可直接 mirror `gaussian/channels.py`。
