# Homodyne 采样（G 精确 + B 混合物）

## Goal

```text
homodyne_sample(state, mode=0, phi=0.0, *, rng=None) -> float
```

G：边缘高斯精确采样；B：实中心组件混合物采样（交叉不参与抽签）。**不**自动 condition（要条件另调 `homodyne_condition`）。

## Background

- 队列 ②；① 全复似然已归档
- 用户选 **B**（非 A 矩匹配单峰、非 C 一步 condition）

## Decisions

| # | 选择 |
|---|------|
| D1 | **B：G 精确 + B 实峰混合物** |
| D2 | API：`homodyne_sample` 各后端各一份（`gaussian` / `bosonic`），返回 `float` |
| D3 | `rng: np.random.Generator | None`；`None` → `np.random.default_rng()` |
| D4 | 无 `sample_and_condition` 本切片 |
| D5 | B：仅 `‖Im r̄‖_∞ ≤ tol` 且 `Re(w) > 0` 的组件入池；权 `p_k ∝ Re(w_k)` 归一 |

## Requirements

### R1 Gaussian

```text
μ = homodyne_mean(state, mode, phi)
σ² = homodyne_var(state, mode, phi)   # σ² > 0
outcome ~ N(μ, σ²)
```

### R2 Bosonic mixture

1. 过滤：实 `r̄`（`max|Im|≤tol`）且 `Re(w)>0`
2. `p_k = Re(w_k) / ∑ Re(w)`
3. 抽组件 k，再 `outcome ~ N(μ_k, σ_k²)`，`μ_k=u·Re(r̄_k)`, `σ_k²=uᵀ V_k u`
4. 无合格组件 → ValueError
5. 复交叉 **不** 进池（诚实：忽略干涉对边缘的修正）

### R3 文件

- `gaussian/observables.py` · `homodyne_sample`
- `bosonic/observables.py` · `homodyne_sample`
- 导出 `__init__.py`
- `tests/test_homodyne_sample.py`
- README + quality 一行

## Acceptance Criteria

- [x] **AC-S1** G 真空大样本 mean≈0、var≈0.5
- [x] **AC-S2** G 挤态 φ=0 var≈½e^{-2r}
- [x] **AC-S3** B `from_gaussian` 同 seed ≡ G（单组件跳过 choice）
- [x] **AC-S4** even cat 两侧峰都能采到
- [x] **AC-S5** 同 seed 可复现；pytest 74；UAT 6/6

## Out of Scope

- `sample_and_condition`
- Fock 采样；完整 cat 边缘（含交叉核）
- ③ Fock loss · ④ U8

## Notes

- 诚实：B 混合物 = 对角峰经典混合边缘，**非** 精确 |ψ⟩ 干涉边缘
- tol 默认 `1e-12`
