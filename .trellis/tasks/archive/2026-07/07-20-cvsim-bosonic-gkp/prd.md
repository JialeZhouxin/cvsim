# Bosonic 小截断 GKP 态

## Goal

`|0⟩_GKP` 最小物理近似 → `BosonicState`：

```text
x 轴齿 k=-N…N，间距 √(2π) → 窄高斯组件 → ∑w=1 → 矩可测
```

仅 0 码字；无 `|1⟩`、无二维格点、无 Wigner。

## Background

- 笔记 03 §4：理想 Dirac 梳；物理 = 窄齿 × 包络
- Bosonic 已有 Component / cat / 矩 / loss

## Decisions

| # | 决策 | 选择 |
|---|------|------|
| D1 | 态 | 仅 `\|0⟩_GKP` |
| D2 | 格点 | `x_k = k √(2π)`，`\|k\|≤N` |
| D3 | 档 | **A 最瘦**：仅 x 齿；公共 `V`；对角实权重；无 p 齿 / 无 cross |

## Requirements

### API

- **R1** `gkp0(epsilon: float = 0.1, grid_size: int = 3) -> BosonicState`
  - `epsilon` = 齿挤压参数 `ε∈(0,1]`（越小齿越尖）
  - `grid_size = N` → 组件数 `K = 2N+1`
- **R2** 每组件（ħ=1, xxpp, 单模）：
  - `r̄_k = (k √(2π), 0)`
  - `V = ½ diag(ε, 1/ε)`（尖 x、鼓 p；纯高斯 det V=1/4）
  - `w_k ∝ exp(−π ε k²)`，归一 `∑ w = 1`（实）
- **R3** `epsilon≤0` 或 `grid_size<0` → `ValueError`
- **R4** 导出 `cvsim.bosonic`；可选 `gkp.py`
- **R5** `tests/test_bosonic_gkp.py`；README / quality 一行
- **R6** 全量 pytest + UAT 不破

## Acceptance Criteria

- [x] **AC-G1** `N=3`：`K=7`，`|∑w−1|<1e-12`
- [x] **AC-G2** 相邻中心：`Δx = √(2π)`
- [x] **AC-G3** 同 `N`：小 ε → 更大 ⟨n⟩
- [x] **AC-G4** 门后 `w` 不变
- [x] **AC-G5** pytest 56 绿；UAT 5/5

## Out of Scope

- `|1⟩_GKP`、二维 (k,l) 格点、交叉项
- 自适应 amp_cutoff、Wigner 图
- 改 G/F

## Open Questions

无阻塞。包络 `exp(−π ε k²)` 为本任务约定（教学用；非唯一文献归一）。

## Notes

- det `½ε · ½/ε = 1/4` → 每齿纯高斯
- 无 cross → 是 **非相干/对角近似** 的物理 GKP 齿叠加，足够演示多峰；真纯态 GKP 需交叉项（后切片）
