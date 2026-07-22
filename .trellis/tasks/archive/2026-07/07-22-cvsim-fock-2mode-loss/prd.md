# β · G5 Fock 2 模 pure loss

## Goal

Fock **2 模** 纯损耗（真空环境）：一侧或两侧 → **2 模密度矩阵**。  
与 1 模 Kraus、G 单侧 loss 趋势对齐。**无新量子库。**

## Background

- 用户锁深化包 **β = G5**
- 现：`FockDensity` **仅 1 模**；`loss` 对 2 模 pure **raise**
- 1 模 Kraus：`E_k|n⟩=√C(n,k) T^{(n-k)/2} (1-T)^{k/2} |n-k⟩`

## Decisions

| # | 选择 |
|---|------|
| D0 | **扩展 `FockDensity`**：支持 `nmode∈{1,2}`；ρ 存 **展平** `(N^m, N^m)` |
| D1 | `loss(state, T, mode=None)`：1 模忽略 mode；2 模 `mode=0|1` 单侧，`None`=**两侧同 T** |
| D2 | 仅 **pure loss**（环境真空）；**无** Fock `nbar` |
| D3 | 输入：`FockState` 1\|2 模 pure，或已有 `FockDensity` 同 nmode |
| D4 | 2 模 ρ 上 **不做** 本切片门/Wigner/Homodyne；`mean_photon`/`trace`/`pnrd` 要可用 |
| D5 | 理论 MD 默认 **轻补或不改**（可选 01 一句多模 Kraus 积）；工程 README/未做表必改 |
| D6 | 无 Circuit；无 m≥3 |

## Physics

单侧作用在模 \(i\)：

\[
\rho'=\sum_k (E_k^{(i)})\,\rho\,(E_k^{(i)})^\dagger,\quad
E_k^{(0)}=E_k\otimes I,\quad
E_k^{(1)}=I\otimes E_k.
\]

两侧：\(\sum_{k,\ell}(E_k\otimes E_\ell)\rho(E_k\otimes E_\ell)^\dagger\)（或串行两次单侧，同 T 等价）。

## Requirements

### R1 表示

- `FockDensity(rho, nmode=1)` 默认兼容旧行为  
- `from_pure`：1 模 outer；2 模 `ravel` outer  
- `cutoff`：1 模 `shape[0]`；2 模 `isqrt(shape[0])`

### R2 loss API

```text
loss(state, T, mode=None) -> FockDensity
```

- 1 模：同现逻辑  
- 2 模 pure / 2 模 dens：按 mode 施加  

### R3 可观测量

- `trace` 任意 nmode  
- `mean_photon(state, mode=None)` 2 模 dens 按边际  
- `pnrd_probs`：2 模返回 `(N,N)` 联合或按 mode 边际（实现选一，文档写清）

### R4 测试

- T=1 2 模 pure → ρ 同 pure  
- \|10⟩ loss mode0：ρ 对角同 1 模 \|1⟩ loss；mode1 光子≈0  
- \|01⟩ loss mode0：近似不变（真空侧）  
- 相干⊗真空 mode0 loss：⟨n₀⟩≈T|α|²（高 N）  
- 旧 1 模测全绿  

## Acceptance Criteria

- [x] **AC1** 1 模回归全绿  
- [x] **AC2** 2 模单侧 loss 检查点过  
- [x] **AC3** 两侧 loss 可跑、Tr≈1  
- [x] **AC4** pytest **111**；UAT 8/8  
- [x] **AC5** README/USER_ACCEPTANCE 未做更新  

## Out of Scope

- Fock thermal nbar  
- 2 模 ρ 上门 / Homodyne / Wigner  
- m≥3  
- G9 / F condition  
- P2  

## Open（开工默认）

| 项 | 默认 |
|----|------|
| 两侧实现 | 串行 `loss(loss(s,T,0),T,1)` 或双指标；串行更短 |
| pnrd 2 模 | 联合 `reshape(N,N)` 从 diag |

## Notes

- 复杂度：单侧 \(O(N\cdot N^4)=O(N^5)\) 量级教学可接受（N~8–12 测）  
- 诚实：截断边界同 1 模
