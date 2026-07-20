# Fock 损耗通道（1 模 ρ）

## Goal

教学纯损耗 `loss(T)`：`0≤T≤1`，与 G/B 同约定。**仅 1 模**，用 `FockDensity` 存 ρ。

## Background

- 队列 ③；①② 已归档
- 用户：D1=A ρ；**D2=A1 仅 1 模**

## Decisions

| # | 选择 |
|---|------|
| D0 | ③ only；无 U8 |
| D1 | **A：`FockDensity`** |
| D2 | **A1：1 模 only** |
| D3 | API：`fock.loss(state, T) -> FockDensity`；`state` = `FockState`（1 模）或 `FockDensity` |
| D4 | 可观测量：`mean_photon` / `pnrd_probs` / `trace` 支持 ρ（最小集） |
| D5 | 物理：BS(√T) 与 vac 环境 + 偏迹；截断下数值近似 |

## Requirements

### R1 类型

```python
@dataclass
class FockDensity:
    rho: np.ndarray  # (N, N) complex, Hermitian≈
    # cutoff = N
```

- `from_pure(FockState)`：`ρ = |ψ⟩⟨ψ|`（要求 nmode=1）
- 2 模 `FockState` 进 `loss` → ValueError

### R2 loss

```text
# Kraus (beam-splitter model, vacuum env), truncated:
# E_k = √(binomial) * √T^{n-k} * √(1-T)^k * a^k / √(n…), or closed BS+trace
# Prefer: explicit Kraus for number basis (stable teaching form)

ρ' = Σ_k E_k ρ E_k†
```

最小闭式（推荐实现）：

对矩阵元 `ρ_{mn}` 用已知纯损耗振幅因子，或循环 Kraus：

```text
E_k |n⟩ = √C(n,k) (√T)^{n-k} (√(1-T))^k |n-k⟩   (k=0..n, n-k < N)
```

截断：仅 `n < N` 空间；环境 photon 超出截断丢弃（诚实注明）。

### R3 观测

- `trace(ρ)` / `mean_photon(ρ)` / `pnrd_probs(ρ)`
- 纯态路径保持原 `FockState` API 不变

### R4 文件

- `cvsim/fock/state.py` 或 `density.py`：`FockDensity`
- `cvsim/fock/channels.py`：`loss`
- 导出 + tests
- README / quality 一行

## Acceptance Criteria

- [x] **AC-F1** `T=1` 恒等
- [x] **AC-F2** `T=0` 真空
- [x] **AC-F3** `|1⟩` 对角公式
- [x] **AC-F4** 相干 `⟨n⟩≈T|α|²`
- [x] **AC-F5** raise + pytest 80 + UAT 6/6

## Out of Scope

- 2 模 ρ / 2 模 loss
- 热库、增益
- ρ 上门（D/R/S/Kerr on density）本片可不做
- ④ U8

## Notes

- 与 G：`⟨n⟩` 趋势同 `T`，非数值逐元素对齐
- 诚实：截断 Kraus 有边界误差
